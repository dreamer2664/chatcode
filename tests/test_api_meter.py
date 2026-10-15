#!/usr/bin/env python3
"""test_api_meter.py — API-call meter + cheap-reads hint (t-20261014-8794).

The task's acceptance checks, pinned against a local FakeGitHub (same
harness shape as test_branch_reads.py):

  1. `tasks list` in API mode over a 25-task board crosses the floor:
     stderr gets one dim `    api: N request(s)` line with N >= 20, plus
     the `hint: --repo-dir <clone> reads cost 0 API calls` line.
  2. The same command with --repo-dir on a real clone prints NO meter and
     NO hint (local reads cost 0 API calls).
  3. A light command (quota, 1 request) stays below the floor: silent.
  4. JSON mode keeps stdout parseable: `quota --json` prints pure JSON on
     stdout whatever the meter does (the meter writes to stderr).
"""
from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REPO = "o/r"


class FakeGitHub:
    """contents API + /rate_limit, main branch only — enough for the meter."""

    def __init__(self) -> None:
        self.files: dict[str, str] = {}   # path -> text (branch main)

    def sha(self, path: str) -> str:
        import hashlib
        return hashlib.sha1(self.files.get(path, "").encode()).hexdigest()


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

    def do_GET(self):                       # noqa: N802
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path.endswith("/rate_limit"):
            return self._send(200, {"resources": {"core": {"limit": 5000,
                                                           "remaining": 4999}}})
        rel = parsed.path[len(f"/repos/{REPO}/contents/"):].strip("/")
        text = self.state.files.get(rel)
        if text is not None:
            return self._send(200, {
                "name": rel.split("/")[-1], "path": rel, "sha": self.state.sha(rel),
                "size": len(text), "type": "file", "encoding": "base64",
                "content": base64.b64encode(text.encode()).decode()})
        head = rel + "/"
        children = sorted(p for p in self.state.files if p.startswith(head))
        if children:
            return self._send(200, [{
                "name": c[len(head):], "path": c, "sha": self.state.sha(c),
                "size": len(self.state.files[c]), "type": "file",
            } for c in children])
        return self._send(404, {"message": "Not Found"})


def start_mock(state: FakeGitHub):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    srv.state = state                        # type: ignore[attr-defined]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def run(cli: str, base: str, home: str, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, CHATCODE_API=base, CHATCODE_TOKEN="test-token",
               CHATCODE_REPO=REPO, CHATCODE_AGENT="test-agent",
               CHATCODE_BRANCH="main", HOME=home)
    return subprocess.run([sys.executable, os.path.abspath(cli), *args],
                          capture_output=True, text=True, env=env, timeout=120)


def task_json(i: int) -> str:
    return json.dumps({
        "id": f"t-20261015-{i:04x}", "title": f"fake task {i}", "desc": "x",
        "status": "open", "owner": None, "created_by": "test", "priority": 3,
        "created_ts": "2026-10-15T00:00:00Z", "updated_ts": "2026-10-15T00:00:00Z",
        "tags": [], "deps": [], "parent": None, "branch": None, "pr": None,
        "history": []})


def meter_of(stderr: str) -> int:
    m = re.search(r"api: (\d+) request\(s\)", stderr)
    return int(m.group(1)) if m else 0


def case_heavy_api_run_meters_and_hints(cli: str) -> tuple[bool, str]:
    state = FakeGitHub()
    for i in range(25):
        state.files[f"board/tasks/t-20261015-{i:04x}.json"] = task_json(i)
    srv, base = start_mock(state)
    home = tempfile.mkdtemp(prefix="chatcode-meter-home-")
    try:
        r = run(cli, base, home, "tasks", "list")
    finally:
        srv.shutdown()
    n = meter_of(r.stderr)
    ok = (r.returncode == 0 and n >= 20
          and "hint: --repo-dir <clone> reads cost 0 API calls" in r.stderr)
    detail = f"rc={r.returncode} api={n} hint={'yes' if 'hint:' in r.stderr else 'no'}"
    if not ok:
        detail += "\n--- stderr tail ---\n" + "\n".join(r.stderr.splitlines()[-3:])
    return ok, detail


def case_local_mode_stays_silent(cli: str) -> tuple[bool, str]:
    state = FakeGitHub()
    srv, base = start_mock(state)
    home = tempfile.mkdtemp(prefix="chatcode-meter-home-")
    clone = tempfile.mkdtemp(prefix="chatcode-meter-clone-")
    os.makedirs(os.path.join(clone, "bus"), exist_ok=True)
    os.makedirs(os.path.join(clone, "board/tasks"), exist_ok=True)
    open(os.path.join(clone, "bus/general.jsonl"), "w").close()
    for i in range(3):
        with open(os.path.join(clone, f"board/tasks/t-20261015-{i:04x}.json"),
                  "w") as f:
                    f.write(task_json(i))
    try:
        r = run(cli, base, home, "--repo-dir", clone, "tasks", "list")
    finally:
        srv.shutdown()
    ok = (r.returncode == 0 and "api:" not in r.stderr
          and "hint:" not in r.stderr)
    detail = f"rc={r.returncode} meter={'yes' if 'api:' in r.stderr else 'no'}"
    if not ok:
        detail += "\n--- stderr tail ---\n" + "\n".join(r.stderr.splitlines()[-3:])
    return ok, detail


def case_light_run_below_floor_stays_silent(cli: str) -> tuple[bool, str]:
    state = FakeGitHub()
    srv, base = start_mock(state)
    home = tempfile.mkdtemp(prefix="chatcode-meter-home-")
    try:
        r = run(cli, base, home, "quota")
    finally:
        srv.shutdown()
    ok = r.returncode == 0 and "api:" not in r.stderr
    detail = f"rc={r.returncode} meter={'yes' if 'api:' in r.stderr else 'no'}"
    if not ok:
        detail += "\n--- stderr tail ---\n" + "\n".join(r.stderr.splitlines()[-3:])
    return ok, detail


def case_json_stdout_stays_parseable(cli: str) -> tuple[bool, str]:
    state = FakeGitHub()
    srv, base = start_mock(state)
    home = tempfile.mkdtemp(prefix="chatcode-meter-home-")
    try:
        r = run(cli, base, home, "quota", "--json")
    finally:
        srv.shutdown()
    try:
        json.loads(r.stdout)
        clean = True
    except Exception:
        clean = False
    ok = r.returncode == 0 and clean
    return ok, f"rc={r.returncode} stdout_json={clean}"


CASES = [
    ("heavy `tasks list` in API mode meters + hints", case_heavy_api_run_meters_and_hints),
    ("`tasks list --repo-dir` prints no meter, no hint", case_local_mode_stays_silent),
    ("light command below the floor stays silent", case_light_run_below_floor_stays_silent),
    ("JSON stdout stays parseable", case_json_stdout_stays_parseable),
]


def main() -> int:
    cli = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "bin", "chatcode")
    failed = 0
    for name, fn in CASES:
        ok, detail = fn(cli)
        print(("PASS " if ok else "FAIL "), name, " ", detail, sep="")
        failed += 0 if ok else 1
    print(f"{len(CASES) - failed}/{len(CASES)} cases passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
