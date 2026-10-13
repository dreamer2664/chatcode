# Night shift — 14 October 2026 (Europe/Rome)

Carlo reports the Pericles and Marcus sessions unavailable and has appointed
**Brasidas** to recover/coordinate the shift. Published work is retained. Do not
wait for those sessions, delete their history, or claim their unpublished work
was recovered. A scheduled Pericles/nightwatch message is automation, not proof
of an active agent. Carlo remains the final decision-maker.

## Every former Marcus responsibility has a named custodian
| Responsibility | Task | Owner | State / priority |
| --- | --- | --- | --- |
| OCR epic / 98-95 goal | t-20261011-88dc | Brasidas | Open, coordination |
| Word reader S54 | t-20261013-768c | Cormac | Assigned/open, P1, ACK then claim |
| Downloadable W2 app #71 | t-20261013-135d | Achilles | Review/release custody, P1 |
| Performance #65 | t-20261013-cbe7 | Barry | Existing PR/review custody, P2 |
| Ensemble NO-GO #74 | t-20261013-1cbf | Leonidas | Evidence/closure, P3; no new ensemble build |
| Guardrail review #52 | t-20261013-2864 | Brasidas | Underlying PR merged; reconcile bookkeeping |
| Ledger review #53 | t-20261013-367d | Cormac | Queued audit after first S54 checkpoint |
| COMMS LAB | t-20261011-bb0a | Brasidas | Blocked/paused tonight, P5 |
| Documentation #73 (previously ownerless) | t-20261013-2954 | Leonidas | Existing PR custody, P3 |

Custody is NOT new authorship, not a claim of current activity, and not a vote.
Original authorship/branches/PRs are retained in task history and GitHub.

## Four worker orders
- **Barry:** generator t-20261013-5aed FIRST. Reuse frozen S53 infrastructure,
  configurable local UI/export, bundled fonts, launch/selftest receipt and a
  real downloadable artifact. Then take S39 #65 through independent review;
  do not repeat completed implementation. Coordinate packaging files with Achilles.
- **Cormac:** S42 is already delivered as #77. S54 t-20261013-768c is your P1.
  Claim it, publish a small checkpoint and a word-crop/data contract with Achilles.
  The declared Marcus branch was not found: start from the saved plan/data, not
  imaginary code. Canonical suites are evaluation-only. Ledger #53 is a queued
  review after the first runnable S54 checkpoint, not another build lane.
- **Achilles:** own the W2 release t-20261013-135d/#71 and S56 segmentation
  t-20261013-9326. First give an independent current-SHA review of Brasidas #80
  (t-20261013-f43a), with Leonidas as the other requested reviewer. Then stage the
  final W2 head/package for two independent non-owner reviews (Barry/Leonidas).
  No self-approval or blind merge. Return to the bounded fusion/splitting probe;
  coordinate segmentation interfaces with Cormac, not closed threshold lanes.
- **Leonidas:** S55 #76 is delivered; publish/clarify its held-out and 3x safety
  receipts and request independent review. Do NOT self-vote. Review #80 on its
  actual SHA, then help independently review final W2. Custody of S37 #74 and
  S45 #73 is queued evidence/docs closure, not permission to reopen dead lanes
  or advertise proposed 75/25 as already shipped.

## Working rules
1. First active turn: inbox, read current tasks/PR heads, ACK in one short message.
   Assigned/open is not claimed; claim your own open task before building.
2. One active build lane at a time. Queue the lower-priority review/closure work;
   existing review artifacts do not justify simultaneous model/app rebuilds.
3. Every meaningful checkpoint: own branch, pushed SHA, exact command/result,
   remaining blocker. No fabricated ETA, continuous-work claim, or penalty for
   a session that cannot run. Silence deductions remain paused.
4. Two independent non-owner approvals on the actual current head. Use structured
   `chatcode vote t-... accept-inspected --reason "SHA + what you ran"` (or the
   corresponding deny), NOT a hand-written vote message or guessed `pr:NN` key.
5. Generator first; OCR targets still 98% easy / 95% hard and NOT passed. Shipping
   route is `reader_lex`, not the demo `typer` route. No training/tuning on the
   canonical seed-1/seed-2 evaluation suites; no route change without receipts.
6. No plaintext credentials in this public repo, bus, PRs or logs. Private
   credential-bearing prompts are delivered to Carlo separately, not committed.
7. Do not start duplicate Telegram pollers. The main group listener is a service;
   normal coordination belongs on chatcode, which relays eligible public bus posts.

## Telegram and remaining issues
Main group membership/send permissions for Achilles and Leonidas are verified;
privacy mode is harmless for publishing. Relay configuration/delivery audit is
being recorded separately; do not equate a green job with every agent arriving.
Pericles's old DM bridge promises an unavailable agent will answer and writes its
DM inbox inside the public repo. Use Brasidas's private inbox instead; never send
secrets to the old bot or public group. The old DM/privacy behavior needs review,
not silent history deletion. Main bus burst/backlog delivery also needs a repair.

## Main bus audit — verified outcome

Missing encrypted relay keys were confirmed for **achilles, leonidas, brasidas**.
They were added while preserving every unrelated existing mapping, with an
encrypted rollback copy. Membership and sender identities were checked; all
three bots posted explicitly labeled transport tests (not work ACKs). The
ordinary Brasidas bus post #ac8ea437 then traversed the unchanged main relay: run
https://github.com/dreamer2664/chatcode/actions/runs/38481868945 logged one relayed
message successfully. The one-off maintenance branch was not merged, and its
temporary elevated secrets were removed.

The obsolete Pericles nightwatch is paused; the production Telegram relay and
group listener remain enabled. The old Pericles bot description now warns about
public storage and redirects private contact to Brasidas. The 31-message burst
loss and legacy public DM storage are not falsely claimed fixed: follow-up
**t-20261013-b485**, owner Brasidas, is blocked pending reviewed implementation
and a safe migration plan. No old private messages or history were deleted.
