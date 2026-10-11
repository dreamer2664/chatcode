#!/usr/bin/env python3
"""The -c flag must work before AND after the subcommand (t-20261011-25ff).

add_common_flags() gives every subparser a suppressed -c so a value the root
parser already parsed survives (that is the design: `chatcode --agent x init`
and `chatcode init --name x` are the same). But nine subparsers called
set_defaults(func=..., channel=None), and set_defaults overwrites the DEFAULT
OF THE SHARED ACTION OBJECT — parents share actions — so the first such call
poisoned -c for all 24 subparsers at once. Symptom: `chatcode -c dev say "hi"`
silently posted to #general, and `chatcode -c dev vote ...` silently voted on
the default channel. A message the user believes went to dev landing in
general is not a small thing on a bus relayed to a phone.

    python3 tests/test_channel_flag_position.py
    python3 tests/test_channel_flag_position.py --cli /path/to/bin/chatcode

Exit 0 = both positions land in bus/dev.jsonl. Stdlib only, offline.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CLI = os.path.join(HERE, os.pardir, "bin", "chatcode")
CLI = sys.argv[sys.argv.index("--cli") + 1] if "--cli" in sys.argv else DEFAULT_CLI

fails = []


def run(*args):
    return subprocess.run([sys.executable, CLI, *args], capture_output=True,
                          text=True, timeout=120)


def check(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + (f"   {detail}" if detail and not ok else ""))
    if not ok:
        fails.append(name)


for label, marker, argv in (
        ("after the subcommand", "pos-after", ["say", "pos-after", "-c", "dev"]),
        ("before the subcommand", "pos-before", ["-c", "dev", "say", "pos-before"])):
    with tempfile.TemporaryDirectory() as td:
        run("--local", td, "--agent", "tt", "init", "--quiet")
        r = run("--local", td, "--agent", "tt", *argv)
        path = os.path.join(td, "bus", "dev.jsonl")
        ok = r.returncode == 0 and os.path.exists(path)
        if ok:
            lines = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
            ok = any(m.get("text", "").endswith(marker) for m in lines)
        # and the default channel must NOT have it (the old silent-reroute bug)
        general = os.path.join(td, "bus", "general.jsonl")
        if ok and os.path.exists(general):
            gl = [json.loads(l) for l in open(general, encoding="utf-8") if l.strip()]
            ok = not any(marker in m.get("text", "") for m in gl)
        check(f"-c {label} lands in bus/dev.jsonl (not general)", ok,
              (r.stderr.strip() or r.stdout.strip())[:160])

print()
if fails:
    print(f"FAIL: {len(fails)} case(s): {', '.join(fails)}")
    sys.exit(1)
print("OK: -c works in both positions (the set_defaults poisoning is gone)")
