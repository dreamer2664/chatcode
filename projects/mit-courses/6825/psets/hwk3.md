# 6.825 Homework 3 — solved (M2, t-20261011-5542)

Source: MIT OCW 6.825 Fall 2002, hwk3.pdf ("Not to be handed in" — the
paper problem set of the course). Every answer below derived independently
with reasoning shown; afterwards cross-checked against the OCW solutions
PDF — agreement noted per problem. Arithmetic verified by the companion
script `verify_hwk3.py` (values solve the linear systems / run the
iterations exactly as written below).

---

## 1. Easy EM

Network of Figure 1: A is the root; D is the child of A, B, C. The table
has 17 rows of observed (A,B,C) and a soft count Pr(D|A,B,C) per row, so
the expected count of D=1 in a row is exactly that number.

### 1.1 Maximum-likelihood estimates

MLE for a CPT entry = expected count of (child∧parents) / expected count
of (parents).

**Pr(A)** = (#rows with A=1)/17. Rows with A=1: rows 1,5,7,8,15,16,17 → 7
rows. **Pr(A) = 7/17 ≈ 0.412.**

**Pr(D|A)** = E#[D∧A] / E#[A]. E#[A]=7. E#[D∧A] = sum of Pr(D|·) over the
A=1 rows: rows 1,5,17 contribute 3×0.6=1.8; rows 7,16 contribute
2×0.5=1.0; row 8 contributes 0.4; row 15 contributes 0.2. Total
1.8+1.0+0.4+0.2 = 3.4. **Pr(D|A) = 3.4/7 ≈ 0.486.**

**Pr(B|D)** = E#[B∧D] / E#[D]. First E#[D] = sum over all 17 rows of
Pr(D|·): three 0.6-rows (1.8), two 0.3-rows (0.6), three 0.7-rows (2.1),
four 0.9-rows (3.6), two 0.5-rows (1.0), one each of 0.4, 0.1, 0.2 →
1.8+0.6+2.1+3.6+1.0+0.4+0.1+0.2 = 9.8. Rows with B=1: 1,4,5,8,9,12,13,14,17;
their D-expected counts: 0.6+0.9+0.6+0.4+0.9+0.1+0.9+0.9+0.6 = 5.9.
**Pr(B|D) = 5.9/9.8 ≈ 0.602.**

**Pr(C|D)** = E#[C∧D] / E#[D]. Rows with C=1: 1,3,4,5,7,9,10,11,13,14,16,17;
D-expected counts: 0.6+0.7+0.9+0.6+0.5+0.9+0.7+0.7+0.9+0.9+0.5+0.6 = 8.5.
**Pr(C|D) = 8.5/9.8 ≈ 0.867.**

(Only these four CPT entries are asked for: A has no parents, B and C have
parent D only, D's full CPT over (A,B,C) is what the original table gives.)

### 1.2 An 8-entry representation

Collapse the 17 rows into a tally of the 8 distinct (A,B,C) patterns —
identical patterns have identical Pr(D|·), so nothing is lost:

| A | B | C | Pr(D\|A,B,C) | count |
|---|---|---|---|---|
| 0 | 0 | 0 | .3 | 2 |
| 0 | 0 | 1 | .7 | 3 |
| 0 | 1 | 0 | .1 | 1 |
| 0 | 1 | 1 | .9 | 4 |
| 1 | 0 | 0 | .2 | 1 |
| 1 | 0 | 1 | .5 | 2 |
| 1 | 1 | 0 | .4 | 1 |
| 1 | 1 | 1 | .6 | 3 |

Counts sum to 17. Cross-check vs OCW solutions: all five answers agree.

---

## 2. Harder EM

Structure of Figure 2 (read off the factorisation the solutions PDF uses,
consistent with the figure): F is the root; A,B have parent F; C has
parents A,B; D,E have parent C; G has parents D,E.

### 2.1 Joint probability

By the chain rule for Bayes nets, each node conditioned on its parents:

Pr(a,b,c,d,e,f,g) = Pr(f)·Pr(a|f)·Pr(b|f)·Pr(c|a,b)·Pr(d|c)·Pr(e|c)·Pr(g|d,e)

### 2.2 Irrelevant variables for Pr(d|b)

E and G. Both sit strictly downstream of D (the query variable): summing
them out multiplies by Σ_e Pr(e|c) = 1 and Σ_g Pr(g|d,e) = 1 for every
setting of the rest, so they contribute a factor identically 1 and can be
dropped before any arithmetic.

### 2.3 Factors created in the order A,B,C,D,E,F,G

B and D are observed (fixed at b, d), and E,G are irrelevant, so the only
variables actually summed out are F, C, A:

1. Sum out F: f₁(a,b) = Σ_f Pr(f)·Pr(a|f)·Pr(b|f) — a function of (a,b).
2. Sum out C: f₂(a,b,d) = Σ_c Pr(c|a,b)·Pr(d|c) — a function of (a,b,d).
3. Sum out A: Pr(b,d) = Σ_a f₁(a,b)·f₂(a,b,d).
4. Normalise: Pr(b) = Σ_d Pr(b,d), then **Pr(d|b) = Pr(b,d)/Pr(b)**.

The cost of each step is set by the largest factor created — here
f₂ with scope {a,b,d}: this is where elimination order earns its keep.

### 2.4 Estimating F and C separately — justified?

Yes for this network, and the reason is d-separation: with A and B
observed, every path between F and C runs through A or B (F→A→C and
F→B→C), so F ⊥ C | A,B, and further observations (D,E,G are downstream of
C, with C/A/B conditioning in place) do not reopen a path. Hence
Pr(F,C|a,b,d,e,g) = Pr(F|a,b)·Pr(C|a,b,d,e), and the two columns of the
proposed table can be filled independently. Practical win: Pr(F|a,b) has
only 4 entries — compute it once, fill the whole column.

The counter-example that shows this is a property of THIS graph, not of
EM: had A and B been the hidden variables instead, they are NOT
independent given the rest (they share the unobserved path through C's
other parent, and conditioning on descendants of a collider opens paths),
so one would need the joint Pr(A,B | c,d,e,f,g) per data row.

### 2.5 Estimating Pr(G|d,e) from data and skipping G in EM — justified?

Yes. By the Markov property of the structure, Pr(G | a,b,c,d,e,f) =
Pr(G | d,e): G's CPT depends only on its parents D,E, both fully observed.
EM's loop alternates (a) filling in expected counts of hidden data and
(b) re-estimating CPTs from those counts — but G's sufficient statistics
never involve the hidden F or C, so its MLE from the raw data is already
exact and re-running it inside EM would not change it. Compute once,
exclude from the loop.

Cross-check vs OCW solutions: agrees on all five parts, including the
factorisation and both justifications.

---

## 3. Markov chain values

Bellman equations for the fixed policy (there is no choice here):
v₁ = 1 + γ(0.8v₁ + 0.1v₂ + 0.1v₃)
v₂ = 3 + γ(0.2v₁ + 0.1v₂ + 0.7v₃)
v₃ = −1 + γ(0.9v₁ + 0.1v₂)

Solving (I − γP) v = R, verified numerically by `verify_hwk3.py`:

- **γ = 0.9:** v₁ ≈ 9.257, v₂ ≈ 10.266, v₃ ≈ 7.422 (OCW rounds 9.26 /
  10.27 / 7.42 — agrees).
- **γ = 0.1:** v₁ ≈ 1.110, v₂ ≈ 2.991, v₃ ≈ −0.870 (OCW: 1.11 / 2.99 /
  −0.87 — agrees).

Reading the numbers: s₂ is the only state worth being in (reward 3), but
from s₂ the chain leaks to s₃ with probability 0.7 and s₃ is a trap with
negative reward that only exits via s₁ — at high γ that future pain is
priced in fully (v₃ = 7.42, still positive because escape to s₁ is almost
certain); at low γ the chain barely looks ahead and v₃ ≈ its immediate
reward −1.

---

## 4. Markov decision process — value iteration

Same rewards; action 1 = the matrix above, action 2 =
[[.1,.1,.8],[.7,.1,.2],[.9,0,.1]]. Update: V ← R + γ·max(P₁V, P₂V),
starting from V₀ = 0. All ten iterates (script-verified):

**γ = 0.9**

| iter | v₁ | v₂ | v₃ |
|---|---|---|---|
| 1 | 1.0000 | 3.0000 | −1.0000 |
| 2 | 1.9000 | 3.7200 | 0.0800 |
| 3 | 2.7100 | 4.5462 | 0.8738 |
| 4 | 3.4390 | 5.2737 | 1.6043 |
| 5 | 4.0951 | 5.9300 | 2.2602 |
| 6 | 4.6856 | 6.5205 | 2.8507 |
| 7 | 5.2170 | 7.0519 | 3.3822 |
| 8 | 5.6953 | 7.5302 | 3.8605 |
| 9 | 6.1258 | 7.9607 | 4.2909 |
| 10 | 6.5132 | 8.3481 | 4.6784 |

**γ = 0.1**

| iter | v₁ | v₂ | v₃ |
|---|---|---|---|
| 1 | 1.0000 | 3.0000 | −1.0000 |
| 2 | 1.1000 | 3.0800 | −0.8800 |
| 3 | 1.1100 | 3.0902 | −0.8702 |
| 4 | 1.1110 | 3.0912 | −0.8692 |
| 5 | 1.1111 | 3.0913 | −0.8691 |
| 6–10 | 1.1111 | 3.0913 | −0.8691 (no change to 4 decimals) |

(OCW reports the same 10-iteration endpoints: 6.51/8.35/4.68 and
1.11/3.09/−0.87 — agrees.)

**Convergence:** γ = 0.1 is converged by iteration 5; γ = 0.9 is still
climbing at iteration 10. Value iteration is a γ-contraction: the error
shrinks by a factor γ per step, so with γ = 0.9 the horizon that matters
is ~1/(1−γ) = 10 steps and ten iterations have barely covered it; with
γ = 0.1 the future decays so fast that three steps already see the whole
relevant horizon.

**Sanity check against problem 3:** at γ = 0.1 the MDP values (1.111,
3.091, −0.869) are ≥ the chain values (1.110, 2.991, −0.870) — correct,
since always-action-1 reproduces the chain and the optimum can only do
better. At γ = 0.9 the 10-iteration values are still BELOW the chain
values (6.51 < 9.26…): not a violation — the algorithm simply has not
converged yet. Running to convergence (script, 200 iterations) gives
**V\* = (10.000, 11.835, 8.165)**, which does dominate the chain values,
as it must.

**Optimal policy:** once converged, pick argmax per state:
s₁ → action 1 (10.0 vs 8.72), s₂ → action 2 (9.82 vs 8.90),
s₃ → action 1 (10.18 vs 9.82) — policy (1, 2, 1); OCW agrees.

**Values under the optimal policy, exactly:** freeze the policy and solve
the resulting Markov chain's linear system (as in problem 3) with the
mixed transition matrix (row s₁ from P₁, row s₂ from P₂, row s₃ from P₁) —
gives the same V\* = (10, 11.835, 8.165), which is the cheap way to get
exact values without iterating.

---

## 5. At the races, again

Let x = net gain (returned − staked). Outcomes:
- Moon $2: win +2 (p .7), lose −2 (p .3).
- Jeb $2: win +20 (p .2), lose −2 (p .8).
- Split $1+$1: Moon wins → back $2 on $2 staked → 0 (p .7); Jeb wins →
  back $11 on $2 → +9 (p .2); both lose → −2 (p .1).

### 5.1 Expected value (risk-neutral)

E[Moon] = .7·2 + .3·(−2) = 1.4 − 0.6 = **0.8**
E[Jeb] = .2·20 + .8·(−2) = 4.0 − 1.6 = **2.4**
E[split] = .7·0 + .2·9 + .1·(−2) = 1.8 − 0.2 = **1.6**

A risk-neutral bettor chooses **Jeb** (highest EV). All three bets have
positive EV — the odds offered are genuinely favourable.

### 5.2 Risk-averse: U(x) = √(x+20)

EU[Moon] = .7·√22 + .3·√18 = .7(4.6904) + .3(4.2426) ≈ **4.556**
EU[Jeb] = .2·√40 + .8·√18 = .2(6.3249) + .8(4.2426) ≈ **4.659**
EU[split] = .7·√20 + .2·√29 + .1·√18
= .7(4.4721) + .2(5.3852) + .1(4.2426) ≈ **4.632**
(no bet: √20 ≈ 4.472, so betting is still preferred to not betting)

The risk-averse bettor **still chooses Jeb**, but the margin over the
split bet has shrunk to 4.659 vs 4.632 — the concavity of √ compresses
the payoff of the high-variance bet and nearly closes the gap with the
hedged bet. Push the curvature further (OCW's check: U(x)=√(x+3),
i.e. only $3 to one's name) and the split bet wins (≈2.01 vs 1.87/1.76):
poverty makes hedging rational.

### 5.3 Relation to investment strategy

Same arithmetic, larger stakes: the utility function — not the odds —
decides between concentration and diversification. A nearly-linear utility
(deep pockets relative to the bet) behaves risk-neutrally and
concentrates in the highest-EV position; a strongly concave utility
(thin margins, ruin on the table) pays EV to buy variance reduction —
index funds over single stocks, insurance, hedges. Kelly-style sizing is
the continuous version of this same trade-off: bet fraction chosen to
maximise expected log-wealth, which is exactly a concave-U calculation.
Honest limit of the analogy: real markets don't hand you +EV bets; the
portfolio lesson here is about variance tolerance, not about finding
free money.

Cross-check vs OCW solutions: EVs, EUs, both choices, and the √(x+3)
variant all agree.
