#!/usr/bin/env python3
"""Regression test for the duplicate-id policy + rotation drift guard (vesta, 2026-10-14).

Context: validate counted 384 duplicate-id errors on the live bus. Audit result:
383 of them are the SAME message sitting in two overlapping archive files (a
hot file that reappeared with already-archived lines — workspace rollback —
was re-archived under a fresh timestamp). The 384th is the real defect: one id
(6acd4708, pericles, 2026-10-12T20:46Z) held TWO different messages, minted in
the same second by the old random short_id().

What this test proves, with no network and no token, against any revision of
the CLI:

  1. validate's verdict on duplicates is content-based: byte-identical copies
     are the record → one summary warning, zero errors; differing copies are
     id drift → an error naming the id. (Before this change both were errors.)
  2. rotation never re-archives a line whose id is already in an archive of
     that channel, even when the hot file comes back carrying archived lines:
     every id survives exactly once across hot + archives. (Before this
     change, the rollback case produced the 383 identical duplicates.)
  3. a second rotation inside the same second (same archive file name)
     appends to the existing archive instead of replacing it — zero loss.
  4. short_id() no longer derives from the seedable `random` module: two
     identical seeds do not produce the same id (the fork-inherited RNG state
     is the suspected collision mechanism), and the format stays 8 hex chars.
  5. `normalize-dups` leaves identical merges alone, repairs a differing dup
     by re-iding the later copy (never touching the keeper), is dry-run by
     default, and the repaired repo validates clean.

Run from the repo root (one command, stdlib only, ~3 seconds):

    python3 tests/test_dup_identity.py

Against another revision (e.g. to see it fail on main):

    python3 tests/test_dup_identity.py --cli /path/to/other/bin/chatcode

Exit code 0 = all cases pass.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import importlib.machinery
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import types

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
        self.writes = []

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
    def __init__(self, cc):
        self.cc = cc
        self.repo_cls = type("CasRepoWired", (CasRepo,), {})
        if hasattr(cc, "Conflict"):
            globals()["ConflictSim"] = cc.Conflict
        if hasattr(cc, "AlreadyExists"):
            globals()["AlreadyExistsSim"] = cc.AlreadyExists


class Ctx:
    def __init__(self, api, root):
        self.api = api
        self.local = root


def msg(mid, i, frm="alpha", mtype="say", to="*", text=None):
    return {"id": mid, "ts": "2026-10-11T14:00:%02dZ" % (i % 60), "from": frm,
            "type": mtype, "to": to, "text": text or ("msg %d" % i)}


def write_lines(root, relpath, lines):
    p = os.path.join(root, relpath)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("".join(json.dumps(l) + "\n" for l in lines))


def read_lines(root, relpath):
    p = os.path.join(root, relpath)
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def seed_channel(root, n, name="testrot"):
    ids = ["b%07x" % i for i in range(n)]
    write_lines(root, f"bus/{name}.jsonl", [msg(mid, i) for i, mid in enumerate(ids)])
    return ids


def all_archive_ids(root, channel="testrot"):
    """id -> count, across every archive file of the channel."""
    from collections import Counter
    cnt = Counter()
    adir = os.path.join(root, "bus", "archive")
    if os.path.isdir(adir):
        for n in sorted(os.listdir(adir)):
            if n.startswith(channel + "-") and n.endswith(".jsonl"):
                for m in read_lines(root, f"bus/archive/{n}"):
                    cnt[m["id"]] += 1
    return cnt


def validate_repo(cc, root):
    ctx = Ctx(Harness(cc).repo_cls(root), root)
    msgs = cc.fetch_messages(ctx, all_channels=True, include_archive=True,
                             include_dms=True)
    return cc.validate_state(msgs, [], [], [])


def case_validate_policy(cc):
    """(1) content-based verdicts: identical → warning, differing → error."""
    label = "validate: identical copies warn, differing copies error"
    a = dict(msg("aa000001", 0), _file="bus/archive/x.jsonl", _lineno=1, _channel="general")
    twin = dict(a, _file="bus/archive/y.jsonl", _lineno=9)
    errs, warns = cc.validate_state([a, twin], [], [], [])
    ok1 = not errs and any("identical content" in w for w in warns)

    b = dict(msg("bb000002", 1, text="to cormac"),
             _file="bus/archive/z.jsonl", _lineno=159, _channel="general")
    c = dict(msg("bb000002", 1, text="to barry"),
             _file="bus/archive/z.jsonl", _lineno=160, _channel="general")
    errs, warns = cc.validate_state([b, c], [], [], [])
    ok2 = (len(errs) == 1 and "DIFFERING" in errs[0] and "bb000002" in errs[0]
           and not any("identical content" in w for w in warns))
    print(f"{'PASS' if ok1 and ok2 else 'FAIL'}  {label}")
    if not (ok1 and ok2):
        print(f"      identical→errs={errs} warns={warns}")
    return ok1 and ok2


def case_rotation_drift_guard(cc):
    """(2) a rolled-back hot file must not re-archive archived lines."""
    label = "rotation: hot file carrying archived lines → zero duplicates, zero loss"
    root = tempfile.mkdtemp(prefix="dup-rot-")
    try:
        repo = Harness(cc).repo_cls(root)
        ids = seed_channel(root, 505)                    # > ROTATE_AT (500)
        cc.rotate_channel(Ctx(repo, root), "testrot")
        arch_before = all_archive_ids(root)
        # rollback simulation: the working copy comes back with the hot file
        # holding BOTH the archived lines and the live tail — exactly what the
        # server saw on Oct 12-13.
        arch_files = sorted(os.listdir(os.path.join(root, "bus", "archive")))
        restored = []
        for n in arch_files:
            restored += read_lines(root, f"bus/archive/{n}")
        restored += read_lines(root, "bus/testrot.jsonl")
        write_lines(root, "bus/testrot.jsonl", restored)
        cc.rotate_channel(Ctx(repo, root), "testrot")     # the second rotation

        arch_after = all_archive_ids(root)
        hot = [m["id"] for m in read_lines(root, "bus/testrot.jsonl")]
        dup_in_archives = {k: v for k, v in arch_after.items() if v > 1}
        covered = set(arch_after) | set(hot)
        ok = (not dup_in_archives and set(ids) <= covered
              and sum(arch_after.values()) == sum(arch_before.values())
              and len(hot) <= 130)
        print(f"{'PASS' if ok else 'FAIL'}  {label}")
        print(f"      archive ids={sum(arch_after.values())} (dups={dup_in_archives or 'none'}),"
              f" hot={len(hot)}, unique preserved={len(set(ids) & covered)}/{len(ids)}")
        return bool(ok)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def case_same_second_append(cc):
    """(3) second rotation in the same second appends; it never replaces."""
    label = "rotation: same-second rerun appends to the archive (no replacement)"
    root = tempfile.mkdtemp(prefix="dup-sec-")
    real_dt = cc.datetime

    class FixedDT(real_dt):
        @classmethod
        def now(cls, tz=None):
            return real_dt(2026, 10, 11, 14, 0, 0, tzinfo=_dt.timezone.utc)

    cc.datetime = FixedDT
    try:
        repo = Harness(cc).repo_cls(root)
        ids = seed_channel(root, 505)
        name = "testrot-20261011T140000Z.jsonl"
        # this exact archive already exists and already holds the first 60 lines
        # (a rotation that ran earlier in this same second)
        pre = [msg(mid, i) for i, mid in enumerate(ids[:60])]
        write_lines(root, f"bus/archive/{name}", pre)

        cc.rotate_channel(Ctx(repo, root), "testrot")

        arch = read_lines(root, f"bus/archive/{name}")
        arch_ids = [m["id"] for m in arch]
        hot = [m["id"] for m in read_lines(root, "bus/testrot.jsonl")]
        kept_pre = {m["id"] for m in arch} >= set(ids[:60])
        ok = (count_dups(arch_ids) == 0 and len(set(arch_ids)) == 385
              and kept_pre and len(hot) == 120
              and len(set(arch_ids) | set(hot)) == 505
              and len(os.listdir(os.path.join(root, "bus", "archive"))) == 1)
        print(f"{'PASS' if ok else 'FAIL'}  {label}")
        print(f"      archive={len(arch)} lines (dups={count_dups(arch_ids)}), hot={len(hot)},"
              f" pre-seeded 60 still present={kept_pre}, union={len(set(arch_ids) | set(hot))}")
        return bool(ok)
    finally:
        cc.datetime = real_dt
        shutil.rmtree(root, ignore_errors=True)


def count_dups(seq):
    from collections import Counter
    return sum(v - 1 for v in Counter(seq).values() if v > 1)


def case_short_id(cc):
    """(4) ids must not come from the seedable, fork-inherited random module."""
    label = "short_id: seed-independent, format 8 hex"
    import re
    import random as _r
    _r.seed(1234)
    a = cc.short_id()
    _r.seed(1234)
    b = cc.short_id()
    fmt_ok = all(re.match(r"^[0-9a-f]{8}$", cc.short_id()) for _ in range(50))
    # 4 bytes of entropy: 200 draws must not (in practice) contain a repeat
    drawn = {cc.short_id() for _ in range(200)}
    ok = (a != b) and fmt_ok and len(drawn) == 200
    print(f"{'PASS' if ok else 'FAIL'}  {label}")
    if not ok:
        print(f"      seeded twice: {a} vs {b}; fmt_ok={fmt_ok}; unique={len(drawn)}/200")
    return bool(ok)


def case_normalize_dups(cc):
    """(5) the repair tool: dry-run by default, re-ids the later copy only."""
    label = "normalize-dups: dry-run silent, --write repairs, keeper untouched"
    root = tempfile.mkdtemp(prefix="dup-norm-")
    try:
        repo = Harness(cc).repo_cls(root)
        keeper = msg("cc000003", 1, text="to cormac")
        later = msg("cc000003", 1, text="to barry")           # same second, same id
        twin = msg("dd000004", 2)                             # identical merge
        arch = "bus/archive/general-20261013T000000Z.jsonl"
        write_lines(root, arch, [keeper, later, twin])
        write_lines(root, "bus/archive/general-20261012T000000Z.jsonl", [twin])
        # archives are discovered via their channel's hot file — give
        # 'general' a hot file or fetch_messages never sees the archive
        write_lines(root, "bus/general.jsonl", [msg("ee000005", 3)])
        before = open(os.path.join(root, arch), encoding="utf-8").read()

        args = types.SimpleNamespace(id=None, write=False)
        ctx = Ctx(repo, root)
        cc.cmd_normalize_dups(ctx, args)
        dry_ok = open(os.path.join(root, arch), encoding="utf-8").read() == before

        args.write = True
        cc.cmd_normalize_dups(ctx, args)
        after = read_lines(root, arch)
        ids_now = [m["id"] for m in after]
        new_id = ids_now[1]
        errs, warns = validate_repo(cc, root)
        ok = (dry_ok and len(set(ids_now)) == 3 and ids_now[0] == "cc000003"
              and new_id != "cc000003" and after[0]["text"] == keeper["text"]
              and after[1]["text"] == later["text"] and not errs
              and any("identical content" in w for w in warns))
        print(f"{'PASS' if ok else 'FAIL'}  {label}")
        print(f"      dry-run unchanged={dry_ok}, repaired id={new_id}, errors={errs or 'none'}")
        return bool(ok)
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
        case_validate_policy(cc),
        case_rotation_drift_guard(cc),
        case_same_second_append(cc),
        case_short_id(cc),
        case_normalize_dups(cc),
    ]
    print()
    print(f"{sum(results)}/{len(results)} cases passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
