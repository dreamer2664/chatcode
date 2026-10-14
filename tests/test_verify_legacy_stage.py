#!/usr/bin/env python3
"""Regression test for the verify-stage policy on legacy records (vesta, 2026-10-14).

Context: `chatcode validate` sat red for two days on exactly two errors:

    bus/general.jsonl:170: verify message needs stage='ask'|'answer'|'verdict'
    bus/general.jsonl:177: verify message needs stage='ask'|'answer'|'verdict'

Both are stage-less `type: "verify"` records from 2026-10-12 21:3xZ (bob,
pericles) — written with `say -T verify`, which the protocol never sanctioned
(`chatcode verify` is the only writer: ask -> answer -> verdict, each step
citing its task and, for a verdict, the answer). They carry no task ref and
no stage: they are free-form broadcasts that happen to use the type word.
Deleting history to make a checker green is not a fix, so the policy is:

  * stage-less verify with NO task ref  -> legacy broadcast: warning only
    (stays visible), validate exits 0;
  * stage-less verify WITH a task ref   -> still an error: that is a protocol
    message missing its stage;
  * `say -T verify` is refused at the source — the record can never be
    created again;
  * the real three-stage protocol is untouched: ask/answer/verdict still
    written and still validated, with a verdict's answer_msg_id enforced.

    python3 tests/test_verify_legacy_stage.py              # CLI = repo's bin/chatcode
    python3 tests/test_verify_legacy_stage.py --cli PATH   # explicit CLI

Stdlib only, offline, exits 0 when the policy holds on every case.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
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


def append_bus(repo, line):
    path = os.path.join(repo, "bus", "general.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(line) + "\n")


def legacy_verify(mid, frm, ref=None):
    return {"id": mid, "ts": "2026-10-12T21:31:04Z", "from": frm, "type": "verify",
            "to": "*", "text": "status board is green", "ref": ref, "reply": None}


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

    repo = tempfile.mkdtemp(prefix="chatcode-legacy-verify-")
    try:
        for a in ("alice", "bob"):
            run(repo, ["--agent", a, "init", "--quiet"], 0)

        # --- case 1: legacy broadcast (no ref): warning, exit 0 ------------
        append_bus(repo, legacy_verify("aa111111", "bob", ref=None))
        p = run(repo, ["validate"], 0)
        check("stage-less verify without a task ref: warning, not an error",
              "legacy verify message without stage" in p.stdout,
              p.stdout[-400:])

        # --- case 2: stage-less WITH a ref: still an error ------------------
        append_bus(repo, legacy_verify("bb222222", "alice", ref="t-20261012-c4af"))
        p = run(repo, ["validate"])
        check("stage-less verify WITH a task ref still fails the gate",
              p.returncode != 0 and "refs a task but has no stage" in p.stdout,
              p.stdout[-400:])
        n_errors = sum(1 for l in p.stdout.splitlines() if l.startswith("ERROR"))
        check("that record is the only error on the bus", n_errors == 1,
              p.stdout[-400:])

        # --- case 3: `say -T verify` refused at the source ------------------
        bus_path = os.path.join(repo, "bus", "general.jsonl")
        before = sum(1 for l in open(bus_path) if l.strip())
        p = run(repo, ["--agent", "alice", "say", "-T", "verify", "not a protocol step"])
        check("say -T verify is refused and points at `chatcode verify`",
              p.returncode != 0 and "chatcode verify" in p.stdout + p.stderr,
              p.stdout + p.stderr)
        after = sum(1 for l in open(bus_path) if l.strip())
        check("the refused say wrote nothing to the bus", after == before,
              f"before={before} after={after}")

        # --- case 4: the real three-stage protocol is untouched -------------
        # the legacy fixtures above were only for cases 1-3; on the live bus
        # such records sit in an archive. Drop them so this case proves the
        # protocol path alone keeps the gate green.
        open(bus_path, "w").close()
        p = run(repo, ["--agent", "alice", "tasks", "new", "ship the widget", "--mine"], 0)
        tid = re.search(r"t-\d{8}-[0-9a-f]{4}", p.stdout).group(0)
        run(repo, ["--agent", "bob", "verify", tid, "--ask", "--claim", "it is fast"], 0)
        run(repo, ["--agent", "alice", "verify", tid, "--answer", "it is, here is the run"], 0)
        p = run(repo, ["--agent", "bob", "verify", tid, "--verdict", "approve",
                       "--reason", "re-ran the probe"], 0)
        with open(os.path.join(repo, "board", f"{tid}.verify.json"), encoding="utf-8") as fh:
            doc = json.load(fh)
        check("the verdict file still cites the answer and carries its stage",
              doc.get("answer_msg_id") and doc.get("state") == "closed"
              and doc.get("verdict") == "approve", json.dumps(doc)[-300:])
        p = run(repo, ["validate"], 0)
        check("a real ask/answer/verdict chain keeps validate green",
              p.returncode == 0 and "verify message needs" not in p.stdout,
              p.stdout[-400:])

        # --- case 5: stage typos are still errors ---------------------------
        append_bus(repo, dict(legacy_verify("cc333333", "alice"), stage="approve"))
        p = run(repo, ["validate"])
        check("an invented stage is still an error",
              p.returncode != 0 and "stage='ask'|'answer'|'verdict'" in p.stdout,
              p.stdout[-400:])

    finally:
        shutil.rmtree(repo, ignore_errors=True)

    if failures:
        print(f"\n{len(failures)} checks failed")
        for f in failures:
            print(" -", f.splitlines()[0])
        return 1
    print("\nOK: legacy broadcasts warn, protocol records are still strict, "
          "say cannot forge a verify")
    return 0


if __name__ == "__main__":
    sys.exit(main())
