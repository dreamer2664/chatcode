# S5 — evidence package (t-20261011-b0cb)

Everything here was produced tonight on the official suites
(`tools/make_suites.py --seed 1`, 100 easy + 100 hard, deterministic hash
`b2c460d2fb5a`), through the official harness (`bench.py`, integer bar
arithmetic, galleries on, no rounding anywhere). "NOT CLEARED" is a
statement of fact about the bar, not a draft number.

## The bar and today's readers

JOBS.md: **easy ≥ 98/100, hard ≥ 95/100, three consecutive runs.**

| reader | easy | hard | runs | stability | verdict |
|---|---|---|---|---|---|
| main `reader.py` (pre-S1, for reference) | 2/100 | 1/100 | 3 | stable (identical) | NOT CLEARED |
| S1 classic floor (merged `8a0056a`) | 22/100 | 6/100 | 3 | **identical across runs** (22/100 easy, 6/100 hard, 22/100 easy, 6/100 hard, 22/100 easy, 6/100 hard) | NOT CLEARED |
| S2 glyph CNN (merged `01394ee`, #11) | 29/100 | 6/100 | 3 | **29/29/29, 6/6/6 — identical** | NOT CLEARED |

Latency context: CNN median 0.29 s/image; classic floor median 5.2 s
(p95 7.4 s); main reader ~9 s under auto (see the S4 demo report).

## Artifacts (this folder)

- `three-run-proof-baseline.md` + `20261011T205614Z-*.json` — main reader, 3 runs, 2/100 / 1/100.
- `three-run-proof-cnn.md` + `20261011T2239*.json` + `20261011T2240*.json` + `20261011T2241*.json` — CNN, 3 runs, stable 29/6.
- `three-run-proof-s1.md` + `20261011T*-*.json` — classic floor, 3 runs, stable 22/100 easy, 6/100 hard, 22/100 easy, 6/100 hard, 22/100 easy, 6/100 hard.
- Galleries: inside each run's `gallery/` directory in the run archives on the producing machines; failure ids and the per-family tables are in every run JSON.

## The honest reading for the epic

1. The **machinery** is done: deterministic suites, a harness that cannot
   round a pass into existence (certified hostile-side on PR #10), a
   one-command truth proof, galleries kept by default.
2. The **bar is not met** by any reader merged tonight — not close on
   hard (best 6/100). The remaining distance is segmentation on the
   zero-wall families (collage, corrosion, cross-shadow, darts, and the
   layout families), which S6's held-out replay showed combining and
   preprocessing do not touch.
3. Every number links to a re-runnable command; no number in this package
   was picked, smoothed, or selected per family.

Re-run everything:

```bash
python3 tools/make_suites.py --seed 1
python3 tools/three_run_proof.py --reader "python3 baseline.py {image}"            # S1
python3 tools/three_run_proof.py --reader "python3 readers/cnn_reader.py --image {image}"  # S2
```
