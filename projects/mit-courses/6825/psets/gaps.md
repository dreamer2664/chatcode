# 6.825 problem sets — honest gap register (M2, t-20261011-5542)

What is solved, and what is not, per the rule: numbers must be real, so
unfinished work is listed, not hidden.

## Solved in this branch
- **Homework 3** (the paper problem set, all 5 problems): full solutions
  with reasoning in `hwk3.md`, arithmetic re-derived independently and
  then cross-checked against the OCW solutions PDF — agreement on every
  answer. `verify_hwk3.py` re-runs all the arithmetic; `sat.py` is
  self-contained.
- **Project 1a** (SAT solvers): DPLL + WalkSAT implemented from scratch
  in Python, debug instances reproduced, ratio experiment run with real
  measurements — `results.md`.

## Not settled — and why
- **Project 1a, items 2 & 5**: the course's five official test CNFs
  (test1…test5) were not downloaded; my runs use the four reconstructed
  debug instances plus seeded random generation. A solver's answer on
  test1–5 remains unverified. The "graph to impracticality" was bounded
  by time budget, not by hitting the 5-minute bar.
- **Project 1b** (FOL railways, safety and liveness by SAT): not
  attempted. It requires the course's FOL jar and a working FOL→CNF
  pipeline against the given world axioms; the page text was read (task
  list captured in the notes), but writing train-world axioms blind and
  grading them against an unavailable checker would produce unverified
  answers — refused rather than faked.
- **Project 1c** (resolution-refutation proofs checked by the course's
  RRPC jar): not attempted for the same reason — the proofs are checked
  by the course's tool against its given KB files; hand-deriving them
  without that loop risks unchecked mistakes. My M1 logic notes carry a
  worked resolution refutation of a self-chosen KB instead.
- **Project 2a** (Bayes net structure learning, Nilsson-chapter scoring):
  not attempted. Parts 1–2 (CPT counting, scoring) are well-specified and
  the Data A/B files are downloadable — a legitimate next step for M4 or
  a follow-up task; flagged here as the natural continuation rather than
  done under pressure.

## Judgment applied
Solving HW3 fully + 1a with real measurements beats five half-verified
artefacts. Everything shipped here can be re-run from this branch with
`python3 verify_hwk3.py` and `python3 sat.py`.
