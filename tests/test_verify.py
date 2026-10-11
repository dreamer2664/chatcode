#!/usr/bin/env python3
"""COMMS LAB 1/5 (t-20261011-3e64): `chatcode verify` — the order is the check.

A verification that costs the verifier something:
  1. ONE claim from the report becomes ONE question on #task-<id>, filed
     BEFORE the verifier reads the code (the CLI cannot see your eyes; what it
     can enforce is that no verdict exists without a recorded question, and
     that the verdict cites the author's answer).
  2. The author answers — only the owner, who holds the context the verifier
     cannot obtain alone.
  3. Only then can the verdict be written; it must cite the answer's message id
     and say whether the answer changed the verdict.
Two agents are structurally required: owner != verifier != answerer-by-proxy.
The tool refuses every shortcut. Solo version impossible by design.

    python3 tests/test_verify.py              # CLI = repo's bin/chatcode
    python3 tests/test_verify.py --cli PATH   # explicit CLI

Stdlib only, offline, exits 0 when every refusal refuses and the happy path
writes what the spec promises.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CLI = os.path.join(HERE, os.pardir, "bin", "chatcode")
CLI = None
failures = []


def run(repo, args, expect_rc=None):
    p = subprocess.run([sys.executable, CLI, "--local", repo] + args,
                       capture_output=True, text=True, timeout=60)
    if expect_rc is not None and p.returncode != expect_rc:
        failures.append(f"rc {p.returncode} != {expect_rc}: {' '.join(args)}\n"
                        f"stdout: {p.stdout[-300:]}\nstderr: {p.stderr[-300:]}")
    return p


def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name
          + (f"\n      {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(name)


def channel(repo, ch):
    path = os.path.join(repo, "bus", f"{ch}.jsonl")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def verify_file(repo, tid):
    path = os.path.join(repo, "board", f"{tid}.verify.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cli", default=DEFAULT_CLI)
    args, _ = ap.parse_known_args()
    global CLI
    CLI = os.path.abspath(args.cli)
    if not os.path.exists(CLI):
        print(f"cannot find CLI at {CLI}")
        sys.exit(1)
    print("chatcode CLI under test:", CLI)

    repo = tempfile.mkdtemp(prefix="chatcode-verify-")
    try:
        for a in ("alice", "bob", "carol"):
            run(repo, ["--agent", a, "init", "--quiet"], 0)
        p = run(repo, ["--agent", "alice", "tasks", "new", "ship the widget", "--mine"], 0)
        tid = re.search(r"t-\d{8}-[0-9a-f]{4}", p.stdout).group(0)

        # --- refusals first: every shortcut must be refused -----------------
        p = run(repo, ["--agent", "alice", "verify", tid, "--ask", "--claim", "it is fast"])
        check("owner cannot be the verifier", p.returncode != 0 and "own" in p.stdout + p.stderr)

        p = run(repo, ["--agent", "bob", "verify", tid, "--ask"])
        check("ask without --claim is refused",
              p.returncode != 0 and "--claim" in p.stdout + p.stderr)

        p = run(repo, ["--agent", "bob", "verify", tid, "--verdict", "approve",
                       "--reason", "looks fine from here"])
        check("verdict before any question is refused",
              p.returncode != 0 and "answer" in (p.stdout + p.stderr).lower())

        # --- happy path, stage 1: the question ------------------------------
        p = run(repo, ["--agent", "bob", "verify", tid, "--ask",
                       "--claim", "the retry loop cannot double-post"], 0)
        msgs = channel(repo, f"task-{tid}")
        asked = [m for m in msgs if m.get("type") == "verify" and m.get("stage") == "ask"]
        check("the question lands on #task-<id> with stage=ask", len(asked) == 1,
              json.dumps(msgs)[-300:])
        doc = verify_file(repo, tid)
        check("board/<id>.verify.json exists: state=asked, cites the question id",
              doc and doc.get("state") == "asked"
              and doc.get("question_msg_id") == asked[0]["id"]
              and doc.get("verifier") == "bob", json.dumps(doc))

        p = run(repo, ["--agent", "carol", "verify", tid, "--ask",
                       "--claim", "another thing entirely"])
        check("a second open question is refused (one claim, one question)",
              p.returncode != 0 and "already open" in p.stdout + p.stderr)

        # --- refusals at stage 2 --------------------------------------------
        p = run(repo, ["--agent", "bob", "verify", tid, "--answer", "yes it does"])
        check("the verifier cannot answer their own question",
              p.returncode != 0 and "verifier cannot answer" in p.stdout + p.stderr)

        p = run(repo, ["--agent", "carol", "verify", tid, "--answer", "sure, trust me"])
        check("a third party cannot answer for the author",
              p.returncode != 0 and "author" in p.stdout + p.stderr)

        # --- happy path, stage 2: the author answers ------------------------
        p = run(repo, ["--agent", "alice", "verify", tid, "--answer",
                       "the ballot write is the last fallible step; retries cannot re-post"], 0)
        msgs = channel(repo, f"task-{tid}")
        ans = [m for m in msgs if m.get("type") == "verify" and m.get("stage") == "answer"]
        check("the answer lands on #task-<id> with stage=answer", len(ans) == 1)
        doc = verify_file(repo, tid)
        check("state=answered and the answer id is recorded",
              doc and doc.get("state") == "answered"
              and doc.get("answer_msg_id") == ans[0]["id"] and doc.get("answerer") == "alice",
              json.dumps(doc))

        # --- refusals at stage 3 --------------------------------------------
        p = run(repo, ["--agent", "carol", "verify", tid, "--verdict", "deny",
                       "--reason", "I have opinions"])
        check("only the verifier writes the verdict",
              p.returncode != 0 and "only the verifier" in p.stdout + p.stderr)

        p = run(repo, ["--agent", "bob", "verify", tid, "--verdict", "approve"])
        check("verdict without --reason is refused",
              p.returncode != 0 and "--reason" in p.stdout + p.stderr)

        # --- happy path, stage 3: the verdict, citing the answer ------------
        p = run(repo, ["--agent", "bob", "verify", tid, "--verdict", "approve",
                       "--reason", "the guard branch runs after the append; re-ran his probe",
                       "--changed", "yes"], 0)
        doc = verify_file(repo, tid)
        check("the verdict file cites the answer's message id",
              doc and doc.get("answer_msg_id") == ans[0]["id"], json.dumps(doc))
        check("the verdict says whether the answer changed it",
              doc and doc.get("changed_verdict") is True and doc.get("verdict") == "approve",
              json.dumps(doc))
        check("state=closed with the verdict message id",
              doc and doc.get("state") == "closed" and doc.get("verdict_msg_id"),
              json.dumps(doc))
        msgs = channel(repo, f"task-{tid}")
        ver = [m for m in msgs if m.get("type") == "verify" and m.get("stage") == "verdict"]
        check("the verdict also lands on the bus, citing the answer",
              len(ver) == 1 and ver[0].get("answer_msg_id") == ans[0]["id"])

        p = run(repo, ["--agent", "carol", "verify", tid, "--ask", "--claim", "one more"])
        check("a closed verification cannot be re-opened",
              p.returncode != 0 and "closed" in p.stdout + p.stderr)

        # --- the record survives validate -----------------------------------
        p = run(repo, ["validate"], 0)
        check("chatcode validate stays green with verify messages on the bus",
              p.returncode == 0 and "unknown type" not in p.stdout + p.stderr)

        # --- show -------------------------------------------------------------
        p = run(repo, ["verify", tid, "--show"], 0)
        check("--show prints the record",
              "changed_verdict" in p.stdout and ans[0]["id"] in p.stdout, p.stdout[-200:])

    finally:
        import shutil
        shutil.rmtree(repo, ignore_errors=True)

    if failures:
        print(f"\n{len(failures)} checks failed")
        for f in failures:
            print(" -", f.splitlines()[0])
        return 1
    print("\nOK: every shortcut refused, the three stages enforced, the verdict cites the answer")
    return 0


if __name__ == "__main__":
    sys.exit(main())
