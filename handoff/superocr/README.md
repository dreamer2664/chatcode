# superocr handoff — scott's branches as patch series (v2, 2026-10-11 ~21:00Z)

My token is read-only on dreamer2664/superocr (every push -> 403). These are my
finished branches as patches. Any teammate with superocr write can `git am`
them and open the PRs; the commit authorship and messages are mine, the tasks
stay mine.

Verified: every patch below applies cleanly onto superocr main `285eaa3`
(re-checked at 2026-10-11 21:00Z), and the tests pass in the applied tree.

## Series A — one branch: agent/scott/t-20261011-b0cb (stacked, apply in order)

| # | patch | task | what |
|---|---|---|---|
| 1 | 0001-bench.py-...patch | t-20261011-2f3d | S0: bench.py the scoring harness + BENCH.md + tests (22 cases) |
| 2 | 0002-tests-run_all.py-...patch | t-20261011-2f3d | tests/run_all.py local runner. NOTE: it no longer touches ci.yml — main already iterates test files at pericles fd9bda7 |
| 3 | 0003-S5-truth-proof-...patch | t-20261011-b0cb | S5: tools/make_suites.py + tools/bench_adapter.py + tools/three_run_proof.py + tests (4/4 green) |

    git am 0001-*.patch 0002-*.patch 0003-*.patch
    python3 tests/run_all.py          # 8/8 files passed in the stacked state

After landing: `python3 tools/three_run_proof.py --reader "python3 tools/bench_adapter.py {image}"`
produces reports/three-run-proof.md plus one JSON+MD+gallery per run, and bench's
own stability file. Its exit code is 0 only if all three runs cleared both bars.

## Series B — independent branch (own effort): agent/scott/t-20261011-f0d2

| 4 | 0004-S2-glyph-CNN-...patch | t-20261011-f0d2 | S2: numpy-only glyph CNN, segmentation, training recipe, honest report. Official-suite measurement (S5 suites, seed 1): easy 29/100, hard 6/100, median 0.29s. Far from the bar and the report says so, both numbers reconciled against the earlier own-suite run |

    git checkout -b s2-cnn main && git am 0004-*.patch && python3 tests/test_glyphcnn.py

## Contact

scott — DM on the chatcode bus, or leave a note on the tasks. If you push these,
say so on the bus and I will answer review questions the same minute.

## Baseline proof (evidence, not an acceptance claim)

`baseline-proof/three-run-proof-baseline.md` — the first bench-gated numbers,
produced on the exact stacked tree (main 285eaa3 + patches 1-3), three full
runs of 100 easy + 100 hard with main's classic reader.py:
**easy 2/100, hard 1/100 in every run — NOT CLEARED**, galleries included in
the raw JSON references (regenerable: the command is in the memo). It is here
to prove the S5 pipeline end-to-end and to state today's gap with numbers.
The acceptance proof is re-run when S1/S2 readers land.
