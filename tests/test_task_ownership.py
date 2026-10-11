#!/usr/bin/env python3
"""Ownership regression test: a plain worker must not be able to move a task
it does not own.

Three ways to move a foreign task were open on main (evidence: review
#a5af03fe findings 1-2, reproduced in #e5ef06a8):

  * `tasks block <id>`   — the :1342 tuple listed only done/drop/update/status,
                           so block/unblock skipped the ownership guard entirely
  * `tasks unblock <id>` — same gap, and it rewrites status to `claimed`
                           whatever the real owner was waiting on
  * `tasks update <id> --status claimed` on a task in review — the takeover
                           branch printed a note and allowed it, although
                           PROTOCOL section 5 reserves review->claimed for a
                           reviewer or the lead

and four things that must keep working: the owner moving their own task, a
roster reviewer acting on someone else's, the lead doing the same, and the
documented `--force` escape hatch.

Every case runs against a throwaway `--local` repo with HOME redirected to a
temp dir, so no shared surface and no real config is touched.

    python3 tests/test_task_ownership.py
    python3 tests/test_task_ownership.py --cli /path/to/main/bin/chatcode   # red

Exit 0 = all cases pass.
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
TID_RE = re.compile(r"(t-\d{8}-[0-9a-f]{4})")


class Repo:
    """A throwaway --local blackboard, driven through the CLI under test."""

    def __init__(self, cli_path: str) -> None:
        self.cli = os.path.abspath(cli_path)
        self.dir = tempfile.mkdtemp(prefix="chatcode-own-test-")
        self.home = tempfile.mkdtemp(prefix="chatcode-own-home-")
        for name, role in (("alice", "worker"), ("bob", "worker"),
                           ("rev", "reviewer"), ("boss", "lead")):
            self.run(name, "init", "--quiet", "--model", "mock", "--role", role)

    def run(self, agent: str, *args: str) -> subprocess.CompletedProcess:
        env = dict(os.environ, HOME=self.home, CHATCODE_AGENT=agent)
        return subprocess.run(
            [sys.executable, self.cli, "--local", self.dir, "--agent", agent, *args],
            capture_output=True, text=True, env=env, timeout=60)

    def task(self, agent: str, title: str = "a task") -> str:
        out = self.run(agent, "tasks", "new", title).stdout
        m = TID_RE.search(out)
        assert m, f"no task id in output: {out!r}"
        return m.group(1)

    def state(self, agent: str, tid: str) -> dict:
        out = self.run(agent, "tasks", "show", tid).stdout
        return json.loads(out[out.index("{"):])


def _refused(proc: subprocess.CompletedProcess, who: str) -> bool:
    return proc.returncode != 0 and who in (proc.stdout + proc.stderr)


# --- cases ----------------------------------------------------------------

def case_worker_cannot_block_foreign(cli: str) -> tuple[bool, str]:
    r = Repo(cli)
    tid = r.task("alice")
    r.run("alice", "tasks", "claim", tid)
    proc = r.run("bob", "tasks", "block", tid, "--note", "not mine to block")
    st = r.state("bob", tid)
    ok = _refused(proc, "alice") and st["status"] == "claimed" and st["owner"] == "alice"
    return ok, f"rc={proc.returncode} status={st['status']} owner={st['owner']}"


def case_worker_cannot_unblock_foreign(cli: str) -> tuple[bool, str]:
    r = Repo(cli)
    tid = r.task("alice")
    r.run("alice", "tasks", "claim", tid)
    r.run("alice", "tasks", "block", tid, "--note", "waiting on a dependency")
    proc = r.run("bob", "tasks", "unblock", tid)
    st = r.state("bob", tid)
    ok = _refused(proc, "alice") and st["status"] == "blocked"
    return ok, f"rc={proc.returncode} status={st['status']} (must stay blocked)"


def case_worker_cannot_reopen_foreign_review(cli: str) -> tuple[bool, str]:
    r = Repo(cli)
    tid = r.task("alice")
    r.run("alice", "tasks", "claim", tid)
    r.run("alice", "tasks", "update", tid, "--status", "review")
    proc = r.run("bob", "tasks", "update", tid, "--status", "claimed")
    st = r.state("bob", tid)
    ok = _refused(proc, "alice") and st["status"] == "review"
    return ok, f"rc={proc.returncode} status={st['status']} (must stay review)"


def case_owner_still_moves_own_task(cli: str) -> tuple[bool, str]:
    r = Repo(cli)
    tid = r.task("alice")
    r.run("alice", "tasks", "claim", tid)
    b = r.run("alice", "tasks", "block", tid, "--note", "mine to block")
    after_block = r.state("alice", tid)["status"]
    u = r.run("alice", "tasks", "unblock", tid)
    after_unblock = r.state("alice", tid)["status"]
    ok = (b.returncode == 0 and after_block == "blocked"
          and u.returncode == 0 and after_unblock == "claimed")
    return ok, f"block rc={b.returncode}→{after_block}, unblock rc={u.returncode}→{after_unblock}"


def case_reviewer_may_reopen_foreign_review(cli: str) -> tuple[bool, str]:
    r = Repo(cli)
    tid = r.task("alice")
    r.run("alice", "tasks", "claim", tid)
    r.run("alice", "tasks", "update", tid, "--status", "review")
    proc = r.run("rev", "tasks", "update", tid, "--status", "claimed",
                 "--note", "reopening for rework")
    st = r.state("rev", tid)
    ok = proc.returncode == 0 and st["status"] == "claimed"
    return ok, f"rc={proc.returncode} status={st['status']} (reviewer authority)"


def case_lead_may_act_on_foreign_task(cli: str) -> tuple[bool, str]:
    r = Repo(cli)
    tid = r.task("alice")
    r.run("alice", "tasks", "claim", tid)
    proc = r.run("boss", "tasks", "block", tid, "--note", "lead decision")
    st = r.state("boss", tid)
    ok = proc.returncode == 0 and st["status"] == "blocked"
    return ok, f"rc={proc.returncode} status={st['status']} (lead authority)"


def case_force_still_overrides(cli: str) -> tuple[bool, str]:
    r = Repo(cli)
    tid = r.task("alice")
    r.run("alice", "tasks", "claim", tid)
    proc = r.run("bob", "tasks", "block", tid, "--force", "--note", "explicit override")
    st = r.state("bob", tid)
    ok = proc.returncode == 0 and st["status"] == "blocked"
    return ok, f"rc={proc.returncode} status={st['status']} (escape hatch intact)"


def case_control_plain_status_change_still_refused(cli: str) -> tuple[bool, str]:
    """The pre-existing guard must not regress while widening to block/unblock."""
    r = Repo(cli)
    tid = r.task("alice")
    r.run("alice", "tasks", "claim", tid)
    proc = r.run("bob", "tasks", "update", tid, "--status", "done")
    st = r.state("bob", tid)
    ok = _refused(proc, "alice") and st["status"] == "claimed"
    return ok, f"rc={proc.returncode} status={st['status']}"


CASES = [
    ("worker cannot block a foreign task", case_worker_cannot_block_foreign),
    ("worker cannot unblock a foreign task", case_worker_cannot_unblock_foreign),
    ("worker cannot reopen a foreign review task", case_worker_cannot_reopen_foreign_review),
    ("owner still moves their own task", case_owner_still_moves_own_task),
    ("roster reviewer may reopen a foreign review task", case_reviewer_may_reopen_foreign_review),
    ("lead may act on a foreign task", case_lead_may_act_on_foreign_task),
    ("--force still overrides", case_force_still_overrides),
    ("control: plain status change on a foreign task still refused",
     case_control_plain_status_change_still_refused),
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
        except Exception as e:                  # noqa: BLE001 — a crash is a failure
            ok, detail = False, f"harness error: {type(e).__name__}: {e}"
        print(f"{'PASS' if ok else 'FAIL'}  {title}\n      {detail}")
        failed += 0 if ok else 1
    print(f"\n{len(CASES) - failed}/{len(CASES)} cases passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
