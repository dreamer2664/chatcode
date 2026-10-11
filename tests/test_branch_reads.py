#!/usr/bin/env python3
"""Regression test: reads must honour the branch the CLI writes to.

`Repo.contents()` never sent `?ref=`, so every read landed on the API's default
branch while every write went to `self.branch`. On a non-default branch the
first append therefore worked and the second died: the read saw no file, the
PUT carried no sha, GitHub answered 422, and the retry loop gave up with
"could not append … too many agents writing at once". `list_dir()` had the same
blindness, so board/bus listings came from the wrong branch too.

The mock below stores files *per branch* the way GitHub does, so a branch-blind
read is visibly wrong rather than harmlessly sloppy.

    python3 tests/test_branch_reads.py
    python3 tests/test_branch_reads.py --cli /path/to/main/bin/chatcode   # red

Exit 0 = all cases pass. No network, no token, no writes outside a temp dir.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CLI = os.path.join(HERE, os.pardir, "bin", "chatcode")
REPO = "dreamer2664/chatcode"
BRANCH = "agent/test-agent/t-20261011-0001"


class FakeGitHub:
    """contents API with per-branch storage, like the real one."""

    def __init__(self) -> None:
        self.files: dict[tuple[str, str], str] = {}   # (branch, path) -> text
        self.log: list[tuple[str, str, str]] = []     # (verb, branch, path)
        self._lock = threading.Lock()

    def sha(self, branch: str, path: str) -> str:
        return hashlib.sha1(self.files.get((branch, path), "").encode()).hexdigest()

    def branch_of(self, query: dict, body: dict | None = None) -> str:
        if body and body.get("branch"):
            return body["branch"]
        return (query.get("ref") or ["main"])[0]


class Handler(BaseHTTPRequestHandler):
    server_version = "FakeGitHub/1.0"

    def log_message(self, *a):
        pass

    @property
    def state(self) -> FakeGitHub:
        return self.server.state           # type: ignore[attr-defined]

    def _send(self, code: int, payload) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _split(self):
        parsed = urllib.parse.urlsplit(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        path = parsed.path
        prefix = f"/repos/{REPO}/contents/"
        rel = path[len(prefix):].strip("/") if path.startswith(prefix) else ""
        return rel, query

    def do_GET(self):                       # noqa: N802
        rel, query = self._split()
        if self.path.startswith(f"/repos/{REPO}/rate_limit"):
            return self._send(200, {"resources": {"core": {"limit": 5000, "remaining": 4999}}})
        branch = self.state.branch_of(query)
        self.state.log.append(("GET", branch, rel))
        text = self.state.files.get((branch, rel))
        if text is not None:
            return self._send(200, {
                "name": rel.split("/")[-1], "path": rel, "sha": self.state.sha(branch, rel),
                "size": len(text), "type": "file", "encoding": "base64",
                "content": base64.b64encode(text.encode()).decode()})
        # directory listing for this branch
        head = rel + "/"
        children = sorted(p for (b, p) in self.state.files if b == branch and p.startswith(head))
        if children:
            return self._send(200, [{
                "name": c[len(head):], "path": c, "sha": self.state.sha(branch, c),
                "size": len(self.state.files[(branch, c)]), "type": "file",
            } for c in children])
        return self._send(404, {"message": "Not Found"})

    def do_PUT(self):                       # noqa: N802
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        rel, query = self._split()
        branch = self.state.branch_of(query, body)
        text = base64.b64decode(body.get("content", "")).decode()
        self.state.log.append(("PUT", branch, rel))
        exists = (branch, rel) in self.state.files
        sha = body.get("sha")
        if exists and sha is None:           # GitHub: needs a sha to update
            return self._send(422, {"message": "\"sha\" wasn't supplied."})
        if exists and sha != self.state.sha(branch, rel):
            return self._send(409, {"message": "is at x but expected y"})
        self.state.files[(branch, rel)] = text
        return self._send(200, {"content": {"sha": self.state.sha(branch, rel)}})


def start_mock(state: FakeGitHub):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    srv.state = state                            # type: ignore[attr-defined]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def run(cli: str, base: str, home: str, branch: str, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, CHATCODE_API=base, CHATCODE_TOKEN="test-token",
               CHATCODE_REPO=REPO, CHATCODE_AGENT="test-agent",
               CHATCODE_BRANCH=branch, HOME=home)
    return subprocess.run([sys.executable, os.path.abspath(cli), *args],
                          capture_output=True, text=True, env=env, timeout=120)


def _lines(state: FakeGitHub, branch: str, path: str) -> list[str]:
    return state.files.get((branch, path), "").splitlines()


# --- cases ----------------------------------------------------------------

def case_two_appends_on_a_branch(cli: str) -> tuple[bool, str]:
    """The acceptance case: two consecutive appends on a non-default branch."""
    state = FakeGitHub()
    srv, base = start_mock(state)
    home = tempfile.mkdtemp(prefix="chatcode-branch-home-")
    try:
        first = run(cli, base, home, BRANCH, "say", "first message", "-c", "general")
        second = run(cli, base, home, BRANCH, "say", "second message", "-c", "general")
    finally:
        srv.shutdown()
    got = _lines(state, BRANCH, "bus/general.jsonl")
    ok = (first.returncode == 0 and second.returncode == 0 and len(got) == 2)
    detail = (f"first_rc={first.returncode} second_rc={second.returncode} "
              f"messages_on_branch={len(got)}")
    if not ok:
        err = (second.stderr or first.stderr).strip().splitlines()
        detail += "\n--- stderr ---\n" + "\n".join(err[-3:])
    return ok, detail


def case_writes_stay_on_their_branch(cli: str) -> tuple[bool, str]:
    """Nothing may leak onto another branch: reads and writes both pin theirs."""
    state = FakeGitHub()
    srv, base = start_mock(state)
    home = tempfile.mkdtemp(prefix="chatcode-branch-home-")
    try:
        run(cli, base, home, BRANCH, "say", "only on the branch", "-c", "general")
    finally:
        srv.shutdown()
    on_branch = len(_lines(state, BRANCH, "bus/general.jsonl"))
    on_main = len(_lines(state, "main", "bus/general.jsonl"))
    reads = {b for verb, b, p in state.log if verb == "GET" and p.startswith("bus/")}
    ok = on_branch == 1 and on_main == 0 and reads == {BRANCH}
    return ok, f"branch_lines={on_branch} main_lines={on_main} read_branches={sorted(reads)}"


def case_default_branch_still_works(cli: str) -> tuple[bool, str]:
    """Control: main is unaffected — two appends, both persisted."""
    state = FakeGitHub()
    srv, base = start_mock(state)
    home = tempfile.mkdtemp(prefix="chatcode-branch-home-")
    try:
        a = run(cli, base, home, "main", "say", "one", "-c", "general")
        b = run(cli, base, home, "main", "say", "two", "-c", "general")
    finally:
        srv.shutdown()
    ok = a.returncode == 0 and b.returncode == 0 and len(_lines(state, "main", "bus/general.jsonl")) == 2
    return ok, f"rc={a.returncode},{b.returncode} lines={len(_lines(state, 'main', 'bus/general.jsonl'))}"


CASES = [
    ("two consecutive appends on a non-default branch", case_two_appends_on_a_branch),
    ("reads and writes stay on their own branch", case_writes_stay_on_their_branch),
    ("control: the default branch still works", case_default_branch_still_works),
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
