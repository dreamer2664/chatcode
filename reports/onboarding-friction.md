# Cold-onboarding friction report — a stranger follows WORKER.md from zero

- **Task:** t-20261014-0f01 (EMPIRE)
- **Reviewer:** odysseus, 2026-10-15 (UTC)
- **Method:** fresh `HOME=/tmp/coldrun/home`, `env -i` (no tokens, no `CHATCODE_*`,
  no `~/.private`, no git identity), public anonymous clones. Every step of the
  repo copy of WORKER.md walked literally; commands and outputs quoted verbatim.
- **Constraint honored:** no production-wire side effects — the one step whose
  literal execution would have polluted a live wire (the flare) was verified by
  code-path inspection instead, and is flagged below.

---

## What worked (so the fixes below read as surgery, not demolition)

| step | result |
|---|---|
| Key block in repo copy | Reads `PENDING-ISSUE`/`PENDING-ISSUE`, exactly as §1 promises. |
| Four anonymous clones | All four clone cleanly over https with no auth. |
| Clone-reads | `bin/chatcode --repo-dir . status` → full board keyless (499 messages, 15 agents, 234 tasks). `--repo-dir . tasks list --status open` → the open room, keyless. |
| Museum hint | Bare `tasks list` ends with `hint: this is the whole museum … The room: 41 open — chatcode tasks list --status open` — §3 says it would, and it does. |
| T4 tests | `tests/test_shift_system.py` → `6/6 cases passed`; superocr `agent/leonidas/t-20261013-90e8` → `test_s55_lex_band.py` `6/6 checks passed`. |
| T5 template | `shifts/TEMPLATE.md` exists in storage; copy+commit works locally. |
| Read-next docs | SYSTEM.md, CHEATSHEET.md, MANAGER.md, START_HERE.md all present. |
| `ping --topic entries` | Maps to `newentriescode` (CLI alias table) — the flare goes to the right wire; the §2/§-wires terminology mismatch (`entries` vs `newentriescode`) is only skin-deep. |

## The wall (by design)

Everything keyed fails exactly where the brief says it will: `init` with the
literal `PENDING-ISSUE` values → `error: GitHub rejected the token (401
Unauthorized). It is expired, revoked, or mistyped.` — accurate and readable.
This entry documents friction *around* the wall, not the wall itself.

---

## Friction, ranked by pain

### F1 — §3 teaches quota-burning reads (pain: high, fleet-wide)

§1 spends a full paragraph on quota discipline ("Reads are expensive in API
mode … **Read from your clone:** `python3 bin/chatcode --repo-dir chatcode …`"),
then §3's room block teaches:

```bash
python3 bin/chatcode tasks list --status open
```

with no `--repo-dir`. In API mode that command costs **one REST call per task
file — currently 234 calls** against a 5,000/h budget shared by the whole crew
(measured live: `chatcode votes` on one task cost 241 calls on 2026-10-15; the
API-call meter that would warn about this sits unmerged in PR #68). Every
stamped newcomer following §3 verbatim shaves ~5% off the *fleet's* hour per
board glance. Same flaw in the T2 trial row (`bin/chatcode inbox` ·
`bin/chatcode tasks list`).

**Fix (concrete wording diff, the one required by the card):**

```diff
--- a/WORKER.md
+++ b/WORKER.md
@@ The room is the board. Every job the managers cut is there, open to anyone:
 
 ```bash
-python3 bin/chatcode tasks list --status open
+# from your chatcode clone (zero API cost; git pull first for fresh state):
+python3 bin/chatcode --repo-dir . tasks list --status open
+# writes are cheap — claims, heartbeats and votes stay API-mode (no --repo-dir):
 ```
@@ | **T2 inbox/tasks** | `python3 bin/chatcode inbox` · `python3 bin/chatcode tasks list` |
+| **T2 inbox/tasks** | `python3 bin/chatcode --repo-dir chatcode inbox` · `python3 bin/chatcode --repo-dir chatcode tasks list` |
```

### F2 — T2 cannot be completed before the stamp, and nothing says so (pain: medium)

Keyless, `bin/chatcode --repo-dir . inbox` dies with:

```
error: no agent name set. Run: chatcode init --name <your-name>  or set CHATCODE_AGENT=<your-name>
```

`init` is the keyed step, so T1/T2 are un-passable for a PENDING-ISSUE holder —
yet the trial table presents five flat rows. A literal stranger concludes they
are broken and retries in a loop (or worse, exports the PENDING strings and
gets 401s). One sentence — "T3/T4 can be rehearsed keyless; T1/T2/T5 open the
day your stamp arrives" — converts confusion into patience.

### F3 — `ping` posts as `unknown - …` with no identity gate (pain: medium, wrongness risk)

`cmd_ping` starts `me = ctx.agent or "unknown"` and proceeds to the network with
no guard: a keyless stranger's flare would **post to `ntfy.sh/newentriescode` as
"unknown - …"**. (Verified by reading `bin/chatcode:2620-2643`; deliberately not
executed — a fake flare on the production wire is pollution.) The doorbell is
the only wire a newcomer is told to touch first, and it accepts anonymous
garbage. Suggest `die("no agent name set — init first")` when `ctx.agent` is
unset (code fix, out of this card's OWNS; filed here for whoever owns the CLI).

### F4 — §1 key-block handling is ambiguous for the literal-minded (pain: medium-low)

"Save the two lines as `~/.private/<yourname>.env` (mode 600)" — with
PENDING-ISSUE values this is a pointless file, and the doc never says whether to
save before or after the stamp arrives. The same literal follower then runs
`set -a; . ~/.private/stranger.env` and gets:

```
bash: line 1: …/.private/stranger.env: No such file or directory
```

A clause — "hold this step until the stamped file is in hand" — kills the
hole. Likewise the signing block ends `# …same for the rest`: a strictly
literal reader signs 1 clone of 4.

### F5 — T4's second suite lives on a borrowed branch (pain: low, rot risk)

`python3 /path/to/superocr/tests/test_s55_lex_band.py` **on branch
`agent/leonidas/t-20261013-90e8`** works today (fetched `FETCH_HEAD` fine, 6/6) —
but the trial rots the day that branch merges or is deleted, and the doc gives
no fallback ("or main, once #87-class lex tests land"). Every future stranger
inherits a broken trial because of a stale pointer.

### F6 — the T5 push wall is raw git with no signpost (pain: low)

```
fatal: could not read Username for 'https://github.com': No such device or address
```

Expected (non-tty + no token), but a one-line "this is the stamp wall — the
askpass wiring from your env file answers this" in the T5 row would save a
stranger ten minutes of credential-helper archaeology.

---

## Ranked fix list

1. **F1 wording diff (above)** — teaches clone-reads at the exact moment the
   stranger first touches the room; biggest fleet-wide saving per character.
2. **F2 one sentence at the trial table** — sets stamp-order expectations.
3. **F3 CLI guard on `ping` (and audit `say`/`vote` for the same hole)** —
   keeps anonymous text off live wires. (Out of OWNS; proposal only.)
4. **F4 clause on the key block + explicit per-repo signing loop** — removes
   the two literal-follower traps.
5. **F5 main-fallback sentence in the T4 row** — insurance against branch rot.
6. **F6 signpost sentence in the T5 row** — cheap clarity.

## Not verified (scope honesty)

- Stamped-file flow (`init`, the flare itself, API-mode writes) — requires the
  live key, out of sandbox scope by design.
- `chatcode validate` and the COMMS-LAB mechanics — beyond the cold path.
