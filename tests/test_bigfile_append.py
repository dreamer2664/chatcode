#!/usr/bin/env python3
"""Regression test: appending to a channel larger than 1MB must not wipe it.

The GitHub contents API inlines a file's body only up to 1MB. Above that it
answers `encoding: "none"` with `content: ""` and a sha, and the body has to be
read from `/git/blobs/{sha}`. `append_lines` treated that empty string as the
file's content, so it built `"" + the new message`, PUT it with a still-valid
sha, and replaced the whole channel. It happened for real: commit 5316ac2 is
1 insertion and 1150 deletions.

The mock below reproduces that contract faithfully — a "big" path is served
blob-only, everything else is inlined — so the test is honest about the API
behaviour rather than about an easy stub.

    python3 tests/test_bigfile_append.py
    python3 tests/test_bigfile_append.py --cli /path/to/main/bin/chatcode   # red

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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CLI = os.path.join(HERE, os.pardir, "bin", "chatcode")
REPO = "dreamer2664/chatcode"
BIG = 1_000_000


class FakeGitHub:
    """contents API with GitHub's >1MB behaviour, plus a blob endpoint."""

    def __init__(self) -> None:
        self.files: dict[str, str] = {}
        self.big: set[str] = set()          # served blob-only, like a >1MB file
        self.log: list[tuple[str, str]] = []
        self.max_put_bytes: int | None = None   # contents API caps PUTs at 1MB
        self._lock = threading.Lock()

    def sha(self, path: str) -> str:
        return hashlib.sha1(self.files.get(path, "").encode()).hexdigest()

    def path_for_sha(self, sha: str) -> str | None:
        for p in self.files:
            if self.sha(p) == sha:
                return p
        return None


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

    def _rel(self) -> str:
        prefix = f"/repos/{REPO}/contents/"
        p = self.path.split("?", 1)[0]
        return p[len(prefix):].strip("/") if p.startswith(prefix) else ""

    def do_GET(self):                       # noqa: N802
        path = self.path.split("?", 1)[0]
        if path.startswith(f"/repos/{REPO}/git/blobs/"):
            sha = path.rsplit("/", 1)[-1]
            rel = self.state.path_for_sha(sha)
            self.state.log.append(("GET-blob", sha[:8]))
            if rel is None:
                return self._send(404, {"message": "Not Found"})
            text = self.state.files[rel]
            return self._send(200, {
                "sha": sha, "size": len(text), "encoding": "base64",
                "content": base64.b64encode(text.encode()).decode()})

        rel = self._rel()
        if rel in self.state.files:
            text = self.state.files[rel]
            self.state.log.append(("GET", rel))
            if rel in self.state.big:       # exactly what GitHub answers >1MB
                return self._send(200, {
                    "name": rel.split("/")[-1], "path": rel, "sha": self.state.sha(rel),
                    "size": len(text), "type": "file", "encoding": "none", "content": ""})
            return self._send(200, {
                "name": rel.split("/")[-1], "path": rel, "sha": self.state.sha(rel),
                "size": len(text), "type": "file", "encoding": "base64",
                "content": base64.b64encode(text.encode()).decode()})
        self.state.log.append(("GET-404", rel))
        return self._send(404, {"message": "Not Found"})

    def do_PUT(self):                       # noqa: N802
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        rel = self._rel()
        text = base64.b64decode(body.get("content", "")).decode()
        had_sha = "sha" in body
        self.state.log.append(("PUT", rel))
        if (self.state.max_put_bytes
                and len(text.encode()) > self.state.max_put_bytes):
            # what the real endpoint answers above its size cap; the exact
            # wording is not guaranteed, the refusal is
            return self._send(422, {"message": "Invalid request. content is too "
                                               "large to be handled by this endpoint."})
        if rel in self.state.files and had_sha and body["sha"] != self.state.sha(rel):
            return self._send(409, {"message": "is at x but expected y"})
        self.state.files[rel] = text
        return self._send(200, {"content": {"sha": self.state.sha(rel)}})


def start_mock(state: FakeGitHub):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    srv.state = state                            # type: ignore[attr-defined]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def big_channel(n: int = 1300) -> str:
    """A JSONL channel comfortably over 1MB, in the real message shape."""
    lines = []
    for i in range(n):
        lines.append(json.dumps({
            "id": f"{i:08x}", "ts": "2026-10-11T14:00:00Z", "from": "peer",
            "type": "say", "to": "*", "reply": None, "ref": None,
            "text": f"message {i} — " + "x" * 860,
        }, ensure_ascii=False))
    return "\n".join(lines) + "\n"


def run(cli: str, base: str, home: str, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, CHATCODE_API=base, CHATCODE_TOKEN="test-token",
               CHATCODE_REPO=REPO, CHATCODE_AGENT="test-agent", HOME=home)
    return subprocess.run([sys.executable, os.path.abspath(cli), *args],
                          capture_output=True, text=True, env=env, timeout=120)


# --- cases ----------------------------------------------------------------

def _all_lines(state, prefix="bus/") -> list[str]:
    """Every message line across the channel and any archive it rotated into."""
    out = []
    for path, text in state.files.items():
        if path.startswith(prefix):
            out.extend(text.splitlines())
    return out


def case_append_to_big_channel_keeps_every_message(cli: str) -> tuple[bool, str]:
    """Zero loss across channel AND archive: the CLI auto-rotates past 500 lines
    (ROTATE_AT), so counting only the hot file would be measuring the wrong thing."""
    state = FakeGitHub()
    original = big_channel()
    originals = original.splitlines()
    state.files["bus/general.jsonl"] = original
    state.big.add("bus/general.jsonl")
    srv, base = start_mock(state)
    home = tempfile.mkdtemp(prefix="chatcode-big-home-")
    try:
        proc = run(cli, base, home, "say", "hello big channel", "-c", "general")
    finally:
        srv.shutdown()
    after = _all_lines(state)
    new = [l for l in after if l not in set(originals)]
    lost = [l for l in originals if l not in set(after)]
    hot = len(state.files["bus/general.jsonl"].splitlines())
    archived = len(after) - hot
    ok = (proc.returncode == 0 and not lost and len(new) == 1
          and "hello big channel" in new[0] and len(original) > BIG)
    detail = (f"exit={proc.returncode} bytes={len(original)} lines {len(originals)}->"
              f"{len(after)} (hot={hot} archived={archived}) lost={len(lost)} added={len(new)}")
    if not ok:
        detail += "\n--- stderr ---\n" + proc.stderr.strip()[-500:]
    return ok, detail


def case_append_to_big_channel_uses_the_sha(cli: str) -> tuple[bool, str]:
    """The append must still be anchored to the sha, not become a blind overwrite."""
    state = FakeGitHub()
    original = big_channel(400)
    state.files["bus/general.jsonl"] = original
    state.big.add("bus/general.jsonl")
    srv, base = start_mock(state)
    home = tempfile.mkdtemp(prefix="chatcode-big-home-")
    try:
        proc = run(cli, base, home, "say", "second message", "-c", "general")
    finally:
        srv.shutdown()
    blob_reads = [x for x in state.log if x[0] == "GET-blob"]
    ok = proc.returncode == 0 and len(blob_reads) >= 1
    return ok, f"exit={proc.returncode} blob_reads={len(blob_reads)} (body fetched, not assumed empty)"


def case_task_read_via_blob(cli: str) -> tuple[bool, str]:
    """A task file served blob-only must still be updatable (update_task/claim_task reads)."""
    tid = "t-20261011-0001"
    state = FakeGitHub()
    state.files[f"board/tasks/{tid}.json"] = json.dumps({
        "id": tid, "title": "big task", "desc": "", "status": "claimed",
        "owner": "test-agent", "created_by": "test-agent",
        "created_ts": "2026-10-11T00:00:00Z", "updated_ts": "2026-10-11T00:00:00Z",
        "priority": 3, "tags": [], "deps": [], "branch": None, "pr": None, "history": [],
    }, indent=2) + "\n"
    state.big.add(f"board/tasks/{tid}.json")     # served without inline content
    srv, base = start_mock(state)
    home = tempfile.mkdtemp(prefix="chatcode-big-home-")
    try:
        proc = run(cli, base, home, "tasks", "update", tid, "--status", "done")
    finally:
        srv.shutdown()
    stored = state.files[f"board/tasks/{tid}.json"]
    ok = proc.returncode == 0 and json.loads(stored)["status"] == "done"
    detail = f"exit={proc.returncode} status={json.loads(stored)['status']}"
    if not ok:
        detail += "\n--- stderr ---\n" + proc.stderr.strip()[-300:]
    return ok, detail


def case_truly_empty_file_is_still_empty(cli: str) -> tuple[bool, str]:
    """Control: a real 0-byte file (encoding=base64, content='') is not a missing body."""
    state = FakeGitHub()
    state.files["bus/general.jsonl"] = ""
    srv, base = start_mock(state)
    home = tempfile.mkdtemp(prefix="chatcode-big-home-")
    try:
        proc = run(cli, base, home, "say", "first ever message", "-c", "general")
    finally:
        srv.shutdown()
    after = state.files["bus/general.jsonl"]
    blob_reads = [x for x in state.log if x[0] == "GET-blob"]
    ok = proc.returncode == 0 and len(after.splitlines()) == 1 and not blob_reads
    return ok, (f"exit={proc.returncode} lines={len(after.splitlines())} "
                f"blob_reads={len(blob_reads)} (should be 1 line, 0 blob reads)")


def case_at_the_real_size_cap_it_fails_loudly_instead_of_wiping(cli: str) -> tuple[bool, str]:
    """With the fix, a >1MB append on the real API must refuse, not destroy.

    The contents endpoint rejects bodies over 1MB, so a faithful fix cannot
    promise the append succeeds — it can promise the channel is not wiped and
    the failure is loud. Full support needs rotate-before-append or the Git
    Data API, which is a separate task.
    """
    state = FakeGitHub()
    original = big_channel()
    state.files["bus/general.jsonl"] = original
    state.big.add("bus/general.jsonl")
    state.max_put_bytes = BIG
    srv, base = start_mock(state)
    home = tempfile.mkdtemp(prefix="chatcode-big-home-")
    try:
        proc = run(cli, base, home, "say", "hello big channel", "-c", "general")
    finally:
        srv.shutdown()
    intact = state.files["bus/general.jsonl"] == original
    loud = proc.returncode != 0 and (proc.stderr + proc.stdout).strip() != ""
    ok = intact and loud
    detail = (f"exit={proc.returncode} channel_intact={intact} "
              f"lines={len(state.files['bus/general.jsonl'].splitlines())}")
    if ok:
        detail += f" | refused with: {(proc.stderr or proc.stdout).strip().splitlines()[-1][:90]}"
    return ok, detail


CASES = [
    (">1MB channel survives an append with zero loss (channel + archive)",
     case_append_to_big_channel_keeps_every_message),
    ("the append fetches the body via /git/blobs",
     case_append_to_big_channel_uses_the_sha),
    ("a task file served blob-only is still updatable", case_task_read_via_blob),
    ("control: a truly empty file stays empty", case_truly_empty_file_is_still_empty),
    ("at the real 1MB PUT cap: loud refusal, channel intact",
     case_at_the_real_size_cap_it_fails_loudly_instead_of_wiping),
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
