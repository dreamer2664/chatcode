#!/usr/bin/env python3
"""Run every offline test in tests/ and fail if any of them does.

t-20261011-bf89: ci.yml ran exactly one test file (python3
tests/test_conflict_retry.py) while tests/ held seven. The same day, a
commit that silently reverted the t-d481 say gate (a634690) merged green
through that hole — tests/test_say_unknown_flags.py was red on main and
nothing ran it. This runner is what CI calls now; the single-file job it
replaces would have stayed green on a revert exactly like that one.

Discovery: tests/test_*.py, sorted. repro_*.py are excluded on purpose —
they are parameterised probes (some require a branch argument), not gate
material. HOME is NOT redirected here: every test in this directory is
written to redirect it itself and run hermetically, and forcing one would
hide a test that forgot to.

Usage:
    python3 tests/run_all.py                 # run everything
    python3 tests/run_all.py --list          # show what would run
    python3 tests/run_all.py --timeout 60    # per-test timeout, seconds

Exit status: 0 when every test exits 0; 1 on any failure, crash or timeout.
"""

import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def discover() -> list[str]:
    return sorted(
        os.path.join(HERE, f)
        for f in os.listdir(HERE)
        if f.startswith("test_") and f.endswith(".py")
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="run every offline test in tests/")
    ap.add_argument("--list", action="store_true", help="list what would run, then exit")
    ap.add_argument("--timeout", type=float, default=180.0,
                    help="per-test timeout in seconds (default: 180)")
    args = ap.parse_args()

    tests = discover()
    if not tests:
        print("run_all: no tests/test_*.py found — that is itself a failure")
        return 1
    if args.list:
        for t in tests:
            print(os.path.relpath(t, os.path.dirname(HERE)))
        return 0

    root = os.path.dirname(HERE)
    failures: list[str] = []
    print(f"run_all: {len(tests)} test file(s), interpreter {sys.executable}\n")
    for path in tests:
        name = os.path.relpath(path, root)
        start = time.monotonic()
        try:
            p = subprocess.run([sys.executable, path], capture_output=True,
                               text=True, timeout=args.timeout)
            rc = p.returncode
            out = (p.stdout or "") + (p.stderr or "")
        except subprocess.TimeoutExpired as e:
            rc = -1
            out = (f"TIMEOUT after {args.timeout:.0f}s\n"
                   + (e.stdout or "") + (e.stderr or ""))
        took = time.monotonic() - start
        print(f"{'PASS' if rc == 0 else 'FAIL'}  {name}  ({took:.1f}s)")
        if rc != 0:
            failures.append(name)
            for line in out.strip().splitlines()[-12:]:
                print(f"      | {line}")

    print(f"\n{len(tests) - len(failures)}/{len(tests)} test files passed")
    if failures:
        print("failing: " + ", ".join(failures))
        print("Run a failing file directly for its full output.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
