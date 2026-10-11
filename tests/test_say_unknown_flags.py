#!/usr/bin/env python3
"""t-20261011-d481 — say must not silently swallow unknown flags into text.

DEFECT: bin/chatcode:1686-1687 appends unrecognized argv to say's text, so
'say hello --typee note' posts the text 'hello --typee note' as type 'say'
— the flag the agent intended is lost with zero warning.

CHOSEN SEMANTIC (per the task's acceptance): strict — unknown flags to say
are a hard error with a clear message; genuine dash-starting text is posted
via the -- separator (argparse-native).

One command, runnable by any agent from the repo root:

    python3 tests/test_say_unknown_flags.py

Exits 0 when the fix is in place; exits 1 with a clear report against the
unfixed CLI. Stdlib only, runs against a throwaway --local repo.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CLI = os.path.normpath(os.path.join(HERE, "..", "bin", "chatcode"))

SEED = ('{"id": "00000001", "ts": "2026-10-11T10:00:00Z", "from": "alice", '
        '"type": "say", "to": "*", "text": "seed", "ref": null, "reply": null}')


def run(root, argv):
    cmd = [sys.executable, CLI, "--local", root, "--agent", "bob"] + argv
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60)


def bus_lines(root):
    path = os.path.join(root, "bus", "general.jsonl")
    with open(path, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def main():
    if not os.path.exists(CLI):
        print(f"FAIL: cannot find CLI at {CLI}")
        return 1
    root = tempfile.mkdtemp(prefix="cc-say-flags-")
    failures = []
    try:
        os.makedirs(os.path.join(root, "bus"))
        with open(os.path.join(root, "bus", "general.jsonl"), "w") as fh:
            fh.write(SEED + "\n")

        # Case 1: a typo'd flag must NOT be folded into the message.
        # Required behavior: non-zero exit, nothing posted.
        before = len(bus_lines(root))
        p = run(root, ["say", "hello", "--typee", "note"])
        after = bus_lines(root)
        if p.returncode == 0:
            failures.append(f"case1: unknown flag accepted silently (rc=0)")
        if len(after) != before:
            posted = after[-1]
            failures.append(
                "case1: message was posted despite the unknown flag: "
                f"type={posted.get('type')!r} text={posted.get('text')!r}")
        if p.returncode != 0 and "unrecognized" not in (p.stderr + p.stdout).lower():
            failures.append("case1: error message does not say what was unrecognized")

        # Case 2: genuine dash-starting text stays postable via --.
        before = len(bus_lines(root))
        p = run(root, ["say", "--", "--typee", "note"])
        after = bus_lines(root)
        if p.returncode != 0 or len(after) != before + 1:
            failures.append(f"case2: '-- <text>' escape hatch broken (rc={p.returncode})")
        elif after[-1].get("text") != "--typee note" or after[-1].get("type") != "say":
            failures.append(f"case2: wrong message posted: {after[-1]!r}")

        # Case 3: ordinary say with valid flags is untouched.
        p = run(root, ["say", "hello", "world", "--type", "note"])
        after = bus_lines(root)
        if p.returncode != 0 or after[-1].get("type") != "note" \
                or after[-1].get("text") != "hello world":
            failures.append(f"case3: normal say regressed (rc={p.returncode}, last={after[-1]!r})")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    if failures:
        print("FAIL: say swallows unknown flags / escape hatch broken")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("OK: say rejects unknown flags, '--' escape hatch works, normal say intact (3 cases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
