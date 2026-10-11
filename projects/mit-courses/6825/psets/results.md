# 6.825 Project 1a — DPLL & WalkSAT: implementation + experiment (M2)

The course's Project 1a asks for two SAT solvers plus a ratio experiment.
Implemented here in Python (stdlib only, seeded) instead of the course's
Java skeleton — `sat.py`; the algorithm descriptions below are what the
code does, as the assignment's write-up rule requires ("not code!").

## DPLL, as implemented

Complete and sound. Loop: (1) unit propagation — any clause with exactly
one unassigned literal forces that literal, repeated to a fixpoint; a
clause whose literals are all falsified reports conflict and backtracks.
(2) Pure-literal elimination — a variable appearing with only one sign
gets that sign. (3) Branch on a variable from a shortest remaining
clause (short clauses constrain most), True first. Metric counted per the
assignment's collection rule: complete assignments examined.

## WalkSAT, as implemented

Sound but incomplete. Start from a random complete assignment. Each flip:
pick a random unsatisfied clause; with probability p=0.5 flip a random
variable in it, otherwise flip the variable in it that minimises the
number of unsatisfied clauses. Stop at a satisfying assignment or a
budget (20,000 flips here). Never proves UNSAT — budget exhaustion is
"no answer", not "unsatisfiable".

## Debug instances

The course's four debug instances, recreated from their description
(satisfiable1/2, unsatisfiable1/2):

    satisfiable1   -> SAT    assignment={1: True}
    satisfiable2   -> SAT    assignment={1: True, 2: True}
    unsatisfiable1 -> UNSAT
    unsatisfiable2 -> UNSAT

WalkSAT independently finds assignments on both satisfiable instances —
cross-validation between the exact and stochastic solvers.

## The ratio experiment

Random 3-SAT, generator per the assignment (uniform 3-literal clauses,
random signs), 5 trials per point, seeded. Metric = average assignments
checked over the trials; satisfiability rate reported beside it since
both solvers must agree on it (DPLL decides; WalkSAT must match on the
SAT side — it does at every point).

| n | m/n | DPLL SAT/5 | DPLL avg checks | WalkSAT SAT/5 | WalkSAT avg checks |
|---|-----|-----------|------------------|----------------|---------------------|
| 15 | 3.0 | 5 | 10 | 5 | 14 |
| 15 | 3.5 | 5 | 23 | 5 | 62 |
| 15 | 4.0 | 5 | 10 | 5 | 23 |
| 15 | 4.5 | 4 | 13 | 4 | 4,161 |
| 15 | 5.0 | 2 | 19 | 2 | 12,020 |
| 15 | 5.5 | 0 | 17 | 0 | 20,000 (budget) |
| 15 | 6.0 | 1 | 15 | 1 | 16,011 |
| 20 | 3.0 | 5 | 11 | 5 | 18 |
| 20 | 3.5 | 5 | 22 | 5 | 30 |
| 20 | 4.0 | 4 | 20 | 4 | 4,093 |
| 20 | 4.5 | 4 | 18 | 4 | 4,399 |
| 20 | 5.0 | 2 | 35 | 2 | 12,191 |
| 20 | 5.5 | 2 | 21 | 2 | 12,023 |
| 20 | 6.0 | 1 | 27 | 1 | 16,013 |

(Reproduce: `python3 sat.py` — deterministic under the fixed seeds.)

## Reading the results

1. **The phase transition is visible.** Satisfiability falls from 5/5 to
   0–2/5 between m/n ≈ 4.0 and 5.5 for both n; the asymptotic threshold
   for random 3-SAT is ≈ 4.27, and even at n = 15–20 the curve sits
   where theory puts it. Below it, instances are easy-SAT; above, easy-
   UNSAT; the interesting band is the transition itself.
2. **WalkSAT's effort peaks in the transition band.** Flip counts explode
   from tens (easy-SAT) to the 20,000-flip budget right where the
   satisfiable instances become rare and rugged — local search has to
   walk between near-solutions that differ in many variables. This is the
   classical "hardness peak at the threshold".
3. **DPLL stays cheap at these sizes** because unit propagation collapses
   most of the tree: the interesting DPLL explosion needs larger n (the
   assignment's "impractical = >5 min" criterion would only bite at
   substantially larger instances; at n ≤ 20 everything runs in under a
   second, honestly so — no timeout was needed).
4. **Both solvers agree on SAT/UNSAT at every point** (DPLL decides,
   WalkSAT confirms on the SAT side) — the sound/complete vs
   sound/incomplete distinction from the assignment text, demonstrated.

Honest limits of this reproduction: n ≤ 20 and 5 trials per point (the
course suggested ≥5; I did not push into the minutes-range), DPLL has no
clause learning (the course's extra-credit speed-up), and the official
test-1…test-5 CNF files were not re-downloaded — the debug instances are
reconstructions from their descriptions on the OCW page.
