#!/usr/bin/env python3
"""Legacy claims, the room hint, and the lead's release (2026-10-14).

Three holes found live on the board the night two new hands arrived and a
veteran's branch went quiet:

  1. A `claimed` card from the pre-lease era carries no lease map, so
     `tasks sweep` can never expire it — it holds work forever and the
     room reads as "everything is taken". Sweep must LIST such claims
     (a manager decides) but never auto-reclaim them — the holder may
     be alive.
  2. Plain `tasks list` prints the whole museum (done, dropped, other
     people's reviews) and does not say where the room is. It now appends
     the open count and the exact command.
  3. A lead must be able to clear a dead legacy claim without a script:
     `tasks release <id> --force --note "…"` (and a non-owner without
     --force must be refused).

Cases (throwaway --local repo, HOME redirected — same harness as
tests/test_shift_system.py):

  1. legacy claim (lease stripped) is listed by sweep but survives --apply
  2. sweep --apply still reclaims a genuinely expired lease (no regression)
  3. unfiltered `tasks list` shows the room hint; `--status open` does not
  4. non-owner release without --force is refused; with --force it works
     and the release note lands in the task history

    python3 tests/test_legacy_claims.py
"""
from __future__ import annotations

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
    def __init__(self, cli_path: str) -> None:
        self.cli = os.path.abspath(cli_path)
        self.dir = tempfile.mkdtemp(prefix="chatcode-legacy-test-")
        self.home = tempfile.mkdtemp(prefix="chatcode-legacy-home-")
        for name in ("alice", "bob"):
            self.run(name, "init", "--quiet", "--model", "mock")

    def run(self, agent: str, *args: str):
        e = dict(os.environ, HOME=self.home, CHATCODE_AGENT=agent)
        return subprocess.run(
            [sys.executable, self.cli, "--local", self.dir, "--agent", agent, *args],
            capture_output=True, text=True, env=e, timeout=60)

    def task(self, agent: str, title: str = "a task") -> str:
        out = self.run(agent, "tasks", "new", title).stdout
        m = TID_RE.search(out)
        assert m, f"no task id in output: {out!r}"
        return m.group(1)

    def path(self, tid: str) -> str:
        return os.path.join(self.dir, "board", "tasks", f"{tid}.json")

    def state(self, tid: str) -> dict:
        return json.load(open(self.path(tid)))


def _strip_lease(tid: str, repo: Repo) -> None:
    """Simulate a pre-lease-era claim: owned, claimed, no lease map."""
    t = repo.state(tid)
    t["lease"] = None
    json.dump(t, open(repo.path(tid), "w"), indent=2)


def case_legacy_listed_not_reclaimed(cli: str):
    r = Repo(cli)
    tid = r.task("alice")
    r.run("alice", "tasks", "claim", tid)
    _strip_lease(tid, r)
    listed = r.run("bob", "tasks", "sweep")
    ok_list = tid in listed.stdout and "no lease" in listed.stdout
    applied = r.run("bob", "tasks", "sweep", "--apply")
    st = r.state(tid)
    ok_keep = st.get("owner") == "alice" and st.get("status") == "claimed"
    return (ok_list and ok_keep), (
        f"listed_ok={ok_list} kept_after_apply={ok_keep} "
        f"(sweep said: {listed.stdout.strip().splitlines()[0][:80]!r})")


def case_expired_still_reclaimed(cli: str):
    r = Repo(cli)
    tid = r.task("alice")
    r.run("alice", "tasks", "claim", tid)
    t = r.state(tid)
    t["lease"]["expires"] = "2000-01-01T00:00:00Z"
    json.dump(t, open(r.path(tid), "w"), indent=2)
    r.run("bob", "tasks", "sweep", "--apply")
    st = r.state(tid)
    return (st.get("owner") is None and st.get("status") == "open"), (
        f"owner={st.get('owner')} status={st.get('status')}")


def case_room_hint(cli: str):
    r = Repo(cli)
    r.task("alice", "open one")
    r.task("alice", "open two")
    unfiltered = r.run("bob", "tasks", "list")
    filtered = r.run("bob", "tasks", "list", "--status", "open")
    ok_hint = "The room:" in unfiltered.stdout and "--status open" in unfiltered.stdout
    ok_quiet = "The room:" not in filtered.stdout
    both = "open one" in filtered.stdout and "open two" in filtered.stdout
    return (ok_hint and ok_quiet and both), (
        f"hint={ok_hint} filtered_clean={ok_quiet} filtered_has_jobs={both}")


def case_force_release(cli: str):
    r = Repo(cli)
    tid = r.task("alice")
    r.run("alice", "tasks", "claim", tid)
    refused = r.run("bob", "tasks", "release", tid)
    ok_refused = refused.returncode != 0 and "lease" in (refused.stdout + refused.stderr)
    forced = r.run("bob", "tasks", "release", tid, "--force",
                   "--note", "manager call: holder silent, branch preserved")
    st = r.state(tid)
    ok_released = st.get("owner") is None and st.get("status") == "open"
    note_seen = any("holder silent" in (h.get("note") or "")
                    for h in st.get("history", []))
    return (ok_refused and ok_released and note_seen), (
        f"refused_without_force={ok_refused} released={ok_released} "
        f"note_preserved={note_seen}")


CASES = [
    ("legacy claim is listed by sweep but survives --apply",
     case_legacy_listed_not_reclaimed),
    ("an expired lease is still reclaimed by sweep --apply",
     case_expired_still_reclaimed),
    ("unfiltered tasks list points at the room; a filtered list stays quiet",
     case_room_hint),
    ("release refused without --force; forced release keeps the note",
     case_force_release),
]


def main() -> int:
    cli = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CLI
    bad = 0
    for name, fn in CASES:
        ok, detail = fn(cli)
        print(f"{'ok  ' if ok else 'FAIL'}  {name}\n        {detail}")
        bad += 0 if ok else 1
    print()
    if bad:
        print(f"FAIL: {bad} case(s) failed")
        return 1
    print(f"all {len(CASES)} cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
