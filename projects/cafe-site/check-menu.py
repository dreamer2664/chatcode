#!/usr/bin/env python3
"""Validate menu.json against the epic contract (task t-20261011-dbee).

One command, stdlib only, runnable from anywhere:

    python3 check-menu.py

Checks: valid JSON array, >= 8 items, every item has the 4 contract fields
(name, price, description, tags), price is a display string like "3.50 EUR"
(with the euro sign), >= 2 tags per item, no duplicate names, and no menu
item name is hardcoded into index.html (data must come from menu.json).
Exits 1 with FAIL lines on any violation.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
errors = []

try:
    menu = json.loads((HERE / "menu.json").read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    print(f"FAIL: menu.json does not parse: {exc}")
    sys.exit(1)

if not isinstance(menu, list):
    errors.append("menu.json must be a JSON array of items")
    menu = []
if len(menu) < 8:
    errors.append(f"only {len(menu)} items, contract requires >= 8")

PRICE = re.compile(r"^\d+\.\d{2} €$")
FIELDS = ("name", "price", "description", "tags")
names = []

for i, item in enumerate(menu):
    if not isinstance(item, dict):
        errors.append(f"item {i}: not an object")
        continue
    label = item.get("name", f"#{i}")
    names.append(item.get("name"))
    for field in FIELDS:
        if field not in item:
            errors.append(f"{label}: missing field {field!r}")
    if not isinstance(item.get("name"), str) or not item.get("name", "").strip():
        errors.append(f"item {i}: name must be a non-empty string")
    if not PRICE.match(str(item.get("price", ""))):
        errors.append(f"{label}: price must be a display string like '3.50 €', "
                      f"got {item.get('price')!r}")
    if not isinstance(item.get("description"), str) or len(item.get("description", "")) < 10:
        errors.append(f"{label}: description missing or too short (<10 chars)")
    tags = item.get("tags")
    if not isinstance(tags, list) or len(tags) < 2:
        errors.append(f"{label}: needs a list of >= 2 tags")
    elif not all(isinstance(t, str) and t.strip() for t in tags):
        errors.append(f"{label}: tags must be non-empty strings")

if len(names) != len(set(names)):
    errors.append("duplicate item names in menu.json")

# app.js carries an embedded fallback mirror of menu.json (for file://, where
# fetch is blocked). menu.json is canonical; the two must never drift.
app_js = HERE / "app.js"
if app_js.exists():
    src = app_js.read_text(encoding="utf-8")
    m = re.search(r"/\* FALLBACK-BEGIN \*/\s*(\[.*?\])\s*/\* FALLBACK-END \*/",
                  src, re.DOTALL)
    if not m:
        errors.append("app.js: FALLBACK-BEGIN/END markers not found")
    else:
        try:
            fallback = json.loads(m.group(1))
            if fallback != menu:
                errors.append("app.js FALLBACK_MENU differs from menu.json — "
                              "menu.json is canonical; re-embed it (see README)")
        except json.JSONDecodeError as exc:
            errors.append(f"app.js FALLBACK_MENU does not parse: {exc}")
else:
    print("note: app.js not present next to this check; skipping fallback sync")

index = HERE / "index.html"
if index.exists():
    html = index.read_text(encoding="utf-8")
    # the contract: <ul id="menu"> starts empty and is filled from menu.json
    # only. Page copy elsewhere (tagline, about) may freely mention items.
    block = re.search(r'<ul[^>]*id="menu"[^>]*>(.*?)</ul>', html, re.DOTALL)
    if block is None:
        errors.append('index.html has no <ul id="menu"> (interface contract #1510fc30)')
    else:
        inner = block.group(1)
        if re.search(r"<li[\s>]", inner):
            errors.append('<ul id="menu"> contains hardcoded <li> entries '
                          "(must be filled from menu.json by app.js)")
        spilled = [n for n in names if n and n in inner]
        if spilled:
            errors.append(f"menu item names hardcoded inside <ul id=\"menu\">: {spilled}")
else:
    print("note: index.html not present next to this check; skipping hardcode scan")

if errors:
    for err in errors:
        print("FAIL:", err)
    sys.exit(1)
print(f"OK: {len(menu)} items, all with name/price/description/tags, "
      ">=2 tags each, prices as display strings, none hardcoded in index.html")
