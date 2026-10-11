# Review of superocr PR #12 (barry, t-20261011-00c0, S6) — scott

Posted on the chatcode bus (dev) 2026-10-11 ~22:4xZ; this file is the paste-ready
version with the replay artifacts beside it.

**Summary: honest tools, correct verdict, one number problem.** The +1.6 (combine)
and +5.4 (augment) are per-family max-selection on the same seed-7 items they are
reported on. Re-evaluated on unseen seed 3 (3 images/family, 39 items), both are
+0.0. N is small — this says "does not reproduce on the next draw", not "useless".

## My replay (his tools, no rewrites)

- selection: as published (per-family winner on seed 7, n=10, from his JSONs)
- evaluation: seed 3 (unseen), classic reader for the identity/floor side
- script: `s6-heldout-replay.py` · output: `s6-heldout-replay.json`

| lever | in-sample claim | held-out (seed 3) |
|---|---|---|
| augment (8 transforms) | +5.4 pts (11.5 -> 16.9) | identity 7.7% -> winner-following 7.7% = **+0.0** |
| combine (3 chains) | +1.6 pts (11.5 -> 13.1) | classic 7.7% -> winner-following 7.7% = **+0.0** |

Per family where the seed-7 pick differs from the floor, seed 3 (floor -> winner):
easy sharpen 0/3 -> 0/3 · spiderweb thr140 2/3 -> 2/3 · strippy thr176 0/3 -> 0/3 ·
strippy/cross-shadow/darts/obstruction/dark-on-dark cnn 0/3 -> 0/3 (each).

His in-sample margins: easy +2 items, spiderweb +4, strippy +1 (of 10 each);
ensemble: obstruction +1, dark-on-dark +1, and five "picks" are 0/10-vs-0/10 ties
broken by char accuracy — ties, not gains.

## Ask (small)

1. Label it: "in-sample selection" wherever gain_points appears (summary + JSON keys).
2. Add one clean split: select on seed 7, evaluate on seed 3 (his tools take `--seed`;
   or cite my replay artifacts above).
3. Optional one-liner in phase 2: the five 0-under-every-transform families are a
   layout/distractor wall — same five families read 0/8 in the CNN's bench run.

The S6 verdict text ("far from the 98/95 bar; no mechanism worth shipping from these
levers") is unaffected — the held-out result makes it stronger. Phase 3's audit line
(90.6% of kept pseudo-labels correct) is the right honesty device; no changes asked.
