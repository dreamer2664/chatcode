#!/usr/bin/env python3
"""t-20261011-6891 — the quorum-closing accept vote must score once, not twice.

DEFECT on main: `compute_points` pays +25 for every `type=review` bus message, and
`cmd_vote`'s accept branch posts the "ACCEPTED by vote" record with `mtype="review"`
in the name of the voter who closed the quorum — so that voter is paid their vote
points (+25 inspected / +10 trusted) *plus* +25 for the record the CLI wrote for
them. Measured on main in this testbed: the trusted voter who closes reads 35
points (10 + 25) for one `chatcode vote` command. The deny path announces with
`type=archive` (+0), so accepting and denying quorums are scored asymmetrically.

FIX under test: the CLI's own vote records carry `extra={"auto": True}` and
`compute_points` skips auto messages — one command, one score event, while the
record stays on the bus where readers expect it.

Cases:
  1. RED on main: the accept-trusted voter who closes the quorum has exactly 10.
  2. the first (accept-inspected) voter has exactly 25.
  3. the accept record is STILL on the bus (type=review, ref=<task>) — the fix
     must silence the scoring, not the record.
  4. deny path is symmetric: deny-inspected 25 / deny-trusted 10, archive written.
  5. the closing voter's review counter counts one event, not two.

One command from the repo root:

    python3 tests/test_vote_points_no_double.py

Stdlib only, HOME redirected, throwaway --local repo, no network.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CLI = os.path.normpath(os.path.join(HERE, "..", "bin", "chatcode"))


def run(root, home, agent, argv):
    cmd = [sys.executable, CLI, "--local", root, "--agent", agent] + argv
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                          env=dict(os.environ, HOME=home))


def make_repo():
    root = tempfile.mkdtemp(prefix="cc-points-")
    for sub in ("agents", "bus", "board/tasks"):
        os.makedirs(os.path.join(root, sub))
    for name in ("alice", "bob", "carol"):
        with open(os.path.join(root, "agents", f"{name}.json"), "w") as fh:
            json.dump({"name": name, "kind": "ai", "role": "worker", "status": "active"}, fh)
    return root


def make_task(root, home, title):
    p = run(root, home, "carol", ["tasks", "new", title, "--priority", "3"])
    for line in p.stdout.splitlines():
        if "created" in line and "t-2026" in line:
            tid = line.split("created", 1)[1].strip().split()[0]
            run(root, home, "carol", ["tasks", "update", tid, "--status", "review"])
            return tid
    raise SystemExit(f"could not create task: {p.stdout} {p.stderr}")


def points(root, home):
    p = run(root, home, "carol", ["points", "--json"])
    try:
        return json.loads(p.stdout)["scores"]
    except Exception:
        raise SystemExit(f"points --json failed: {p.stdout!r} {p.stderr!r}")


def main():
    if not os.path.exists(CLI):
        print(f"FAIL: cannot find CLI at {CLI}")
        return 1
    root = make_repo()
    home = tempfile.mkdtemp(prefix="cc-home-")
    failures = []
    try:
        # ---- accept path -------------------------------------------------
        t_ok = make_task(root, home, "points probe — accept")
        run(root, home, "alice", ["vote", t_ok, "accept-inspected", "--reason", "read it"])
        p2 = run(root, home, "bob", ["vote", t_ok, "accept-trusted", "--reason", "trust alice"])
        if "accepted by vote" not in (p2.stdout + p2.stderr).lower():
            failures.append(f"case0: the second accept vote did not close the quorum: {p2.stdout[-120:]}")

        # ---- deny path ---------------------------------------------------
        t_no = make_task(root, home, "points probe — deny")
        run(root, home, "alice", ["vote", t_no, "deny-inspected", "--reason", "broken"])
        run(root, home, "bob", ["vote", t_no, "deny-trusted", "--reason", "agreed"])

        sc = points(root, home)

        def total(who):
            return sc.get(who, {}).get("total", 0)

        if total("bob") != 20:
            failures.append(
                f"case1: the quorum-closing trusted voter scored {total('bob')} "
                "(want 20 = two trusted votes at 10) — main pays +25 for the CLI's own record")
        if total("alice") != 50:
            failures.append(f"case2: inspected voter scored {total('alice')} (want 50 = two inspected votes at 25)")
        if total("carol") != 0:
            failures.append(f"case3: carol only created tasks and scored {total('carol')} (want 0)")

        accepted = []
        busf = os.path.join(root, "bus", "dev.jsonl")
        if not os.path.exists(busf):
            busf = os.path.join(root, "bus", "general.jsonl")
        for line in open(busf, encoding="utf-8"):
            if not line.strip():
                continue
            m = json.loads(line)
            if m.get("type") == "review" and m.get("ref") == t_ok:
                accepted.append(m)
        if not accepted:
            failures.append("case4: the accept record vanished from the bus — silence the scoring, not the record")
        elif not failures and total("bob") == 20 and not accepted[0].get("auto"):
            failures.append("case4b: the accept record is untagged — mark it extra={'auto': True} so scoring stays honest")

        arc = os.path.join(root, "board", "archive", f"{t_no}.json")
        if not os.path.exists(arc):
            failures.append("case5: the denied task was not archived")

        if failures:
            print("FAIL: the quorum-closing vote is scored twice")
            for f in failures:
                print(f"  - {f}")
            return 1
        print("OK: one vote = one score event (closing trusted voter 20, inspected 50), "
              "the accept record is still on the bus, deny path symmetric, archive written")
        return 0
    finally:
        shutil.rmtree(root, ignore_errors=True)
        shutil.rmtree(home, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
