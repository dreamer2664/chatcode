#!/usr/bin/env python3
"""Tests for validate_delivery.py — every check gets a real file, not a mock.

Media is generated with the same ffmpeg the validator will use (FFMPEG_PATH),
so 'full decode' and 'duration' checks run against actual H.264 bytes.
The duration window is overridden to [1,3] because a real 300 s film in a unit
test would be dishonest padding; the window mechanism itself is what's tested
here (the 300–330 rule is exercised by the V02 calibration runs).
"""
import copy, json, os, subprocess, sys, tempfile, unittest, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import validate_delivery as vd

FFMPEG = os.environ.get("FFMPEG_PATH", "ffmpeg")
FFPROBE = os.environ.get("FFPROBE_PATH", "ffprobe")

def make_clip(path, seconds=2, corrupt=False, seed=None):
    # distinct frame count => distinct bytes => distinct sha256 (no seed option
    # in this ffmpeg's testsrc2, and identical inputs hash identically)
    if seed is not None:
        seconds = seconds + seed * 0.04
    subprocess.run([FFMPEG, "-y", "-v", "error", "-f", "lavfi",
                    "-i", f"testsrc2=size=320x180:rate=30:duration={seconds}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", path], check=True)
    if corrupt:
        with open(path, "r+b") as f:
            f.seek(2000)
            f.truncate()  # cut mid-stream: first frames decode, the file does not

class ValidatorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp(prefix="vd-test-")
        cls.final = os.path.join(cls.dir, "final.mp4")
        make_clip(cls.final)
        cls.final_sha = vd.sha256_file(cls.final)
        for name in ("final.srt", "final.vtt", "final.txt"):
            with open(os.path.join(cls.dir, name), "w") as f:
                f.write(f"placeholder {name}\n")
        cls.base = {
            "slot": "YT01", "campaign": "yt-training-s1", "owner": "scipio",
            "final": {"file": "final.mp4", "sha256": cls.final_sha},
            "captions": {
                "srt": {"file": "final.srt", "sha256": vd.sha256_file(os.path.join(cls.dir, "final.srt"))},
                "vtt": {"file": "final.vtt", "sha256": vd.sha256_file(os.path.join(cls.dir, "final.vtt"))},
                "transcript": {"file": "final.txt", "sha256": vd.sha256_file(os.path.join(cls.dir, "final.txt"))},
            },
            "reviews": [
                {"reviewer": "vesta", "sha256": cls.final_sha, "verdict": "accept"},
                {"reviewer": "cormac", "sha256": cls.final_sha, "verdict": "accept"},
            ],
        }

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def check(self, man, lo=1.0, hi=3.0):
        return vd.validate_manifest(man, self.dir, FFPROBE, FFMPEG, (lo, hi))

    def msgs(self, findings):
        return " | ".join(m for _, m in findings)

    def test_good_manifest_passes(self):
        ok, f = self.check(copy.deepcopy(self.base))
        self.assertTrue(ok, self.msgs(f))

    def test_missing_asset_fails(self):
        man = copy.deepcopy(self.base)
        man["captions"]["srt"]["file"] = "nope.srt"
        ok, f = self.check(man)
        self.assertFalse(ok)
        self.assertIn("file missing on disk", self.msgs(f))

    def test_wrong_hash_fails(self):
        man = copy.deepcopy(self.base)
        man["final"]["sha256"] = "0" * 64
        ok, f = self.check(man)
        self.assertFalse(ok)
        self.assertIn("sha256 mismatch", self.msgs(f))

    def test_owner_review_fails(self):
        man = copy.deepcopy(self.base)
        man["reviews"][0]["reviewer"] = "scipio"  # the owner reviews their own film
        ok, f = self.check(man)
        self.assertFalse(ok)
        self.assertIn("owner-authored", self.msgs(f))

    def test_duplicate_reviewer_fails(self):
        man = copy.deepcopy(self.base)
        man["reviews"][1]["reviewer"] = "vesta"
        ok, f = self.check(man)
        self.assertFalse(ok)
        self.assertIn("DISTINCT", self.msgs(f))

    def test_stale_review_binding_fails(self):
        man = copy.deepcopy(self.base)
        man["reviews"][1]["sha256"] = "f" * 64  # reviewed an older cut
        ok, f = self.check(man)
        self.assertFalse(ok)
        self.assertIn("stale binding", self.msgs(f))

    def test_single_review_fails(self):
        man = copy.deepcopy(self.base)
        man["reviews"] = man["reviews"][:1]
        ok, f = self.check(man)
        self.assertFalse(ok)
        self.assertIn("2 distinct", self.msgs(f))

    def test_reject_verdict_fails(self):
        man = copy.deepcopy(self.base)
        man["reviews"][1]["verdict"] = "reject"
        ok, f = self.check(man)
        self.assertFalse(ok)
        self.assertIn("verdict is reject", self.msgs(f))

    def test_duration_window_enforced(self):
        ok, f = self.check(copy.deepcopy(self.base), lo=300.0, hi=330.0)
        self.assertFalse(ok)
        self.assertIn("outside [300.0,330.0]", self.msgs(f))

    def test_corrupt_media_fails_full_decode(self):
        bad = os.path.join(self.dir, "corrupt.mp4")
        make_clip(bad, corrupt=True)
        man = copy.deepcopy(self.base)
        man["final"] = {"file": "corrupt.mp4", "sha256": vd.sha256_file(bad)}
        for r in man["reviews"]:
            r["sha256"] = man["final"]["sha256"]
        ok, f = self.check(man)
        self.assertFalse(ok)
        self.assertIn("full-file decode failed", self.msgs(f))
        os.unlink(bad)

    def test_campaign_close_needs_ten_distinct_finals(self):
        idx_dir = tempfile.mkdtemp(prefix="vd-idx-")
        try:
            deliveries = []
            for i in range(9):  # only nine distinct films
                name = f"f{i}.mp4"
                make_clip(os.path.join(self.dir, name), seconds=1, seed=i)
                m = copy.deepcopy(self.base)
                m["final"] = {"file": name, "sha256": vd.sha256_file(os.path.join(self.dir, name))}
                mp = os.path.join(idx_dir, f"m{i}.json")
                with open(mp, "w") as fh:
                    json.dump(m, fh)
                deliveries.append({"slot": f"YT{i:02d}", "manifest": mp, "assets_dir": self.dir})
            # the tenth 'film' is film #0 renamed — same hash, must not count
            dup = copy.deepcopy(deliveries[0])
            dup["slot"] = "YT09"
            deliveries.append(dup)
            idx = os.path.join(idx_dir, "index.json")
            with open(idx, "w") as fh:
                json.dump({"deliveries": deliveries}, fh)
            ok, n, problems = vd.campaign_close(idx, self.dir)
            self.assertFalse(ok)
            self.assertEqual(n, 9)
            self.assertTrue(any("identical" in p for p in problems))
            self.assertTrue(any("NOT DONE" in p for p in problems))
        finally:
            shutil.rmtree(idx_dir, ignore_errors=True)

if __name__ == "__main__":
    unittest.main(verbosity=2)
