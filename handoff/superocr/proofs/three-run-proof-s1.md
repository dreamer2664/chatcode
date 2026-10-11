# three-run proof — superocr (S5, t-20261011-b0cb)

> MERGED-MAIN RUN (8a0056a: S1 baseline + S4 demo): the classic floor measured through the official harness, three consecutive runs. Acceptance proof for the 98/95 bar: NOT met — this is the truth report as of tonight.

- produced: 20261011T223845Z (UTC) · commit `8a0056a32816`
- reader: `python3 baseline.py {image}`
- suites: `/tmp/vh5/data` · seed 1 · bars easy >= 98%, hard >= 95%
- runs: 3 consecutive full passes · raw reports + galleries: `reports/three-run-20261011T223845Z/`
- bench's own stability file: `20261011T223845Z-stability.json`
- all items excluded in a suite means nothing was scored; excluded ids are listed per suite (0 across runs)

## The claim

**NOT CLEARED.** At least one run missed at least one bar. The numbers below are the truth as measured, not a draft. Re-run this proof when stronger readers land; the gap is named per line.

- run 1: easy 22/100 = 22.0% < bar 98%
- run 1: hard 6/100 = 6.0% < bar 95%
- run 2: easy 22/100 = 22.0% < bar 98%
- run 2: hard 6/100 = 6.0% < bar 95%
- run 3: easy 22/100 = 22.0% < bar 98%
- run 3: hard 6/100 = 6.0% < bar 95%

## the runs

| run | easy (bar 98) | hard (bar 95) | verdict | slowest p95 |
|---|---|---|---|---|
| 1 | 22/100 (22.0%) NO | 6/100 (6.0%) NO | FAIL | 7.91s |
| 2 | 22/100 (22.0%) NO | 6/100 (6.0%) NO | FAIL | 7.53s |
| 3 | 22/100 (22.0%) NO | 6/100 (6.0%) NO | FAIL | 8.35s |

## by family (last run) — and how far each moved across runs

| suite/family | correct (last run) | total | across runs |
|---|---|---|---|
| easy/easy | 22 | 100 | 22 / 22 / 22 |
| hard/collage | 0 | 8 | 0 / 0 / 0 |
| hard/corrosion | 0 | 8 | 0 / 0 / 0 |
| hard/cross-shadow | 0 | 8 | 0 / 0 / 0 |
| hard/cut | 2 | 8 | 2 / 2 / 2 |
| hard/dark-on-dark | 0 | 8 | 0 / 0 / 0 |
| hard/darts | 0 | 8 | 0 / 0 / 0 |
| hard/obstruction | 1 | 8 | 1 / 1 / 1 |
| hard/snow | 1 | 9 | 1 / 1 / 1 |
| hard/spiderweb | 1 | 9 | 1 / 1 / 1 |
| hard/split | 0 | 9 | 0 / 0 / 0 |
| hard/stitch | 1 | 9 | 1 / 1 / 1 |
| hard/strippy | 0 | 8 | 0 / 0 / 0 |

## the ugly cases (gallery)

- run 1 easy: 78 failure(s) — gallery `/tmp/vh5/reports/three-run-20261011T223845Z/gallery/20261011T223845Z-easy-hard-r1of3/easy` — first: easy-0000, easy-0001, easy-0002, easy-0003, easy-0004, easy-0005, easy-0006, easy-0007, easy-0009, easy-0010 …
- run 1 hard: 94 failure(s) — gallery `/tmp/vh5/reports/three-run-20261011T223845Z/gallery/20261011T223845Z-easy-hard-r1of3/hard` — first: snow-0000, spiderweb-0000, split-0000, stitch-0000, strippy-0000, cut-0000, collage-0000, corrosion-0000, cross-shadow-0000, darts-0000 …
- run 2 easy: 78 failure(s) — gallery `/tmp/vh5/reports/three-run-20261011T223845Z/gallery/20261011T225608Z-easy-hard-r2of3/easy` — first: easy-0000, easy-0001, easy-0002, easy-0003, easy-0004, easy-0005, easy-0006, easy-0007, easy-0009, easy-0010 …
- run 2 hard: 94 failure(s) — gallery `/tmp/vh5/reports/three-run-20261011T223845Z/gallery/20261011T225608Z-easy-hard-r2of3/hard` — first: snow-0000, spiderweb-0000, split-0000, stitch-0000, strippy-0000, cut-0000, collage-0000, corrosion-0000, cross-shadow-0000, darts-0000 …
- run 3 easy: 78 failure(s) — gallery `/tmp/vh5/reports/three-run-20261011T223845Z/gallery/20261011T231246Z-easy-hard-r3of3/easy` — first: easy-0000, easy-0001, easy-0002, easy-0003, easy-0004, easy-0005, easy-0006, easy-0007, easy-0009, easy-0010 …
- run 3 hard: 94 failure(s) — gallery `/tmp/vh5/reports/three-run-20261011T223845Z/gallery/20261011T231246Z-easy-hard-r3of3/hard` — first: snow-0000, spiderweb-0000, split-0000, stitch-0000, strippy-0000, cut-0000, collage-0000, corrosion-0000, cross-shadow-0000, darts-0000 …

## re-run this

```
python3 tools/make_suites.py --seed 1   # if data/ is missing
python3 tools/three_run_proof.py --reader "python3 baseline.py {image}" --runs 3
```
