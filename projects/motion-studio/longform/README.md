# Long-form orchestration (V02, t-20261015-fec3)

Five-minute films from bounded shots, without touching the engine's safety
caps. This directory is the rig; `engine/longform.mjs` is the orchestrator;
`../engine/` still owns rendering and its per-shot limits (≤30 s, 2–900 frames).

## Install and run (rootless sandbox included)

```bash
cd projects/motion-studio
npm ci                                  # lockfile committed; playwright included
npx playwright install chromium         # browser binary (re-run after a snapshot wipe)
bash <repo>/../ytlab/tools/bootstrap-ffmpeg.sh   # static ffmpeg + chromium libs, no root
LD_LIBRARY_PATH=$HOME/chromium-libs \
FFMPEG_PATH=$HOME/bin/ffmpeg FFPROBE_PATH=$HOME/bin/ffprobe \
node longform/build.mjs --spec <spec.json> --work <dir> [--cache <dir>]
```

Notes from the calibration runs on a 2 vCPU / 2 GB box:
- `--work` and `--cache` must live on the **persistent disk**, never `/tmp`
  (tmpfs here is 992 MB; a five-minute 1080p run needs ~600 MB of shot cache).
- PNG frame scratch is deleted after each shot encodes (~2 GB peak otherwise).
- Throughput measured: ~10 fps at 1080p30 → a 300 s film ≈ 15–17 min render +
  ~40 s QC. `--max-old-space-size=768` keeps Node inside a 2 GB box.

## What the orchestrator guarantees

| property | mechanism |
|---|---|
| bounded shots | every shot goes through the engine's own `validateConfig` — caps preserved, never widened |
| resume | shots are content-hash cached (scene bytes + config + engine version); failed/partial shots are refused and re-rendered, never reused |
| no lost/duplicated material | concat total must equal the sum of shot durations (±0.5 s) |
| no filler/loops | any two byte-identical shots fail closed unless `spec.allowRepeatedShots.reason` is recorded (found by calibration run A itself) |
| A/V integrity | narration drift gate ≤1.0 s; never pads to fit |
| measured QC, fail closed | full-file decode, black/freeze with timecoded reasons, duration window, −16 LUFS ±1.5, TP ≤ −1 dBTP, 48 kHz |
| receipts | `film-manifest.json`: per-shot + final sha256, cache hits, loudness, wall time; grading field states it is engineering, not taste |

## Calibration evidence (labeled fixtures, not editorial films)

| run | result | artifact |
|---|---|---|
| A — 12×25 s, one demo reel, interrupted mid-shot-7 and relocated | qc-pass, 300.000000 s, sha256 `ebe4cd54…1d5e`, resume proven (6 cache hits, 6 re-rendered, 0 lost/duplicated); exposed the loop hole → guard added | storagecode `data/youtube-training/yt-training-s1/engineering/v02-calibration/` |
| B — 12×25 s distinct per-shot content + 300 s audio bed | qc-pass, 300.000000 s, sha256 `6acb039d…6055`, 12/12 distinct shot hashes, −15.9 LUFS, TP −11.8 dBFS, drift 0.000 s, decode exit 0 | storagecode (run-b receipt) |

Negative-test battery (all live, in `tests/longform.test.mjs` 7/7 and
`projects/youtube-training/tools/test_validate_delivery.py` 11/11): missing
scene · broken timing · duration-window violation · byte-identical shots ·
bogus repeat reason · corrupt media (truncated file fails full decode) ·
wrong hash · missing asset · owner-authored review · duplicate reviewer ·
stale review binding · <10 distinct finals at campaign close.
