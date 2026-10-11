#!/usr/bin/env python3
"""t-20261011-4949: cmd_vote must reject voters not on the roster.

Red on main: an unregistered --agent name casts a counted ballot.
Green here: hard error pointing at init; rostered voters unchanged.
Run: python3 tests/test_vote_roster.py
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

CLI = Path(__file__).resolve().parent.parent / "bin" / "chatcode"


def run(args, home, local):
    env = dict(os.environ, HOME=str(home))
    env.pop("CHATCODE_AGENT", None)
    env.pop("CHATCODE_TOKEN", None)
    return subprocess.run([sys.executable, str(CLI), *args, "--local", str(local)],
                          capture_output=True, text=True, env=env, timeout=120)


def main():
    tmp = Path(tempfile.mkdtemp(prefix="vr_"))
    home, local = tmp / "home", tmp / "repo"
    local.mkdir(parents=True)
    (local / "board" / "tasks").mkdir(parents=True)
    (local / "bus").mkdir(parents=True)

    for name in ("alpha", "beta"):
        r = run(["init", "--name", name, "--model", "m", "--role", "worker",
                 "--caps", "t"], home, local)
        assert r.returncode == 0, f"init {name}: {r.stderr[-200:]}"

    task = {"id": "t-x1", "title": "roster test", "status": "review",
            "owner": "beta", "priority": 3, "votes": {}}
    (local / "board" / "tasks" / "t-x1.json").write_text(json.dumps(task))

    r = run(["vote", "t-x1", "accept-inspected", "--reason", "ghost",
             "--agent", "gamma"], home, local)
    assert r.returncode != 0, "RED: unregistered voter was accepted"
    out = (r.stderr + r.stdout)
    assert "roster" in out and "init" in out, f"error lacks guidance: {out[-200:]}"
    busf = local / "bus" / "general.jsonl"
    lines = busf.read_text().splitlines() if busf.exists() else []
    ghost = [l for l in lines if "gamma" in l]
    assert not ghost, "ghost ballot landed on the bus"

    r = run(["vote", "t-x1", "accept-inspected", "--reason", "real",
             "--agent", "alpha"], home, local)
    assert r.returncode == 0, f"rostered voter rejected: {r.stderr[-300:]}"

    print("OK: unregistered voters rejected with guidance; rostered voters fine")
    return 0


if __name__ == "__main__":
    sys.exit(main())
