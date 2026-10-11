#!/usr/bin/env python3
"""`votes <task-id>` shows one tally, fails loudly when not applicable
(task t-20261011-0cb0).

One command, offline, no token:

    python3 tests/test_votes_id.py              # CLI = repo's bin/chatcode
    python3 tests/test_votes_id.py --cli PATH   # explicit CLI to test

Red on main: argparse rejects the positional (unrecognized arguments).
Green on the branch: one-task tally prints only that task; unknown id or a
task that is not under vote exits non-zero; an under-vote task with no
votes says so and still succeeds.
"""
import argparse
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
CLI = None
failures = []


def run(repo, args):
    cmd = ["python3", CLI, "--local", repo] + args
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60)


def make_agent(repo, name):
    p = run(repo, ["--agent", name, "init", "--quiet"])
    assert p.returncode == 0, p.stderr


def new_task(repo, title):
    p = run(repo, ["--agent", "alice", "tasks", "new", title, "--mine"])
    assert p.returncode == 0, p.stderr
    return re.search(r"t-\d{8}-[0-9a-f]{4}", p.stdout).group(0)


def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"\n      {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cli", default=str(HERE.parent / "bin" / "chatcode"))
    args, _ = ap.parse_known_args()
    global CLI
    CLI = os.path.abspath(args.cli)
    if not os.path.exists(CLI):
        print(f"cannot find CLI at {CLI}")
        sys.exit(1)
    print("chatcode CLI under test:", CLI)

    repo = tempfile.mkdtemp(prefix="chatcode-votes-id-")
    try:
        for a in ("alice", "bob", "carol"):
            make_agent(repo, a)
        t1 = new_task(repo, "task one")
        t2 = new_task(repo, "task two")
        run(repo, ["--agent", "alice", "tasks", "update", t1, "--status", "review"])
        run(repo, ["--agent", "alice", "tasks", "update", t2, "--status", "review"])
        run(repo, ["--agent", "bob", "vote", t1, "accept-inspected", "--reason", "ran it"])
        run(repo, ["--agent", "carol", "vote", t2, "deny-trusted", "--reason", "no repro"])

        # case 1: one-task tally shows ONLY that task's tally
        p = run(repo, ["votes", t1])
        check("votes <id> succeeds for an under-vote task", p.returncode == 0, p.stderr[-200:])
        check("votes <id> prints that task's tally", "accept" in p.stdout and t1 in p.stdout, p.stdout[-200:])
        check("votes <id> does NOT print the other task",
              t2 not in p.stdout and p.stdout.count("tally for") == 1, p.stdout[-200:])

        # case 2: unknown id exits non-zero
        p = run(repo, ["votes", "t-20990101-0000"])
        check("unknown id exits non-zero", p.returncode != 0)
        check("unknown id says so", "no such task" in (p.stderr + p.stdout), p.stderr[-200:])

        # case 3: task not under vote exits non-zero
        p = run(repo, ["votes", t1])  # still review rc 0 (sanity)
        p_closed = new_task(repo, "done task")  # claimed, is under vote... close t1 instead
        run(repo, ["--agent", "carol", "vote", t1, "accept-trusted", "--reason", "second"])
        p = run(repo, ["votes", t1])
        check("task closed by vote exits non-zero", p.returncode != 0)
        check("message explains it is not under vote", "not under vote" in (p.stderr + p.stdout),
              p.stderr[-200:])

        # case 4: under-vote task with no votes still succeeds, says so
        p = run(repo, ["votes", p_closed])
        check("under-vote task with no votes succeeds", p.returncode == 0, p.stderr[-200:])
        check("says (no votes yet)", "(no votes yet)" in p.stdout, p.stdout[-200:])

        # case 5: full listing unchanged (still works after the change)
        p = run(repo, ["votes"])
        check("plain votes still lists under-vote tasks", p.returncode == 0 and t2 in p.stdout,
              p.stdout[-200:])
    finally:
        shutil.rmtree(repo, ignore_errors=True)

    print()
    if failures:
        print("FAILURES:", len(failures))
        sys.exit(1)
    print("OK: votes <id> prints one tally; unknown/not-under-vote fails loudly")


if __name__ == "__main__":
    main()
