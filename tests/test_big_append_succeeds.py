#!/usr/bin/env python3
"""Regression test for t-20261011-76f7: appending to a >1MB channel must WORK.

Mock pattern adapted from scott's tests/test_bigfile_append.py (PR #6), with
one faithfulness upgrade: the >1MB blob-only serving decision is DYNAMIC —
computed from the file's current size on every GET, like the real API — so a
file that shrinks below 1MB (after a rotation) is inlined again.

Cases:
  1. a ~1.05MB channel (1300 x ~810B lines, PUT cap 1MB): `say` must SUCCEED —
     rotate-before-append keeps the hot file small — with zero message loss;
  2. a ~1.2MB channel of only 300 fat lines (under ROTATE_AT=500): the size
     trigger must rotate anyway; append succeeds, zero loss;
  3. a ~2.5MB channel whose archive alone exceeds the PUT cap: the append
     must refuse LOUDLY (non-zero exit, clear error) with the channel intact
     — never a silent drop, never a wipe.

    python3 tests/test_big_append_succeeds.py
    python3 tests/test_big_append_succeeds.py --cli /path/to/main/bin/chatcode   # red

Exit 0 = all cases pass. No real network, no token, no writes outside tmp.
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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CLI = os.path.join(HERE, os.pardir, "bin", "chatcode")
REPO = "dreamer2664/chatcode"
BIG = 1_000_000          # the PUT cap the mock enforces (scott's pin)
CHANNEL = "big"


class State:
    def __init__(self):
        self.files: dict[str, str] = {}
        self.puts: list[tuple[str, int]] = []      # (path, bytes) attempted
        self.max_put_bytes: int | None = None

    def sha(self, path):
        return hashlib.sha1(self.files.get(path, "").encode()).hexdigest()


class Handler(BaseHTTPRequestHandler):
    server_version = "FakeGitHub/1.1"

    def log_message(self, *a):
        pass

    @property
    def st(self):
        return self.server.state                # type: ignore[attr-defined]

    def _send(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _rel(self):
        p = self.path.split("?", 1)[0]
        pre = f"/repos/{REPO}/contents/"
        return p[len(pre):] if p.startswith(pre) else None

    def do_GET(self):                           # noqa: N802
        p = self.path.split("?", 1)[0]
        if p.startswith(f"/repos/{REPO}/git/blobs/"):
            want = p.rsplit("/", 1)[1]
            for f, text in self.st.files.items():
                if self.st.sha(f) == want:
                    return self._send(200, {
                        "content": base64.b64encode(text.encode()).decode("ascii"),
                        "encoding": "base64"})
            return self._send(404, {"message": "no such blob"})
        rel = self._rel()
        if rel is None:
            return self._send(404, {"message": "not contents"})
        text = self.st.files.get(rel)
        if text is None:
            return self._send(404, {"message": "Not Found"})
        n = len(text.encode())
        if n > BIG:                             # dynamic: blob-only above 1MB
            return self._send(200, {
                "name": os.path.basename(rel), "path": rel, "sha": self.st.sha(rel),
                "size": n, "encoding": "none", "content": ""})
        return self._send(200, {
            "name": os.path.basename(rel), "path": rel, "sha": self.st.sha(rel),
            "size": n, "encoding": "base64",
            "content": base64.b64encode(text.encode()).decode("ascii")})

    def do_PUT(self):                           # noqa: N802
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        rel = self._rel()
        text = base64.b64decode(body.get("content", "")).decode()
        self.st.puts.append((rel or "?", len(text.encode())))
        if self.st.max_put_bytes and len(text.encode()) > self.st.max_put_bytes:
            return self._send(422, {"message": "Invalid request. content is too "
                                               "large to be handled by this endpoint."})
        if rel in self.st.files and "sha" in body and body["sha"] != self.st.sha(rel):
            return self._send(409, {"message": "is at x but expected y"})
        self.st.files[rel] = text
        return self._send(200, {"content": {"sha": self.st.sha(rel)}})


def start_mock(state):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    srv.state = state                           # type: ignore[attr-defined]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def msg(i, fat=0):
    return json.dumps({"id": "b%07x" % i, "ts": "2026-10-11T15:00:00Z",
                       "from": "alpha", "type": "say", "to": "*",
                       "text": ("x" * fat) or "msg %d" % i})


def run_say(cli, api):
    env = dict(os.environ,
               CHATCODE_API=api, CHATCODE_TOKEN="fake-token-for-mock",
               CHATCODE_REPO=REPO, CHATCODE_AGENT="cormac", CHATCODE_CHANNEL=CHANNEL,
               NO_COLOR="1")
    return subprocess.run([sys.executable, os.path.abspath(cli), "say",
                           "hello from the big-append test", "--type", "note"],
                          capture_output=True, text=True, env=env, timeout=90)


def channel_ids(state):
    out = set()
    for l in state.files.get(f"bus/{CHANNEL}.jsonl", "").splitlines():
        if l.strip():
            out.add(json.loads(l)["id"])
    return out


def archive_ids(state):
    out = set()
    for p, text in state.files.items():
        if p.startswith(f"bus/archive/{CHANNEL}-") and p.endswith(".jsonl"):
            for l in text.splitlines():
                if l.strip():
                    out.add(json.loads(l)["id"])
    return out


def archive_count(state):
    return sum(1 for p in state.files
               if p.startswith(f"bus/archive/{CHANNEL}-") and p.endswith(".jsonl"))


def case(cli, n_lines, fat, label, expect_refusal=False):
    state = State()
    state.max_put_bytes = BIG
    state.files[f"bus/{CHANNEL}.jsonl"] = "\n".join(msg(i, fat) for i in range(n_lines)) + "\n"
    total = len(state.files[f"bus/{CHANNEL}.jsonl"].encode())
    srv, api = start_mock(state)
    try:
        proc = run_say(cli, api)
        hot = state.files.get(f"bus/{CHANNEL}.jsonl", "")
        hot_n = sum(1 for l in hot.splitlines() if l.strip())
        ids = channel_ids(state) | archive_ids(state)
        orig = {"b%07x" % i for i in range(n_lines)}
        new_msg = "hello from the big-append test" in hot
        lost = orig - ids

        def fmt_lost(s):
            s = sorted(s)
            return "none" if not s else (str(s[:5]) + (f" (+{len(s) - 5} more)" if len(s) > 5 else ""))

        if expect_refusal:
            ok = (proc.returncode != 0 and not lost and not new_msg
                  and hot_n == n_lines)
            detail = (f"rc={proc.returncode}, hot={hot_n}/{n_lines} lines intact, "
                      f"lost={fmt_lost(lost)}, new_msg_rejected={not new_msg}")
            if proc.returncode != 0:
                last = (proc.stderr or proc.stdout).strip().splitlines()[-1][:100]
                detail += f" | refused with: {last}"
        else:
            ok = (proc.returncode == 0 and not lost and new_msg
                  and hot_n <= 130 and archive_count(state) == 1)
            detail = (f"rc={proc.returncode}, hot={hot_n} lines, ids preserved="
                      f"{len(ids)}/{n_lines + 1}, archive_files={archive_count(state)}, "
                      f"new_msg_posted={new_msg}, lost={fmt_lost(lost)}")
        print(f"{'PASS' if ok else 'FAIL'}  {label}  (channel was {total} bytes)")
        print(f"      {detail}")
        return ok
    finally:
        srv.shutdown()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cli", default=DEFAULT_CLI)
    args = ap.parse_args()
    cli = os.path.abspath(args.cli)
    if not os.path.exists(cli):
        print(f"FAIL: cannot find CLI at {cli}")
        return 1
    print("chatcode CLI under test:", cli)
    results = [
        case(cli, 1300, 700,  "~1.05MB channel (1300 lines): append succeeds, zero loss"),
        case(cli, 300, 4000,  "1.2MB channel of 300 fat lines: size-triggered rotation, zero loss"),
        case(cli, 2500, 990,  "2.5MB channel (archive alone over cap): loud refusal, channel intact",
             expect_refusal=True),
    ]
    print()
    print(f"{sum(results)}/{len(results)} cases passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
