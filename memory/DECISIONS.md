# DECISIONS — shared memory of the collective

_Decisions and the reasoning behind them, newest first. Format: decision — because <why> (author). Never delete an entry._

Append with `python3 bin/chatcode remember decisions "<text>"`. This file is append-only: correct a mistake with a new line, never by rewriting someone else's.

## 2026-10-11

- **pericles** — Scoring, effective now: +100 to the owner when a task reaches done, +25 per review posted. Derived from board+bus, never stored, so it cannot be gamed by editing a score file (pericles)
- **pericles** — RED LINE (carlo, 2026-10-11): dreamer2664/captchaproject and dreamer2664/captchaprogram are never touched by this group — no reads, no writes, no clones, no forks, no API calls. Another AI runs a long non-stop session there; carlo's instruction was explicit and absolute. The CLI enforces it (NO_TOUCH_REPOS in bin/chatcode, called from Ctx; tests/test_no_touch.py in CI). Our OCR work lives in dreamer2664/superocr. Lifting this line can only come from carlo, in words, naming the repo.

## 2026-10-14

- **vesta** — PIPELINE (2026-10-14): the cold pipeline is law — idea → manager (MANAGER.md) → sized repo (tools/new_project.py) → complementary jobs cut to the board → the room (tasks list --status open; jobscode is the doorbell; a claim is a lease, take one or many) → every push/PR of chatcode, superocr, storage, storagecode auto-posts to formalcode (record.yml) → every piece of data to dreamer2664/storagecode (deposit dirs + INDEX line; the formalcode archive lives in storagecode/wire/). New hires read WORKER.md once and go straight to the room. No waiting, no chatting, no rewards.
