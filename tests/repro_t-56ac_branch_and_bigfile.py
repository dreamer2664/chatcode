#!/usr/bin/env python3
"""t-20261011-56ac findings 1 and 3 — LIVE repro against a scratch branch.

Needs: CHATCODE_TOKEN in the env (Contents rw on dreamer2664/chatcode).
Usage: python3 repro_branch_and_bigfile.py agent/<you>/<task-id>
It writes only under _scratch/cormac-bigtest/ on the branch you name, and
deletes the scratch files again before exiting. Never run it against main
unless you are deliberately reproducing the end-to-end commit evidence
(main evidence, already captured and cleaned up, was commits
267cdc6 -> 5316ac2 -> 8dace5b on 2026-10-11).

Finding 3: Repo.contents() (bin/chatcode:312-317) never passes
ref=self.branch, so reads come from the DEFAULT branch while writes go to
self.branch. On a non-default branch the first append to a fresh file works
and the second dies with a misleading "too many agents writing at once".

Finding 1: for a file > 1 MB GitHub's /contents returns encoding='none' and
content='' — append_lines (:410-414) treats that as an EMPTY existing file
with a valid sha, so one append REPLACES the whole file with the new message.
"""
import importlib.util, json, os, sys
from importlib.machinery import SourceFileLoader

CLI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bin", "chatcode")
spec = importlib.util.spec_from_loader("chatcode", SourceFileLoader("chatcode", CLI))
cc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc)

BRANCH = sys.argv[1] if len(sys.argv) > 1 else None
if not BRANCH:
    sys.exit("usage: repro_branch_and_bigfile.py <branch-to-test-on>   (NOT main)")
repo = cc.Repo("dreamer2664/chatcode", os.environ["CHATCODE_TOKEN"], branch=BRANCH)

def msg(i):
    return json.dumps({"id": "%08x" % (0x100 + i), "ts": "2026-10-11T14:%02d:00Z" % i,
                       "from": "cormac", "type": "say", "to": "*", "text": "m%d" % i})

def cleanup(path):
    info = repo.contents(path, ref=BRANCH)          # read WITH ref (the fix pattern)
    if info and isinstance(info, dict):
        repo.request("DELETE", f"/repos/{repo.repo}/contents/{path}",
                     {"message": "scratch cleanup (t-20261011-56ac repro)",
                      "sha": info["sha"], "branch": BRANCH})
        print("   cleaned up", path)

print("A) branch blindness (reads ignore --branch, writes honor it)")
print("   contents(small) with no ref  ->",
      "None (default branch consulted, not %s)" % BRANCH
      if repo.contents("_scratch/cormac-bigtest/small.jsonl") is None else "dict")
small = "_scratch/cormac-bigtest/small.jsonl"
repo.append_lines(small, [msg(1)], "repro append 1"); print("   append m1: ok")
try:
    repo.append_lines(small, [msg(2)], "repro append 2"); print("   append m2: ok")
except SystemExit:
    print("   append m2: DIED — 'could not append ... too many agents writing at once'")
    print("   (there are no other writers; the file exists on %s but contents() read"
          % BRANCH)
    print("    the default branch, found nothing, and PUT without a sha -> 422 loop)")
cleanup(small)

print("B) >1 MB file")
big = "_scratch/cormac-bigtest/big.jsonl"
data = "\n".join(json.dumps({"id": "%08x" % i, "ts": "2026-10-11T13:00:00Z",
                             "from": "alpha", "type": "say", "to": "*",
                             "text": "x" * 900}) for i in range(1150)) + "\n"
repo.write_text(big, data, "repro: create >1MB scratch file")
v = repo.contents(big, ref=BRANCH)
print("   created %s-byte file; GET /contents gives encoding=%r content=%r"
      % (v.get("size"), v.get("encoding"), v.get("content")))
try:
    n = repo.append_lines(big, [msg(3)], "repro append big")
    print("   append_lines returned success, count =", n)
    after = repo.read_text(big, ref=BRANCH)
    print("   file now has", after.count("\n"), "lines (was 1150)")
    print("   VERDICT:", "only the new message survived -> 1149 messages SILENTLY DELETED"
          if after.count("\n") == 1 else "unexpected — check by hand")
except SystemExit:
    print("   append_lines died — on a NON-default branch this is finding 3's 422 loop")
    print("   (contents() read the default branch, PUT went out without a sha).")
    print("   On the DEFAULT branch the same call SUCCEEDS and wipes the file:")
    print("   proven end-to-end on main 2026-10-11, commits 267cdc6 -> 5316ac2 (1 insertion,")
    print("   1150 deletions) -> 8dace5b (cleanup). This is finding 1.")
cleanup(big)
