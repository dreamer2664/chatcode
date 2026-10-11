#!/usr/bin/env python3
"""t-20261011-c1fa — a channel-scoped archive read must not sweep sibling channels.

DEFECT on main: fetch_messages includes archive files with a bare prefix match
(`name.startswith(ch + "-")`). Archive files are named
`<channel>-<YYYYMMDDTHHMMSSZ>.jsonl` and `-` is legal inside channel names, so
a read of channel `dev` also matches the archive of channel `dev-hotfix`.

Reproduced before the fix, with two 600-message channels and rotate:

    read -c dev --all --jsonl   ->  1080 messages: 600 [dev] + 480 [dev-hotfix]
    read -c dev-hotfix --all    ->  600 messages, 0 leaked (one-directional)

Four cases, and case 4 exists so a fix that simply drops archives cannot pass:

  1. RED on main: `read -c dev --all` returns only dev's own messages.
  2. the channel's OWN archive is still included (600 = 120 hot + 480 archived).
  3. control: `read -c dev-hotfix --all` returns only its own 600.
  4. the all-channels read still returns every message from both channels (1200).

One command, runnable by any agent from the repo root:

    python3 tests/test_archive_channel_scope.py

Exits 0 when the fix is in place; exits 1 with a clear report otherwise.
Stdlib only, throwaway --local repo under a temp dir, no network.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CLI = os.path.normpath(os.path.join(HERE, "..", "bin", "chatcode"))
TAG = {"dev": "[dev]", "dev-hotfix": "[dev-hotfix]"}
HOT = 120          # KEEP_AFTER_ROTATE
PER_CHANNEL = 600  # > ROTATE_AT (500) so rotate has something to do


def run(root, home, argv):
    cmd = [sys.executable, CLI, "--local", root, "--agent", "alice"] + argv
    env = dict(os.environ, HOME=home)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)


def make_repo():
    root = tempfile.mkdtemp(prefix="cc-scope-")
    os.makedirs(os.path.join(root, "agents"))
    os.makedirs(os.path.join(root, "bus"))
    with open(os.path.join(root, "agents", "alice.json"), "w") as fh:
        json.dump({"name": "alice", "kind": "ai", "role": "worker", "status": "active"}, fh)
    for ch in TAG:
        lines = []
        for i in range(PER_CHANNEL):
            lines.append(json.dumps({
                "id": f"{ch[:1]}{i:07d}",
                "ts": f"2026-10-11T09:{i // 60:02d}:{i % 60:02d}Z",
                "from": "alice", "type": "say", "to": "*",
                "text": f"{TAG[ch]} message {i}", "ref": None, "reply": None}))
        with open(os.path.join(root, "bus", f"{ch}.jsonl"), "w") as fh:
            fh.write("\n".join(lines) + "\n")
    return root


def read_jsonl(root, home, channel, extra=()):
    # --tail high enough that nothing is truncated: on an unfixed CLI the same
    # read returns 1080 lines (600 own + 480 foreign), and truncation would
    # hide part of the leak from the assertions below.
    p = run(root, home, ["read", "-c", channel, "--all", "--tail", "2000", "--jsonl", *extra])
    if p.returncode != 0:
        return None, f"rc={p.returncode} stderr={p.stderr.strip()[-160:]}"
    out = []
    for line in p.stdout.splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                return None, f"unparseable line: {line[:80]!r}"
    return out, ""


def belongs(msg):
    for ch, tag in TAG.items():
        if (msg.get("text") or "").startswith(tag):
            return ch
    return "?"


def main():
    if not os.path.exists(CLI):
        print(f"FAIL: cannot find CLI at {CLI}")
        return 1
    root = make_repo()
    home = tempfile.mkdtemp(prefix="cc-home-")
    failures = []
    try:
        p = run(root, home, ["rotate"])
        if p.returncode != 0:
            print(f"FAIL: rotate failed rc={p.returncode}: {p.stderr.strip()[-200:]}")
            return 1
        archived = sorted(os.listdir(os.path.join(root, "bus", "archive")))
        if len(archived) != 2:
            print(f"FAIL: expected 2 archives, found {archived}")
            return 1

        dev, err = read_jsonl(root, home, "dev")
        if dev is None:
            failures.append(f"case1: read -c dev --all crashed ({err})")
        else:
            foreign = [m for m in dev if belongs(m) == "dev-hotfix"]
            if foreign:
                failures.append(
                    f"case1: read -c dev --all swept {len(foreign)} message(s) from "
                    "channel dev-hotfix (cross-channel archive leak)")
            own = [m for m in dev if belongs(m) == "dev"]
            if len(own) != PER_CHANNEL:
                failures.append(
                    f"case2: dev's own history incomplete: {len(own)} of {PER_CHANNEL} "
                    "(own archive must still be included)")

        hotfix, err = read_jsonl(root, home, "dev-hotfix")
        if hotfix is None:
            failures.append(f"case3: read -c dev-hotfix --all crashed ({err})")
        else:
            foreign = [m for m in hotfix if belongs(m) == "dev"]
            if foreign:
                failures.append(f"case3: control channel swept {len(foreign)} foreign message(s)")
            if len(hotfix) != PER_CHANNEL:
                failures.append(f"case3: dev-hotfix history incomplete: {len(hotfix)} of {PER_CHANNEL}")

        p = run(root, home, ["read", "--all", "--tail", "5000", "--jsonl"])
        if p.returncode != 0:
            failures.append(f"case4: all-channels read crashed rc={p.returncode}")
        else:
            all_msgs = [json.loads(l) for l in p.stdout.splitlines() if l.strip()]
            both = [m for m in all_msgs if belongs(m) in TAG]
            if len(both) != 2 * PER_CHANNEL:
                failures.append(
                    f"case4: all-channels read returned {len(both)} of {2 * PER_CHANNEL} "
                    "messages — the fix must not drop legitimate archives")

        if failures:
            print("FAIL: channel-scoped archive reads are not scoped")
            for f in failures:
                print(f"  - {f}")
            return 1
        print("OK: archive reads are scoped by channel — own archive included (600), "
              "sibling channel not swept, all-channels read still complete (1200)")
        return 0
    finally:
        shutil.rmtree(root, ignore_errors=True)
        shutil.rmtree(home, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
