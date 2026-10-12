#!/usr/bin/env python3
"""keys_usage.py — who used the keys, how much. The whole floor checks here.

Reads keys/usage/*.jsonl (written by tools/keys_ask.py) and prints per-agent
and per-key tallies with daily budgets from keys/budget.json.

  python3 tools/keys_usage.py                 # today
  python3 tools/keys_usage.py --day 2026-10-12
  python3 tools/keys_usage.py --json
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", default=datetime.now(timezone.utc)
                    .strftime("%Y-%m-%d"))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    rows = []
    for f in sorted((ROOT / "keys" / "usage").glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("ts", "").startswith(a.day):
                rows.append(r)

    by_agent = defaultdict(lambda: {"calls": 0, "ok": 0, "err": 0, "chars": 0})
    by_key = defaultdict(lambda: {"calls": 0, "agents": set()})
    for r in rows:
        A = by_agent[r.get("agent", "?")]
        A["calls"] += 1
        A["ok" if r.get("ok") else "err"] += 1
        A["chars"] += r.get("chars") or 0
        K = by_key[r.get("key_fp", "?")]
        K["calls"] += 1
        K["agents"].add(r.get("agent", "?"))

    budget = {}
    try:
        budget = json.loads((ROOT / "keys" / "budget.json").read_text())
    except Exception:
        pass

    if a.json:
        print(json.dumps({
            "day": a.day,
            "agents": dict(by_agent),
            "keys": {k: {"calls": v["calls"], "agents": sorted(v["agents"])}
                     for k, v in by_key.items()}}, indent=1))
        return 0

    print(f"key usage — {a.day} (UTC)")
    print(f"{'agent':22}{'calls':>7}{'ok':>6}{'err':>6}{'chars':>9}{'cap':>6}")
    for ag, v in sorted(by_agent.items()):
        cap = budget.get("per_agent", {}).get(
            ag, budget.get("default_per_day", "-"))
        print(f"{ag:22}{v['calls']:>7}{v['ok']:>6}{v['err']:>6}"
              f"{v['chars']:>9}{str(cap):>6}")
    if not by_agent:
        print("  (no registered calls today)")
    print()
    print(f"{'key fp':14}{'calls':>7}  used by")
    for k, v in sorted(by_key.items(), key=lambda kv: -kv[1]["calls"]):
        print(f"{k:14}{v['calls']:>7}  {', '.join(sorted(v['agents']))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
