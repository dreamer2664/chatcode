#!/usr/bin/env python3
"""`chatcode reputation <agent>` — reputation computed only from bus messages
about the agent, every data point a message id (task t-20261011-c261).

One command, offline, no token:

    python3 tests/test_reputation.py              # CLI = repo's bin/chatcode
    python3 tests/test_reputation.py --cli PATH   # explicit CLI to test

Seed a --local repo with: two accept-ballots on alice's task (quorum closes it
and the CLI posts its acceptance announcement), a 'changes requested' review on
her other task, a direct help-ask, a flattering broadcast, and a self-ask.

Red on main: no such subcommand (argparse error).
Green on the branch: alice = +1 ballot +1 ballot +5 quorum -2 review +1 ask = 6,
five data points, each named by its bus message id; broadcasts and self-asks do
not count; bob is empty; --json parses; two runs are byte-identical.
"""
import argparse
import json
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


def new_task(repo, owner, title):
    p = run(repo, ["--agent", owner, "tasks", "new", title, "--mine"])
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

    repo = tempfile.mkdtemp(prefix="chatcode-rep-")
    try:
        for a in ("alice", "bob", "carol", "dave"):
            make_agent(repo, a)
        t1 = new_task(repo, "alice", "alice task one")
        t2 = new_task(repo, "alice", "alice task two")
        run(repo, ["--agent", "alice", "tasks", "update", t1, "--status", "review"])
        run(repo, ["--agent", "alice", "tasks", "update", t2, "--status", "review"])
        run(repo, ["--agent", "bob", "vote", t1, "accept-inspected", "--reason", "ran it"])   # +1
        run(repo, ["--agent", "carol", "vote", t1, "accept-trusted", "--reason", "seems fine"])  # +1, closes -> +5 announcement
        run(repo, ["--agent", "carol", "say", "Review: changes requested, repro attached",
                   "--type", "review", "--ref", t2])                                             # -2
        run(repo, ["--agent", "dave", "say", "alice: can you help me with the menu?", "--to", "alice"])  # +1
        run(repo, ["--agent", "dave", "say", "broadcast: alice did great work on the menu"])    # NOT counted
        run(repo, ["--agent", "alice", "say", "alice: help?", "--to", "alice"])                 # self-ask NOT counted

        p1 = run(repo, ["reputation", "alice"])
        check("reputation command runs", p1.returncode == 0, p1.stderr[-200:])
        check("alice's score is exactly +6", "score +6" in p1.stdout, p1.stdout[-300:])
        check("five data points", "5 data point(s)" in p1.stdout, p1.stdout[-200:])
        ids = set(re.findall(r"^\s*([+-]\d+)\s+#([0-9a-f]{8})", p1.stdout, re.M))
        check("every data point cites a bus message id", len(ids) == 5,
              p1.stdout[-300:])
        deltas = sorted(int(d) for d, _ in ids)
        check("deltas are the announced table (+5,+1,+1,+1,-2)",
              deltas == [-2, 1, 1, 1, 5], str(deltas))
        check("broadcast flattery does not count",
              all("broadcast" not in line for line in p1.stdout.splitlines()),
              p1.stdout[-300:])

        pb = run(repo, ["reputation", "bob"])
        check("agent with nothing about them is empty, not an error", pb.returncode == 0 and
              "(no data yet" in pb.stdout, (pb.stdout + pb.stderr)[-200:])

        pj = run(repo, ["reputation", "alice", "--json"])
        try:
            doc = json.loads(pj.stdout)
            okjson = doc["score"] == 6 and len(doc["data"]) == 5 and all(
                d.get("id") for d in doc["data"])
        except Exception:
            okjson = False
        check("--json is machine-readable with the same numbers", okjson, pj.stdout[-200:])

        p2 = run(repo, ["reputation", "alice"])
        check("deterministic: two runs byte-identical", p1.stdout == p2.stdout)
    finally:
        shutil.rmtree(repo, ignore_errors=True)

    print()
    if failures:
        print("FAILURES:", len(failures))
        sys.exit(1)
    print("OK: reputation is bus-only, cited, and deterministic")


if __name__ == "__main__":
    main()
