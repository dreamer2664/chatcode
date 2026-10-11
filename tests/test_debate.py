#!/usr/bin/env python3
"""t-20261011-2531: `chatcode debate` — structured disagreement, enforced.

Runs the CLI in --local mode against a throwaway checkout: four agents,
a full debate lifecycle (proposal → openings → rebuttals → votes →
recorded decision), every enforcement rule exercised against a wrong-doer,
and the no-opposition failure mode (proposal dropped, not decided).

Run: python3 tests/test_debate.py     (exit 0 = all green)
"""
import json
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = os.path.join(REPO, "bin", "chatcode")


def run(root, agent, *args, expect_ok=True):
    cmd = [sys.executable, CLI, "--local", root, "--agent", agent, *args]
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO,
                       env={**os.environ, "CHATCODE_TOKEN": "", "CHATCODE_REPO": ""})
    if expect_ok and p.returncode != 0:
        raise AssertionError(f"command failed: {' '.join(cmd)}\n"
                             f"stdout: {p.stdout}\nstderr: {p.stderr}")
    if not expect_ok and p.returncode == 0:
        raise AssertionError(f"command should have been refused: {' '.join(cmd)}\n"
                             f"stdout: {p.stdout}")
    return p


def read_task(root, tid):
    with open(os.path.join(root, "board", "tasks", f"{tid}.json")) as fh:
        return json.load(fh)


def bus_messages(root, channel="general"):
    p = os.path.join(root, "bus", f"{channel}.jsonl")
    if not os.path.exists(p):
        return []
    with open(p) as fh:
        return [json.loads(l) for l in fh if l.strip()]


def main():
    with tempfile.TemporaryDirectory() as root:
        for who in ("alpha", "beta", "gamma", "delta"):
            run(root, who, "init", "--quiet", "--display", who.title())

        # ---- open a debate ------------------------------------------------
        p = run(root, "alpha", "debate", "new", "We should adopt policy X",
                "--for", "alpha", "--against", "beta")
        tasks = os.listdir(os.path.join(root, "board", "tasks"))
        debate_ids = []
        for f in tasks:
            t = read_task(root, f[:-5])
            if t.get("debate_for"):
                debate_ids.append(t["id"])
        assert len(debate_ids) == 1, f"expected one debate task, got {debate_ids}"
        tid = debate_ids[0]
        t = read_task(root, tid)
        assert t["debate_for"] == "alpha" and t["debate_against"] == "beta"
        assert t["status"] == "review", "debate task must be votable"
        prop = [m for m in bus_messages(root) if m.get("debate_slot") == "proposal"]
        assert len(prop) == 1, "proposal message must be on the bus"

        # ---- enforcement: wrong agent, wrong order, duplicates ------------
        run(root, "gamma", "debate", "speak", tid, "--side", "for",
            "--round", "opening", "--text", "usurping", expect_ok=False)
        run(root, "beta", "debate", "speak", tid, "--side", "against",
            "--round", "rebuttal", "--text", "too early", expect_ok=False)

        run(root, "alpha", "debate", "speak", tid, "--side", "for",
            "--round", "opening", "--text", "X is good because A")
        # rebuttal before the OTHER side has opened: refused
        run(root, "alpha", "debate", "speak", tid, "--side", "for",
            "--round", "rebuttal", "--text", "pre-emptive", expect_ok=False)
        run(root, "beta", "debate", "speak", tid, "--side", "against",
            "--round", "opening", "--text", "X is bad because B")
        run(root, "alpha", "debate", "speak", tid, "--side", "for",
            "--round", "rebuttal", "--text", "B is wrong because C")
        # second opening: refused
        run(root, "alpha", "debate", "speak", tid, "--side", "for",
            "--round", "opening", "--text", "again", expect_ok=False)
        run(root, "beta", "debate", "speak", tid, "--side", "against",
            "--round", "rebuttal", "--text", "C is wrong because D")
        # second rebuttal: refused — max 2 rounds is real
        run(root, "beta", "debate", "speak", tid, "--side", "against",
            "--round", "rebuttal", "--text", "one more", expect_ok=False)

        slots = [m.get("debate_slot") for m in bus_messages(root)
                 if m.get("ref") == tid and m.get("debate_slot")]
        assert sorted(slots) == sorted(["proposal", "for-opening", "against-opening",
                                        "for-rebuttal", "against-rebuttal"]), slots

        # ---- votes: everyone but the debaters; a debater's ballot is
        # ignored at close ---------------------------------------------------
        run(root, "gamma", "vote", tid, "accept-trusted", "--reason", "for-side wins")
        run(root, "delta", "vote", tid, "accept-trusted", "--reason", "agreed")
        # a debater voting their own debate is refused by the CLI
        run(root, "beta", "vote", tid, "deny-trusted",
            "--reason", "I lost the debate but I am a debater", expect_ok=False)
        # votes alone must NOT auto-close a debate — only `debate close` decides
        t = read_task(root, tid)
        assert t["status"] == "review", "votes must not auto-close a debate"
        run(root, "gamma", "debate", "close", tid)
        t = read_task(root, tid)
        assert t["status"] == "done", t["status"]
        assert t["debate_result"] == "accepted", t["debate_result"]
        assert len(t["debate_messages"]) == 4, "decision must link the four speeches"
        assert t["decided_by"].startswith("debate vote 2-0"), \
            f"debater's deny ballot must be excluded: {t['decided_by']}"
        dec = [m for m in bus_messages(root) if m.get("debate_slot") == "decision"]
        assert len(dec) == 1 and dec[0]["debate_links"] == t["debate_messages"]

        # ---- failure mode: no opposition ever speaks -> dropped -----------
        run(root, "alpha", "debate", "new", "Policy Y, nobody objects",
            "--for", "alpha", "--against", "gamma")
        tids = []
        for f in os.listdir(os.path.join(root, "board", "tasks")):
            tt = read_task(root, f[:-5])
            if tt.get("debate_for") and tt["id"] != tid:
                tids.append(tt)
        assert len(tids) == 1
        t2 = tids[0]
        run(root, "alpha", "debate", "speak", t2["id"], "--side", "for",
            "--round", "opening", "--text", "Y is great")
        run(root, "delta", "vote", t2["id"], "accept-trusted", "--reason", "sure")
        run(root, "delta", "debate", "close", t2["id"])
        t2 = read_task(root, t2["id"])
        assert t2["status"] == "dropped", t2["status"]
        assert t2["debate_result"] == "failed-no-opposition", t2["debate_result"]

        print("OK — debate lifecycle, enforcement, debater-exclusion and the "
              "no-opposition drop all behave as specified")


if __name__ == "__main__":
    main()
