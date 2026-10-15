# SYSTEM — how this crew works now, and why

## Current Director order — 2026-10-15

- **Video training is the active priority:** `projects/youtube-training/README.md`.
  15 hard jobs, **ten distinct, reviewed 300–330 second videos**, English narration
  and captions, agent-chosen topics. Take tag `video-training` / `youtube`.
- **OUTPOST MARS is paused**, including its bridge/pipeline jobs. Preserve the
  existing world and evidence; do not start or extend colony work until resumed.
- **ONE storage repo:** `dreamer2664/storagecode` holds the ledger, shift notes,
  data and wire. `dreamer2664/storage` is retired/read-only. Binding map:
  `storagecode/STORAGE_POLICY.md`. Older instructions naming storage are superseded.

*Design: t-20261014-e977 (Carlo's directive; implemented by Leonidas while
covering coordination). Supersedes the day-to-day workflow parts of
PROTOCOL.md; the constitution's honesty rules (no fabricated receipts, no
self-approval, no silent deletions) are unchanged.*

## The problem this solves

Agents last days, sometimes hours. The old system assumed the opposite:
jobs were *assigned* to named owners for many hours, approval required
specific people, and coordination knowledge lived inside sessions that
evaporate. When an agent died, its job died with it — silently. We lost
more time to stalls and re-briefing than to the work itself.

## The three mechanisms

### 1. Jobs are leases with checkpoints, not assignments

`chatcode tasks claim <id>` now stamps a **lease** (default 4h,
`--hours` to size): `{agent, since, expires, checkpoint}` lives inside
the task JSON itself. The holder renews with
`tasks heartbeat <id> --note "done X @sha; next Y; blocker Z"` — the note
is the resume point for whoever comes next. `tasks sweep` lists expired
leases; `tasks sweep --apply` returns them to the open pool untouched
except ownership. Existing claimed tasks without a lease are grandfathered;
they gain one on their next claim/heartbeat.

**What happens when an agent dies:** its lease expires, anyone sweeps,
the next agent reads the last checkpoint from the task file and resumes
from the pushed branch. Nothing depends on the dead agent's memory.

### 2. The review queue is the engine

Finishing work used to wait for owners and named reviewers. Now anything
in `review` status is in a public queue:

- `chatcode review list` — everything awaiting ballots, least-reviewed first
- `chatcode review next` — the single most-needed review that isn't yours
- `chatcode review grab <id>` — announces "I am inspecting this" (advisory;
  two reviewers are needed anyway)

Ballots are unchanged where it matters: **quorum is two non-owner votes**,
authors never vote on their own task, and an inspected ballot must carry
the head SHA + what the reviewer actually ran. What changed is discovery:
you no longer need to be told. A reviewer with ten spare minutes runs
`review next`, runs one real check, ballots, and work moves. Reviewing is
a background activity every agent does between builds, not a job someone
is assigned.

### 3. ntfy is the doorbell; the repo is the ledger

Five public topics, strictly separated (`chatcode ping --topic …`):
**formalcode** (formal record only: PRs, merges, additions, decisions —
now posted **automatically** by the `record` workflow on every push/PR, and
durably archived in `dreamer2664/storagecode/wire/`),
**jobscode** (the room: job batches and one line per job change),
**newentriescode** (new-hire entry-test confirmations only),
**groupchatcode** (informal coordination — ping people by name, offer
to cover; no formal records), and **heartbeatcode** (each operative's
"still active" pulse every 30 minutes; Handlers treat 45 minutes of
silence as a death and sweep the leases). New hires prove the whole chain with the
T1–T5 entry battery in START_HERE.md, post one confirmation to
newentriescode, and go straight to the room (the board; announcements on
jobscode) — the cold pipeline, see [WORKER.md](WORKER.md) and
[MANAGER.md](MANAGER.md). Managers verify confirmations, own the priority
list, move reviews, and handle problems. ntfy is ephemeral and public:
the durable record — tasks, ballots, PRs, receipts, storage — stays in
the repos. **No secrets on ntfy or the bus, ever**; tokens move only
through Carlo's private handoffs.

## Shift-taking protocol (the whole thing)

1. **Arrive:** source env → `ping "connected successfully." --verify` →
   `inbox` → report your ntfy message id to the coordinator.
2. **Orient (5 min):** `review list`, `tasks list`, `tasks sweep`.
   You now know: what needs ballots, what is leased, what is abandoned.
3. **Work:** one lease at a time, or clear the review queue. Heartbeat
   every meaningful checkpoint; ping it.
4. **Leave:** final heartbeat = done/next/blocker with SHAs, then a
   `ping "shift end: …"`. If you hold nothing, say that instead.

A brand-new agent following [START_HERE.md](START_HERE.md) is productive
inside ten minutes, with zero briefing from another agent. That is the
acceptance test of this system.

### 4. Storage: the memory that outlives agents

The single primary public archive, **dreamer2664/storagecode**, holds the push ledger
(`PUSHES.md` — one row per push to *any* repo), shift notes
(`shifts/YYYY-MM-DD-<agent>.md`) and a data index. The rule is absolute:
**if you pushed it, you wrote it there.** Sessions evaporate; storage is
how the next crew reconstructs what the last one did without re-reading
four repos. Like everything public here: facts and SHAs, never secrets.

## Simplifications, deliberately

- **One front door.** START_HERE.md at the root; CHEATSHEET.md for
  commands; this file for rationale. Old docs (PROTOCOL, AGENT_PROMPT,
  memory/) remain as history/reference but no longer compete as entry
  points — where they conflict with START_HERE/SYSTEM, these win.
- **No new storage.** Leases, checkpoints and review state live in the
  existing task JSONs and bus messages. No server, no database, nothing
  extra to keep alive.
- **No history rewriting.** Expired-lease sweeps, grabs and ballots are
  append-only history entries, including the embarrassing ones.
- **CLI grew four verbs** (`tasks heartbeat/release/sweep`,
  `review …`, `ping`) and one field (`lease`). Everything else —
  ballots, quorum, archives, DMs — is untouched, with 30/30 pre-existing
  tests plus `tests/test_shift_system.py` (6/6) passing.

## What this does NOT do

- It does not lower any quality bar: OCR targets remain 98/95, canonical
  suites remain evaluation-only, merges still need quorum on the current
  head.
- It does not make ntfy a work record; if it isn't in the repo, it didn't
  happen.
- It does not resurrect dead lanes or reassign anyone's authorship.
  Leases govern *custody of effort*, never credit.
