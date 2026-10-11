#!/usr/bin/env python3
"""`tasks update` without --status must not null the status (t-20261011-9fc4).

Found by marcus-aurelius (alert #48610e9f, 19:14Z): attaching a PR or a note
without --status wrote `status: null` into live task files. Two real victims
(2f3d, f0d2) lost their status silently, and plain `tasks list` then crashed
with `TypeError: can only concatenate str (not "NoneType") to str` for every
agent on the repo (-‑json still worked, which is how it went unnoticed).

    python3 tests/test_status_kept.py               # CLI = repo's bin/chatcode
    python3 tests/test_status_kept.py --cli PATH

The three checks: the writer keeps the status; the listing survives a legacy
null-status file made by hand; a real --status change still lands.
Stdlib only, offline.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CLI = os.path.join(HERE, os.pardir, "bin", "chatcode")
CLI = None
failures = []


def run(repo, args, expect_rc=None):
    p = subprocess.run([sys.executable, CLI, "--local", repo] + args,
                       capture_output=True, text=True, timeout=60)
    if expect_rc is not None and p.returncode != expect_rc:
        failures.append(f"rc {p.returncode} != {expect_rc}: {' '.join(args)}\n"
                        f"stdout: {p.stdout[-300:]}\nstderr: {p.stderr[-300:]}")
    return p


def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name
          + (f"\n      {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cli", default=DEFAULT_CLI)
    args, _ = ap.parse_known_args()
    global CLI
    CLI = os.path.abspath(args.cli)
    if not os.path.exists(CLI):
        print(f"cannot find CLI at {CLI}")
        sys.exit(1)
    print("chatcode CLI under test:", CLI)

    repo = tempfile.mkdtemp(prefix="chatcode-status-")
    try:
        run(repo, ["--agent", "alice", "init", "--quiet"], 0)
        p = run(repo, ["--agent", "alice", "tasks", "new", "victim task", "--mine"], 0)
        tid = re.search(r"t-\d{8}-[0-9a-f]{4}", p.stdout).group(0)
        tpath = os.path.join(repo, "board", "tasks", f"{tid}.json")

        # 1. the reported bug: --pr only (and --note only) must keep the status
        run(repo, ["--agent", "alice", "tasks", "update", tid,
                   "--pr", "https://example.com/pr/1", "--note", "attach pr"], 0)
        d = json.load(open(tpath, encoding="utf-8"))
        check("--pr-only update keeps the status", d.get("status") == "claimed",
              f"status={d.get('status')!r} (was written as null before the fix)")
        check("the PR url still lands", d.get("pr") == "https://example.com/pr/1")

        run(repo, ["--agent", "alice", "tasks", "update", tid, "--note", "note only"], 0)
        d = json.load(open(tpath, encoding="utf-8"))
        check("--note-only update keeps the status", d.get("status") == "claimed",
              f"status={d.get('status')!r}")

        p = run(repo, ["tasks", "list"], 0)
        check("tasks list does not crash", p.returncode == 0,
              (p.stderr or p.stdout)[-200:])

        # 2. legacy file with status:null (older writers) must not crash listing
        d = json.load(open(tpath, encoding="utf-8"))
        d["status"] = None
        json.dump(d, open(tpath, "w", encoding="utf-8"), indent=2)
        p = run(repo, ["tasks", "list"])
        crashed = p.returncode != 0 and "TypeError" in p.stderr
        check("tasks list survives a legacy null-status file", not crashed,
              f"rc={p.returncode}: {p.stderr[-200:]}")
        # restore for later checks
        d["status"] = "claimed"
        json.dump(d, open(tpath, "w", encoding="utf-8"), indent=2)

        # 3. a real status change still lands (the fix must not freeze status)
        run(repo, ["--agent", "alice", "tasks", "update", tid, "--status", "review"], 0)
        d = json.load(open(tpath, encoding="utf-8"))
        check("--status still changes the status", d.get("status") == "review",
              f"status={d.get('status')!r}")
        run(repo, ["--agent", "alice", "tasks", "done", tid], 0)
        d = json.load(open(tpath, encoding="utf-8"))
        check("the done shortcut still works", d.get("status") == "done"
              and d.get("completed_ts"), f"status={d.get('status')!r}")
        check("history records the real transitions",
              any("done" in (h.get("action") or "") for h in d.get("history") or []),
              json.dumps(d.get("history") or [])[-200:])
    finally:
        import shutil
        shutil.rmtree(repo, ignore_errors=True)

    if failures:
        print(f"\n{len(failures)} checks failed")
        for f in failures:
            print(" -", f.splitlines()[0])
        return 1
    print("\nOK: the writer keeps the status, the listing survives legacy nulls, real changes land")
    return 0


if __name__ == "__main__":
    sys.exit(main())
