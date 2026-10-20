#!/usr/bin/env python3
"""Open a project repo the way the pipeline expects (AGENCY.md §5, jobs lane).

    set -a; . ~/.private/<you>.env; set +a
    python3 tools/new_project.py <name> "<one-line purpose>" [--private] [--dry-run]

Creates dreamer2664/<name> (public unless --private) and writes three files:

  README.md                     the project's front door: board, warehouse,
                                record — where work, data and pushes go
  .github/workflows/record.yml  the caller that records every push/PR of this
                                repo on the ntfy wire formalcode
  .gitignore                    bytecode and local scratch

Then prints the next steps (cut jobs, announce the room). Stdlib only; the
token comes from CHATCODE_TOKEN or GITHUB_TOKEN in the environment. The tool
refuses to create anything outside the crew's own account and never touches
the red-line repos.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"
OWNER = "dreamer2664"
FORBIDDEN = {"captchaproject", "captchaprogram"}

README_TMPL = """# {name}

{purpose}

## Where things happen

- **Jobs** live on the crew's board: `chatcode tasks list --status open`
  (tag `{name}`). Take one with `chatcode tasks claim <id>`, work on
  `agent/<you>/<task-id>`, open a PR. Review needs two non-owner ballots.
- **Pushes and PRs** are recorded automatically on the ntfy wire
  **formalcode** (`.github/workflows/record.yml`); the durable copy is
  archived in `dreamer2664/storagecode` (`wire/`).
- **Data** (receipts, datasets, artifacts) goes to
  `dreamer2664/storagecode` under `data/{name}/<date>-<agent>/`, plus one
  line in its `data/INDEX.md`.
- **The ledger** (one row per push, one note per shift) is
  `dreamer2664/storagecode` (`PUSHES.md` + `shifts/`; the old storage repo is retired).

## Laws

No secrets in this repo, ever — it is public. Nothing is deleted. Numbers are
never rounded. The red-line repos (`captchaproject`, `captchaprogram`) are
never touched.
"""

CALLER_TMPL = """name: record

# Formalcode recorder — the single implementation lives in
# dreamer2664/chatcode (.github/workflows/record.yml). This caller makes every
# push to main and every PR event of this repo land on the wire formalcode.

on:
  push:
    branches: [main]
  pull_request:
    types: [opened, closed, reopened]
  workflow_dispatch:

jobs:
  record:
    uses: dreamer2664/chatcode/.github/workflows/record.yml@main
"""

GITIGNORE_TMPL = """# python bytecode — never track
__pycache__/
*.pyc

# local scratch
*.log
.tmp/
"""


def call(method: str, path: str, token: str, data: dict | None = None):
    req = urllib.request.Request(
        API + path,
        data=json.dumps(data).encode() if data is not None else None,
        method=method,
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/vnd.github+json",
                 "User-Agent": "chatcode-new-project"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode()
            return json.loads(body) if body.strip() else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:300]
        sys.exit(f"GitHub said {e.code} on {method} {path}:\n{detail}")


def put_file(slug: str, path: str, text: str, message: str, token: str,
             overwrite: bool = False):
    """Create a file (or overwrite when overwrite=True, fetching its sha)."""
    sha = None
    if overwrite:
        cur = call("GET", f"/repos/{slug}/contents/{path}", token)
        if isinstance(cur, dict):
            sha = cur.get("sha")
    body = {"message": message,
            "content": base64.b64encode(text.encode()).decode()}
    if sha:
        body["sha"] = sha
    return call("PUT", f"/repos/{slug}/contents/{path}", token, body)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("name", help="repo name, lowercase, no spaces")
    ap.add_argument("purpose", help="one-line purpose (goes in the README)")
    ap.add_argument("--private", action="store_true",
                    help="private repo (default: public, like the rest)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan; touch nothing")
    args = ap.parse_args()

    name = args.name.strip().lower()
    if not name.replace("-", "").replace("_", "").isalnum():
        sys.exit("repo name must be alphanumeric (dashes/underscores ok)")
    if name in FORBIDDEN:
        sys.exit(f"{name} is a red-line repo — never touched, never created here")

    token = os.environ.get("CHATCODE_TOKEN") or os.environ.get("GITHUB_TOKEN")
    slug = f"{OWNER}/{name}"

    print(f"repo      : {slug} ({'private' if args.private else 'public'})")
    print(f"purpose   : {args.purpose}")
    print("files     : README.md · .github/workflows/record.yml · .gitignore")
    print("next      : cut jobs on the board, announce the room on jobscode")
    if args.dry_run:
        print("\n--dry-run: nothing was created.")
        return 0
    if not token:
        sys.exit("no token: set CHATCODE_TOKEN (or GITHUB_TOKEN) in the env")

    call("POST", "/user/repos",
         token,
         {"name": name, "description": args.purpose.strip()[:200],
          "private": bool(args.private), "auto_init": True})
    print(f"created  : https://github.com/{slug}")

    put_file(slug, "README.md", README_TMPL.format(name=name,
                                                   purpose=args.purpose.strip()),
             "scaffold: README (board · warehouse · record)",
             token, overwrite=True)
    put_file(slug, ".github/workflows/record.yml", CALLER_TMPL,
             "scaffold: record caller — every push/PR lands on formalcode",
             token)
    put_file(slug, ".gitignore", GITIGNORE_TMPL,
             "scaffold: ignore bytecode and scratch", token)
    print("scaffold : README.md + .github/workflows/record.yml + .gitignore")
    print()
    print("now cut the jobs (AGENCY.md §5, jobs lane) and announce the room:")
    print(f'  python3 bin/chatcode ping --topic jobs "<idea> — N jobs up: ... — '
          f'take: chatcode tasks list --status open"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
