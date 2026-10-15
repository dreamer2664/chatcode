#!/usr/bin/env python3
"""Tests for narrate.py — real ffmpeg audio, measured timings, real captions.

Voice audio is synthesised with ffmpeg (sine tones) so timing behaviour is
deterministic; the TTS engine is out of scope here. What IS under test is the
part that can silently ruin a film: cue boundaries, gap handling, caption
limits, loudness mastering and the fail-closed guards.
"""
import json, os, re, subprocess, sys, tempfile, unittest, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import narrate

FFMPEG = os.environ.get("FFMPEG_PATH", "ffmpeg")
FFPROBE = os.environ.get("FFPROBE_PATH", "ffprobe")

def tone(path, seconds, freq=220):
    subprocess.run([FFMPEG, "-y", "-v", "error", "-f", "lavfi",
                    "-i", f"sine=frequency={freq}:duration={seconds}", "-ar", "48000", path], check=True)

class NarrateTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="narrate-test-")
        self.audio = os.path.join(self.dir, "audio"); os.makedirs(self.audio)
        self.out = os.path.join(self.dir, "out")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def run_build(self, cues, default_gap=0.25, expect_fail=None):
        cpath = os.path.join(self.dir, "cues.json")
        with open(cpath, "w") as fh:
            json.dump(cues, fh)
        r = subprocess.run([sys.executable, os.path.join(HERE, "narrate.py"),
                            "--ffmpeg", FFMPEG, "--ffprobe", FFPROBE, "build",
                            "--cues", cpath, "--audio-dir", self.audio,
                            "--out", self.out, "--default-gap", str(default_gap)],
                           capture_output=True, text=True)
        if expect_fail:
            self.assertNotEqual(r.returncode, 0, f"expected failure, got: {r.stdout}")
            self.assertIn(expect_fail, r.stderr + r.stdout)
            return None
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.load(open(os.path.join(self.out, "narration-receipt.json")))

    def test_three_cues_produce_measured_timeline_and_valid_captions(self):
        for i, sec in enumerate([2.0, 3.0, 2.5]):
            tone(os.path.join(self.audio, f"c{i}.wav"), sec)
        cues = [
            {"id": "c0", "text": "Roman concrete gets stronger at sea."},
            {"id": "c1", "text": "Tiny cracks fill with new crystal growth."},
            {"id": "c2", "text": "Modern engineers want that trick back.", "gap_after": 0},
        ]
        rec = self.run_build(cues)
        self.assertEqual(rec["cues"], 3)
        self.assertEqual(rec["words"], 19)
        # timeline is arithmetic on measured durations: 2.0 + gap .25 + 3.0 + .25 + 2.5
        self.assertAlmostEqual(rec["plan"][0]["start"], 0.0, places=2)
        self.assertAlmostEqual(rec["plan"][1]["start"], 2.25, delta=0.05)
        self.assertAlmostEqual(rec["plan"][2]["start"], 5.50, delta=0.05)
        self.assertAlmostEqual(rec["bed_duration_s"], 8.0, delta=0.15)
        # loudness gate actually ran and passed
        self.assertAlmostEqual(rec["integrated_lufs"], -16.0, delta=1.5)
        self.assertLessEqual(rec["true_peak_dbfs"], -1.0 + 0.001)
        # captions: 3 numbered cues, monotonic, <=2 lines of <=42 chars
        srt = open(os.path.join(self.out, "final.srt")).read().strip().split("\n\n")
        self.assertEqual(len(srt), 3)
        prev_end = -1.0
        for i, block in enumerate(srt, 1):
            lines = block.split("\n")
            self.assertEqual(lines[0], str(i))
            m = re.match(r"(\d\d):(\d\d):(\d\d),(\d\d\d) --> (\d\d):(\d\d):(\d\d),(\d\d\d)", lines[1])
            self.assertTrue(m, f"bad SRT timestamp: {lines[1]}")
            secs = lambda g: int(g[0])*3600 + int(g[1])*60 + int(g[2]) + int(g[3])/1000
            start, end = secs(m.group(1, 2, 3, 4)), secs(m.group(5, 6, 7, 8))
            self.assertGreater(start, prev_end - 0.001, "cues must not overlap")
            prev_end = end
            body = lines[2:]
            self.assertLessEqual(len(body), 2)
            for l in body:
                self.assertLessEqual(len(l), 42, f"line too long: {l!r}")
        vtt = open(os.path.join(self.out, "final.vtt")).read()
        self.assertTrue(vtt.startswith("WEBVTT"))
        self.assertEqual(vtt.count("-->"), 3)
        # transcript is plain text of the script, no timestamps
        tr = open(os.path.join(self.out, "transcript.txt")).read()
        self.assertNotIn("-->", tr)
        self.assertEqual(len(tr.split()), 19)

    def test_missing_audio_fails_closed(self):
        tone(os.path.join(self.audio, "c0.wav"), 1.5)
        self.run_build([{"id": "c0", "text": "Present."}, {"id": "ghost", "text": "Absent."}],
                       expect_fail="no audio file")

    def test_too_fast_caption_is_refused_not_stretched(self):
        # 1 second of audio carrying 120 characters => way over the 20 c/s cap
        tone(os.path.join(self.audio, "fast.wav"), 1.0)
        long_text = " ".join(["word"] * 16)  # 79 chars in 1.0 s = 79 c/s, still fits 2 lines
        self.run_build([{"id": "fast", "text": long_text}], expect_fail="exceeds hard cap")

    def test_overlong_cue_is_refused_for_splitting(self):
        tone(os.path.join(self.audio, "c0.wav"), 6.0)
        # >84 chars cannot fit two 42-char lines
        text = "This caption line is deliberately far too long to ever fit inside two lines of forty-two characters each"
        self.run_build([{"id": "c0", "text": text}], expect_fail="split it")

    def test_short_cue_pads_the_gap_not_the_audio(self):
        tone(os.path.join(self.audio, "tiny.wav"), 0.4)
        tone(os.path.join(self.audio, "next.wav"), 1.5)
        rec = self.run_build([{"id": "tiny", "text": "Yes."}, {"id": "next", "text": "And so it goes on."}])
        self.assertGreaterEqual(rec["plan"][0]["gap_end"] - rec["plan"][0]["start"], 1.0 - 0.001)
        self.assertAlmostEqual(rec["plan"][0]["duration"], 0.4, delta=0.05)  # audio untouched
        self.assertGreaterEqual(rec["plan"][1]["start"], 1.0 - 0.001)

    def test_receipt_hashes_match_the_files_on_disk(self):
        tone(os.path.join(self.audio, "c0.wav"), 1.2)
        rec = self.run_build([{"id": "c0", "text": "Hashes must be real."}])
        for key, fname in (("bed", "bed.wav"),):
            self.assertEqual(rec["bed_sha256"], narrate.sha256_file(os.path.join(self.out, fname)))
        self.assertEqual(rec["captions"]["srt"], narrate.sha256_file(os.path.join(self.out, "final.srt")))
        self.assertEqual(rec["captions"]["vtt"], narrate.sha256_file(os.path.join(self.out, "final.vtt")))

if __name__ == "__main__":
    unittest.main(verbosity=2)
