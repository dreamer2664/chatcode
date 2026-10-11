#!/usr/bin/env python3
"""Every workflow file must be valid YAML before it reaches main.

Learned the hard way (pericles, 2026-10-11): a single colon inside an unquoted
step name ("offline: no network") made ci.yml invalid, and GitHub silently
stopped running the whole pipeline - three pushes went red before anyone looked
at why. A workflow file that cannot parse takes its checks down with it, so the
check lives outside: this test runs from ci.yml, and telegram.yml runs it too
(so if ci.yml itself ever breaks again, the room still says so).

    python3 tests/test_workflows_parse.py
"""
from __future__ import annotations

import glob
import os
import sys

try:
    import yaml
except ImportError:                                   # CI installs pyyaml for this
    print("note: pyyaml is not installed - cannot validate here")
    sys.exit(0)

HERE = os.path.dirname(os.path.abspath(__file__))
WF = os.path.join(HERE, os.pardir, ".github", "workflows")


def main() -> int:
    files = sorted(glob.glob(os.path.join(WF, "*.yml")) + glob.glob(os.path.join(WF, "*.yaml")))
    if not files:
        print("FAIL: no workflow files found - wrong path?")
        return 1
    bad = []
    for f in files:
        try:
            doc = yaml.safe_load(open(f, encoding="utf-8"))
        except Exception as e:
            bad.append(f"{os.path.basename(f)}: {e}")
            continue
        if not isinstance(doc, dict) or "jobs" not in doc or not doc["jobs"]:
            bad.append(f"{os.path.basename(f)}: parses but has no jobs")
    if bad:
        print("FAIL: workflow files that GitHub would refuse to run:")
        for b in bad:
            print("  -", b)
        return 1
    print(f"OK: {len(files)} workflow files parse and declare jobs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
