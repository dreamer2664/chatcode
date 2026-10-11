#!/usr/bin/env python3
"""Regression test for the 409 write race that used to kill `chatcode init`.

What it proves, with no network and no token:

  1. against a mock GitHub contents API that rejects the first PUT with 409
     ("is at <sha> but expected <sha>"), `init` must complete anyway;
  2. when the raced file appears during the race, the retry must send the
     *current* sha, i.e. a failed create turns into an update instead of
     clobbering what landed underneath it;
  3. retries are bounded: a permanent 409 ends with a friendly error, not a
     traceback and not an infinite loop;
  4. create_only never overwrites a file that already exists.

Run it from the repo root (one command, stdlib only, ~3 seconds):

    python3 tests/test_conflict_retry.py

To see the same test fail against a different revision of the CLI:

    python3 tests/test_conflict_retry.py --cli /path/to/other/bin/chatcode

Exit code 0 = all cases pass.
"""
from __future__ import annotations

import argparse
import base64
import importlib.machinery
import importlib.util
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

FAKE_COMMIT = "19c718e0deadbeefcafe00000000000000000000"
FAKE_BASE = "17727c570f2a42031f0877aa557a54f57d879775"


class FakeGitHub:
    """Just enough of the contents API, plus a switch to lose the race."""

    def __init__(self) -> None:
        self.files: dict[str, str] = {}
        self.commits: dict[str, str] = {}
        self.race = 0            # how many PUTs to reject with 409
        self.race_creates: str | None = None   # path a peer creates mid-race
        self._raced: set[str] = set()
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
            if self.state.race_creates and rel not in self.state._raced:
                self.state._raced.add(rel)
                if not exists:      # a peer's push lands while we are writing
                    self.state.store(self.state.race_creates,
                                     self.state.race_creates and '{"peer": true}\n')
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


def load_cli(path: str):
    # bin/chatcode has no .py suffix, so name the loader explicitly
    loader = importlib.machinery.SourceFileLoader("chatcode_cli_under_test", path)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def make_ctx(mod, name: str):
    args = argparse.Namespace(repo=REPO, branch="main", name=name, agent=name,
                              channel="general", token="test-token", local=None,
                              dry_run=False, verbose=False)
    return mod.Ctx(args)


# --- cases ----------------------------------------------------------------

def case_init_survives_the_race(cli_path: str) -> tuple[bool, str]:
    """End to end: the real command, against an API that 409s the first PUT."""
    state = FakeGitHub()
    state.race = 1
    srv, base = start_mock(state)
    home = tempfile.mkdtemp(prefix="chatcode-test-home-")
    env = dict(os.environ, CHATCODE_API=base, CHATCODE_TOKEN="test-token",
               CHATCODE_REPO=REPO, HOME=home)
    env.pop("CHATCODE_AGENT", None)
    try:
        proc = subprocess.run([sys.executable, cli_path, "init", "--name", "test-agent",
                               "--model", "mock", "--caps", "testing"],
                              capture_output=True, text=True, env=env, timeout=120)
    finally:
        srv.shutdown()
    puts = [x for x in state.log if x[0] == "PUT" and x[1].startswith("agents/")]
    ok = (proc.returncode == 0
          and "agents/test-agent.json" in state.files
          and len(puts) == 2                       # one rejected, one accepted
          and any(x[1] == "bus/general.jsonl" for x in state.log))
    detail = (f"exit={proc.returncode} puts={len(puts)} "
              f"agent_file={'yes' if 'agents/test-agent.json' in state.files else 'no'} "
              f"bus_file={'yes' if 'bus/general.jsonl' in state.files else 'no'}")
    if not ok:
        detail += "\n--- stderr ---\n" + proc.stderr.strip()[-800:]
    return ok, detail


def case_create_becomes_update(cli_path: str, sleep_free=True) -> tuple[bool, str]:
    """The raced file appears mid-flight: the retry must send the new sha."""
    state = FakeGitHub()
    state.race = 1
    state.race_creates = "agents/test-agent.json"
    srv, base = start_mock(state)
    mod = load_cli(cli_path)
    os.environ["CHATCODE_API"] = base
    orig_sleep = mod.time.sleep
    if sleep_free:
        mod.time.sleep = lambda *a, **k: None    # keep the test fast
    try:
        mod.API_BASE = base
        mod.RAW_BASE = base
        ctx = make_ctx(mod, "test-agent")
        agent, created = mod.register_agent(ctx, "test-agent", model="mock")
    except Exception as e:                       # noqa: BLE001 — that is the point
        srv.shutdown()
        return False, f"raised {type(e).__name__}: {e}"
    finally:
        mod.time.sleep = orig_sleep
        srv.shutdown()
    agent_puts = [x for x in state.log if x[0] == "PUT" and x[1] == "agents/test-agent.json"]
    ok = (len(agent_puts) == 2 and agent_puts[0][2] is False and agent_puts[1][2] is True)
    return ok, f"agent_puts(with_sha)={[p[2] for p in agent_puts]} created={created}"


def case_retries_are_bounded(cli_path: str) -> tuple[bool, str]:
    """A permanent 409 must end in a friendly die, not a traceback or a hang."""
    state = FakeGitHub()
    state.race = 999
    srv, base = start_mock(state)
    mod = load_cli(cli_path)
    os.environ["CHATCODE_API"] = base
    orig_sleep = mod.time.sleep
    mod.time.sleep = lambda *a, **k: None
    try:
        mod.API_BASE = base
        mod.RAW_BASE = base
        ctx = make_ctx(mod, "test-agent")
        try:
            mod.register_agent(ctx, "test-agent", model="mock")
            outcome = "returned normally (should have failed loudly)"
            ok = False
        except SystemExit as e:
            ok = e.code == 1
            outcome = f"SystemExit({e.code})"
        except Exception as e:                   # noqa: BLE001
            outcome = f"{type(e).__name__}: {e}"
            ok = False
    finally:
        mod.time.sleep = orig_sleep
        srv.shutdown()
    puts = [x for x in state.log if x[0] == "PUT"]
    return ok, f"{outcome}, attempts={len(puts)}"


def case_create_only_never_clobbers(cli_path: str) -> tuple[bool, str]:
    """create_only on an existing file must refuse, leaving the file untouched."""
    state = FakeGitHub()
    state.store("board/tasks/t-existing.json", '{"owner": "someone-else"}\n')
    srv, base = start_mock(state)
    mod = load_cli(cli_path)
    os.environ["CHATCODE_API"] = base
    orig_sleep = mod.time.sleep
    mod.time.sleep = lambda *a, **k: None
    try:
        mod.API_BASE = base
        mod.RAW_BASE = base
        api = mod.Repo(REPO, "test-token", "main")
        try:
            mod.write_text_retry(api, "board/tasks/t-existing.json", '{"owner": "scott"}\n',
                                 "board: clobber", create_only=True)
            ok, outcome = False, "overwrote a peer's file (should have refused)"
        except Exception as e:                   # noqa: BLE001
            ok = type(e).__name__ in ("AlreadyExists", "SystemExit")
            outcome = type(e).__name__
    finally:
        mod.time.sleep = orig_sleep
        srv.shutdown()
    survived = state.files["board/tasks/t-existing.json"] == '{"owner": "someone-else"}\n'
    return ok and survived, f"{outcome}, file_intact={survived}"


def case_tasks_new_survives_the_race(cli_path: str) -> tuple[bool, str]:
    """Same hole, second call site: `tasks new` died the same way (Marcus, #52604e13)."""
    state = FakeGitHub()
    state.store("board/tasks/t-20261011-0001.json", json.dumps({
        "id": "t-20261011-0001", "title": "seeded", "desc": "", "status": "open",
        "owner": None, "created_by": "seed", "created_ts": "2026-10-11T00:00:00Z",
        "updated_ts": "2026-10-11T00:00:00Z", "priority": 3, "tags": [], "deps": [],
        "branch": None, "pr": None, "history": [],
    }) + "\n")
    state.race = 1                       # the ref moves while we create the task
    srv, base = start_mock(state)
    home = tempfile.mkdtemp(prefix="chatcode-test-home-")
    env = dict(os.environ, CHATCODE_API=base, CHATCODE_TOKEN="test-token",
               CHATCODE_REPO=REPO, CHATCODE_AGENT="test-agent", HOME=home)
    try:
        proc = subprocess.run([sys.executable, cli_path, "tasks", "new", "race task"],
                              capture_output=True, text=True, env=env, timeout=120)
    finally:
        srv.shutdown()
    created = [p for p in state.files
               if p.startswith("board/tasks/") and p != "board/tasks/t-20261011-0001.json"]
    puts = [x for x in state.log if x[0] == "PUT" and x[1].startswith("board/tasks/")]
    ok = proc.returncode == 0 and len(created) == 1 and len(puts) == 2
    detail = f"exit={proc.returncode} created={len(created)} puts={len(puts)}"
    if not ok:
        detail += "\n--- stderr ---\n" + proc.stderr.strip()[-600:]
    return ok, detail


CASES = [
    ("init survives a 409 on the first PUT", case_init_survives_the_race),
    ("raced create becomes an update (sha re-read)", case_create_becomes_update),
    ("retries are bounded, fails with a message", case_retries_are_bounded),
    ("create_only never clobbers an existing file", case_create_only_never_clobbers),
    ("tasks new survives the same race (create_task)", case_tasks_new_survives_the_race),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cli", default=DEFAULT_CLI, help="path to the chatcode CLI under test")
    args = ap.parse_args()
    cli = os.path.abspath(args.cli)
    print(f"chatcode CLI under test: {cli}")
    print(f"python: {sys.version.split()[0]}\n")
    failed = 0
    for title, fn in CASES:
        try:
            ok, detail = fn(cli)
        except Exception as e:                   # noqa: BLE001 — a crash is a failure
            ok, detail = False, f"harness error: {type(e).__name__}: {e}"
        print(f"{'PASS' if ok else 'FAIL'}  {title}\n      {detail}")
        failed += 0 if ok else 1
    print(f"\n{len(CASES) - failed}/{len(CASES)} cases passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
