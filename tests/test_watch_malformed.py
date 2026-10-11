#!/usr/bin/env python3
"""t-20261011-792d — watch must survive malformed bus lines.

DEFECT: bin/chatcode:1185 (startup) and :1211 (in-loop) index msgs[-1]["id"];
a malformed JSONL line becomes a `_broken` entry with no `id`, so `watch`
dies with KeyError: 'id'.

One command, runnable by any agent from the repo root:

    python3 tests/test_watch_malformed.py

Exits 0 when the fix is in place; exits 1 with a clear report against the
unfixed CLI. Stdlib only, runs against a throwaway --local repo, never
touches the live board.
"""

import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CLI = os.path.normpath(os.path.join(HERE, "..", "bin", "chatcode"))

VALID_LINE = ('{"id": "deadbeef", "ts": "2026-10-11T10:00:00Z", "from": "alice", '
              '"type": "say", "to": "*", "text": "hello", "ref": null, "reply": null}')


def run_watch(root, channel, extra):
    cmd = [sys.executable, CLI, "--local", root, "watch", "-c", channel,
           "--interval", "1"] + extra
    return subprocess.run(cmd, capture_output=True, text=True, timeout=90)


def main():
    if not os.path.exists(CLI):
        print(f"FAIL: cannot find CLI at {CLI}")
        return 1
    root = tempfile.mkdtemp(prefix="cc-watch-malformed-")
    failures = []
    try:
        os.makedirs(os.path.join(root, "bus"))

        # Case 1: channel whose ONLY line is malformed, --once (startup path,
        # bin/chatcode:1185). Must exit 0, warn about the line, no traceback.
        with open(os.path.join(root, "bus", "broken.jsonl"), "w") as fh:
            fh.write("this line is not json at all\n")
        p = run_watch(root, "broken", ["--once"])
        if p.returncode != 0 or "Traceback" in p.stderr:
            tail = (p.stderr.strip().splitlines() or ["<empty>"])[-1]
            failures.append(f"case1 startup: rc={p.returncode}, stderr tail: {tail}")
        if "malformed line" not in (p.stdout + p.stderr):
            failures.append("case1: expected the malformed-line warning to be printed")

        # Case 2: same channel across several poll loops (in-loop path,
        # bin/chatcode:1211 — last_id stays None, so every poll re-slices the
        # malformed entries). Must survive 3 loops without a traceback.
        p = run_watch(root, "broken", ["--for", "3"])
        if p.returncode != 0 or "Traceback" in p.stderr:
            tail = (p.stderr.strip().splitlines() or ["<empty>"])[-1]
            failures.append(f"case2 loop: rc={p.returncode}, stderr tail: {tail}")

        # Case 3: healthy channel mixed with one garbage line — no regression:
        # the valid message must still be shown and the watch must not die.
        with open(os.path.join(root, "bus", "mixed.jsonl"), "w") as fh:
            fh.write(VALID_LINE + "\n")
            fh.write("garbage line\n")
        p = run_watch(root, "mixed", ["--once"])
        if p.returncode != 0 or "Traceback" in p.stderr:
            tail = (p.stderr.strip().splitlines() or ["<empty>"])[-1]
            failures.append(f"case3 mixed: rc={p.returncode}, stderr tail: {tail}")
        if "hello" not in p.stdout:
            failures.append("case3 mixed: valid message not shown any more")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    if failures:
        print("FAIL: watch does not survive malformed bus lines")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("OK: watch survives malformed bus lines (3 cases: startup, loop, mixed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
