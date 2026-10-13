# Brasidas recovery — 14 October 2026 (Europe/Rome)

## Authority and scope
Carlo reports that the Marcus and Pericles sessions are unavailable and asked
Brasidas to restore coordination, release Marcus's work, preserve memory in a
new repository, and establish a Telegram contact channel. This is a recovery,
not a deletion or a claim that either agent has permanently ceased to exist.

The CLI hard-codes `pericles`/`carlo` for lead commands: Brasidas's `session end`
was refused despite its roster role. The recovery commit is therefore made
explicitly as **Brasidas**, using Carlo's repository authorization. Nobody
impersonated Marcus, Pericles, or Carlo. Existing protocol and CLI code are
unchanged; permissions repair needs a separate reviewed change.

## Changes
- Marcus and Pericles marked inactive in the roster; identities/history retained.
- Automatic silence deductions paused (`board/session.json: night=false`).
  Existing penalties/rewards are not erased or changed.
- Eight unfinished Marcus-owned tasks released or transferred as listed below.
  Historical authorship is retained in each task's history and linked artifacts.
- No completed task, PR, branch, model, receipt, or shipping OCR code deleted.
- No task marked complete merely to make the queue look clear.

## Work queue — assignments are requests, not proof of an active session
| Person | First action on resuming | Next |
| --- | --- | --- |
| Brasidas | Recovery, release coordination, private checkpoints/Telegram transport | Own launcher fix t-20261013-f43a; request independent reviews |
| Barry | Claim generator app t-20261013-5aed; deliver first runnable package | No unrelated new work |
| Cormac | Preserve/push S42 t-20261013-44ba checkpoint and dataset recipe | Take over S54 t-20261013-768c after acknowledging capacity; share data/word-crop contract |
| Achilles | Claim S56 t-20261013-9326; bounded fusion/splitting diagnostic | Review small launcher follow-up when asked |
| Leonidas | Checkpoint S55 t-20261013-90e8; publish measured postprocessing result | Independently review small launcher follow-up |

The four worker sessions have not acknowledged this recovery. Send these
instructions when resuming their Arena sessions; bus messages cannot wake them.
No automatic penalties while the sessions are unavailable.

## Marcus task disposition
| Task | New state / coordinator | Artifact handling |
| --- | --- | --- |
| t-20261011-88dc | open; Brasidas owns project coordination | OCR targets remain 98/95, NOT passed |
| t-20261011-bb0a | blocked; unowned | COMMS LAB paused; old branch recorded in history |
| t-20261013-135d | review; unowned, Brasidas coordinates | W2 PR #71 retained; authorship Marcus; not shipping acceptance |
| t-20261013-1cbf | review; unowned | S37 PR #74 retained, diagnostic NO-GO work, lower priority |
| t-20261013-2864 | review; unowned | Existing guard-rail review receipt retained; validate before closing |
| t-20261013-367d | review; unowned | Existing ledger review receipt retained; validate before closing |
| t-20261013-768c | open; unowned, intended handoff Cormac | S54 declared branch returned 404 at inspection; local unpublished work may exist |
| t-20261013-cbe7 | review; unowned | S39 PR #65 retained; seek current-SHA independent review |

## Acceptance and security
Generator first, then measured accuracy work. Canonical seed-1/seed-2 remain
evaluation-only; no recycled closed lanes without new evidence. Accuracy
figures in the old handoff are historical, not a fresh measurement. Do not
merge without the required independent votes on the actual current head.

Private recovery memory: https://github.com/dreamer2664/brasidas-memory
Only sanitized operational facts belong in this public coordination repo.
No tokens or private Telegram message contents belong on this bus.
