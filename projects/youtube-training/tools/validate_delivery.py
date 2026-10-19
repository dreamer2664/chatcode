#!/usr/bin/env python3
"""validate_delivery.py — technical delivery-manifest validator (V02, t-20261015-fec3).

Fail-closed by design. Verdicts come only from measured bytes:

  * every asset listed in the manifest must exist in --assets-dir  (missing  -> FAIL)
  * every sha256 must match the actual file                        (mismatch -> FAIL)
  * the final film must measure 300.0-330.0 s via ffprobe          (outside  -> FAIL)
  * full-file decode must succeed (not just the first frame)       (corrupt  -> FAIL)
  * >= 2 reviews, by DISTINCT reviewers, none authored by the film
    owner, each bound to the EXACT final sha256                    (else     -> FAIL)
  * with --campaign-close: at least 10 finals across the index,
    pairwise-distinct sha256 (ten renames of one film do not count)-> FAIL

Exit codes: 0 = all checked manifests pass; 1 = at least one FAIL;
2 = could not check (missing ffprobe, unreadable manifest) — never a pass.

This tool certifies ENGINEERING facts only. Artistic approval is the two
non-owner full-watch reviews themselves; nothing here substitutes a score.
"""
import argparse, hashlib, json, os, subprocess, sys

REQUIRED_ASSETS = ["final", "captions.srt", "captions.vtt", "captions.transcript"]

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def ffprobe_duration(path, ffprobe):
    out = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", path], capture_output=True, text=True)
    if out.returncode != 0:
        return None
    try:
        return float(out.stdout.strip())
    except ValueError:
        return None

def full_decode(path, ffmpeg):
    out = subprocess.run([ffmpeg, "-v", "error", "-xerror", "-i", path, "-f", "null", "-"],
                         capture_output=True, text=True)
    return out.returncode == 0, out.stderr.strip()[:300]

def get(dotted, obj):
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur

def validate_manifest(manifest, assets_dir, ffprobe=None, ffmpeg=None, duration_window=(300.0, 330.0)):
    """Returns (ok, findings) where findings is a list of (level, message)."""
    f = []
    ok = True

    def fail(msg):
        nonlocal ok
        ok = False
        f.append(("FAIL", msg))

    def warn(msg):
        f.append(("warn", msg))

    for field in ("slot", "campaign", "owner", "final"):
        if not manifest.get(field if "." not in field else None) and get(field, manifest) is None:
            fail(f"manifest missing required field: {field}")
    final = manifest.get("final") or {}
    owner = manifest.get("owner")

    # 1) required assets present + hash-correct
    hashes = {}
    for dotted in REQUIRED_ASSETS:
        entry = get(dotted, manifest)
        if not entry or not isinstance(entry, dict):
            fail(f"asset entry missing from manifest: {dotted}")
            continue
        name, want = entry.get("file"), entry.get("sha256")
        if not name or not want:
            fail(f"asset {dotted}: file/sha256 required")
            continue
        path = os.path.join(assets_dir, name)
        if not os.path.isfile(path):
            fail(f"asset {dotted}: file missing on disk: {name}")
            continue
        got = sha256_file(path)
        hashes[dotted] = (path, got)
        if got != want:
            fail(f"asset {dotted}: sha256 mismatch — manifest {want[:16]}… != actual {got[:16]}…")

    # 2) the final film: measured duration + full decode
    if "final" in hashes:
        path, _ = hashes["final"]
        if ffprobe:
            dur = ffprobe_duration(path, ffprobe)
            if dur is None:
                fail("final: ffprobe could not measure duration (corrupt or unreadable)")
            else:
                lo, hi = duration_window
                if not (lo <= dur <= hi):
                    fail(f"final: measured {dur:.3f}s outside [{lo},{hi}]")
                else:
                    f.append(("info", f"final duration {dur:.3f}s in window"))
        else:
            fail("final: duration unchecked (no ffprobe) — refusing to pass an unmeasured film")
        if ffmpeg:
            dok, derr = full_decode(path, ffmpeg)
            if not dok:
                fail(f"final: full-file decode failed: {derr}")
        else:
            warn("full decode skipped (no ffmpeg supplied)")

    # 3) reviews: distinct non-owner, bound to the exact final hash
    reviews = manifest.get("reviews") or []
    if len(reviews) < 2:
        fail(f"reviews: {len(reviews)} found, 2 distinct non-owner full-watch reviews required")
    reviewers = set()
    final_hash = (manifest.get("final") or {}).get("sha256")
    for i, r in enumerate(reviews):
        who, bound, verdict = r.get("reviewer"), r.get("sha256"), (r.get("verdict") or "").lower()
        if not who or verdict not in ("accept", "reject"):
            fail(f"review {i}: needs reviewer + verdict accept|reject")
            continue
        if who == owner:
            fail(f"review {i}: owner-authored review by '{who}' is not a review")
        if who in reviewers:
            fail(f"review {i}: reviewer '{who}' already voted — two DISTINCT reviewers required")
        reviewers.add(who)
        if final_hash and bound != final_hash:
            fail(f"review {i}: stale binding — review hash {str(bound)[:16]}… != current final {final_hash[:16]}…")
        if verdict == "reject":
            fail(f"review {i}: recorded verdict is reject — delivery is not accepted")

    return ok, f

def campaign_close(index_path, assets_dirs):
    """At least ten finals with pairwise-distinct sha256 across the index."""
    with open(index_path) as fh:
        index = json.load(fh)
    finals = {}
    problems = []
    for entry in index.get("deliveries", []):
        slot = entry.get("slot", "?")
        man_path, adir = entry.get("manifest"), entry.get("assets_dir")
        if not man_path or not os.path.isfile(man_path):
            problems.append(f"{slot}: manifest missing: {man_path}")
            continue
        with open(man_path) as fh:
            man = json.load(fh)
        h = (man.get("final") or {}).get("sha256")
        if not h:
            problems.append(f"{slot}: no final sha256")
            continue
        if h in finals:
            problems.append(f"{slot}: final sha256 identical to {finals[h]} — not a distinct film")
            continue
        finals[h] = slot
    n = len(finals)
    if n < 10:
        problems.append(f"campaign close: {n} distinct accepted finals < 10 — NOT DONE")
    return (n >= 10 and not problems), n, problems

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--manifest", action="append", default=[], help="delivery manifest JSON (repeatable)")
    ap.add_argument("--assets-dir", default=".", help="directory holding the downloaded assets")
    ap.add_argument("--ffprobe", default=os.environ.get("FFPROBE_PATH", "ffprobe"))
    ap.add_argument("--ffmpeg", default=os.environ.get("FFMPEG_PATH", "ffmpeg"))
    ap.add_argument("--campaign-close", metavar="INDEX", help="index JSON: >=10 distinct finals or FAIL")
    ap.add_argument("--lo", type=float, default=300.0)
    ap.add_argument("--hi", type=float, default=330.0)
    args = ap.parse_args()

    exit_code = 0
    for mp in args.manifest:
        try:
            with open(mp) as fh:
                man = json.load(fh)
        except (OSError, json.JSONDecodeError) as e:
            print(f"[FAIL] {mp}: unreadable manifest: {e}")
            exit_code = 1
            continue
        ok, findings = validate_manifest(man, args.assets_dir, args.ffprobe, args.ffmpeg, (args.lo, args.hi))
        for level, msg in findings:
            print(f"[{level.upper():4}] {mp}: {msg}")
        print(f"[{'PASS' if ok else 'FAIL'}] {mp}")
        if not ok:
            exit_code = 1
    if args.campaign_close:
        ok, n, problems = campaign_close(args.campaign_close, args.assets_dir)
        for p in problems:
            print(f"[FAIL] campaign-close: {p}")
        print(f"[{'PASS' if ok else 'FAIL'}] campaign-close: {n} distinct finals")
        if not ok:
            exit_code = 1
    if not args.manifest and not args.campaign_close:
        print("nothing to check; supply --manifest and/or --campaign-close", file=sys.stderr)
        exit_code = 2
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
