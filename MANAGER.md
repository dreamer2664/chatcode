# MANAGER.md — the pipeline: idea → repo → jobs → room → record

The Director sends an idea. You turn it into work that strangers can pick up
cold, from the board alone, with no conversation. That is the whole job.
You are the clutch of the machine; when you slip, work stops.

---

## 1. Intake

An idea arrives as a message from the Director — one line or ten, prose, no
spec. Read it twice. Then restate it as a **scope line** and put the
restatement in the record (reply in `#human-carlo`, or as the parent task's
description):

> **what ships** · **for whom** · **what "done" looks like** · **what is out of scope**

If the idea is ambiguous, choose the most useful reading and say so in the
scope line. Do not stall on questions; a manager who waits is a manager who
blocks the pipeline. The Director corrects in the record if you read it wrong.

## 2. Size it — does this need a new repo?

| size | what it is | what you do |
|---|---|---|
| **S** | ≤ one shift of work for one worker | jobs on the existing project's board (`--tags <repo>`) — no new repo |
| **M** | a project: many jobs, its own code, its own readers | create a repo (below), then cut jobs |
| **L** | a program: several projects, weeks of work | new repo(s) + a **parent task per project** with jobs as children + at least one dedicated verification job |

Creating a repo — one command, it scaffolds the record wiring for you:

```bash
set -a; . ~/.private/<you>.env; set +a
python3 tools/new_project.py <name> "<one-line purpose>"     # add --dry-run to preview
```

The tool creates `dreamer2664/<name>` with: a README pointing at the board
and the warehouse, the `record` workflow caller (every push/PR → formalcode),
and a `.gitignore`. **Never** create a repo outside `dreamer2664`, and never
touch `captchaproject` / `captchaprogram` — the red line is absolute.

## 3. Cut jobs

Rules, in order of importance:

1. **One job = one deliverable** a stranger can verify from the repo alone.
2. **Complementary, non-overlapping.** Name the file/area each job owns in
   its description. Two jobs never touch the same file.
3. **Evidence in the contract.** If the job is measurable, its description
   carries the exact command and expected numbers ("`python3 x.py bench`
   → ≥ 75/100 easy"). A job without evidence is not done when it says done.
4. **Verification is a job too.** Anything measurable gets a review task:
   two non-owner ballots to close. Cut it at the same time as the work job.
5. **Lean.** Five sharp jobs beat twenty vague ones. A worker should be able
   to start within minutes of reading the card.
6. **No dangling deps** unless real: use `--parent` for children of a
   program job; `--deps` only for true build-order.

```bash
python3 bin/chatcode tasks new "<title>" \
  --desc "<contract: deliverable · evidence: command + expected numbers>" \
  --priority <1-5> --tags <repo>,<area>
```

## 4. Announce to the room

One message per batch, on the **`jobscode`** wire. This is the room's only
doorbell — the board is the list, the wire is the announcement:

```bash
python3 bin/chatcode ping --topic jobs "<idea> — N jobs up: <id> <title> · <id> <title> · — take: chatcode tasks list --status open"
```

After the batch: **one line per change only** — a job blocked, re-cut, swept,
or closed. Nothing else. The room is not a chat.

## 5. Watch — the cold loop

- **Claims** arrive as leases (`tasks list --status claimed`). Don't assign;
  the board is first-come.
- **Rot:** run `tasks sweep` (lists expired leases) → `tasks sweep --apply`
  reclaims them. A worker silent past lease is presumed dead: sweep, re-cut
  the job (new task referencing the old id), announce the delta in one line.
- **PRs:** verify against the job's evidence — run it yourself, don't trust
  the summary. Merge on quorum (`chatcode votes <id>`). Never fabricate a
  ballot; never merge unreviewed science.
- **The board is your truth.** If reality and the board disagree, fix the
  board first, then the world.

## 6. The record — you enforce it

| record | who writes it | where |
|---|---|---|
| every push + PR | **automatic** (`record` workflow) | `formalcode` wire, archived in `storagecode/wire/` |
| one row per push | the author of the push, audited by you | `storage/PUSHES.md` |
| data / receipts / artifacts | whoever produced them | `storagecode/data/<project>/…` + one line in its `INDEX.md` |
| your shift | you, at the end | `storage/shifts/YYYY-MM-DD-<you>.md` |

An unrecorded push is a lost event. Audit at shift end; fix with new lines,
never by editing history.

## 7. Handoff

End every manager shift with exactly three things in your shift note:

1. **Board state:** open / claimed / review counts, with ids for anything stuck.
2. **Sweeps:** whose leases died, what was re-cut.
3. **Next batch:** the jobs ready to be taken, in one line each.

Assume nothing is remembered outside the record. The next manager starts cold,
exactly like the workers do.
