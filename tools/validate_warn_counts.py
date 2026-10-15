#!/usr/bin/env python3
"""Classify and count the warnings printed by `chatcode validate`.

Usage:
    python3 tools/validate_warn_counts.py              # runs bin/chatcode validate
    python3 tools/validate_warn_counts.py FILE         # reads saved validate output
    python3 tools/validate_warn_counts.py --json

Each warning line is matched against the known warning classes below. The
script checks that the classes add up to the warning total printed on the
footer line (`N messages · N tasks · N agents · E errors · W warnings`) and
exits 1 if any warning matched no class, so a new warning kind is noticed.
"""
import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (key, regex, meaning) — order matters only for readability; each line is counted once.
CLASSES = [
    ("agent_missing_roster",
     r"from '[^']+' has no agents/[^']+\.json entry",
     "a message's sender has no agents/<name>.json file (retired or never-joined name)"),
    ("owner_not_in_roster",
     r"owner '[^']+' is not in agents/",
     "a task's owner field names an agent with no agents/ entry"),
    ("done_without_owner",
     r"status done without an owner",
     "a task is marked done but has no owner recorded"),
    ("long_bus_message",
     r"chars on the bus — the chat is for talking",
     "a say/note/status/idea/join/done message is over 1200 chars (rule R3: reports go in files)"),
    ("human_channel_unprompted",
     r"started a new message in #human-",
     "an agent posted a new message in a human-* channel without replying (human channels are reply-only)"),
]
FOOTER_RE = re.compile(
    r"(\d+) messages · (\d+) tasks · (\d+) agents · (\d+) errors · (\d+) warnings")


def run_validate():
    proc = subprocess.run([sys.executable, str(ROOT / "bin" / "chatcode"), "validate"],
                          capture_output=True, text=True, cwd=ROOT)
    return proc.stdout + proc.stderr


def classify(text):
    counts = Counter()
    unmatched = []
    warn_lines = [ln for ln in text.splitlines() if re.match(r"^warn\b", ln)]
    for ln in warn_lines:
        for key, rx, _ in CLASSES:
            if re.search(rx, ln):
                counts[key] += 1
                break
        else:
            unmatched.append(ln)
    footer = FOOTER_RE.search(text)
    return counts, unmatched, len(warn_lines), footer


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", nargs="?", help="saved `chatcode validate` output (default: run it)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    text = Path(args.file).read_text(encoding="utf-8") if args.file else run_validate()
    counts, unmatched, total, footer = classify(text)
    report = {
        "classes": {k: {"count": counts.get(k, 0), "meaning": m} for k, _, m in CLASSES},
        "warnings_counted": total,
        "unmatched": unmatched,
        "footer": footer.group(0) if footer else None,
    }
    if footer:
        report["footer_warnings"] = int(footer.group(5))
        report["footer_errors"] = int(footer.group(4))
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        for k, _, m in CLASSES:
            print(f"{counts.get(k, 0):4d}  {k:26s} {m}")
        print(f"{total:4d}  total warning lines")
        print("footer:", report["footer"] or "(not found)")
    ok = not unmatched and (not footer or int(footer.group(5)) == total)
    if not ok:
        print("MISMATCH: unmatched warnings or footer count differs", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
