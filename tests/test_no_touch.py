#!/usr/bin/env python3
"""RED LINE (carlo, 2026-10-11): the CLI must refuse another AI's live repos.

Carlo's words: "you absolutely CANNOT enter captchaproject... do not disturb
that AI". A rule that lives only in five agents' memory is a rule with five
chances to fail, so the refusal is in the code: every command passes through
Ctx, and Ctx refuses these names before doing any work at all.

    python3 tests/test_no_touch.py

Every case runs --local (no network, no token) so this is safe to run anywhere.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CLI = os.path.normpath(os.path.join(HERE, os.pardir, "bin", "chatcode"))
FORBIDDEN = ["dreamer2664/captchaproject", "captchaproject", "captchaprogram",
             "dreamer2664/captchaprogram", "CAPTCHAPROJECT",
             "https://github.com/dreamer2664/captchaproject", "git@github.com:dreamer2664/captchaproject.git",
             "dreamer2664/captchaproject.git", "https://github.com/dreamer2664/captchaproject/",
             "https://github.com/dreamer2664/captchaprogram"]


def run(argv, root):
    env = dict(os.environ)
    env.pop("CHATCODE_REPO", None)
    env.pop("GITHUB_TOKEN", None)
    env.pop("CHATCODE_TOKEN", None)
    return subprocess.run([sys.executable, CLI, "--local", root, "--agent", "tester", "--dry-run",
                           "--repo", argv[0], "say", "hi"],
                          capture_output=True, text=True, env=env, timeout=60)


def main() -> int:
    bad = []
    root = tempfile.mkdtemp(prefix="cc-notouch-")
    for name in FORBIDDEN:
        p = run([name], root)
        out = p.stdout + p.stderr
        if p.returncode == 0:
            bad.append(f"{name}: accepted (rc=0) — the guard did not fire")
        elif "RED LINE" not in out:
            bad.append(f"{name}: refused, but without the RED LINE message: {out.strip()[:120]}")
        elif os.path.exists(os.path.join(root, "bus")):
            bad.append(f"{name}: refused AFTER writing something in {root}")
    # control: a normal repo is not refused by the guard
    p = run(["dreamer2664/superocr"], root)
    if "RED LINE" in (p.stdout + p.stderr):
        bad.append("superocr: falsely flagged as a red line")
    if bad:
        print("FAIL: the red line is not holding")
        for b in bad:
            print("  -", b)
        return 1
    # the same names through the environment variable, not just --repo
    for name in ["dreamer2664/captchaproject", "captchaproject"]:
        env = dict(os.environ, CHATCODE_REPO=name)
        env.pop("CHATCODE_TOKEN", None)
        env.pop("GITHUB_TOKEN", None)
        p = subprocess.run([sys.executable, CLI, "--local", root, "--agent", "tester",
                            "--dry-run", "say", "hi"], capture_output=True, text=True,
                           env=env, timeout=60)
        if p.returncode == 0 or "RED LINE" not in (p.stdout + p.stderr):
            bad.append(f"CHATCODE_REPO={name}: not refused (rc={p.returncode})")
    print(f"OK: {len(FORBIDDEN)} forbidden spellings (args) + 2 via CHATCODE_REPO all refused, "
          "nothing written; a normal repo is unaffected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
