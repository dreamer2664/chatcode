#!/usr/bin/env python3
"""t-20261011-a716 — one ballot, one score event: re-voting must not re-pay.

DEFECT on main: `cmd_vote` appends a `type=vote` bus message per cast and
re-voting is allowed — `collect_votes` documents "Latest vote per agent for one
task. Later votes replace earlier ones.", so the TALLY counts one ballot per
agent, but `compute_points` pays +25 (inspected) / +10 (trusted) for EVERY vote
message. Measured on main in this testbed: an agent that votes
accept-inspected and then changes to deny-inspected reads 50 points for one
ballot (2 x 25), and the tally still counts them once. Cast ten times for 250
points with the tally untouched: a points-farming vector, and honest
mind-changers are overpaid.

FIX under test: scoring, not records — `compute_points` finds the last vote
message per (task, voter) and skips the superseded casts. The earlier casts
stay on the bus; the tally (collect_votes) was already last-ballot-wins.

Cases:
  1. RED on main: two casts by one agent on one task score 25 once, not 50.
  2. three casts on one task still score once (the last ballot's weight).
  3. the same agent voting on TWO different tasks still scores each ballot —
     the fix must dedupe per (task, voter), not per voter.
  4. the tally resolves on the LAST ballot: deny-then-accept stays a 1A/1D tie.
  5. every cast record remains on the bus (the fix silences scoring, not the
     record), and the counter counts ballot events, not casts.

One command from the repo root:

    python3 tests/test_revote_points_once.py

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
    root = tempfile.mkdtemp(prefix="cc-revote-")
    for sub in ("agents", "bus", "board/tasks"):
        os.makedirs(os.path.join(root, sub))
    for name in ("alice", "bob", "carol", "dave"):
        with open(os.path.join(root, "agents", f"{name}.json"), "w") as fh:
            json.dump({"name": name, "kind": "ai", "role": "worker", "status": "active"}, fh)
    return root


def make_task(root, home, author, title):
    p = run(root, home, author, ["tasks", "new", title, "--priority", "3"])
    for line in p.stdout.splitlines():
        if "created" in line and "t-2026" in line:
            tid = line.split("created", 1)[1].strip().split()[0]
            run(root, home, author, ["tasks", "update", tid, "--status", "review"])
            return tid
    raise SystemExit(f"could not create task: {p.stdout} {p.stderr}")


def points(root, home):
    p = run(root, home, "carol", ["points", "--json"])
    try:
        return json.loads(p.stdout)["scores"]
    except Exception:
        raise SystemExit(f"points --json failed: {p.stdout!r} {p.stderr!r}")


def bus_messages(root):
    for name in ("dev", "general"):
        path = os.path.join(root, "bus", f"{name}.jsonl")
        if os.path.exists(path):
            out = []
            for line in open(path, encoding="utf-8"):
                if line.strip():
                    try:
                        out.append(json.loads(line))
                    except Exception:
                        pass
            return out
    return []


def main():
    if not os.path.exists(CLI):
        print(f"FAIL: cannot find CLI at {CLI}")
        return 1
    root = make_repo()
    home = tempfile.mkdtemp(prefix="cc-home-")
    failures = []
    try:
        # task1 (owner carol): alice changes her mind, bob ties the quorum —
        # ties escalate, so no task completes and no accept record is posted
        # (this test stays independent of the accept-announcement scoring,
        # which is t-20261011-6891's subject).
        t1 = make_task(root, home, "carol", "revote probe — one task")
        run(root, home, "alice", ["vote", t1, "accept-inspected", "--reason", "first look"])
        run(root, home, "alice", ["vote", t1, "deny-inspected", "--reason", "second thoughts"])
        p_bob = run(root, home, "bob", ["vote", t1, "accept-trusted", "--reason", "trust alice"])

        # task2 (owner dave): carol casts three times, alice denies — tie again.
        t2 = make_task(root, home, "dave", "revote probe — second task")
        run(root, home, "carol", ["vote", t2, "accept-trusted", "--reason", "looks fine"])
        run(root, home, "carol", ["vote", t2, "accept-trusted", "--reason", "still fine"])
        run(root, home, "carol", ["vote", t2, "accept-trusted", "--reason", "final"])
        p_alice2 = run(root, home, "alice", ["vote", t2, "deny-trusted", "--reason", "disagree"])

        sc = points(root, home)

        def total(who):
            return sc.get(who, {}).get("total", 0)

        def reviews(who):
            return sc.get(who, {}).get("reviews", 0)

        if total("alice") != 35:
            failures.append(
                f"case1: alice cast three votes (two on one task, one on another) and scored "
                f"{total('alice')} (want 35 = 25 for task1's last ballot, deny-inspected, + 10 for "
                "task2's deny-trusted) — the CLI pays per cast, not per ballot")
        if total("carol") != 10:
            failures.append(
                f"case2: carol cast three trusted ballots on one task and scored {total('carol')} "
                "(want 10 = one ballot) — superseded casts are being paid")
        if total("bob") != 10:
            failures.append(f"case3: bob scored {total('bob')} (want 10 for one trusted vote)")
        if total("dave") != 0:
            failures.append(f"case4: dave only owns an unfinished task and scored {total('dave')} (want 0)")
        if reviews("carol") != 1:
            failures.append(f"case5: carol's ballot counter reads {reviews('carol')} (want 1 event)")
        if reviews("alice") != 2:
            failures.append(f"case6: alice's ballot counter reads {reviews('alice')} (want 2 events, "
                            "one per task — not one per cast)")

        if "tie" not in (p_bob.stdout + p_bob.stderr).lower():
            failures.append(
                "case7: bob's accept did not read as a 1A/1D tie — the tally must resolve on the "
                f"LAST ballot (alice's deny), not her first: {(p_bob.stdout + p_bob.stderr)[-120:]!r}")
        if "tie" not in (p_alice2.stdout + p_alice2.stderr).lower():
            failures.append("case8: task2 did not read as a tie under last-ballot semantics")

        msgs = bus_messages(root)
        alice_t1 = [m for m in msgs if m.get("type") == "vote" and m.get("ref") == t1 and m.get("from") == "alice"]
        carol_t2 = [m for m in msgs if m.get("type") == "vote" and m.get("ref") == t2 and m.get("from") == "carol"]
        if len(alice_t1) != 2 or len(carol_t2) != 3:
            failures.append(
                f"case9: every cast must stay on the bus — found alice/task1 {len(alice_t1)} "
                f"(want 2), carol/task2 {len(carol_t2)} (want 3)")

        if failures:
            print("FAIL: re-voting re-scores — one ballot, N casts, N payouts")
            for f in failures:
                print(f"  - {f}")
            return 1
        print("OK: one ballot = one score event (one mind changed 25 once, three casts 10 once, "
              "a second task scores separately), the tally resolves on the last ballot, "
              "every cast stays on the bus")
        return 0
    finally:
        shutil.rmtree(root, ignore_errors=True)
        shutil.rmtree(home, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
