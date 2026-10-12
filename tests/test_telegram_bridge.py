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
texts, dms, state, notes = b.parse_updates(list(updates), state)
check("the group chat is adopted", state["chat_id"] == -1009, str(state))
check("the first human is pinned as owner", state["owner_id"] == 42, str(state))
check("a group-only batch queues no DMs", dms == [], str(dms))
check("only the owner's text crosses", texts == ["hello everyone"], str(texts))
check("the offset advances past every update", state["offset"] == 6, str(state))
check("a photo is skipped with a note, not silently",
      any("photo" in n for n in notes), str(notes))
check("a non-owner is called out", any("Stranger" in n for n in notes), str(notes))

# the ingest clamp (t-20261011-e993): Telegram allows 4096 chars, the bus 4000.
# One long phone message must not produce a line the CLI's validator flags.
long_text = "x" * 4096
clamped = b.clamp_text(long_text)
check("a 4096-char message is clamped under the bus limit",
      len(clamped) <= 4000 and clamped.endswith("… [truncated]"), f"len={len(clamped)}")
check("a short message passes through untouched",
      b.clamp_text("hello") == "hello", "short text was modified")
check("exactly-4000 stays whole", len(b.clamp_text("y" * 4000)) == 4000,
      "boundary off-by-one")


# --- the direct line (Carlo -> Pericles, 12 Oct) ---------------------------
dstate = {"offset": 100, "chat_id": -1009, "owner_id": 42}
dupdates = [
    {"update_id": 101, "message": {"message_id": 5, "chat": {"id": 42, "type": "private"},
                                   "from": {"id": 42, "first_name": "Carlo", "is_bot": False},
                                   "text": "add a page for the numbers"}},
    {"update_id": 102, "message": {"message_id": 6, "chat": {"id": 77, "type": "private"},
                                   "from": {"id": 77, "first_name": "Stranger", "is_bot": False},
                                   "text": "let me in"}},
    {"update_id": 103, "message": {"message_id": 7, "chat": {"id": 42, "type": "private"},
                                   "from": {"id": 42, "first_name": "Carlo", "is_bot": False},
                                   "text": "!team tell everyone this"}},
    {"update_id": 104, "message": {"message_id": 8, "chat": {"id": 42, "type": "private"},
                                   "from": {"id": 42, "first_name": "Carlo", "is_bot": False},
                                   "photo": [{"file_id": "small"}, {"file_id": "big"}]}},
    {"update_id": 105, "message": {"message_id": 9, "chat": {"id": 42, "type": "private"},
                                   "from": {"id": 42, "first_name": "Carlo", "is_bot": False},
                                   "text": "/start"}},
]
texts, dms, dstate, notes = b.parse_updates(list(dupdates), dstate)
check("a DM text is queued for the direct line",
      dms and dms[0]["text"] == "add a page for the numbers" and dms[0]["update_id"] == 101, str(dms))
check("a DM does not become a group message by itself", texts == [], str(texts))
check("the stranger's DM is ignored, content and all",
      all("let me in" != d.get("text") for d in dms) and any("Stranger" in n for n in notes), str(notes))
check("the owner's DM chat id is remembered", dstate["dm_chat_id"] == 42, str(dstate))
check("!team keeps its text for the inbox", dms[1]["text"].startswith("!team"), str(dms[1]))
check("a photo DM carries its largest file id",
      dms[2]["kind"] == "photo" and dms[2]["file_id"] == "big", str(dms[2]))
check("/start is a start, not a message to answer", dms[3]["kind"] == "start", str(dms[3]))
check("the ack reads like a person", b.dm_ack_text(1).startswith("📥 Got it"), b.dm_ack_text(1))
check("a burst is acked with its count", "3 messages" in b.dm_ack_text(3), b.dm_ack_text(3))
check("a !team ack says so", "group" in b.dm_ack_text(1, True), b.dm_ack_text(1, True))
check("a bus line carries the name rule",
      json.loads(b.bus_line("hi", "2026-01-01T00:00:00Z"))["text"] == "Carlo: hi", "")
import tempfile
with tempfile.TemporaryDirectory() as td:
    b.DM_INBOX = os.path.join(td, "dm-inbox.jsonl")
    with open(b.DM_INBOX, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"update_id": 7, "text": "x"}) + "\n")
    check("a redelivered update id is recognised", b.existing_dm_ids() == {7}, str(b.existing_dm_ids()))

print()
if failures:
    print(f"FAIL: {len(failures)} case(s): {', '.join(failures)}")
    sys.exit(1)
print("OK: telegram bridge logic holds (formatting, filters, diff, ingest)")
