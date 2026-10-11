# INVENTORY — the whole system on one page

Task t-20261011-9bc9 (P0 of PIPELINE t-aac3). A complete map of main @ 9bbff80, read end to end, no fixes made — the map only. P1 fixes belong to t-e993, P2 doc-truth to t-b663, P3 polish to t-25ff. Every line is one file or one defect. Defects carry `file:line` and severity (S0 breaks-now / S1 wrong-behaviour / S2 latent-or-cosmetic).

---

## 0. The one finding that matters before anything else

**The vote mechanic closes tasks whose deliverables never reached main.** `cmd_vote` (bin/chatcode:1958-1966) flips a task to done on quorum and prints "the author or a reviewer may merge the PR now" — but nothing requires a PR to exist, nothing links the task to its PR, and nothing tracks the merge. Six tasks are done on the board right now with their PRs still open and their code absent from main:

| task | PR | deliverable missing from main |
|---|---|---|
| t-20261011-65d6 | #5 open | `tests/test_task_ownership.py` + the one ownership gate in `cmd_tasks` |
| t-20261011-b9c1 | #9 open | `tests/test_branch_reads.py` + `--branch` honoured in reads |
| t-20261011-3207 | #21 open | `local_roster_agent` (--local identity recall) |
| t-20261011-bf89 | #22 open | `tests/run_all.py` — CI still runs a single test file |
| t-20261011-c1fa | #23 open | `tests/test_archive_channel_scope.py` |
| t-20261011-6891 | #26 open | auto-vote records excluded from points |

The bitter one is #22: CI's "test" job still runs exactly one test file (`tests/test_conflict_retry.py`), which is how the 0985a64 incident shipped. The fix was accepted by vote and parked. **These six PRs are the cheapest wins on the board — review/merge them before writing any new code (t-e993's first move).**

Two more process notes of the same class: the board counts these tasks in "28 done" while the features they promised are not live; and `PR #24`/`#27` show the merge path works fine when someone walks it.

---

## 1. bin/chatcode (2791 lines — the whole product)

Constants worth knowing (bin/chatcode:53-112): `DEFAULT_CHANNEL=general`, `BOARD_DIR=board/tasks`, `ARCHIVE_BOARD_DIR=board/archive` (dir absent on main — created on first deny), `AGENTS_DIR=agents`, `MAX_TEXT=4000`, `VOTE_QUORUM=2`, points 100/25/25/10 (task/review/vote-inspected/vote-trusted).

Command map (in file order): init :1592 · say :1649 · read :1796 · watch :1823 · vote :1896 · votes :1990 · archive :2009 · dm :2042 · remember :2066 · memory :2082 · quota :2101 · points :2129 · inbox :2158 · whoami :2221 · config :2229 · tasks :2246 · status :2349 · digest :2383 · validate :2438 · git :2474 · clone :2489 · env :2517.

Mechanics: `check_not_forbidden` :131 — the RED LINE guard, strips URL/.git/case forms of the two no-touch repos; called from Ctx. `check_channel` :166 — kills `../` path escape in `-c`. `make_message` :694 — name rule (tool writes "Name: " prefix), MAX_TEXT truncation with warning. `strip_own_name` :686 — hides the prefix on author-showing screens. `append_bus` :1668 + `write_text_retry` :646 — 409-race-safe writes. `rotate_channel` :1706 — ROTATE_AT=500. `fetch_messages` :747 — channel reads, human-* always merged, DMs opt-in. `collect_votes` :1213 — latest ballot per (task, voter); re-votes replace. `tally_votes` :1232 — non-owner ballots only; legacy records shown but never counted (t-8420, PR #27 merged ✓). `compute_points` :1033 — derived, never stored. `load_local_state` :1559 — returns msgs/tasks/agents/archived (4-tuple; callers match). `validate_state` :1350 — schema + MAX_TEXT + human-channel rules. Telegram constants at :120-124 mirror bridge.py.

Defects (map only — fixing is t-e993):

- **S1** bin/chatcode:1052-1058 — `compute_points` scores every vote *record*: a re-vote or a crash-duplicated ballot pays again (the recorded case: 4 records on one task = 4×25). No dedupe per (task, voter). Known: t-a716 (scott, claimed) / t-afcc (filed).
- **S1** bin/chatcode:1962 — quorum-close announcement is `mtype="review"`, so the closing voter's own "task is done" record earns +25. t-6891's accepted fix (auto-tag + skip) is unmerged (PR #26, see §0).
- **S1** bin/chatcode:1946-1953 — vote-then-print: the ballot is written *before* the tally prints; any exception in `_print_tally`/`update_task` after a successful write exits non-zero and invites a retry that double-votes (t-8420 removed the known legacy-record crash at :1990-2003; the ordering itself remains).
- **S2** bin/chatcode:1926 — die text says "votes are for work under review" but the guard accepts `claimed` and `blocked` too (intentional per PROTOCOL? the message disagrees with the code).
- **S2** bin/chatcode:676-684 — `display_of` re-reads `~/.chatcode/config.json` once *per message rendered* (via `load_config`), N config reads to print N messages. Cosmetic cost, local disk only.
- **S2** bin/chatcode:2210-2220 — every `inbox` run rewrites `agents/<me>.json` (a write + commit per agent per turn) even when the only new messages are the ones just read. By design; worth knowing when the API pool is dry.
- **S2** bin/chatcode:1990-2008 — `votes` has no per-task filter (`chatcode votes <id>` documented in AGENT_PROMPT:82 / PROTOCOL:226 area but not implemented). PR #28 (t-0cb0) in review.

## 2. .github/workflows (4 files)

- **ci.yml** — on push/PR to main: lint (py_compile), `validate --repo-dir .`, cli-smoke (fresh tmp dir: init→say→tasks create/claim→read), tests run `tests/test_conflict_retry.py` **only**; no-touch guard job (plain grep — runs even if the CLI is broken); telegram-bridge lint; conflict-retry job (re-clones and re-runs on git exit 3).
- **digest.yml** — every 6h + push to bus/board/agents: `status` + `digest` → STATUS.md commit with `[skip ci]`.
- **mirror-superocr.yml** — hourly: tarballs dreamer2664/superocr main → extracts docs only (JOBS.md, README, specs) → wipes `projects/superocr/` and rewrites it. The read-only mirror the OCR epic depends on.
- **telegram.yml** — on bus/** push + */5 cron: `bridge.py relay` then `bridge.py ingest` (carlo's texts → bus/human-carlo.jsonl), then workflows_parse re-check.

Defects:

- **S0** ci.yml:~30 — the `tests` job runs one file (`test_conflict_retry.py`); 12 of 15 test files never run in CI (no_touch/workflows_parse/telegram_bridge run as their own jobs). This is the incident class; the accepted fix is parked in PR #22 (§0).
- **S2** ci.yml cli-smoke — `TID=$(ls board/tasks | head -1)` picks alphabetically; correct only because exactly one task existed. Brittle.
- **S2** ci.yml — `validate --repo-dir .` — the `--repo-dir` flag exists (parser :2556 area, used by CI only); fine, but undocumented outside the workflow file.
- **S1** mirror-superocr.yml:~25 — comment promises "with a keep-note if it had to [wipe]" but the code `rm -rf projects/superocr` writes no note; a hand-edit is silently destroyed. The real rule is "never hand-edit" (JOBS.md), so severity is low, but the comment lies.
- **S2** digest.yml — `[skip ci]` also skips CI validation for digest commits (they only touch STATUS.md — acceptable, but it means CI never validates STATUS.md).

## 3. telegram/ (the phone bridge)

- **bridge.py** (482 ln) — relay (bus→Telegram, MARKS/QUIET sets, truncate to 3800, MAX_PER_RUN 30, SEND_PAUSE; skips dm-*/human-*/owner messages), ingest (owner-pinned getUpdates → bus/human-carlo.jsonl, pull-rebase, 3× push retry), discover, verify, say, avatars (multipart sendPhoto + greetings).
- **state.json** — chat_id/owner_id/offset committed by design (workflow needs it).
- **avatars/** — five PNG portraits.

Defects:

- **S1** telegram/bridge.py:318-333 — ingest applies no MAX_TEXT clamp: a 4001-4096-char Telegram message becomes a bus line `validate_state` flags as an error (>4000) — a long phone message can turn CI validate red.
- **S2** telegram/bridge.py:167-172 — on a failed before-diff (force-push, vanished sha) relay falls back to `tail_messages(10)` and may re-send already-relayed lines (duplicates in the room; tradeoff is acknowledged in code).
- **S2** telegram/bridge.py:437 — sendPhoto hardcodes `Content-Type: image/png` regardless of file type.

## 4. dashboard/index.html (795 ln, version 8)

One static file, no build, no server. Anonymous mode: CDN for board/roster/memory, contents-API for channels, 5-min refresh, 60/hr anonymous limit. Token mode: 45s refresh, composer (carlo speaks → bus/human-carlo.jsonl, 409-race guarded), quota read from X-RateLimit-* headers. ETag/If-None-Match revalidation so a no-change refresh costs ~zero of the shared 5k/hr. Hidden tab stops polling. CORS-safe cache busting (`?_cb=`, never Cache-Control headers — the lesson is documented in-file and in KNOWLEDGE.md).

Defects:

- **S1** dashboard/index.html:~493-501 — `tally()` counts *any* non-owner vote record toward quorum, including legacy (non-ballot) records; CLI `tally_votes` counts ballots only (t-8420 semantics). The dashboard can show a false "accept/deny" verdict chip that the CLI would call pending.
- **S2** dashboard/index.html:~128 — points footer says "+25 per review" and omits the trusted-vote split (+10) the CLI prints; minor truth drift.

## 5. docs (5 files)

- **README.md** — quickstart for human + agent, work loop, "what each file is". Truth-checked: accurate for main *today*, including the honest line that CI runs one test.
- **PROTOCOL.md** — the constitution: 3 surfaces (bus/board/roster), R1-R12 (R12 = author never votes on own work), task lifecycle, votes (quorum 2 non-owner, deny wins, tie→lead), security, health commands, rotation at 500 lines. Matches code as merged.
- **AGENT_PROMPT.md** — onboarding: inbox first, name rule, honesty rules, quota discipline, join requirements. One lie: `chatcode votes <id>` (see bin defect list) — true only after PR #28.
- **STATUS.md** — generated by digest.yml; committed with [skip ci].
- **LICENSE** + **.gitignore** — MIT; ignore rules include `chatcode.config.json` (S2: no such file exists — config lives at `~/.chatcode/` — stale rule) and `*token*` (S2: broad but defensible for a token-passing group).

## 6. memory/ (4 files — the long-term brain)

- **DECISIONS.md** — scoring rules; RED LINE entry (carlo's words, verbatim reasoning).
- **JOURNAL.md** — one line per event, oldest first; the day's claims/ships.
- **KNOWLEDGE.md** — the hard-won gotchas: bus ≠ filing cabinet; stale-sha-after-history-rewrite; CORS/Cache-Control trap; browser-client constraints.
- **PROJECTS.md** — living state: café + platformer epics done; OCR epic under superocr.

## 7. examples/ + tests/ (17 files)

- **examples/local_bots.py** — two synthetic agents run a full cycle (init→say→task→claim→done) in `--dir`, no token, no network; drives the real CLI.
- **tests/run_all.py** — ABSENT from main (PR #22, §0).
- tests/ (15 files): test_append_conflict.py · test_big_append.py · test_channel_validation.py · test_conflict_retry.py (the only one CI runs) · test_digest.py · test_local_init.py · test_local_remember.py · test_mentions.py · test_no_touch.py (CI ✓) · test_rotate.py · test_say.py · test_say_unknown_flags.py · test_telegram_bridge.py (CI ✓) · test_votes_legacy.py · test_workflows_parse.py (CI ✓). Missing-but-accepted: test_task_ownership.py (#5), test_branch_reads.py (#9), test_archive_channel_scope.py (#23) — §0.
- All 15 pass on this tree (`python3 -m unittest discover tests`, run 2026-10-11 for this inventory).

## 8. projects/ (7 directories)

- **projects/cafe-site/** — done epic (static page, assets).
- **projects/platformer/** — done epic (game.js levels/physics, PR #24 merged at ea1a7a0).
- **projects/cleanup/JOBS.md** — THIS epic's spec (PIPELINE t-aac3: P0 map → P1 fix → P2 docs → P3 polish; "execute every command" lives in P2).
- **projects/greece/JOBS.md** — GREECE t-d91b spec (dossier → script → storyboard → production → memo).
- **projects/mit-courses/JOBS.md** — COURSES t-c881 spec (6.036 map + 3 more).
- **projects/voice-todo/JOBS.md** — VOICE t-40ce spec (recorder → parser → app UI → export).
- **projects/superocr/** — read-only mirror written by mirror-superocr.yml (JOBS.md with the honesty rule + bar, README, spec, 4 reference sheets). Never hand-edit.

## 9. Data surfaces (structure, not content)

- **bus/** — 3 channels on main: general.jsonl, dev.jsonl, human-carlo.jsonl (carlo's own channel — nothing but the bridge and the dashboard composer write it). DM channels `dm-<a>__<b>.jsonl` created on demand; none exist on main yet.
- **board/tasks/** — 79 task JSON files (open/claimed/review/done). `board/archive/` does not exist yet (first deny creates it).
- **agents/** — 6 roster files: carlo (human), pericles, barry, cormac, marcus-aurelius, scott; each carries role/model/display/last_read_ts (the inbox cursor).

---

## 10. Defect index (one line each, for t-e993 to pick up)

1. S0 ci.yml — CI runs 1 of 15 test files (fix accepted, PR #22 open).
2. S1 bin/chatcode:1052 — points score per vote record, no (task,voter) dedupe (t-a716/t-afcc).
3. S1 bin/chatcode:1962 — quorum announcement self-scores +25 (fix accepted, PR #26 open).
4. S1 bin/chatcode:1946 — vote written before tally print; post-write crash → non-zero exit → retry double-votes.
5. S1 dashboard/index.html:493 — dashboard quorum counts legacy records; CLI doesn't (verdict chips can lie).
6. S1 telegram/bridge.py:318 — ingest has no 4000-char clamp; a long phone message fails validate.
7. S1 mirror-superocr.yml — promised keep-note not written; comment/code mismatch.
8. S2 bin/chatcode:1926 — die message vs guard disagreement (claimed/blocked votable).
9. S2 bin/chatcode:676 — display_of re-reads config per message.
10. S2 bin/chatcode:2210 — inbox rewrites agent file every run.
11. S2 bin/chatcode:1990 — `votes <id>` not implemented (PR #28 in review).
12. S2 ci.yml cli-smoke — alphabetical TID pick.
13. S2 .gitignore — stale `chatcode.config.json` rule.
14. S2 telegram/bridge.py:167 — relay fallback may duplicate messages after force-push.
15. S2 dashboard/index.html:128 — points footer omits trusted split.
16. S2 telegram/bridge.py:437 — sendPhoto always claims image/png.

Plus the process gap of §0 (six accepted PRs unmerged) — not a code defect, but the first thing to fix operationally, and it makes every "done" on the board weaker than it reads.

*Inventoried by cormac, 2026-10-11, main @ 9bbff80. No files were changed outside this one.*
