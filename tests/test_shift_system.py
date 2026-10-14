#!/usr/bin/env python3
"""Shift-system regression test (t-20261014-e977): leases, the review
queue, and ntfy pings — the pieces that let a brand-new agent integrate
mid-stream and survive another agent dying mid-job.

Cases (all against a throwaway --local repo, HOME redirected):
  1. claiming a task stamps a lease with a future expiry
  2. heartbeat renews the lease and stores the resume checkpoint
  3. a foreign agent cannot heartbeat someone else's lease
  4. sweep lists an expired lease without mutating, then --apply
     returns the task to the open pool (owner and lease cleared)
  5. the review queue lists review work, `next` skips your own tasks,
     and an owner cannot grab their own review
  6. ping posts to a local ntfy stand-in and --verify reads its own
     message id back (CHATCODE_NTFY_BASE override)

    python3 tests/test_shift_system.py
    python3 tests/test_shift_system.py --cli /path/to/bin/chatcode

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
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CLI = os.path.join(HERE, os.pardir, "bin", "chatcode")
TID_RE = re.compile(r"(t-\d{8}-[0-9a-f]{4})")


class Repo:
    def __init__(self, cli_path: str) -> None:
        self.cli = os.path.abspath(cli_path)
        self.dir = tempfile.mkdtemp(prefix="chatcode-shift-test-")
        self.home = tempfile.mkdtemp(prefix="chatcode-shift-home-")
        for name, role in (("alice", "worker"), ("bob", "worker")):
            self.run(name, "init", "--quiet", "--model", "mock", "--role", role)

    def run(self, agent: str, *args: str, env: dict | None = None):
        e = dict(os.environ, HOME=self.home, CHATCODE_AGENT=agent)
        if env:
            e.update(env)
        return subprocess.run(
            [sys.executable, self.cli, "--local", self.dir,
             "--agent", agent, *args],
            capture_output=True, text=True, env=e, timeout=60)

    def task(self, agent: str, title: str = "a task") -> str:
        out = self.run(agent, "tasks", "new", title).stdout
        m = TID_RE.search(out)
        assert m, f"no task id in output: {out!r}"
        return m.group(1)

    def state(self, agent: str, tid: str) -> dict:
        out = self.run(agent, "tasks", "show", tid).stdout
        return json.loads(out[out.index("{"):])

    def expire_lease(self, tid: str) -> None:
        path = os.path.join(self.dir, "board", "tasks", f"{tid}.json")
        t = json.load(open(path))
        t["lease"]["expires"] = "2000-01-01T00:00:00Z"
        json.dump(t, open(path, "w"), indent=2)


def case_claim_stamps_lease(cli: str):
    r = Repo(cli)
    tid = r.task("alice")
    r.run("alice", "tasks", "claim", tid)
    st = r.state("alice", tid)
    lease = st.get("lease") or {}
    ok = lease.get("agent") == "alice" and lease.get("expires", "") > st["created_ts"]
    return ok, f"lease={lease}"


def case_heartbeat_renews_with_checkpoint(cli: str):
    r = Repo(cli)
    tid = r.task("alice")
    r.run("alice", "tasks", "claim", tid, "--hours", "0.01")
    before = r.state("alice", tid)["lease"]["expires"]
    r.run("alice", "tasks", "heartbeat", tid, "--note", "step 2 of 5 done",
          "--hours", "2")
    st = r.state("alice", tid)
    ok = (st["lease"]["expires"] > before
          and st["lease"]["checkpoint"] == "step 2 of 5 done")
    return ok, f"before={before} after={st['lease']}"


def case_foreign_heartbeat_refused(cli: str):
    r = Repo(cli)
    tid = r.task("alice")
    r.run("alice", "tasks", "claim", tid)
    proc = r.run("bob", "tasks", "heartbeat", tid, "--note", "not mine")
    ok = proc.returncode != 0
    return ok, f"rc={proc.returncode}"


def case_sweep_reclaims_expired(cli: str):
    r = Repo(cli)
    tid = r.task("alice")
    r.run("alice", "tasks", "claim", tid)
    r.expire_lease(tid)
    listing = r.run("bob", "tasks", "sweep")
    st = r.state("bob", tid)
    listed_only = (tid in listing.stdout and st["owner"] == "alice"
                   and st["status"] == "claimed")
    applied = r.run("bob", "tasks", "sweep", "--apply")
    st = r.state("bob", tid)
    ok = (listed_only and applied.returncode == 0 and st["owner"] is None
          and st["status"] == "open" and st.get("lease") is None)
    return ok, f"listed_only={listed_only} after={st['status']}/{st['owner']}"


def case_review_queue(cli: str):
    r = Repo(cli)
    tid = r.task("alice")
    r.run("alice", "tasks", "claim", tid)
    r.run("alice", "tasks", "update", tid, "--status", "review")
    queue = r.run("bob", "review", "list")
    nxt = r.run("bob", "review", "next")
    own_grab = r.run("alice", "review", "grab", tid)
    grab = r.run("bob", "review", "grab", tid)
    ok = (tid in queue.stdout and tid in nxt.stdout
          and own_grab.returncode != 0 and grab.returncode == 0)
    return ok, (f"queue/next rc ok, own_grab rc={own_grab.returncode}, "
                f"grab rc={grab.returncode}")


class _NtfyStub(BaseHTTPRequestHandler):
    messages = []
    paths = []

    def do_POST(self):
        _NtfyStub.paths.append(self.path)
        body = self.rfile.read(int(self.headers["Content-Length"])).decode()
        msg = {"id": "testid123", "event": "message", "topic": "chatcode",
               "message": body}
        _NtfyStub.messages.append(msg)
        data = json.dumps(msg).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        data = "".join(json.dumps(m) + "\n" for m in _NtfyStub.messages)
        raw = data.encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *a):
        pass


def case_ping_posts_and_verifies(cli: str):
    _NtfyStub.messages = []
    srv = HTTPServer(("127.0.0.1", 0), _NtfyStub)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        r = Repo(cli)
        proc = r.run("alice", "ping", "connected successfully.", "--verify",
                     env={"CHATCODE_NTFY_BASE":
                          f"http://127.0.0.1:{srv.server_port}"})
        entry = r.run("alice", "ping", "entry tests passed", "--topic",
                      "entries",
                      env={"CHATCODE_NTFY_BASE":
                           f"http://127.0.0.1:{srv.server_port}"})
        pulse = r.run("alice", "ping", "still active", "--topic", "heartbeat",
                      env={"CHATCODE_NTFY_BASE":
                           f"http://127.0.0.1:{srv.server_port}"})
        ok = (proc.returncode == 0 and "testid123" in proc.stdout
              and _NtfyStub.messages
              and _NtfyStub.messages[0]["message"]
              == "alice - connected successfully."
              and entry.returncode == 0 and pulse.returncode == 0
              and _NtfyStub.paths == ["/groupchatcode", "/newentriescode",
                                      "/heartbeatcode"])
        return ok, f"rc={proc.returncode} paths={_NtfyStub.paths}"
    finally:
        srv.shutdown()


CASES = [
    case_claim_stamps_lease,
    case_heartbeat_renews_with_checkpoint,
    case_foreign_heartbeat_refused,
    case_sweep_reclaims_expired,
    case_review_queue,
    case_ping_posts_and_verifies,
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cli", default=DEFAULT_CLI)
    args = ap.parse_args()
    bad = 0
    for fn in CASES:
        try:
            ok, detail = fn(args.cli)
        except Exception as e:                            # noqa: BLE001
            ok, detail = False, f"exception: {type(e).__name__}: {e}"
        print(f"{'PASS' if ok else 'FAIL'}  {fn.__name__}  {detail}")
        bad += not ok
    print(f"{len(CASES) - bad}/{len(CASES)} cases passed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
