#!/usr/bin/env python3
"""
local_bots.py — two synthetic agents run a complete chatcode cycle in a local
directory. No token, no network, no API quota: perfect for testing the system
(or for showing a human what the collective looks like in motion).

    python3 examples/local_bots.py --dir /tmp/demo
    python3 examples/local_bots.py --dir /tmp/demo --clean

It drives the real CLI (bin/chatcode) through a scratch repo, so it exercises
exactly the same code path a remote agent would use.
"""

import argparse
import os
import shutil
import subprocess
import sys
import time

def say(text=""):
    """print + flush, so interleaved subprocess output stays in order"""
    print(text, flush=True)


HERE = os.path.dirname(os.path.abspath(__file__))
CLI = os.path.join(os.path.dirname(HERE), "bin", "chatcode")

C_CLI = "\033[36m"
C_BOT = "\033[35m"
C_DIM = "\033[2m"
C_0 = "\033[0m"


def call(root, agent, *args, quiet=True):
    cmd = [sys.executable, CLI, "--local", root, "--agent", agent, *args]
    p = subprocess.run(cmd, capture_output=True, text=True)
    out = (p.stdout + p.stderr).strip()
    if p.returncode != 0:
        say(f"{C_DIM}  [exit {p.returncode}] {out}{C_0}")
    elif out and not quiet:
        say(f"{C_DIM}  {out.splitlines()[0]}{C_0}")
    return p.returncode, p.stdout


def step(n, text):
    say(f"\n{C_CLI}── step {n}: {text}{C_0}")
    time.sleep(0.15)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="/tmp/chatcode-demo", help="scratch directory")
    ap.add_argument("--clean", action="store_true", help="wipe the scratch directory first")
    args = ap.parse_args()
    root = os.path.abspath(args.dir)

    if args.clean and os.path.exists(root):
        shutil.rmtree(root)
    os.makedirs(root, exist_ok=True)

    say(f"{C_BOT}chatcode demo{C_0} — two agents, one repo, no network")
    say(f"{C_DIM}scratch dir: {root}{C_0}")

    step(1, "two agents join the collective")
    call(root, "nova", "init", "--quiet", "--model", "demo-1", "--role", "worker",
         "--caps", "parsing, tests")
    call(root, "orion", "init", "--quiet", "--model", "demo-2", "--role", "reviewer",
         "--caps", "review, docs")
    call(root, "nova", "say", "nova online. Room looks clean — who is holding the board?")
    call(root, "orion", "say",
         "orion online, reviewer hat on. Convention: post work as tasks on the board, "
         "then claim your own — no grabbing from the chat.")

    step(2, "a task is created and announced")
    rc, out = call(root, "nova", "tasks", "new", "Parse the incoming message stream",
                   "--desc", "jsonl -> objects, tolerate malformed lines, unit tests",
                   "--priority", "1", "--announce")
    tid = next((w.strip(",") for w in out.split() if w.startswith("t-")), None)
    say(f"{C_DIM}  board: {tid}{C_0}")

    step(3, "nova claims it and states a plan")
    call(root, "nova", "tasks", "claim", tid, "--announce")
    call(root, "nova", "say",
         f"plan for {tid}: strict parse with a fallback that surfaces malformed lines "
         "instead of dropping them. Branch agent/nova/" + str(tid) + ".",
         "--type", "claim", "--ref", tid)

    step(4, "orion asks a real question instead of duplicating work")
    call(root, "orion", "say",
         "before you build: does 'malformed' mean skip, or surface? If we surface, the "
         "reader needs a _broken field. I can review that contract.",
         "--type", "note", "--to", "nova", "--ref", tid)

    step(5, "nova answers and hands off for review")
    call(root, "nova", "say",
         "surface, never skip. shape: {\"_broken\": \"<raw line>\", \"_channel\": \"…\"}.",
         "--type", "note", "--to", "orion", "--ref", tid)
    call(root, "nova", "tasks", "update", tid, "--status", "review",
         "--note", "parser + tests in agent/nova/" + str(tid) + ", contract as agreed",
         "--announce")

    step(6, "orion reviews — with evidence, not vibes")
    call(root, "orion", "say",
         "review of " + str(tid) + ": checked parse + fallback + 6 malformed cases in "
         "the tests. verdict: approve — changing the contract now would cost more than "
         "it buys.",
         "--type", "review", "--to", "nova", "--ref", tid)

    step(7, "the lead closes it out")
    call(root, "orion", "tasks", "update", tid, "--status", "done",
         "--note", "reviewed by orion, approved", "--announce")

    step(8, "what the human sees")
    subprocess.run([sys.executable, CLI, "--local", root, "status"], check=False)
    dg = subprocess.run([sys.executable, CLI, "--local", root, "digest", "--print"],
                        capture_output=True, text=True)
    with open(os.path.join(root, "STATUS.md"), "w", encoding="utf-8") as fh:
        fh.write(dg.stdout)
    say(f"\n{C_BOT}STATUS.md written to {root}/STATUS.md{C_0}")
    say(f"{C_DIM}inspect: python3 bin/chatcode --local {root} read --tail 20{C_0}")


if __name__ == "__main__":
    main()
