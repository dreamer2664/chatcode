#!/usr/bin/env python3
"""t-20261011-9b7a — read --mentions must filter broadcasts (or it is a no-op).

CHOSEN SEMANTIC (stated in the PR per acceptance criterion 1): strict.
`--mentions <me>` returns messages with to == me, plus any message whose
text @-mentions me. Broadcasts (to="*") pass ONLY when they @-mention me.
AGENT_PROMPT.md already advertises this command as 'what needs me', so the
code moves to the documented semantic; no doc edit is needed.

One command, runnable by any agent from the repo root:

    python3 tests/test_mentions_filter.py

Exits 0 when the fix is in place; exits 1 against the unfixed CLI.
Stdlib only; runs against a throwaway --local repo, no network.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CLI = os.path.normpath(os.path.join(HERE, "..", "bin", "chatcode"))

MESSAGES = [
    # id, to, text, expected visible with --mentions bob
    ("00000001", "*",     "broadcast plain, no mention",     False),
    ("00000002", "*",     "hello @bob please look at this",  True),
    ("00000003", "bob",   "direct message for bob",          True),
    ("00000004", "carol", "direct message for carol",        False),
]


def main():
    if not os.path.exists(CLI):
        print(f"FAIL: cannot find CLI at {CLI}")
        return 1
    root = tempfile.mkdtemp(prefix="cc-mentions-")
    failures = []
    try:
        os.makedirs(os.path.join(root, "bus"))
        with open(os.path.join(root, "bus", "general.jsonl"), "w") as fh:
            for i, (mid, to, text, _) in enumerate(MESSAGES):
                fh.write(json.dumps({"id": mid, "ts": f"2026-10-11T10:00:0{i}Z",
                                     "from": "alice", "type": "say", "to": to,
                                     "text": text, "ref": None, "reply": None}) + "\n")
        cmd = [sys.executable, CLI, "--local", root, "read", "-c", "general",
               "--mentions", "bob", "--jsonl"]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if p.returncode != 0:
            failures.append(f"read --mentions crashed: rc={p.returncode} "
                            f"stderr={p.stderr.strip().splitlines()[-1:]}")
        else:
            got = {json.loads(l)["id"] for l in p.stdout.splitlines() if l.strip()}
            for mid, to, text, expected in MESSAGES:
                seen = mid in got
                if seen != expected:
                    failures.append(
                        f"message {mid} (to={to!r}, {text!r}): "
                        f"{'shown but must be filtered' if seen else 'filtered but must be shown'}")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    if failures:
        print("FAIL: read --mentions does not implement the strict semantic")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("OK: read --mentions is strict — direct + @-mentions only, "
          "plain broadcasts filtered (4 cases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
