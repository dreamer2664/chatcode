# 6.036 — MAP

**MITx 6.036 *Introduction to Machine Learning*** — the map of the course as the open materials present it, plus how the pieces depend on each other. Notes with worked examples live in `NOTES.md` (same folder). Everything here is in our own words; where the open materials leave something unsettled, §"Honest limits" says so.

## The course in one paragraph

6.036 teaches machine learning as **function fitting with discipline**: pick a parametrised family of functions (a model), a loss that says what "wrong" costs, an algorithm that searches the parameters, and a validation procedure that tells you whether you are fooling yourself. The course walks that pattern six times — linear models, feature maps, regularisation, margins and kernels, trees and ensembles, neural networks — each time changing exactly one thing: the family, the loss, the search, or the validation trick. If you keep the pattern in mind, every unit is a variation, not a new subject.

## Units and dependencies

```text
U1  Linear models        regression (least squares, GD) + classification (perceptron, logistic)
U2  Features             nonlinear features, one-hot, standardisation, feature selection
U3  Regularisation       ridge/lasso, train/val/test, cross-validation, bias-variance
U4  Margins + kernels    SVM, hinge loss, the kernel trick
U5  Trees + ensembles    CART splits, entropy/IG, bagging, random forests, boosting
U6  Neural networks      composition, backprop, SGD, practical choices

U1 -> everything (the loss/search pattern is defined here)
U2 -> U3 -> U4 (features make linear rich; regularisation tames them; margins + kernels
      are the capstone of the linear-with-features story)
U5 (independent of U3/U4: a different family and search, same validation ideas)
U6 -> needs U1 (SGD) and U2 (representation); owes nothing to U4/U5
```

## What each unit is *for* (one line each)

- **U1**: the simplest families, where loss and search can be computed by hand — the reference point for everything after.
- **U2**: the admission that raw coordinates are the wrong basis; the model stays linear, the *inputs* change.
- **U3**: the machinery for choosing between models without lying to yourself — the most transferable unit in the course.
- **U4**: maximum-margin linear separation, and the kernel trick that makes "linear in features" infinite-dimensional for free.
- **U5**: the non-parametric branch — axis-aligned splits, voted together.
- **U6**: layers of nonlinearity trained end-to-end by gradient descent.

## Session order (as the open materials run it)

Vectors and norms → linear regression (normal equations, then gradient descent) → classification (perceptron, logistic loss) → feature maps and one-hot encoding → regularisation and model selection → margin and SVMs → kernels → decision trees → bagging and boosting → neural networks and backprop → (later offerings: clustering, PCA, and reinforcement learning as extensions — see Honest limits).

## Honest limits

- The open materials exist in multiple offerings (MITx/edX cycles, OCW mirrors); **unit ordering and numbering differ between versions**. This map follows the common spine above, not any single offering's numbering. If a specific week number matters, check the offering you are actually reading.
- Grading weights, pset due dates and semester calendars are offering-specific and not settled by the open materials; nothing in these notes depends on them.
- Later offerings include units (clustering/PCA, RL) that the core spine does not; they are *not* covered here beyond this mention — they belong to a future pass, flagged rather than half-taught.
