# PIPELINE - the read-polish-dust-off pass

**Goal:** the whole system read end to end, defects written down, fixed where
fixable, and the docs made true - so a stranger can follow them.

**The bar**
- `INVENTORY.md` exists: every file, command, workflow, doc and memory file
  described in one line, with defects as `file:line - what is wrong`.
- Every defect is either fixed with a test, or explained in the inventory with a
  reason it is deliberately left.
- README rewritten so a person who is not a programmer can follow it; every
  command shown in any doc is actually executed during this pass and behaves as
  documented (or the doc is corrected).
- Full test suite + CI green at the end; the dashboard console clean.

**Branches** (parallel-safe)
- **P0 - inventory**: read everything; write `INVENTORY.md`. No fixes in this
  branch: it is fine to report things you then fix in P1.
- **P1 - fixes**: one commit per defect class, each with a test or a reason.
- **P2 - docs truth**: README/PROTOCOL/AGENT_PROMPT/paste-prompt consistency;
  run every documented command on a throwaway local repo and log the results.
- **P3 - polish**: the 10 most likely user mistakes get honest error messages;
  health snapshot (`status --health`, `quota`) verified; dead files removed;
  `STATUS.md` refreshed.
