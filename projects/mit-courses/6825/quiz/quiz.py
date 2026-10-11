#!/usr/bin/env python3
"""6.825 quiz engine (M4, t-20261011-b060).

Grades an answer sheet against bank.json mechanically. No manual
overrides: the score printed here is the score that goes in the journal.

Usage: python3 quiz.py answers.json [--bank bank.json] [--bar 85]
Exit code 0 = every section at/above bar and total at/above bar.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent

def grade(answers_path, bar=85.0, bank_path=None):
    bank_file = Path(bank_path) if bank_path else (HERE / "bank.json")
    bank = json.loads(bank_file.read_text())
    answers = json.loads(Path(answers_path).read_text())
    sections = {}
    total_q = total_ok = 0
    wrong = []
    for q in bank["questions"]:
        sec = q["section"]
        got = str(answers.get(q["id"], "")).strip().lower()
        want = str(q["answer"]).strip().lower()
        ok = got == want
        d = sections.setdefault(sec, [0, 0])
        d[0] += 1
        total_q += 1
        if ok:
            d[1] += 1
            total_ok += 1
        else:
            wrong.append((q["id"], got or "<blank>", want))
    print(f"bar: {bar:.0f}%")
    failed = []
    for sec in sorted(sections):
        n, ok = sections[sec]
        pct = 100.0 * ok / n
        flag = "PASS" if pct >= bar else "WEAK"
        print(f"  {sec:12s} {ok}/{n}  {pct:5.1f}%  {flag}")
        if pct < bar:
            failed.append(sec)
    pct = 100.0 * total_ok / total_q
    flag = "PASS" if pct >= bar and not failed else "WEAK"
    print(f"  {'TOTAL':12s} {total_ok}/{total_q}  {pct:5.1f}%  {flag}")
    if wrong:
        print("wrong:")
        for qid, got, want in wrong:
            print(f"  {qid}: answered {got!r} (correct: {want})")
    return 0 if flag == "PASS" else 1

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    bar = 85.0
    if "--bar" in sys.argv:
        bar = float(sys.argv[sys.argv.index("--bar") + 1])
        sys.argv.remove("--bar"); sys.argv.remove(str(bar))
    bank_path = None
    if "--bank" in sys.argv:
        bank_path = sys.argv[sys.argv.index("--bank") + 1]
        sys.argv.remove("--bank"); sys.argv.remove(bank_path)
    sys.exit(grade(sys.argv[1], bar, bank_path))
