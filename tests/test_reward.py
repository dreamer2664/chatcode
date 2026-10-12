#!/usr/bin/env python3
"""The commendation (carlo, 2026-10-12): a reward is a fact with a reason and a
receipt, lead-only, folded into the leaderboard like a penalty.

    python3 tests/test_reward.py

Throwaway --local repo: no network, no token, no shared state.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CLI = os.path.normpath(os.path.join(HERE, os.pardir, "bin", "chatcode"))
failures = []


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def run(root, *argv, agent="pericles"):
    env = dict(os.environ)
    for k in ("CHATCODE_TOKEN", "GITHUB_TOKEN", "CHATCODE_REPO"):
        env.pop(k, None)
    cmd = [sys.executable, CLI, "--local", root, "--agent", agent, *argv]
    return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=90)


def check(name, cond, extra=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else f"  {extra}"))
    if not cond:
        failures.append(name)


def build(root: str):
    for name, role in (("pericles", "lead"), ("alice", "worker"), ("bob", "worker")):
        write(os.path.join(root, "agents", f"{name}.json"),
              json.dumps({"name": name, "display": name.capitalize(), "role": role,
                          "model": "mock", "caps": "testing"}))
    write(os.path.join(root, "board", "tasks", "t-20261012-eeee.json"),
          json.dumps({"id": "t-20261012-eeee", "title": "a finished task",
                      "status": "done", "owner": "alice", "priority": 1,
                      "created_ts": "2026-10-12T00:00:00Z"}))
    write(os.path.join(root, "bus", "general.jsonl"), "")


def main() -> int:
    root = tempfile.mkdtemp(prefix="cc-reward-")
    build(root)

    # --- only the lead (or carlo) rewards ------------------------------------
    p = run(root, "reward", "alice", "--points", "500", "--reason",
            "carried the night watch alone", agent="bob")
    check("a peer cannot grant a reward",
          p.returncode != 0 and "lead" in (p.stdout + p.stderr).lower(),
          (p.stdout + p.stderr)[:140])

    p = run(root, "reward", "alice", "--points", "500", "--reason", "nice")
    check("a reward without a real reason is refused", p.returncode != 0,
          (p.stdout + p.stderr)[:140])

    p = run(root, "reward", "pericles", "--points", "500", "--reason",
            "self-award attempt on the record")
    check("the lead cannot reward himself", p.returncode != 0,
          (p.stdout + p.stderr)[:140])

    p = run(root, "reward", "ghost", "--points", "500", "--reason",
            "no such agent on the roster")
    check("an unknown agent is refused", p.returncode != 0,
          (p.stdout + p.stderr)[:140])

    # --- the real thing: receipt, leaderboard, bus ---------------------------
    p = run(root, "reward", "alice", "--points", "500", "--reason",
            "all-night watch and 32 tasks, far beyond the call")
    check("the lead's reward lands", p.returncode == 0 and "+500" in p.stdout,
          (p.stdout + p.stderr)[:200])

    rew = json.load(open(os.path.join(root, "board", "rewards.json")))
    check("the receipt is on the board", rew["totals"]["alice"] == 500
          and rew["entries"] and rew["entries"][-1]["by"] == "pericles"
          and "beyond the call" in rew["entries"][-1]["reason"], json.dumps(rew)[:200])

    bus = open(os.path.join(root, "bus", "general.jsonl")).read()
    check("the reward is a public bus message",
          '"type": "status"' in bus and "reward: +500 to alice" in bus, bus[-220:])

    p = run(root, "points")
    out = p.stdout
    check("the leaderboard folds the reward in (100 task + 500 = 600)",
          "600" in out and "rewards:" in out and "+500" in out, out[-420:])

    p = run(root, "digest")
    check("STATUS renders with the reward folded in", p.returncode == 0 and "600" in p.stdout,
          (p.stdout + p.stderr)[-300:])

    print()
    if failures:
        print(f"failing: {', '.join(failures)}")
        return 1
    print("OK: rewards are lead-only, receipted, public, and counted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
