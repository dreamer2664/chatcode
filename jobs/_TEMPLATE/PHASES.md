# PHASES — t-YYYYMMDD-<slug>
<!-- Gates, not wishes. `jobs phase close` and `jobs gate` enforce both columns. -->
<!-- min_hours counts from the phase's start checkpoint to its close checkpoint. -->
<!-- Early finisher rule: close before the floor => upgrade the evidence, never stop. -->

| phase | deliverable | required evidence (file names) | min_hours |
|---|---|---|---|
| P1 | concept / plan | `evidence/P1-plan.md` | 1.0 |
| P2 | first build / draft | `evidence/P2-draft.*` + honest notes | 2.0 |
| P3 | full output | `evidence/P3-manifest.sha256` + run log | 2.0 |
| P4 | QC loop, actually looked at | `evidence/P4-SELF_REVIEW.md` — ≥1 defect-fix-reinspect cycle | 2.0 |

**Floor: 7.0 h.** Found zero defects in P4? You did not look hard enough — log
what you checked, at what resolution, and what you would still distrust.
