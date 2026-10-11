#!/usr/bin/env python3
"""t-20261011-56ac finding 2 (rotation data loss) — deterministic repro, no network.

Simulates, with LocalRepo, exactly what happens when another agent's `say`
lands on a channel while rotate_channel() is running on it. The concurrent
message is silently lost: it ends up in neither the hot file nor the archive.

Run from anywhere:  python3 notes/t-20261011-56ac-cormac/repro_rotate_loss.py
"""
import json, os, shutil, sys, tempfile
import importlib.util
from importlib.machinery import SourceFileLoader

CLI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bin", "chatcode")
spec = importlib.util.spec_from_loader("chatcode", SourceFileLoader("chatcode", CLI))
cc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc)

tmp = tempfile.mkdtemp(prefix="rot-")
os.makedirs(os.path.join(tmp, "bus"))
hot = os.path.join(tmp, "bus", "testrot.jsonl")

# 505 valid messages -> above ROTATE_AT (500), rotation will trigger
with open(hot, "w") as fh:
    for i in range(505):
        m = {"id": "%08x" % i, "ts": "2026-10-11T14:00:%02dZ" % (i % 60),
             "from": "alpha", "type": "say", "to": "*", "text": f"msg {i}"}
        fh.write(json.dumps(m) + "\n")

LOST = {"id": "deadbeef", "ts": "2026-10-11T14:05:00Z", "from": "beta",
        "type": "say", "to": "*", "text": "posted while rotation was running"}

class FakeCtx:
    local = tmp
    api = cc.LocalRepo(tmp)

real_write = cc.LocalRepo.write_text
def racing_write(self, path, text, *a, **kw):
    # when the ARCHIVE is written, another agent's `say` lands on the hot file
    # (i.e. between the snapshot read at bin/chatcode:1135 and the final write
    # at :1146-1147)
    if path.startswith("bus/archive/"):
        with open(os.path.join(self.local, "bus", "testrot.jsonl"), "a") as fh:
            fh.write(json.dumps(LOST) + "\n")
    return real_write(self, path, text, *a, **kw)
cc.LocalRepo.write_text = racing_write

cc.rotate_channel(FakeCtx(), "testrot")

hot_now = open(hot).read()
arch = [f for f in os.listdir(os.path.join(tmp, "bus", "archive"))][0]
arch_now = open(os.path.join(tmp, "bus", "archive", arch)).read()

print("hot file lines after rotation :", hot_now.count("\n"))
print("archive lines                 :", arch_now.count("\n"))
print("message #deadbeef in hot?     :", "deadbeef" in hot_now)
print("message #deadbeef in archive? :", "deadbeef" in arch_now)
ok = ("deadbeef" in hot_now) or ("deadbeef" in arch_now)
print("VERDICT:", "message survived (no bug)" if ok else "MESSAGE LOST SILENTLY — bug confirmed")
shutil.rmtree(tmp)
sys.exit(0 if ok else 2)
