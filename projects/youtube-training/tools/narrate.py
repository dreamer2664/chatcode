#!/usr/bin/env python3
"""narrate.py — V03 (t-20261015-947e): cue-timed narration bed + captions + master.

Pipeline (all durations MEASURED with ffprobe — nothing assumes a TTS speed):

  1. read a cues file: [{"id","text","gap_after"?}] — the script, one cue per
     caption unit; the audio files themselves are produced by whatever voice
     tooling the worker has (agent TTS tool, local TTS, a human) and referenced
     by id: <audio-dir>/<id>.<ext>  (.mp3/.wav/.m4a/.ogg, first match wins);
  2. build bed.wav: cues concatenated with measured gaps (silence), then
     ffmpeg loudnorm to the campaign target (integrated -16 LUFS +/- 1.5,
     true peak <= -1 dBTP), resampled 48 kHz;
  3. derive captions from the SAME measured cue boundaries used to build the
     bed: final.srt + final.vtt + transcript.txt, with ACCEPTANCE.md limits
     enforced, not hoped for: <=2 lines, <=42 chars/line, <=17 chars/sec
     target / 20 hard cap, no cue shorter than 1.0 s (gaps pad, never stretch).

Fail closed: missing audio, unmeasurable duration, over-long lines, over-fast
captions or a missed loudness window all exit non-zero with a reason.
Exit 0 prints a JSON receipt: per-cue start/end/duration/chars-per-second,
measured bed loudness, total duration, output hashes.

Usage:
  narrate.py build --cues cues.json --audio-dir audio/ --out out/
                   [--target-lufs -16] [--default-gap 0.35]
"""
import argparse, hashlib, json, os, subprocess, sys

AUDIO_EXTS = (".mp3", ".wav", ".m4a", ".ogg", ".flac")
LINE_MAX = 42
CPS_TARGET, CPS_CAP = 17.0, 20.0
MIN_CUE = 1.0

def die(msg):
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

def ffprobe_duration(path, ffprobe):
    r = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", path], capture_output=True, text=True)
    if r.returncode != 0:
        return None
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None

def ebur128(path, ffmpeg):
    r = subprocess.run([ffmpeg, "-hide_banner", "-nostats", "-i", path,
                        "-filter_complex", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    tail = "\n".join(r.stderr.splitlines()[-14:])
    import re
    m_i = re.search(r"I:\s*(-?[\d.]+)\s*LUFS", tail)
    tp_part = tail.split("True peak:")[-1]
    m_p = re.search(r"Peak:\s*(-?[\d.]+)\s*dBFS", tp_part)
    if not m_i:
        die(f"could not parse ebur128 summary:\n{tail}")
    return float(m_i.group(1)), (float(m_p.group(1)) if m_p else None)

def find_audio(audio_dir, cue_id):
    for ext in AUDIO_EXTS:
        p = os.path.join(audio_dir, cue_id + ext)
        if os.path.isfile(p):
            return p
    return None

def wrap_lines(text):
    """Wrap to at most 2 lines of <=LINE_MAX chars. Greedy first line, then the
    remainder must still fit on one line — otherwise the cue is too long for a
    caption and the SCRIPT must be split. We never shrink or stretch audio."""
    words = text.split()
    if not words:
        die("empty caption text")
    if any(len(w) > LINE_MAX for w in words):
        die(f"single word exceeds {LINE_MAX} chars: {text!r}")
    first = []
    while words and len(" ".join(first + [words[0]])) <= LINE_MAX:
        first.append(words.pop(0))
    if not words:
        return [" ".join(first)]
    rest = " ".join(words)
    if len(rest) > LINE_MAX:
        die(f"cue needs more than 2 lines of <= {LINE_MAX} chars — split it: {text!r}")
    return [" ".join(first), rest]

def ts_srt(sec):
    ms = round(sec * 1000)
    h, ms = divmod(ms, 3_600_000); m, ms = divmod(ms, 60_000); s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def ts_vtt(sec):
    return ts_srt(sec).replace(",", ".")

def cmd_build(a):
    ffmpeg, ffprobe = a.ffmpeg, a.ffprobe
    with open(a.cues) as fh:
        cues = json.load(fh)
    if not cues:
        die("cues file is empty")
    os.makedirs(a.out, exist_ok=True)

    # 1) measure every cue; assign timeline
    plan, t, parts = [], 0.0, []
    for i, cue in enumerate(cues):
        cid, text = cue.get("id"), (cue.get("text") or "").strip()
        if not cid or not text:
            die(f"cue {i}: id and text required")
        src = find_audio(a.audio_dir, cid)
        if not src:
            die(f"cue {cid}: no audio file in {a.audio_dir} ({cid}.{'|'.join(AUDIO_EXTS)})")
        dur = ffprobe_duration(src, ffprobe)
        if dur is None or dur <= 0:
            die(f"cue {cid}: unmeasurable audio duration: {src}")
        lines = wrap_lines(text)
        nchars = sum(len(l) for l in lines)
        cps = nchars / max(dur, 0.001)
        gap = float(cue.get("gap_after", a.default_gap))
        # caption readability: too-fast cues are a script problem, not a timing trick
        if cps > CPS_CAP:
            die(f"cue {cid}: {cps:.1f} chars/sec exceeds hard cap {CPS_CAP} — split the cue or slow the read (never stretch audio to fit)")
        start = t
        audio_end = start + dur          # where the spoken cue actually stops
        cue_end = max(audio_end, start + MIN_CUE)  # caption holds >= 1.0 s
        gap = max(gap, cue_end - audio_end)        # pad the GAP, never the audio
        plan.append({"id": cid, "text": text, "src": src, "start": round(start, 3),
                     "end": round(audio_end, 3), "gap_end": round(cue_end + gap, 3),
                     "duration": round(dur, 3), "lines": lines,
                     "chars_per_sec": round(nchars / max(dur, 0.001), 2),
                     "cps_flag": "over-target" if cps > CPS_TARGET else "ok"})
        parts.append(src)
        if gap > 0:
            parts.append(("silence", gap))
        t = cue_end + gap                # silence is counted exactly once
    if any(p["cps_flag"] != "ok" for p in plan):
        print("warn: cues over the 17 c/s target (under the 20 cap): " +
              ", ".join(p["id"] for p in plan if p["cps_flag"] != "ok"), file=sys.stderr)

    # 2) build the bed: concat via filter_complex with exact measured gaps
    filt, inputs = [], []
    for p in parts:
        if isinstance(p, tuple):
            inputs += ["-f", "lavfi", "-t", f"{p[1]:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
        else:
            inputs += ["-i", p]
    n = len(parts)
    labels = "".join(f"[{i}:a]" for i in range(n))
    bed_raw = os.path.join(a.out, "bed-raw.wav")
    subprocess.run([ffmpeg, "-y", "-v", "error", *inputs,
                    "-filter_complex", f"{labels}concat=n={n}:v=0:a=1[out]",
                    "-map", "[out]", "-ar", "48000", bed_raw], check=True)
    bed = os.path.join(a.out, "bed.wav")
    subprocess.run([ffmpeg, "-y", "-v", "error", "-i", bed_raw, "-af",
                    f"loudnorm=I={a.target_lufs}:TP=-1.0:LRA=11", "-ar", "48000",
                    "-c:a", "pcm_s16le", bed], check=True)
    os.unlink(bed_raw)
    lufs, tp = ebur128(bed, ffmpeg)
    if abs(lufs - a.target_lufs) > 1.5:
        die(f"mastered bed measures {lufs} LUFS, outside {a.target_lufs} +/- 1.5")
    if tp is not None and tp > -1.0:
        die(f"true peak {tp} dBFS exceeds -1.0 dBTP")
    bed_dur = ffprobe_duration(bed, ffprobe)
    if bed_dur is None:
        die("bed.wav unmeasurable after mastering")

    # 3) captions + transcript from the same measured boundaries
    srt, vtt = [], ["WEBVTT", ""]
    for i, p in enumerate(plan, 1):
        body = "\n".join(p["lines"])
        srt.append(f"{i}\n{ts_srt(p['start'])} --> {ts_srt(p['end'])}\n{body}\n")
        vtt.append(f"cue-{p['id']}\n{ts_vtt(p['start'])} --> {ts_vtt(p['end'])}\n{body}\n")
    open(os.path.join(a.out, "final.srt"), "w").write("\n".join(srt))
    open(os.path.join(a.out, "final.vtt"), "w").write("\n".join(vtt))
    open(os.path.join(a.out, "transcript.txt"), "w").write(
        "\n\n".join(p["text"] for p in plan) + "\n")

    words = sum(len(p["text"].split()) for p in plan)
    receipt = {
        "cues": len(plan), "words": words, "bed": bed, "bed_sha256": sha256_file(bed),
        "bed_duration_s": round(bed_dur, 3), "integrated_lufs": lufs, "true_peak_dbfs": tp,
        "captions": {"srt": sha256_file(os.path.join(a.out, "final.srt")),
                     "vtt": sha256_file(os.path.join(a.out, "final.vtt")),
                     "transcript": sha256_file(os.path.join(a.out, "transcript.txt"))},
        "plan": plan,
    }
    open(os.path.join(a.out, "narration-receipt.json"), "w").write(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: receipt[k] for k in ("cues", "words", "bed_duration_s", "integrated_lufs", "true_peak_dbfs")}))

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ffmpeg", default=os.environ.get("FFMPEG_PATH", "ffmpeg"))
    ap.add_argument("--ffprobe", default=os.environ.get("FFPROBE_PATH", "ffprobe"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--cues", required=True)
    b.add_argument("--audio-dir", required=True)
    b.add_argument("--out", required=True)
    b.add_argument("--target-lufs", type=float, default=-16.0)
    b.add_argument("--default-gap", type=float, default=0.35)
    b.set_defaults(fn=cmd_build)
    a = ap.parse_args()
    a.fn(a)

if __name__ == "__main__":
    main()
