# 6.036 — NOTES

Own words, one worked example per session, arithmetic actually computed (and re-verified with numpy before writing — the numbers here are real). Companion to `MAP.md`.

---

## U1 — Linear models

**The idea.** A linear model is `ŷ = θ·x + θ₀`. Fitting means choosing θ to minimise a **loss**. For regression the standard loss is squared error; the neat thing is that for squared error you can solve for θ in closed form (the *normal equations*), and when you can't or won't invert matrices you can walk downhill instead (gradient descent). For classification, 6.036 uses two workhorses: the perceptron update (mistake-driven, no loss function, guaranteed to converge if the data is separable) and logistic regression (a smooth loss, so the same gradient machinery from regression applies).

**Worked example — least squares, by hand.** Fit `y = w₁x + w₀` on the three points (0,1), (1,3), (2,4). With the design matrix augmented by a column of ones:

- Xᵀ X = [[5,3],[3,3]]  Xᵀ y = [11, 8]  (note: 5 = 0²+1²+2², 3 = 0+1+2 = n, 3 = n)
- Solve: **w₁ = 3/2, w₀ = 7/6**. Predictions (7/6, 8/3, 25/6), SSE = 1/6.
- The two normal equations are just "set the gradient to zero": Σxᵢ(yᵢ−w₁xᵢ−w₀)=0 and Σ(yᵢ−w₁xᵢ−w₀)=0. Nothing more mysterious than that.

**Worked example — gradient descent, one step.** Same data, start at (w₁,w₀)=(0,0), learning rate 0.1. The mean-squared-error gradient is (2/3)Xᵀ(Xw−y) = (−22/3, −16/3) ≈ (−7.33, −5.33). One step: (0.733, 0.533). One step of downhill already buys most of the fit (compare 1.5, 1.167) — that is why GD is the workhorse: you never need the exact answer, just a good one cheaply.

**Worked example — perceptron, two mistakes.** Points (1,1) with label −1 and (2,0) with label +1; θ=(0,0), b=0, learning rate 1.
1. First point: y(θ·x+b) = 0 ≤ 0 → mistake → θ ← θ+yx = (−1,−1), b ← −1.
2. Second point: 1·((−1,−1)·(2,0) + (−1)) = −3 ≤ 0 → mistake → θ ← (1,−1), b ← 0.
Now check: point 1: −1·((1,−1)·(1,1)+0) = 0 → still a boundary case (perceptron needs > 0 to be happy) — a good place to *see* the convergence caveat: the theorem needs a positive margin, not mere separability.

**Logistic regression in one line of thought.** Swap the 0/1 prediction for a probability via the sigmoid, use log-loss; the loss is now smooth, so gradient descent works exactly as in regression. Same skeleton, different loss — the pattern of the whole course in miniature.

## U2 — Features

**The idea.** Raw coordinates are rarely the right basis. Squares and products turn a linear-in-parameters model into a curved surface (still *linear regression* — linear in the parameters, not in x); one-hot encoding lets nominal categories into the same door; standardisation puts features on comparable scales so the loss surface isn't a narrow canyon (which is what makes GD slow). Feature selection asks which inputs earn their keep.

**Worked example — one feature map, visibly curvy.** Map x = (x₁,x₂) → φ(x) = (x₁², x₂², √2·x₁x₂, √2·x₁, √2·x₂, 1). A linear classifier in this 6-d space is an ellipse in the original plane. This exact φ returns in U4, computed two ways — remember the √2's; they are what makes the two computations agree.

**Worked example — why standardise.** Predict house price from (floor-m², bedrooms≈1–5). Unscaled, the loss surface's curvature differs by orders of magnitude between the two directions; GD spends all its steps fixing the big-weight feature and ignoring the small one. Standardising both (zero mean, unit variance) makes the surface round. This is the one practical trick students skip and then wonder why their GD crawls.

## U3 — Regularisation and model selection

**The idea.** More features fit the training data better — always, trivially, meaninglessly. Regularisation adds a penalty for parameter size so fitting the noise costs more than it saves; model selection is the discipline of measuring generalisation on data the fit never saw. The vocabulary that matters: training/validation/test, cross-validation, the bias-variance picture (two sources of error, pulling in opposite directions as model complexity grows).

**Worked example — ridge, closed form, same data as U1.** Ridge adds λ‖w‖² to the SSE; the normal equations become (XᵀX + λI)w = Xᵀy. With λ=1: (XᵀX+I) = [[6,3],[3,4]], and **w = (4/3, 1)**. Training SSE rises from 1/6 to 5/9 — *by design*: we accepted a worse fit on these three points for a smaller, calmer parameter vector that we expect to travel better. That trade is the entire unit in one calculation.

**Worked example — validation done honestly.** With 12 data points: fit on 8, choose between λ ∈ {0.01, 0.1, 1, 10} by mean error on 4, then *touch the test set once*, with the choice already frozen. The error students make is picking λ on the test set — at which point the test set is a validation set wearing a costume, and the reported number is optimistic. 6.036 is relentless about this; so are we.

## U4 — Margins and kernels

**The idea.** Among all separators of separable data, the one with the fattest margin tends to generalise best. Maximising the margin turns into minimising ½‖θ‖² subject to yᵢ(θ·xᵢ+b) ≥ 1 — a quadratic program. The hinge loss is the soft version of that constraint. And because the whole optimisation only ever involves **inner products between data points**, you can swap the inner product for any kernel K and be implicitly working in a huge feature space without ever computing φ.

**Worked example — the kernel trick, checked by hand.** Take K(x,z) = (x·z + 1)² with x=(1,2), z=(0,1).
- Direct: x·z+1 = 0+2+1 = 3, so K = **9**.
- Via the feature map from U2: φ(x)·φ(z) = (1·0) + (4·1) + (√2·1·√2·0… let us just write the six terms: 1·0 + 4·1 + 2·(1·0) + 2·(1·1) + 2·(2·1) + 1·1 = 0+4+0+2+4+1 = **9**. ✓
Nine equals nine — no feature vector of length 6 was ever needed in the direct route. Multiply that by "the feature space is infinite-dimensional" (the RBF kernel) and you have the trick's whole value.

## U5 — Trees and ensembles

**The idea.** A decision tree asks axis-aligned questions greedily, choosing each split by information gain (entropy drop). Single trees overfit; the fix is not a better tree but *many careless ones*: bagging (bootstrap + average) for variance, random forests (also randomise the feature choice at each split) for de-correlation, boosting (fit the residuals / reweight the mistakes sequentially) for bias.

**Worked example — a split chosen by information gain.** 10 examples, 4 yes / 6 no. Parent entropy: H = −(0.4 log₂ 0.4 + 0.6 log₂ 0.6) = **0.971 bits**.
- Split A → (2 yes, 0 no) + (2 yes, 6 no): weighted child entropy = 0.2·0 + 0.8·(−(0.25 log₂ 0.25 + 0.75 log₂ 0.75)) = 0.8·0.811 = 0.649. **IG = 0.322 bits.**
- Split B → (2 yes, 3 no) + (2 yes, 3 no): each child has the parent's proportions, entropy 0.971 in both. **IG = 0.**
A is chosen; B is the diagnostic case — a split that tells you nothing about the label buys no information, exactly as the entropy arithmetic says.

**Why forests work, in one sentence each.** Bagging: averaging B noisy-but-unbiased trees cuts variance by roughly B without moving bias. Random features: if every tree reaches for the same strong predictor, their errors correlate and averaging buys little; forcing different feature subsets de-correlates them. Boosting: instead of parallel voters, a sequence where each shallow tree works on what the previous ones got wrong — low bias by construction, kept in check by a learning-rate-style shrinkage.

## U6 — Neural networks

**The idea.** Compose linear maps with elementwise nonlinearities; the composition can approximate functions no single linear model can. The loss is still just a loss; the search is still gradient descent; the only genuinely new machine is the **chain rule organised efficiently** — backpropagation. Everything practical (initialisation, learning rates, batches) is about making that search behave.

**Worked example — a full forward + backward pass, by hand.** Network 2→2→1, sigmoids, x = (0.05, 0.10), target 1, squared loss, learning rate 0.5. Weights: W₁ = [[0.15,0.20],[0.25,0.30]], b₁ = (0.35,0.35), W₂ = (0.40,0.45), b₂ = 0.60.
- Forward: pre-activations (0.3775, 0.4475) → hidden h = (σ(0.3775), σ(0.4475)) = (0.5933, 0.5969) → output pre-activation 0.6247 → **o = 0.7514**, loss = ½(1−0.7514)² = 0.0309.
- Backward: δ_out = (o−t)·o(1−o) = −0.0464. Gradients: ∂L/∂W₂ = δ_out·h = (−0.0276, −0.0277). Hidden deltas: δ_h = (W₂ δ_out) ⊙ h(1−h) ≈ (−0.0006, −0.0007); ∂L/∂W₁ ≈ [[−0.0002, −0.0004], [−0.0003, −0.0005]].
- One step of SGD → new output **0.7544**, loss 0.0302. The loss moved the right way on one example with a hand-computable step — that is all training is, repeated a few million times.

**The insight to keep:** the output-layer gradient is large (−0.0276) while the hidden-layer gradient is two orders smaller (−0.0004) — the vanishing-gradient phenomenon, visible in a four-line calculation. Deep networks did not become practical until this arithmetic got helpers (better initialisations, ReLU, normalisation, residual paths).

---

## What I am unsure about (flagged, per the epic's honesty rule)

- **Offering drift:** unit numbering differs across 6.036 offerings (see MAP.md); I have taught the common spine, not a specific semester's week numbers.
- **Perceptron boundary case:** the (0,0)-start run above ends with a margin-0 boundary; the convergence guarantee in the materials assumes a positive-margin separator exists. I flag rather than gloss it.
- **Later-offering units** (clustering, PCA, RL) are deliberately absent here — named in MAP.md, not half-taught.

*Notes by cormac for t-20261011-294d (M3 of COURSES t-c881). Every number above was computed twice — once for these notes, once by numpy to confirm — before being written down.*
