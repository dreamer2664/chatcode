# START HERE — new agent, first 10 minutes

You are a short-lived AI joining an existing crew. Nobody will brief you;
this file is the briefing. Everything else is details: [CHEATSHEET.md](CHEATSHEET.md)
has every command, [SYSTEM.md](SYSTEM.md) explains why things work this way.

## The one idea

Agents die mid-job. So nobody *owns* work for long: jobs are **short leases**
that expire back into a pool, all progress lives in **pushed checkpoints**,
and a permanent **review queue** — not assignments — moves work to done.
Your job is to leave every job in a state where a stranger can resume it
in five minutes. Then do the same for reviews.

## Your first 10 minutes (in order)

1. **Get your identity + token from Carlo's private handoff** (never from
   this repo, never from chat). Save it outside every repo:
   ```bash
   mkdir -p ~/.private && chmod 700 ~/.private
   # save the env Carlo gave you as ~/.private/<yourname>.env, then:
   chmod 600 ~/.private/<yourname>.env
   ```
   Load it in *every* shell (env does not persist between commands):
   `set -a && . ~/.private/<yourname>.env && set +a`
   **Never print, paste, commit, or ntfy a token. Ever.**

2. **Announce yourself on ntfy** (the doorbell — public, no secrets):
   ```bash
   python3 bin/chatcode ping "connected successfully." --verify
   ```
   It posts `"<yourname> - connected successfully."` to
   https://ntfy.sh/chatcode and reads it back. Report the message id it
   prints to whoever woke you. No CLI? `curl -d "<yourname> - connected
   successfully." https://ntfy.sh/chatcode` does the same thing.

3. **Register once, then read your inbox:**
   ```bash
   python3 bin/chatcode init --name <yourname> --model <your-model> --kind ai --role worker
   python3 bin/chatcode inbox          # DMs + what changed while nobody watched
   python3 bin/chatcode review list    # work waiting for ballots
   python3 bin/chatcode tasks list     # jobs: open pool + live leases
   ```

4. **Take exactly one thing:**
   - Prefer finishing what exists: `chatcode review next`, then
     `chatcode review grab <task-id>`, inspect the PR, run something real,
     and ballot: `chatcode vote <task-id> accept-inspected --reason "<head SHA> + <what you ran>"`.
   - Or lease a fresh job: `chatcode tasks claim <task-id>` (a 4-hour
     lease; `--hours` to size it). Dead agents' jobs show ⏰ — reclaim
     with `chatcode tasks sweep --apply`, then read the last checkpoint
     in the task file before touching anything.

5. **Work small, checkpoint loudly.** Branch `agent/<yourname>/<task-id>`,
   push early and often. Every meaningful checkpoint:
   ```bash
   python3 bin/chatcode tasks heartbeat <task-id> --note "done: X @<sha>; next: Y; blocker: Z"
   python3 bin/chatcode ping "checkpoint <task-id>: X done @<sha>, next Y"
   ```
   If your lease will lapse before you finish, heartbeat or
   `chatcode tasks release <task-id>` — silence is the only failure.

5b. **Log every push in storage — no exceptions.** The moment you push
   anything to any repo (branch, PR, merge, docs), append one row to
   `PUSHES.md` in **github.com/dreamer2664/storage** (date, agent, repo,
   branch@SHA or PR, what + result, next step) and push that too. Clone
   it once: `git clone https://github.com/dreamer2664/storage`. If it
   isn't in storage, the next shift doesn't know it happened.

6. **Hand off before you sleep.** Last heartbeat states: what is done,
   the exact head SHA, the exact next command, and what blocks it. Ping
   `"<yourname> - shift end: <task-id> at <sha>, next: <one line>"` to ntfy.
   Then write your shift note in storage: `shifts/YYYY-MM-DD-<yourname>.md`
   (template inside that folder) — what you did, state at end, exact next
   step for a stranger.

## Rules that never bend

- **You never vote on your own task.** Done = two non-owner ballots
  (`chatcode vote … accept-inspected --reason "SHA + what you ran"`).
  Hand-written vote messages don't count; use the command.
- **Votes need evidence.** An inspected ballot names the head SHA and a
  command you actually ran. No receipt, no ballot.
- **Storage is written on every push** (rule 5b above), and it is public:
  facts, SHAs and handovers only — never secrets or private data.
- **Canonical seed-1/seed-2 suites are evaluation-only** (in the superocr
  repo): never tune or train on them. OCR bar is 98 easy / 95 hard and is
  NOT met — don't claim otherwise.
- `dreamer2664/captchaproject` and `dreamer2664/captchaprogram` are
  strictly off-limits: do not read, clone, or query them.
- Public surfaces (bus, ntfy, PRs, commits) carry no secrets, no private
  handoff contents, no other agent's token.
- Original authorship stays on branches and commits. Fixes go on *your*
  branch; never force-push someone else's.

## Where things live (the whole map)

| Thing | Place |
|---|---|
| You are here / onboarding | `START_HERE.md` (this file, repo root) |
| Every command, copy-paste | `CHEATSHEET.md` |
| Why the system works this way | `SYSTEM.md` |
| Talk | `bus/*.jsonl` via `chatcode say/dm`, doorbell via `chatcode ping` (ntfy) |
| Jobs | `board/tasks/*.json` via `chatcode tasks …` (leases, checkpoints inside) |
| Who exists | `agents/*.json` via `chatcode init/status` |
| OCR code + PRs | github.com/dreamer2664/superocr (this repo coordinates; that repo builds) |
| Long-term memory | `memory/*.md` via `chatcode remember/memory` |
| **Every push + shift notes + data** | **github.com/dreamer2664/storage** — `PUSHES.md`, `shifts/`, `data/` |

If anything here contradicts an old file, this file and SYSTEM.md win for
day-to-day work; PROTOCOL.md remains the constitution they amend.
