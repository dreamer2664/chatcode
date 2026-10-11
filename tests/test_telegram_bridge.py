#!/usr/bin/env python3
"""The Telegram bridge, tested offline (no network, no tokens).

The bridge is Carlo's room, and it carries the group's words. The parts worth
testing are the pure ones: how a bus message becomes a Telegram text, what the
relay refuses to carry (DMs, the human's own channel, Carlo's own words), and
what becomes a bus message on the way back (only the owner, only in the group,
bots ignored, a photo politely skipped).

    python3 tests/test_telegram_bridge.py
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BRIDGE = os.path.join(HERE, os.pardir, "telegram", "bridge.py")


def load_bridge():
    spec = importlib.util.spec_from_file_location("bridge", os.path.abspath(BRIDGE))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


b = load_bridge()
failures = []


def check(name, cond, extra=""):
    if cond:
        print(f"PASS  {name}")
    else:
        failures.append(name)
        print(f"FAIL  {name}  {extra}")


# --- how a message looks ---------------------------------------------------
m = {"from": "barry", "type": "say", "id": "a1b2c3d4", "text": "Barry: fixed it",
     "_channel": "dev"}
out = b.format_message(m)
check("a plain message keeps its text and gets a footer",
      out.startswith("Barry: fixed it") and "#dev" in out and "#a1b2c3d4" in out, out)

alert = b.format_message({"from": "pericles", "type": "alert", "id": "deadbeef",
                          "text": "Pericles: main is red", "_channel": "general"})
check("alerts carry their mark", alert.startswith("⚠️ "), alert)
check("say carries no mark", not out.startswith("⚠️") and not out.startswith("📋"), out)

long = b.format_message({"type": "say", "id": "x", "text": "y" * 9000, "_channel": "dev"})
check("long text is truncated inside Telegram's limit",
      len(long) <= b.MAX_SEND and "…" in long and long.endswith("#x"), str(len(long)))

# --- what the relay refuses to carry --------------------------------------
check("DMs never reach the group", not b.is_relayable({"from": "barry", "_channel": "dm-barry__scott"}))
check("the human's own channel is not eavesdropped", not b.is_relayable({"from": "scott", "_channel": "human-carlo"}))
check("Carlo's own words are not echoed back", not b.is_relayable({"from": "carlo", "_channel": "general"}))
check("agents on normal channels do reach the group", b.is_relayable({"from": "barry", "_channel": "dev"}))
check("a nameless message is dropped", not b.is_relayable({"from": "", "_channel": "dev"}))

# --- the diff reader -------------------------------------------------------
diff = ("diff --git a/bus/dev.jsonl b/bus/dev.jsonl\n"
        "--- a/bus/dev.jsonl\n+++ b/bus/dev.jsonl\n@@ -1 +1,2 @@\n"
        "+{\"id\":\"11111111\",\"from\":\"barry\",\"type\":\"say\",\"text\":\"one\"}\n"
        "+{\"id\":\"22222222\",\"from\":\"scott\",\"type\":\"say\",\"text\":\"two\"}\n")
check("added_lines takes only the additions", len(b.added_lines(diff)) == 2,
      str(b.added_lines(diff)))

# --- what Carlo's typing becomes ------------------------------------------
state = {"offset": 0, "chat_id": None, "owner_id": None}
updates = [
    {"update_id": 1, "my_chat_member": {"chat": {"id": -1009, "type": "supergroup", "title": "chatcode"}}},
    {"update_id": 2, "message": {"chat": {"id": -1009, "type": "supergroup"},
                                 "from": {"id": 42, "first_name": "Carlo", "is_bot": False},
                                 "text": "hello everyone"}},
    {"update_id": 3, "message": {"chat": {"id": -1009, "type": "supergroup"},
                                 "from": {"id": 99, "first_name": "Stranger", "is_bot": False},
                                 "text": "let me in"}},
    {"update_id": 4, "message": {"chat": {"id": -1009, "type": "supergroup"},
                                 "from": {"id": 7, "first_name": "Barry", "is_bot": True},
                                 "text": "beep"}},
    {"update_id": 5, "message": {"chat": {"id": -1009, "type": "supergroup"},
                                 "from": {"id": 42, "first_name": "Carlo", "is_bot": False},
                                 "photo": [{"file_id": "x"}]}},
]
texts, state, notes = b.parse_updates(list(updates), state)
check("the group chat is adopted", state["chat_id"] == -1009, str(state))
check("the first human is pinned as owner", state["owner_id"] == 42, str(state))
check("only the owner's text crosses", texts == ["hello everyone"], str(texts))
check("the offset advances past every update", state["offset"] == 6, str(state))
check("a photo is skipped with a note, not silently",
      any("photo" in n for n in notes), str(notes))
check("a non-owner is called out", any("Stranger" in n for n in notes), str(notes))

print()
if failures:
    print(f"FAIL: {len(failures)} case(s): {', '.join(failures)}")
    sys.exit(1)
print("OK: telegram bridge logic holds (formatting, filters, diff, ingest)")
