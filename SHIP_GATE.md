# SHIP_GATE.md — the only gate between your branch and main
<!-- EPOCH: 2026-10-20.4 · tier-law: changes need 2 pre-merge votes + the Director -->
<!-- `chatcode ship` runs every line starting with "$ ", in order, in this repo.
     Any failure = no ship. No manager, no override, no exceptions. -->

## tier: work — a worker self-merges on a green gate

$ python3 bin/chatcode --repo-dir . validate
$ python3 tests/run_all.py

# Project repos carry their own SHIP_GATE.md. Put the narrowest command that
# proves THIS deliverable, e.g.:
# $ python3 tools/check_evidence.py jobs/<id>/
# $ ffprobe -v error -show_entries format=duration -of csv=p=0 dist.mp4
# $ python3 tests/test_s99_receipts.py
