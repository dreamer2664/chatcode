# 6.825 Techniques in Artificial Intelligence — topic map (M1, t-20261011-6672)

MIT 6.825 (open course materials). Map first, notes second; this is the
index the notes hang from. Written from memory of the course's classic
structure (Winston lineage) — where the open materials and this map
diverge, the materials win; flagged where known.

## The six sections

### 1. Search
- States / operators / goal test / path cost: the state-space abstraction.
- Uninformed strategies: BFS, DFS, UCS (and when each is complete/optimal).
- Heuristics: admissibility, consistency, dominance; A* and its optimality
  argument; iterative deepening as the DFS/BFS compromise.
- Constraint satisfaction as search with structure: arc consistency, MRV/LCV
  ordering (bridge to planning).
- Depends on: nothing (foundational). Feeds: games (minimax is search with
  an adversary), planning (state-space search over operator schemas).

### 2. Games
- Minimax; the depth-limited evaluation function and its horizon limits.
- Alpha–beta pruning: why the bound never changes the minimax value.
- Practical depth: move ordering, transposition, chance nodes (expectiminimax).
- Depends on: search. Feeds: logic (game semantics), probability (chance nodes).

### 3. Logic
- Propositional vs first-order: syntax, semantics, entailment.
- Inference: forward/backward chaining; resolution with unification.
- Proof by refutation: negate the goal, derive contradiction.
- The limits: undecidability, incompleteness at a headline level; why real
  systems mix logic with search and probability.
- Depends on: search (resolution IS a search over clauses). Feeds: planning
  (STRIPS languages are first-order-ish operator schemas).

### 4. Probability
- Why uncertainty breaks pure logic; probability as belief calculus.
- Joint distributions, conditioning, marginalisation; independence.
- Bayes' rule; Bayes networks: topology encodes conditional independence;
  inference by enumeration and variable elimination.
- Simple decisions under uncertainty: expected utility ties probability back
  to games/search.
- Depends on: search (inference is a search/DP). Feeds: learning.

### 5. Planning
- Why per-step search is hopeless for long horizons: non-interleaving,
  commutativity of operators; planning as proof-ish search.
- STRIPS/PDDL style: preconditions, add/delete lists; classical planning
  assumptions (closed world, deterministic, fully observable).
- Progression vs regression; plan-space search; planning graphs as a
  source of heuristics.
- Depends on: logic + search. Feeds: learning (later: learning the models).

### 6. Learning
- Inductive learning, overfitting, train/validation discipline.
- Decision trees and information gain; nearest neighbour; the curse of
  dimensionality.
- Perceptron and its convergence story; feature spaces as the lever.
- The meta-lesson: learning = search in hypothesis space, scored by data.
- Depends on: everything above. Feeds: nothing within the course — it is
  the capstone.

## Reading order
Map → notes/search → games → logic → probability → planning → learning,
each with its worked example; quizzes (M4) follow the same order.
