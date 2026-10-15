#!/usr/bin/env python3
"""editorial_check.py — slate registry validator (V01, t-20261015-484f).

The slate is the campaign's collision map. This tool is the automated half of
keeping it honest; editorial judgment stays with the reviewers. It refuses:

  * two slots carrying the same premise_key (duplicate premise);
  * suspiciously similar premises (token overlap >= THRESHOLD) unless a
    recorded 'differentiation' note explains why both films may exist;
  * slots without a sources_verified record (unsourced pitch);
  * unknown/duplicated slot ids, unknown task ids, or an owner named on a slot
    whose status says unclaimed (stale registry);
  * asset_strategy entries marked unavailable or unlicensed (rights check) —
    'Found on Google' is not permission, and the registry must say so.

Exit 0 = registry consistent; 1 = violations; 2 = unreadable registry.
"""
import json, re, sys, unicodedata

THRESHOLD = 0.55  # Jaccard overlap on content words that triggers a review demand
STOP = set("a an and are as at be by for from how in into is it its of on or "
           "that the this to was were what when where which who why with your".split())

def norm_tokens(text):
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if c.isalnum() or c.isspace())
    return {w for w in text.split() if w not in STOP and len(w) > 2}

def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)

def check_registry(reg):
    """Returns a list of (level, message) findings; any FAIL fails the run."""
    f = []
    slots = reg.get("slots")
    if not isinstance(slots, list) or not slots:
        return [("FAIL", "registry has no slots")]
    seen_slots, seen_tasks, premises = {}, {}, {}
    for i, s in enumerate(slots):
        sid = s.get("slot")
        if not re.fullmatch(r"YT\d{2}", sid or ""):
            f.append(("FAIL", f"slot[{i}]: slot id must look like YT01..YT99, got {sid!r}"))
            continue
        if sid in seen_slots:
            f.append(("FAIL", f"{sid}: duplicate slot entry (also at index {seen_slots[sid]})"))
        seen_slots[sid] = i
        tid = s.get("task")
        if not re.fullmatch(r"t-\d{8}-[0-9a-f]{4}", tid or ""):
            f.append(("FAIL", f"{sid}: missing/malformed task id {tid!r}"))
        elif tid in seen_tasks:
            f.append(("FAIL", f"{sid}: task {tid} also claimed by {seen_tasks[tid]} — one card, one slot"))
        else:
            seen_tasks[tid] = sid
        pk = s.get("premise_key")
        if not pk:
            f.append(("FAIL", f"{sid}: premise_key required (unsourced pitch cannot be reserved)"))
        elif pk in premises:
            f.append(("FAIL", f"{sid}: duplicate premise_key — collides with {premises[pk]}"))
        else:
            premises[pk] = sid
        if not s.get("sources_verified"):
            f.append(("FAIL", f"{sid}: sources_verified record required before a pitch is usable"))
        if s.get("owner") and s.get("status") in ("pitched-unclaimed", "open"):
            f.append(("FAIL", f"{sid}: owner {s['owner']} on an unclaimed slot — stale registry"))
        if not s.get("owner") and s.get("status") == "reserved":
            f.append(("FAIL", f"{sid}: reserved without an owner"))
    # pairwise premise similarity
    items = [(s["slot"], norm_tokens(s.get("premise_key", "")), s.get("differentiation"))
             for s in slots if s.get("premise_key")]
    for a in range(len(items)):
        for b in range(a + 1, len(items)):
            sim = jaccard(items[a][1], items[b][1])
            if sim >= THRESHOLD and not (items[a][2] or items[b][2]):
                f.append(("FAIL", f"{items[a][0]}/{items[b][0]}: premise overlap {sim:.2f} >= {THRESHOLD} "
                                  f"without a recorded differentiation note"))
            elif sim >= THRESHOLD:
                f.append(("info", f"{items[a][0]}/{items[b][0]}: overlap {sim:.2f} — differentiation on file"))
    # rights/asset strategy when present
    for s in slots:
        for a in s.get("assets", []):
            if a.get("availability") in ("unavailable", "unknown"):
                f.append(("FAIL", f"{s['slot']}: asset {a.get('name','?')} marked {a['availability']} — "
                                  f"inaccessible assets cannot anchor a film"))
            if a.get("license") in (None, "", "unknown", "found on google"):
                f.append(("FAIL", f"{s['slot']}: asset {a.get('name','?')} has no license record — "
                                  f"'found on Google' is not permission"))
    return f

def main(path):
    try:
        with open(path) as fh:
            reg = json.load(fh)
    except (OSError, json.JSONDecodeError) as e:
        print(f"cannot read registry: {e}", file=sys.stderr)
        sys.exit(2)
    findings = check_registry(reg)
    bad = False
    for level, msg in findings:
        print(f"[{level.upper():4}] {msg}")
        if level == "FAIL":
            bad = True
    print("FAIL: registry inconsistent" if bad else "OK: registry consistent")
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else
         "projects/youtube-training/editorial/slate-registry.json")
