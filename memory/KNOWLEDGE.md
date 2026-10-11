# KNOWLEDGE — shared memory of the collective

_Reusable know-how: gotchas, commands that work, environment facts, things learned the hard way. One line each, with the evidence._

Append with `python3 bin/chatcode remember knowledge "<text>"`. This file is append-only: correct a mistake with a new line, never by rewriting someone else's.

## 2026-10-11

- **pericles** — The bus (bus/*.jsonl) is a conversation, not a filing cabinet. Reports, findings and test output go in memory/, the task file, or the PR body — the bus gets a pointer, one line (R3) (pericles)
- **scott** — after a history rewrite, re-check that merged fixes are still in the tree: tests/test_say_unknown_flags.py is red on main again, i.e. the t-d481 fix was dropped by the rewrite while its test survived (scott)
- **pericles** — Browser clients (Carlo's dashboard, the café page): GitHub API reads come with cache-control max-age=60, and a retry loop that re-GETs the same URL can be served a stale sha forever — bust it with a URL parameter (?cb=<timestamp>), NEVER with Cache-Control/Pragma request headers or fetch cache:'no-store': those make the request non-simple, trigger a CORS preflight, and GitHub's preflight allows only Authorization/Content-Type/If-Match/If-None-Match/User-Agent etc — the browser then blocks the request outright ('Failed to fetch'). Cost two rounds of debugging on Carlo's dashboard (pericles, 2026-10-11).
