#!/usr/bin/env python3
"""Legacy vote records must not crash `votes`/`archive`, and must not count as
ballots (task t-20261011-8420).

One command, offline, no token:

    python3 tests/test_votes_legacy.py              # CLI = repo's bin/chatcode
    python3 tests/test_votes_legacy.py --cli PATH   # explicit CLI to test

Scenario in a throwaway --local repo: a pre-ballot-era vote message (type
"vote", free-text, NO verdict fields) sits on the bus next to real ballots.

Red on main: `chatcode votes` crashes with TypeError in _print_tally.
Green on the branch:
  - `votes` prints; the legacy record is shown as a note, not a ballot
  - quorum/needed count only real ballots (legacy does not fake progress)
  - accept closes on real ballots; archive prints legacy rows safely
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


def run(repo, args, expect_rc=None):
    cmd = ["python3", CLI, "--local", repo] + args
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if expect_rc is not None and p.returncode != expect_rc:
        failures.append(f"rc {p.returncode} != {expect_rc}: {' '.join(args)}\n"
                        f"stderr: {p.stderr[-300:]}")
    return p


def make_agent(repo, name):
    run(repo, ["--agent", name, "init", "--quiet"], 0)


def uetc(repo):
    bus = pathlib.Path(repo, "bus", "general.jsonl").read_text(encoding="utf-8")
    return [json.loads(l) for l in bus.splitlines() if l.strip()]


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

    repo = tempfile.mkdtemp(prefix="chatcode-votes-")
    try:
        for a in ("alice", "bob", "carol", "dave"):
            make_agent(repo, a)
        # a task in review (votes only lists review/claimed/blocked)
        p = run(repo, ["--agent", "alice", "tasks", "new", "legacy crash task", "--mine"], 0)
        tid = re.search(r"t-\d{8}-[0-9a-f]{4}", p.stdout).group(0)
        run(repo, ["--agent", "alice", "tasks", "update", tid, "--status", "review"], 0)
        # LEGACY vote: the old decision mechanic — free text, no verdict fields
        run(repo, ["--agent", "bob", "say", "+1 idea A, if anyone asks", "--type", "vote", "--ref", tid], 0)

        # case 1: `votes` must not crash, legacy must not count toward quorum
        p = run(repo, ["votes"])
        crashed = p.returncode != 0 and ("TypeError" in p.stderr or "Traceback" in p.stderr)
        check("votes does not crash with a legacy vote on the bus", not crashed,
              f"rc={p.returncode} stderr tail: {p.stderr[-200:]}")
        if not crashed:
            check("legacy vote is shown but marked as not-a-ballot",
                  "legacy" in p.stdout and "bob" in p.stdout, p.stdout[-300:])
            check("quorum counts ballots only (legacy fakes no progress): still needs 2",
                  "needs 2 more" in p.stdout, p.stdout[-300:])

        # case 2: two real ballots close the vote accept; legacy stays a note
        run(repo, ["--agent", "carol", "vote", tid, "accept-trusted", "--reason", "spot check"], 0)
        p = run(repo, ["--agent", "dave", "vote", tid, "accept-inspected", "--reason", "ran the test"], 0)
        check("verdict accept reached on two real ballots", "→ accept" in p.stdout, p.stdout[-300:])
        check("legacy note printed by the closing tally, still not counted",
              "legacy" in p.stdout and "bob" in p.stdout, p.stdout[-300:])
        p = run(repo, ["--agent", "alice", "tasks", "list"], 0)
        check("accepted task is done (closed by vote, not by listing)",
              re.search(re.escape(tid) + r".*done", p.stdout) is not None, p.stdout[-300:])
        same = [m for m in uetc(repo) if m.get("ref") == tid and m.get("type") == "vote"]
        ballots = [m for m in same if m.get("vote") in ("accept", "deny")]
        legacy = [m for m in same if m.get("vote") not in ("accept", "deny")]
        check("bus keeps every record (2 ballots + 1 legacy)", len(ballots) == 2 and len(legacy) == 1)

        # case 3: deny path closes and archive prints a legacy row safely
        p2 = run(repo, ["--agent", "alice", "tasks", "new", "deny crash task", "--mine"], 0)
        tid2 = re.search(r"t-\d{8}-[0-9a-f]{4}", p2.stdout).group(0)
        run(repo, ["--agent", "alice", "tasks", "update", tid2, "--status", "review"], 0)
        run(repo, ["--agent", "bob", "say", "old-style remark", "--type", "vote", "--ref", tid2], 0)
        run(repo, ["--agent", "carol", "vote", tid2, "deny-trusted", "--reason", "no repro"], 0)
        run(repo, ["--agent", "dave", "vote", tid2, "deny-trusted", "--reason", "no repro either"], 0)
        p = run(repo, ["archive"], 0)
        check("denied task archived without crashing", tid2 in p.stdout and "Traceback" not in p.stderr,
              (p.stdout + p.stderr)[-300:])
        check("archive printer shows the legacy row without crashing", "legacy" in p.stdout, p.stdout[-300:])
    finally:
        shutil.rmtree(repo, ignore_errors=True)

    print()
    if failures:
        print("FAILURES:", len(failures))
        sys.exit(1)
    print("OK: legacy votes never crash, never count as ballots; ballots still close votes")


if __name__ == "__main__":
    main()
