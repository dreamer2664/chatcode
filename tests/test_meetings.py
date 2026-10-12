#!/usr/bin/env python3
"""The meeting system, tested offline (no network, no tokens).

Carlo's ask (12 Oct 2026): a planned room where the AIs talk to each other —
propose, agree a time, be prepared, meet, minutes. The whole lifecycle lives in
the CLI (`chatcode meeting ...`), state on a task, record on the `meetings`
bus channel. This test drives the real CLI end to end in a throwaway repo and
pins the rules that matter:

  * a meeting is a task tagged `meeting`, proposed with slots and a goal
  * the owner (a human in the roster) is a trigger/veto, not a member: he never
    blocks a vote, a schedule or a roll call
  * scheduling waits for every member's availability and picks the earliest
    slot ALL non-chair members can make (the local run below: slot 1 lacks
    barry, so slot 2 must win)
  * prep is one per member, enforced; the chair alone starts and closes; a
    close reports the attendance gap instead of hiding it

    python3 tests/test_meetings.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CLI = os.path.join(ROOT, "bin", "chatcode")
AGENTS = ("pericles", "marcus-aurelius", "barry", "scott", "cormac")

failures = []


def check(name, cond, extra=""):
    if cond:
        print(f"PASS  {name}")
    else:
        failures.append(name)
        print(f"FAIL  {name}  {extra}")


def run(repo, agent, *args):
    p = subprocess.run([sys.executable, CLI, "--local", repo, "--agent", agent, *args],
                       capture_output=True, text=True, timeout=120)
    return p.returncode, (p.stdout + p.stderr).strip()


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="meeting-test-")
    try:
        for a in AGENTS:
            run(tmp, a, "init", "--quiet", "--model", "test")
        # Carlo exists in the roster as a human owner — but he is not a member:
        # trigger/veto only, his availability never blocks a schedule.
        run(tmp, "carlo", "init", "--quiet", "--model", "human")
        cpath = os.path.join(tmp, "agents", "carlo.json")
        with open(cpath, encoding="utf-8") as f:
            ca = json.load(f)
        ca.update({"kind": "human", "role": "owner", "display": "Carlo"})
        with open(cpath, "w", encoding="utf-8") as f:
            json.dump(ca, f, indent=2)

        rc, out = run(tmp, "pericles", "meeting", "new", "--topic", "Speed",
                      "--goal", "pick three levers",
                      "--slot", "2026-10-12T15:00Z", "--slot", "2026-10-12T16:00Z")
        check("a meeting proposes", rc == 0 and "proposed" in out, out)
        mid = None
        for w in out.replace("(", " ").split():
            if w.startswith("t-") and len(w) == 17:
                mid = w
        if not mid:
            board = os.path.join(tmp, "board", "tasks")
            ids = [f[:-5] for f in os.listdir(board) if f.endswith(".json")]
            mid = ids[0] if ids else None
        check("the meeting has a task id", bool(mid), out)
        task = json.load(open(os.path.join(tmp, "board", "tasks", f"{mid}.json")))
        check("the task is tagged as a meeting", "meeting" in (task.get("tags") or []), str(task.get("tags")))
        check("the slots are stored", task.get("meeting_slots") == ["2026-10-12T15:00Z", "2026-10-12T16:00Z"],
              str(task.get("meeting_slots")))

        rc, out = run(tmp, "pericles", "meeting", "schedule", mid)
        check("scheduling before the votes refuses", rc != 0 and "waiting on availability" in out, out)

        for a, slots in (("marcus-aurelius", ["1,2"]), ("scott", ["1,2"]), ("cormac", ["1,2"]),
                         ("barry", ["2"])):
            run(tmp, a, "meeting", "vote", mid, "--slots", *slots)
        rc, out = run(tmp, "pericles", "meeting", "schedule", mid)
        check("the earliest all-can-make slot wins (2, barry cannot make 1)",
              rc == 0 and "2026-10-12T16:00Z" in out, out)
        check("scheduling ran on the four AI votes alone — the owner (carlo) never blocked it",
              "carlo" not in out, out)

        rc, out = run(tmp, "pericles", "meeting")
        check("a bare `meeting` explains itself instead of crashing",
              rc != 0 and "which meeting" in out and "Traceback" not in out, out)

        rc, out = run(tmp, "barry", "meeting", "prep", mid, "--position", "ties lose words",
                      "--proposal", "extend the gated vote to joins")
        check("prep lands", rc == 0 and "proposal(s)" in out, out)
        rc, out = run(tmp, "barry", "meeting", "prep", mid, "--position", "again", "--proposal", "again")
        check("a second prep from the same member refuses", rc != 0 and "already on the record" in out, out)

        rc, out = run(tmp, "barry", "meeting", "start", mid)
        check("a non-chair cannot start", rc != 0 and "only the chair" in out, out)
        rc, out = run(tmp, "pericles", "meeting", "start", mid)
        check("the chair starts", rc == 0 and "LIVE" in out, out)

        for a in ("marcus-aurelius", "barry", "scott"):
            run(tmp, a, "meeting", "roll", mid, "--here")
        rc, out = run(tmp, "scott", "meeting", "say", mid, "--text", "joins are mine")
        check("turns post while live", rc == 0 and "turn 1" in out, out)

        rc, out = run(tmp, "pericles", "meeting", "close", mid,
                      "--minutes", "1) joins go to the CNN vote. 2) training round tonight.")
        check("close records the minutes", rc == 0 and "closed" in out, out)
        check("the attendance gap is reported, not hidden", "cormac did not roll" in out, out)
        task = json.load(open(os.path.join(tmp, "board", "tasks", f"{mid}.json")))
        check("the record keeps decisions, attendance and status",
              task.get("meeting_status") == "closed" and "joins go to the CNN vote" in (task.get("meeting_decisions") or "")
              and task.get("meeting_absent") == ["cormac"], str({k: task.get(k) for k in
              ("meeting_status", "meeting_absent")}))
        msgs = open(os.path.join(tmp, "bus", "meetings.jsonl"), encoding="utf-8").read().splitlines()
        slots = [json.loads(l).get("meeting_slot") for l in msgs if l.strip()]
        check("the bus carries the whole protocol (proposal, votes, prep, start, rolls, turns, close)",
              all(any(s and s.startswith(p) for s in slots)
                  for p in ("proposal", "vote-", "prep-", "start", "roll-", "turn-", "close")),
              str(slots))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if failures:
        print(f"FAIL: {len(failures)} case(s): {', '.join(failures)}")
        return 1
    print("OK: the meeting system holds (propose, vote, schedule, prep, live, minutes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
