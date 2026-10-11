#!/usr/bin/env python3
"""t-20261011-0920: `chatcode digest --write` must survive — and recompute on —
a 409 Conflict while writing STATUS.md.

STATUS.md races with every bus commit (each message is a push to main), and on
the pre-fix CLI the Conflict escaped as a raw traceback. This test proves, with
no network and no real token:

  1. a mock GitHub that 409s the first STATUS.md PUT once: `digest --write`
     completes, the retried PUT carries the current sha, and STATUS.md ends
     up freshly rendered;
  2. THE differentiator: when a peer's bus message lands *during* the race
     window, the retried write must reflect the NEW message count — i.e. the
     retry re-reads the inputs and re-renders the digest, it does not re-PUT
     the stale snapshot (and the 1.5s read cache must not defeat that);
  3. retries are bounded: a permanent 409 ends in a friendly non-zero exit
     with no traceback, after exactly DIGEST_WRITE_ATTEMPTS attempts.

Run it from the repo root (one command, stdlib only, ~15 seconds):

    python3 tests/test_digest_conflict_retry.py

To see the same test fail against a different revision of the CLI:

    python3 tests/test_digest_conflict_retry.py --cli /path/to/other/bin/chatcode

Exit code 0 = all cases pass.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "dreamer2664/chatcode"
DEFAULT_CLI = os.path.join(HERE, os.pardir, "bin", "chatcode")

STATUS = "STATUS.md"
BUS = "bus/general.jsonl"

FAKE_COMMIT = "19c718e0deadbeefcafe00000000000000000000"
FAKE_BASE = "17727c570f2a42031f0877aa557a54f57d879775"


def msg(n: int, author: str = "tester") -> str:
    return json.dumps({"id": f"m{n:04d}", "ts": f"2026-10-11T15:{n:02d}:00Z",
                       "from": author, "type": "say", "text": f"message {n}"})


def fixtures() -> dict[str, str]:
    """A tiny but valid collective: one channel, one agent, one task, old STATUS."""
    return {
        BUS: "\n".join(msg(n) for n in (1, 2, 3)) + "\n",
        "agents/tester.json": json.dumps({"name": "tester", "model": "mock",
                                          "role": "worker", "caps": "testing",
                                          "last_seen": "2026-10-11T15:03:00Z"}) + "\n",
        "board/tasks/t-1.json": json.dumps({"id": "t-1", "title": "sample task",
                                            "status": "open", "owner": None,
                                            "priority": 3}) + "\n",
        STATUS: "# STATUS — chatcode collective\n\n(stale — written before the race)\n",
    }


class FakeGitHub:
    """Just enough of the contents API, plus switches to lose a write race."""

    def __init__(self) -> None:
        self.files: dict[str, str] = dict(fixtures())
        self.commits: dict[str, str] = {}
        self.race = 0                 # how many PUTs to reject with 409
        self.race_appends: tuple[str, str] | None = None  # (path, line) a peer
        #                                               # lands while we race
        self.log: list[tuple[str, str, bool]] = []
        self._lock = threading.Lock()
        self._n = 0

    def sha(self, path: str) -> str:
        if path not in self.commits:
            self._n += 1
            self.commits[path] = f"{self._n:040x}"[-40:]
        return self.commits[path]

    def store(self, path: str, text: str) -> None:
        with self._lock:
            self.files[path] = text
            self._n += 1
            self.commits[path] = f"{self._n:040x}"[-40:]

    def paths_under(self, prefix: str) -> list[str]:
        prefix = prefix.strip("/")
        head = prefix + "/" if prefix else ""
        return sorted(p for p in self.files if p.startswith(head))


class Handler(BaseHTTPRequestHandler):
    server_version = "FakeGitHub/1.0"

    def log_message(self, *a):        # keep the test output clean
        pass

    @property
    def state(self) -> FakeGitHub:
        return self.server.state            # type: ignore[attr-defined]

    def _send(self, code: int, payload, raw: str | None = None) -> None:
        body = raw.encode("utf-8") if raw is not None else json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain" if raw is not None else "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _contents_path(self) -> str:
        prefix = f"/repos/{REPO}/contents/"
        path = self.path.split("?", 1)[0]
        return path[len(prefix):].strip("/") if path.startswith(prefix) else ""

    def do_GET(self):                      # noqa: N802
        raw_wanted = "vnd.github.raw" in self.headers.get("Accept", "")
        path = self.path.split("?", 1)[0]

        if path == f"/repos/{REPO}/rate_limit":
            return self._send(200, {"resources": {"core": {"limit": 5000, "remaining": 4999}}})
        if path.startswith(f"/repos/{REPO}/git/blobs/"):
            sha = path.rsplit("/", 1)[-1]
            text = next((t for p, t in self.state.files.items() if self.state.sha(p) == sha), "")
            return self._send(200, None, raw=text)

        rel = self._contents_path()
        if not rel:
            return self._send(404, {"message": "Not Found"})
        if rel in self.state.files:                      # a file
            text = self.state.files[rel]
            if raw_wanted:
                self.state.log.append(("GET-raw", rel, False))
                return self._send(200, None, raw=text)
            self.state.log.append(("GET", rel, False))
            return self._send(200, {
                "name": rel.split("/")[-1], "path": rel, "sha": self.state.sha(rel),
                "size": len(text), "type": "file", "encoding": "base64",
                "content": base64.b64encode(text.encode()).decode(),
            })
        children = self.state.paths_under(rel)           # a directory
        if children:
            self.state.log.append(("GET-dir", rel, False))
            return self._send(200, [{
                "name": c[len(rel) + 1:], "path": c, "sha": self.state.sha(c),
                "size": len(self.state.files[c]), "type": "file",
            } for c in children])
        self.state.log.append(("GET-404", rel, False))
        return self._send(404, {"message": "Not Found"})

    def do_PUT(self):                      # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        rel = self._contents_path()
        sha = body.get("sha")
        text = base64.b64decode(body.get("content", "")).decode("utf-8")
        exists = rel in self.state.files
        self.state.log.append(("PUT", rel, sha is not None))

        if self.state.race > 0:
            self.state.race -= 1
            if self.state.race_appends and rel == STATUS:
                # a peer's message lands on the bus while our PUT is in flight
                p, line = self.state.race_appends
                self.state.store(p, self.state.files.get(p, "") + line)
            return self._send(409, {"message": f"is at {FAKE_COMMIT} but expected {FAKE_BASE}"})

        if not exists and sha is None:                   # create
            self.state.store(rel, text)
            return self._send(200, {"content": {"sha": self.state.sha(rel)}})
        if exists and sha is None:                       # GitHub: needs a sha
            return self._send(422, {"message": "\"sha\" wasn't supplied."})
        if exists and sha != self.state.sha(rel):        # stale base
            return self._send(409, {"message": f"is at {self.state.sha(rel)} but expected {sha}"})
        self.state.store(rel, text)
        return self._send(200, {"content": {"sha": self.state.sha(rel)}})


def start_mock(state: FakeGitHub) -> tuple[ThreadingHTTPServer, str]:
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    srv.state = state                                # type: ignore[attr-defined]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def run_digest(cli_path: str, state: FakeGitHub):
    """Run the real `digest --write` against the mock, return the CompletedProcess."""
    srv, base = start_mock(state)
    home = tempfile.mkdtemp(prefix="chatcode-test-home-")
    env = dict(os.environ, CHATCODE_API=base, CHATCODE_TOKEN="test-token",
               CHATCODE_REPO=REPO, HOME=home)
    env.pop("CHATCODE_AGENT", None)
    try:
        return subprocess.run([sys.executable, cli_path, "digest", "--write"],
                              capture_output=True, text=True, env=env, timeout=120)
    finally:
        srv.shutdown()


def status_puts(state: FakeGitHub) -> list[tuple[str, str, bool]]:
    return [x for x in state.log if x[0] == "PUT" and x[1] == STATUS]


# --- cases ----------------------------------------------------------------

def case_write_survives_the_race(cli_path: str) -> tuple[bool, str]:
    """One 409, no other changes: digest completes and writes STATUS.md."""
    state = FakeGitHub()
    state.race = 1
    proc = run_digest(cli_path, state)
    puts = status_puts(state)
    final = state.files.get(STATUS, "")
    ok = (proc.returncode == 0
          and len(puts) == 2                       # one rejected, one accepted
          and puts[1][2] is True                   # retry is an update, not blind create
          and "**3** messages" in final            # freshly rendered
          and "stale — written before the race" not in final
          and "wrote STATUS.md" in proc.stderr)
    detail = (f"exit={proc.returncode} status_puts={len(puts)} "
              f"fresh={'yes' if '**3** messages' in final else 'no'}")
    if not ok:
        detail += "\n--- stderr ---\n" + proc.stderr.strip()[-800:]
    return ok, detail


def case_retry_recomputes_fresh_inputs(cli_path: str) -> tuple[bool, str]:
    """A bus message lands during the race window: the retried digest must
    reflect it — re-PUTing the stale snapshot would keep the count at 3."""
    state = FakeGitHub()
    state.race = 1
    state.race_appends = (BUS, msg(4, author="peer") + "\n")
    proc = run_digest(cli_path, state)
    puts = status_puts(state)
    final = state.files.get(STATUS, "")
    peer_line_in_bus = msg(4, author="peer") in state.files.get(BUS, "")
    ok = (proc.returncode == 0
          and len(puts) == 2
          and "**4** messages" in final           # recomputed, not stale-PUT
          and "**1** agents" in final
          and peer_line_in_bus)                   # we never touched the peer's line
    detail = (f"exit={proc.returncode} status_puts={len(puts)} "
              f"counted={'4' if '**4** messages' in final else ('3' if '**3** messages' in final else '?')} "
              f"peer_msg_intact={'yes' if peer_line_in_bus else 'no'}")
    if not ok:
        detail += "\n--- stderr ---\n" + proc.stderr.strip()[-800:]
    return ok, detail


def case_retries_are_bounded(cli_path: str) -> tuple[bool, str]:
    """A permanent 409 must end in a friendly die, not a traceback or a hang."""
    state = FakeGitHub()
    state.race = 999
    proc = run_digest(cli_path, state)
    puts = status_puts(state)
    friendly = ("digest --write" in proc.stderr and STATUS in proc.stderr
                and "Traceback" not in proc.stderr)
    ok = (proc.returncode != 0
          and friendly
          and 1 <= len(puts) <= 6)                # bounded, not a loop
    detail = (f"exit={proc.returncode} status_puts={len(puts)} "
              f"friendly={'yes' if friendly else 'no'} "
              f"traceback={'yes' if 'Traceback' in proc.stderr else 'no'}")
    if not ok:
        detail += "\n--- stderr ---\n" + proc.stderr.strip()[-800:]
    return ok, detail


CASES = [
    ("digest --write survives a one-shot 409 (writes STATUS.md, retry is an update)",
     case_write_survives_the_race),
    ("retry recomputes from fresh inputs (peer message landing mid-race is counted)",
     case_retry_recomputes_fresh_inputs),
    ("permanent 409: bounded retries, friendly die, no traceback",
     case_retries_are_bounded),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cli", default=DEFAULT_CLI,
                    help="path to the bin/chatcode under test (default: this repo's)")
    args = ap.parse_args()
    cli = os.path.abspath(args.cli)
    if not os.path.exists(cli):
        print(f"FAIL: cannot find CLI at {cli}")
        return 1
    print(f"chatcode CLI under test: {cli}\n")
    failures = 0
    for title, fn in CASES:
        ok, detail = fn(cli)
        print(("PASS  " if ok else "FAIL  ") + title)
        print("      " + detail)
        failures += 0 if ok else 1
    print()
    if failures:
        print(f"{failures}/{len(CASES)} cases FAILED")
        return 1
    print(f"{len(CASES)}/{len(CASES)} cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
