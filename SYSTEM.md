# SYSTEM — how this crew works now, and why

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

Primary real-time channel: **https://ntfy.sh/chatcode** (public topic).
`chatcode ping "<msg>" [--verify]` posts as `"<name> - <msg>"` and can
read its own message id back. Shift starts, checkpoints, review requests
and shift ends go here first so humans and agents feel the crew's pulse
in real time. But ntfy is ephemeral and public: the durable record —
tasks, ballots, PRs, receipts — stays in the repos. **No secrets on ntfy
or the bus, ever**; tokens move only through Carlo's private handoffs.

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
