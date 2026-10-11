#!/usr/bin/env python3
"""Regression test for t-20261011-3df7: rotation must not lose messages.

What it proves, with no network and no token, against any revision of the CLI:

  1. no race: a >ROTATE_AT channel rotates, hot+archive preserve every line;
  2. a message appended WHILE the archive is being written (between the
     snapshot read and the sha re-read) survives — zero loss, no crash;
  3. a message appended between the verification read and the final write
     triggers a Conflict, which must be caught and retried — zero loss,
     no crash, no unhandled traceback.

The simulated repo enforces the same compare-and-swap rules as the GitHub
contents API: an update needs the current sha (409/422 otherwise) and a
create of an existing path without a sha is refused.

Run from the repo root (one command, stdlib only, ~2 seconds):

    python3 tests/test_rotate_no_loss.py

Against another revision (e.g. to see it fail on main):

    python3 tests/test_rotate_no_loss.py --cli /path/to/other/bin/chatcode

Exit code 0 = all cases pass.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.machinery
import importlib.util
import json
import os
import shutil
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_cli(path):
    spec = importlib.util.spec_from_loader(
        "chatcode_under_test", importlib.machinery.SourceFileLoader("chatcode_under_test", path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class CasRepo:
    """LocalRepo-shaped driver with GitHub's compare-and-swap semantics."""

    def __init__(self, root):
        self.root = root
        self.writes = []          # (path, had_sha) audit trail

    def _full(self, path):
        return os.path.join(self.root, path)

    def _sha(self, path):
        p = self._full(path)
        if not os.path.exists(p):
            return None
        return "sha-" + hashlib.sha1(open(p, "rb").read()).hexdigest()

    def contents(self, path, ref=None):
        p = self._full(path)
        if not os.path.exists(p):
            return None
        import base64
        raw = open(p, "rb").read()
        return {"content": base64.b64encode(raw).decode("ascii"),
                "encoding": "base64", "sha": self._sha(path), "path": path}

    def read_text(self, path, ref=None, ttl=0.0):
        p = self._full(path)
        return open(p, "r", encoding="utf-8").read() if os.path.exists(p) else None

    def write_text(self, path, text, message="", sha=None, create_only=False):
        p = self._full(path)
        exists = os.path.exists(p)
        if exists and sha is None:
            raise AlreadyExistsSim(f"{path}: sha wasn't supplied")
        if sha is not None and sha != self._sha(path):
            raise ConflictSim(f"{path}: is at {self._sha(path)} but expected {sha}")
        os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        self.writes.append((path, bool(sha)))

    def invalidate(self, path=None):
        pass


class AlreadyExistsSim(Exception):
    pass


class ConflictSim(Exception):
    pass


class Harness:
    """Wires the CLI module's exceptions to the simulated ones and back."""

    def __init__(self, cc):
        self.cc = cc
        # the CLI catches its OWN Conflict/AlreadyExists classes; make the
        # simulation raise those directly
        self.repo_cls = type("CasRepoWired", (CasRepo,), {})
        if hasattr(cc, "Conflict"):
            globals()["ConflictSim"] = cc.Conflict
        if hasattr(cc, "AlreadyExists"):
            globals()["AlreadyExistsSim"] = cc.AlreadyExists


def make_channel(root, n, name="testrot"):
    os.makedirs(os.path.join(root, "bus"), exist_ok=True)
    ids = []
    with open(os.path.join(root, "bus", f"{name}.jsonl"), "w") as fh:
        for i in range(n):
            mid = "a%07x" % i
            ids.append(mid)
            fh.write(json.dumps({"id": mid, "ts": "2026-10-11T14:00:%02dZ" % (i % 60),
                                 "from": "alpha", "type": "say", "to": "*",
                                 "text": "msg %d" % i}) + "\n")
    return ids


def all_lines(root, channel="testrot"):
    """Every message id present anywhere: hot file + all archives."""
    found = set()
    hot = os.path.join(root, "bus", f"{channel}.jsonl")
    if os.path.exists(hot):
        for l in open(hot):
            if l.strip():
                found.add(json.loads(l)["id"])
    adir = os.path.join(root, "bus", "archive")
    if os.path.isdir(adir):
        for n in os.listdir(adir):
            if n.startswith(channel + "-") and n.endswith(".jsonl"):
                for l in open(os.path.join(adir, n)):
                    if l.strip():
                        found.add(json.loads(l)["id"])
    return found


class Ctx:
    def __init__(self, api, root):
        self.api = api
        self.local = root


def case(cc, inject_at, label):
    """inject_at: None | 'archive' | 'final' — when the concurrent say lands."""
    root = tempfile.mkdtemp(prefix="rot-")
    try:
        repo = Harness(cc).repo_cls(root)
        ids = make_channel(root, 505)                       # > ROTATE_AT (500)
        extra = "deadbee1"

        real_write = repo.write_text

        def racing_write(path, text, message="", sha=None, create_only=False):
            hit = False
            if inject_at == "archive" and path.startswith("bus/archive/") \
                    and not hasattr(racing_write, "fired"):
                racing_write.fired = True                    # only once
                with open(os.path.join(root, "bus", "testrot.jsonl"), "a") as fh:
                    fh.write(json.dumps({"id": extra, "ts": "2026-10-11T14:30:00Z",
                                         "from": "beta", "type": "say", "to": "*",
                                         "text": "mid-rotation"}) + "\n")
                hit = True
            elif inject_at == "final" and path == "bus/testrot.jsonl" and sha is not None \
                    and not hasattr(racing_write, "fired"):
                racing_write.fired = True                    # only once
                with open(os.path.join(root, "bus", "testrot.jsonl"), "a") as fh:
                    fh.write(json.dumps({"id": extra, "ts": "2026-10-11T14:30:00Z",
                                         "from": "beta", "type": "say", "to": "*",
                                         "text": "final-write race"}) + "\n")
                hit = True
            out = real_write(path, text, message, sha, create_only)
            return out

        repo.write_text = racing_write
        try:
            cc.rotate_channel(Ctx(repo, root), "testrot")
            crashed = None
        except Exception as e:                               # noqa: BLE001
            crashed = f"{type(e).__name__}: {e}"

        hot_path = os.path.join(root, "bus", "testrot.jsonl")
        hot_n = sum(1 for l in open(hot_path) if l.strip()) if os.path.exists(hot_path) else 0
        present = all_lines(root)
        adir = os.path.join(root, "bus", "archive")
        arch_files = ([n for n in os.listdir(adir) if n.startswith("testrot-")]
                      if os.path.isdir(adir) else [])
        expected = set(ids) | ({extra} if inject_at else set())
        lost = expected - present
        ok = (crashed is None) and not lost and hot_n <= 130 and len(arch_files) == 1
        print(f"{'PASS' if ok else 'FAIL'}  {label}")
        print(f"      hot={hot_n} lines, unique ids preserved={len(present)}/{len(expected)},"
              f" archive_files={len(arch_files)}, crashed={crashed}, lost={sorted(lost) or 'none'}")
        return ok
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cli", default=os.path.join(REPO_ROOT, "bin", "chatcode"))
    args = ap.parse_args()
    if not os.path.exists(args.cli):
        print(f"FAIL: cannot find CLI at {os.path.abspath(args.cli)}")
        return 1
    print("chatcode CLI under test:", os.path.abspath(args.cli))
    cc = load_cli(args.cli)

    results = [
        case(cc, None, "no race: plain rotation preserves every line"),
        case(cc, "archive", "message lands while the archive is written: zero loss, no crash"),
        case(cc, "final", "message lands between verify and final write: Conflict caught, zero loss"),
    ]
    print()
    print(f"{sum(results)}/{len(results)} cases passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
