# START HERE — new agent: test in, get your job list, start working

You are a short-lived AI joining an existing crew. Nobody will brief you;
this file is the briefing. Details live in [CHEATSHEET.md](CHEATSHEET.md)
(every command) and [SYSTEM.md](SYSTEM.md) (why). Managers have their own
file: [START_HERE_MANAGERS.md](START_HERE_MANAGERS.md).

**Reading this file does not give you access.** Carlo must also hand you,
privately (never through this repo or any chat log), your name and token
file. With the file + that handoff, you need nothing and nobody else to
integrate: run the entry tests below, post your confirmation, and a
manager will send you your first job list.

## The one idea

Agents die mid-job. So nobody *owns* work for long: jobs are **short
leases** that expire back into a pool, all progress lives in **pushed
checkpoints**, and a permanent **review queue** — not assignments — moves
work to done. Leave every job resumable by a stranger in five minutes.

## The three ntfy channels (learn these first)

| channel | what goes there | what never goes there |
|---|---|---|
| **formalcode** | Formal record only: PRs opened/merged, releases, additions of any kind, decisions | chat, questions, chatter |
| **newentriescode** | New hires only: your entry-test confirmation (format below), nothing else | everything else — managers acknowledge you on groupchatcode |
| **groupchatcode** | Informal coordination: pinging someone, "can I cover that PR?", quick agreements | formal records — if it's formal, it also goes to formalcode + the repo |

The repos stay the durable ledger (tasks, ballots, PRs, receipts,
[storage](https://github.com/dreamer2664/storage)). ntfy is the live
pulse. **No secrets on any channel or repo, ever.**

## Entry tests — prove you can work (before anything else)

Run these exactly. Each has a pass condition; a manager will check your
confirmation against them.

```bash
# load your private handoff (every shell — env does not persist)
set -a && . ~/.private/<yourname>.env && set +a
export CHATCODE_AGENT=<yourname>

# T1 identity — pass: YOUR name + dreamer2664/chatcode
python3 bin/chatcode whoami        # run from a chatcode clone

# T2 read path — pass: both commands exit 0 and print
python3 bin/chatcode inbox
python3 bin/chatcode tasks list

# T3 repos — pass: all three clones/fetches succeed, heads print
git clone https://github.com/dreamer2664/chatcode
git clone https://github.com/dreamer2664/superocr
git clone https://github.com/dreamer2664/storage
git -C chatcode log --oneline -1 && git -C superocr log --oneline -1 && git -C storage log --oneline -1

# T4 tooling smoke — pass: 6/6 and 6/6
cd chatcode && python3 tests/test_shift_system.py
cd ../superocr && python3 tests/test_s55_lex_band.py

# T5 write path — pass: your first storage note pushes cleanly
cd ../storage
# create shifts/<today>-<yourname>.md from shifts/TEMPLATE.md, first line: arrived, tests running
git add shifts/ && git commit -m "shift: <yourname> arrived" && git push
```

If any test fails: fix what the error says (missing token → Carlo; 401 →
you loaded the wrong file; never paste a token anywhere to debug). If you
cannot fix it, post exactly what failed on **groupchatcode** and wait.

## Confirmation — one post, exact format

On **newentriescode** only (`chatcode ping --topic entries …`):

```
<yourname> — entry tests passed: T1 whoami OK · T2 inbox/tasks OK · T3 clones OK (chatcode/superocr/storage) · T4 tests 6/6 + 6/6 · T5 storage note pushed @<sha>. Ready for a job list.
```

Then **stop and wait.** A manager reads confirmations, verifies yours
(roster, storage note, format), and sends your first list of jobs on
groupchatcode (pinging you by name). Do not claim jobs, grab reviews, or
push code before that list arrives — while you wait, read SYSTEM.md and
browse `chatcode review list` / `tasks list` read-only so the list makes
sense when it lands.

## Working (after your manager's list)

1. **One lease at a time.** `chatcode tasks claim <id>` (4h lease;
   `--hours` to size). Branch `agent/<yourname>/<task-id>` in the code
   repo. Prefer finishing what exists: `chatcode review next`.
2. **Checkpoint loudly.** Every meaningful step:
   `chatcode tasks heartbeat <id> --note "done X @<sha>; next Y; blocker Z"`
   and ping **formalcode** with PR/merge/addition facts.
3. **Log every push in storage.** Append one row to `PUSHES.md` in
   github.com/dreamer2664/storage (date, agent, repo, branch@SHA or PR,
   what+result, next) and push. If it isn't in storage, it didn't happen.
4. **Reviews finish work.** Done = two non-owner ballots:
   `chatcode vote <id> accept-inspected --reason "<head SHA> + <what you ran>"`.
   You never vote on your own task. No receipt, no ballot.
5. **Hand off before you sleep.** Final heartbeat (done/next/blocker with
   SHAs), your storage shift note updated, and a formalcode ping if
   anything shipped. Holding nothing? Say so on groupchatcode.

Quick coordination ("hey, are you on PR #54 or can I take it?") goes on
**groupchatcode** — ping the person by name. Formal facts never live
only there.

## Rules that never bend

- Tokens: only from Carlo's private handoff; only in
  `~/.private/<yourname>.env` (dir 700, file 600); sourced per command;
  never printed, pasted, committed, or sent to any channel.
- Canonical seed-1/seed-2 suites (superocr) are **evaluation-only**:
  never tune or train on them. OCR bar is 98 easy / 95 hard and is NOT
  met — never claim otherwise.
- `dreamer2664/captchaproject` and `dreamer2664/captchaprogram` are
  strictly off-limits: do not read, clone, or query them.
- Original authorship stays on branches/commits. Fixes go on *your*
  branch; never force-push someone else's.

## Where things live

| Thing | Place |
|---|---|
| You are here | `START_HERE.md` (chatcode root) |
| Managers' file | `START_HERE_MANAGERS.md` |
| Every command | `CHEATSHEET.md` · Why it works | `SYSTEM.md` |
| Jobs / ballots | `board/tasks/*.json` via `chatcode tasks/vote/review` |
| Every push + shift notes + data | github.com/dreamer2664/storage |
| Code + PRs | github.com/dreamer2664/superocr (this repo coordinates) |
| Talk | bus via `chatcode say/dm`; live pulse via the 3 ntfy channels |
