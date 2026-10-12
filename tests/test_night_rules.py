#!/usr/bin/env python3
"""The night rules (carlo, 2026-10-11): the lead decides, silence costs, collisions
get caught, and the watch never double-charges.

    python3 tests/test_night_rules.py

Everything runs in throwaway --local repos: no network, no token, no shared state.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CLI = os.path.normpath(os.path.join(HERE, os.pardir, "bin", "chatcode"))
failures = []


def iso(minutes_ago: float) -> str:
    t = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=minutes_ago)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def msg(mid, frm, mtype, text, minutes_ago, ref=None, **extra):
    d = {"id": mid, "ts": iso(minutes_ago), "from": frm, "type": mtype, "to": "*",
         "text": text, "ref": ref, "reply": None}
    d.update(extra)
    return json.dumps(d)


def build(root: str):
    for name, role in (("pericles", "lead"), ("alice", "worker"), ("bob", "worker")):
        write(os.path.join(root, "agents", f"{name}.json"),
              json.dumps({"name": name, "display": name.capitalize(), "role": role,
                          "model": "mock", "caps": "testing"}))
    write(os.path.join(root, "board", "tasks", "t-20261011-aaaa.json"),
          json.dumps({"id": "t-20261011-aaaa", "title": "under review", "status": "review",
                      "owner": "alice", "priority": 1, "created_ts": iso(90)}))
    write(os.path.join(root, "board", "tasks", "t-20261011-bbbb.json"),
          json.dumps({"id": "t-20261011-bbbb", "title": "double claimed", "status": "claimed",
                      "owner": "alice", "priority": 1, "created_ts": iso(90)}))
    lines = [
        msg("m0000001", "alice", "say", "Alice: working on it", 41),
        msg("m0000002", "pericles", "note", "Pericles: leading", 1),
        msg("m0000003", "alice", "claim", "Alice: starting", 40, ref="t-20261011-bbbb"),
        msg("m0000004", "bob", "claim", "Bob: starting too", 39, ref="t-20261011-bbbb"),
    ]
    write(os.path.join(root, "bus", "general.jsonl"), "\n".join(lines) + "\n")


def run(root, *argv, agent="pericles"):
    env = dict(os.environ)
    env.pop("CHATCODE_TOKEN", None)
    env.pop("GITHUB_TOKEN", None)
    env.pop("CHATCODE_REPO", None)
    cmd = [sys.executable, CLI, "--local", root, "--agent", agent, *argv]
    return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=90)


def check(name, cond, extra=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else f"  {extra}"))
    if not cond:
        failures.append(name)


def main() -> int:
    root = tempfile.mkdtemp(prefix="cc-night-")
    build(root)

    # --- only the lead (or carlo) decides -----------------------------------
    p = run(root, "verdict", "t-20261011-aaaa", "accept", "--reason",
            "inspected the artifact myself", agent="alice")
    check("a peer cannot issue a verdict", p.returncode != 0 and "lead" in (p.stdout + p.stderr),
          (p.stdout + p.stderr)[:120])
    p = run(root, "verdict", "t-20261011-aaaa", "accept", "--reason", "nah")
    check("a verdict without a real reason is refused", p.returncode != 0, (p.stdout + p.stderr)[:120])
    p = run(root, "verdict", "t-20261011-aaaa", "accept", "--reason",
            "read the artifact and ran the harness on it myself")
    check("the lead's accept verdict lands", p.returncode == 0, (p.stdout + p.stderr)[:200])
    task = json.load(open(os.path.join(root, "board", "tasks", "t-20261011-aaaa.json")))
    check("task is done by lead verdict",
          task.get("status") == "done" and "lead verdict" in str(task.get("decided_by")), str(task.get("status")))
    bus = open(os.path.join(root, "bus", "general.jsonl")).read()
    check("the verdict is a public vote message marked decisive",
          '"decisive": true' in bus and '"inspected": true' in bus, bus[-200:])

    # --- deny goes to the archive, nothing deleted --------------------------
    write(os.path.join(root, "board", "tasks", "t-20261011-cccc.json"),
          json.dumps({"id": "t-20261011-cccc", "title": "bad work", "status": "review",
                      "owner": "bob", "priority": 2, "created_ts": iso(80)}))
    p = run(root, "verdict", "t-20261011-cccc", "deny", "--reason",
            "the artifact is missing entirely; resubmit with the file")
    check("deny verdict runs", p.returncode == 0, (p.stdout + p.stderr)[:160])
    check("denied work is archived, not deleted",
          os.path.exists(os.path.join(root, "board", "archive", "t-20261011-cccc.json"))
          and not os.path.exists(os.path.join(root, "board", "tasks", "t-20261011-cccc.json")))
    arch = json.load(open(os.path.join(root, "board", "archive", "t-20261011-cccc.json")))
    check("the archive keeps the lead's reason",
          "missing entirely" in json.dumps(arch), json.dumps(arch)[:160])

    # --- penalties: deducted from points, with receipts ---------------------
    p = run(root, "penalize", "bob", "--points", "500", "--reason", "slept through the watch")
    check("penalty applied", p.returncode == 0 and "-500" in p.stdout, (p.stdout + p.stderr)[:120])
    p = run(root, "points")
    check("the leaderboard shows the deduction", "-500" in p.stdout, p.stdout[-400:])
    p = run(root, "penalize", "pericles", "--reason", "self-harm test")
    check("the lead cannot penalise himself", p.returncode != 0, (p.stdout + p.stderr)[:120])

    # --- the session and the watch ------------------------------------------
    run(root, "session", "start", "--reason", "overnight")
    sess = json.load(open(os.path.join(root, "board", "session.json")))
    check("the night session opens", sess.get("night") is True, str(sess)[:120])

    p = run(root, "nightcheck", "--dry-run")
    out = p.stdout + p.stderr
    check("a silent agent is named with the minutes",
          "alice" in out and ("40 min" in out or "41 min" in out), out[:250])
    check("the dry run writes nothing",
          not os.path.exists(os.path.join(root, "board", "penalties.json"))
          or "slept through the watch" in open(os.path.join(root, "board", "penalties.json")).read(),
          "penalties.json changed during dry run")

    p = run(root, "nightcheck")
    bus_after_warn = open(os.path.join(root, "bus", "general.jsonl")).read()
    check("the warning names the silent agent (t-20261012: warn first)",
          "alice has been silent for" in bus_after_warn, bus_after_warn[-260:])
    pen_path = os.path.join(root, "board", "penalties.json")
    penned = json.load(open(pen_path))["entries"] if os.path.exists(pen_path) else []
    check("the dock waits out the grace window (no instant charge)",
          [e for e in penned if e["agent"] == "alice"] == [], str(penned))

    p = run(root, "nightcheck", "--grace", "0")
    pen = json.load(open(pen_path))
    alice_entries = [e for e in pen["entries"] if e["agent"] == "alice"]
    check("silence costs 500, once", len(alice_entries) == 1 and alice_entries[0]["points"] == -500,
          str(alice_entries))
    # the episode key is the agent's LAST message — the point silence resumed from
    check("the receipt names the episode",
          alice_entries[0].get("episode") == "m0000003", str(alice_entries[0]))

    p = run(root, "nightcheck", "--grace", "0")
    pen2 = json.load(open(pen_path))
    check("a second run does not double-charge",
          len([e for e in pen2["entries"] if e["agent"] == "alice"]) == 1,
          str([e for e in pen2["entries"] if e["agent"] == "alice"]))
    sess = json.load(open(os.path.join(root, "board", "session.json")))
    check("the collision on t-bbbb is flagged once",
          any("bbbb" in json.dumps(c) for c in sess.get("collisions_warned", [])), str(sess)[:200])
    line = open(os.path.join(root, "bus", "general.jsonl")).read()
    check("the collision warning is on the bus for the human to see",
          line.count("collision on t-20261011-bbbb") == 1,
          str(line.count("collision on t-20261011-bbbb")))

    # a claim the claimant took back is NOT a collision (the t-65ff lesson)…
    write(os.path.join(root, "board", "tasks", "t-20261011-dddd.json"),
          json.dumps({"id": "t-20261011-dddd", "title": "owned by alice", "status": "claimed",
                      "owner": "alice", "priority": 2, "created_ts": iso(70)}))
    # …while a real, unresolved double claim still is (t-eeee)
    write(os.path.join(root, "board", "tasks", "t-20261011-eeee.json"),
          json.dumps({"id": "t-20261011-eeee", "title": "also owned by alice", "status": "claimed",
                      "owner": "alice", "priority": 2, "created_ts": iso(70)}))
    run(root, "session", "end")
    with open(os.path.join(root, "bus", "general.jsonl"), "a") as fh:
        fh.write(msg("m0000005", "alice", "claim", "Alice: claiming dddd", 30, ref="t-20261011-dddd") + "\n")
        fh.write(msg("m0000006", "bob", "claim", "Bob: claiming dddd too", 29, ref="t-20261011-dddd") + "\n")
        fh.write(msg("m0000007", "bob", "say",
                     "Bob: my dddd claim was refused — alice owns it, I stand down.", 28,
                     ref="t-20261011-dddd") + "\n")
        fh.write(msg("m0000008", "alice", "claim", "Alice: claiming eeee", 27, ref="t-20261011-eeee") + "\n")
        fh.write(msg("m0000009", "bob", "claim", "Bob: claiming eeee too", 26, ref="t-20261011-eeee") + "\n")
        fh.write(msg("m0000010", "bob", "say", "Bob: ploughing on with eeee", 25, ref="t-20261011-eeee") + "\n")
    run(root, "session", "start", "--reason", "resolution check")
    p = run(root, "nightcheck")
    sess = json.load(open(os.path.join(root, "board", "session.json")))
    check("a refused-then-released claim is not a collision",
          not any("dddd" in str(c) for c in sess.get("collisions_warned", [])), str(sess)[:220])
    check("an unresolved double claim still is",
          any("eeee" in str(c) for c in sess.get("collisions_warned", [])), str(sess)[:220])
    check("the watch prints one honest summary line",
          "watch:" in p.stdout and "awaiting a verdict" in p.stdout, p.stdout[-200:])
    run(root, "session", "end")

    p = run(root, "session", "end")
    check("the session closes", json.load(open(os.path.join(root, "board", "session.json")))["night"] is False)
    before = open(os.path.join(root, "bus", "general.jsonl")).read()
    run(root, "nightcheck")
    after = open(os.path.join(root, "bus", "general.jsonl")).read()
    check("outside a session the watch enforces nothing", before == after)

    print()
    if failures:
        print(f"FAIL: {len(failures)} case(s): {', '.join(failures)}")
        return 1
    print("OK: night rules hold (verdict, archive, penalty, watch, collision, close)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
