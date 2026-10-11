#!/usr/bin/env python3
"""Channel names must be bus file names (t-20261011-d72a).

CHANNEL_RE existed in bin/chatcode and nothing called it, so `-c` went
straight into `bus/<channel>.jsonl`. Locally that walks out of the checkout
(`-c ../../x` writes ../../x.jsonl beside the repo); against the API GitHub
normalises `bus/../x.jsonl` to `x.jsonl`, so the write reports success and the
message is invisible to `read` and to `validate` — a silent hole in a bus that
is supposed to be append-only and public.

    python3 tests/test_channel_validation.py
    python3 tests/test_channel_validation.py --cli /path/to/main/bin/chatcode   # red

Exit 0 = all cases pass. Stdlib only, no network, no token: every case runs
against a throwaway --local repo, and the traversal case asserts that nothing
was written outside it.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CLI = os.path.join(HERE, os.pardir, "bin", "chatcode")

# names that must die with our own message
BAD = ["../../escaped", "../escaped", "sub/dir", "UPPER", "x" * 33,
       "with space", "dot.dot", "semi;colon"]
# rejected earlier, by argparse, because it looks like a flag (rc=2, no write)
BAD_REFUSED_BY_ARGPARSE = ["-leading"]
# an empty -c is treated as "not supplied" and falls back to the default
# channel. That is pre-existing behaviour for every option in this CLI, so it
# is pinned here as a documented nuance rather than changed in a path fix.
EMPTY_MEANS_DEFAULT = ""
GOOD = ["general", "dev", "task-t-20261011-d72a", "human-carlo", "a1", "x" * 32]


def run(cli: str, root: str, home: str, agent: str, *args: str):
    env = dict(os.environ, HOME=home, CHATCODE_AGENT=agent)
    return subprocess.run([sys.executable, os.path.abspath(cli), "--local", root,
                           "--agent", agent, *args],
                          capture_output=True, text=True, env=env, timeout=60)


def setup(cli: str) -> tuple[str, str]:
    root = tempfile.mkdtemp(prefix="chatcode-chan-")
    home = tempfile.mkdtemp(prefix="chatcode-chan-home-")
    run(cli, root, home, "alice", "init", "--quiet", "--model", "mock")
    return root, home


def files_under(path: str) -> set[str]:
    out = set()
    for base, _dirs, names in os.walk(path):
        for n in names:
            out.add(os.path.join(base, n))
    return out


# --- cases ----------------------------------------------------------------

def case_bad_names_are_refused(cli: str) -> tuple[bool, str]:
    """Every invalid name must die with a message naming the rule, and write nothing."""
    root, home = setup(cli)
    before = files_under(root)
    bad_results = []
    for name in BAD:
        proc = run(cli, root, home, "alice", "say", "hello", "-c", name)
        combined = proc.stdout + proc.stderr
        refused = proc.returncode != 0 and "invalid channel" in combined
        if not refused:
            bad_results.append(f"{name!r} -> rc={proc.returncode}")
    for name in BAD_REFUSED_BY_ARGPARSE:
        proc = run(cli, root, home, "alice", "say", "hello", "-c", name)
        if proc.returncode == 0:
            bad_results.append(f"{name!r} -> accepted (rc=0)")
    after = files_under(root)
    new_files = sorted(after - before)
    ok = not bad_results and not new_files
    detail = f"{len(BAD)} bad names, refused={len(BAD) - len(bad_results)}"
    if bad_results:
        detail += " | accepted: " + ", ".join(bad_results)
    if new_files:
        detail += f" | wrote {new_files}"
    return ok, detail


def case_traversal_writes_nothing_outside_the_repo(cli: str) -> tuple[bool, str]:
    """`-c ../../escaped` must not create a file above the checkout root."""
    root, home = setup(cli)
    parent = os.path.dirname(root)
    before = files_under(parent)
    proc = run(cli, root, home, "alice", "say", "escape attempt", "-c", "../../escaped")
    after = files_under(parent)
    new_outside = sorted(after - before)
    ok = proc.returncode != 0 and not new_outside
    detail = (f"rc={proc.returncode} new_files_outside_root={len(new_outside)}"
              + (f" {new_outside}" if new_outside else ""))
    return ok, detail


def case_empty_c_means_default(cli: str) -> tuple[bool, str]:
    """Pinned nuance: an empty -c behaves like no -c (documented, unchanged)."""
    root, home = setup(cli)
    proc = run(cli, root, home, "alice", "say", "empty channel flag", "-c", EMPTY_MEANS_DEFAULT)
    r = run(cli, root, home, "alice", "read", "-c", "general")
    ok = proc.returncode == 0 and "empty channel flag" in r.stdout
    stray = [f for f in files_under(root) if "bus/general.jsonl" not in f
             and not f.endswith(".json")]
    return ok and not stray, (f"rc={proc.returncode} landed_in_general="
                              f"{'empty channel flag' in r.stdout} stray_files={len(stray)}")


def case_reads_are_guarded_too(cli: str) -> tuple[bool, str]:
    """The hole is not only a write problem: reads must refuse as well."""
    root, home = setup(cli)
    proc = run(cli, root, home, "alice", "read", "-c", "../../escaped")
    ok = proc.returncode != 0 and "invalid channel" in (proc.stdout + proc.stderr)
    return ok, f"rc={proc.returncode}"


def case_rotate_is_guarded(cli: str) -> tuple[bool, str]:
    """rotate takes args.channel directly, bypassing ctx.channel — so it gets its own check."""
    root, home = setup(cli)
    proc = run(cli, root, home, "alice", "rotate", "-c", "../../escaped")
    ok = proc.returncode != 0 and "invalid channel" in (proc.stdout + proc.stderr)
    return ok, f"rc={proc.returncode}"


def case_valid_names_still_work(cli: str) -> tuple[bool, str]:
    """The guard must cost nothing: every legal channel keeps working, writes and reads."""
    root, home = setup(cli)
    failures = []
    for name in GOOD:
        s = run(cli, root, home, "alice", "say", f"hello {name}", "-c", name)
        r = run(cli, root, home, "alice", "read", "-c", name)
        wrote = s.returncode == 0 and r.returncode == 0 and f"hello {name}" in r.stdout
        if not wrote:
            failures.append(f"{name!r} say_rc={s.returncode} read_rc={r.returncode}")
    ok = not failures
    return ok, f"{len(GOOD)} valid names" + (f" | failed: {failures}" if failures else ", all usable")


def case_default_channel_unaffected(cli: str) -> tuple[bool, str]:
    """Control: no -c at all still posts to #general."""
    root, home = setup(cli)
    s = run(cli, root, home, "alice", "say", "no channel flag")
    r = run(cli, root, home, "alice", "read", "-c", "general")
    ok = s.returncode == 0 and "no channel flag" in r.stdout
    return ok, f"say_rc={s.returncode} visible_in_general={'no channel flag' in r.stdout}"


CASES = [
    ("invalid channel names are refused, nothing written", case_bad_names_are_refused),
    ("traversal writes nothing outside the repo root", case_traversal_writes_nothing_outside_the_repo),
    ("empty -c falls back to the default channel (pinned)",
     case_empty_c_means_default),
    ("reads are guarded as well as writes", case_reads_are_guarded_too),
    ("rotate is guarded (it bypasses ctx.channel)", case_rotate_is_guarded),
    ("every valid channel name still works", case_valid_names_still_work),
    ("control: no -c still posts to #general", case_default_channel_unaffected),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cli", default=DEFAULT_CLI, help="path to the chatcode CLI under test")
    args = ap.parse_args()
    print(f"chatcode CLI under test: {os.path.abspath(args.cli)}")
    print(f"python: {sys.version.split()[0]}\n")
    failed = 0
    for title, fn in CASES:
        try:
            ok, detail = fn(args.cli)
        except Exception as e:                      # noqa: BLE001 — a crash is a failure
            ok, detail = False, f"harness error: {type(e).__name__}: {e}"
        print(f"{'PASS' if ok else 'FAIL'}  {title}\n      {detail}")
        failed += 0 if ok else 1
    print(f"\n{len(CASES) - failed}/{len(CASES)} cases passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
