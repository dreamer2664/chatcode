#!/usr/bin/env python3
"""hive.py — one bot, every voice.

The Director's window into the crew. Every operative reports through ONE
collective bot: this bridge puts the operative's name in front of the sentence,
so the King always knows who is speaking without learning a single bot handle.

What crosses the bridge:

  `report` messages  -> the Director's private chat (the enforced register:
                        plain English, salutation, no jargon, no questions)
  everything else    -> the crew's Telegram group, only if one is configured

What does not: direct messages between agents, the Director's own channel, and
anything from the humans themselves. The hive is a stage, not the record — a
decision is a file in the repo, never a Telegram line.

Commands:
  relay [--all] [--dry-run]   send what is new since the last run
  send "<text>"               send one line (manual test / the Director's echo)

Env:
  TELEGRAM_HIVE_TOKEN   the collective bot's token (a repo secret; never committed)
  TELEGRAM_CHAT_ID      the group chat id (optional)
  TELEGRAM_DM_CHAT_ID   the Director's private chat id (defaults to state.dm_chat_id)

Missing token = exit 0 with a note: the repo is not red just because the bot has
not been connected yet. Nothing here ever prints a token.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUS = os.path.join(ROOT, "bus")
STATE_PATH = os.path.join(ROOT, "telegram", "hive_state.json")
TG = os.environ.get("TG_API", "https://api.telegram.org")
MAX_SEND = 3800
OWNER = "carlo"

# agent channels only; dm-* and human-* never cross
SKIP_CHANNEL = re.compile(r"^(dm-|human-)")


def display_of(slug: str) -> str:
    return " ".join(w.capitalize() for w in re.split(r"[-_.]+", slug or "?") if w)


def body_of(msg: dict) -> str:
    """The message text without the 'Name: ' the CLI writes in front."""
    text = (msg.get("text") or "").strip()
    name = display_of(msg.get("from", ""))
    if name and name != "?":
        text = re.sub(rf"^{re.escape(name)}\s*[:\u2014-]\s*", "", text, count=1, flags=re.I)
    return text


def format_line(msg: dict) -> str:
    """AGENT NAME — what they said. Pure, so the wording is pinned by tests."""
    line = f"{display_of(msg.get('from', '?'))} — {body_of(msg)}"
    if len(line) > MAX_SEND:
        line = line[: MAX_SEND - 1] + "…"
    return line


def should_relay(msg: dict, channel: str, relay_all: bool = False) -> bool:
    """Reports always. Other talk only with --all, and never from the humans."""
    if not msg or not msg.get("from"):
        return False
    channel = channel or ""
    if channel.startswith("dm-"):
        return False                     # a DM between agents is never a stage
    if (msg.get("from") or "").lower() == OWNER:
        return False
    if msg.get("type") == "report":
        return True                      # reports live on human-<owner>
    if channel.startswith("human-"):
        return False                     # the Director's own channel stays his
    if not relay_all:
        return False
    return msg.get("type") not in ("join", "leave", "vote", "dm")


def pick_chat(msg: dict, state: dict) -> str | None:
    """Reports go to the Director's private line; the rest to the group."""
    if msg.get("type") == "report":
        return (os.environ.get("TELEGRAM_DM_CHAT_ID")
                or str(state.get("dm_chat_id") or "") or None)
    return (os.environ.get("TELEGRAM_CHAT_ID")
            or str(state.get("chat_id") or "") or None)


def load_state() -> dict:
    try:
        with open(STATE_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, sort_keys=True)
        fh.write("\n")


def tg_send(token: str, chat_id, text: str) -> dict:
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text,
                                   "disable_web_page_preview": "true"}).encode()
    req = urllib.request.Request(f"{TG}/bot{token}/sendMessage", data=data)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def bus_messages() -> list[dict]:
    """Every bus line, tagged with its channel, newest last."""
    out = []
    for path in sorted(glob.glob(os.path.join(BUS, "*.jsonl"))):
        ch = os.path.basename(path)[:-6]
        try:
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        m = json.loads(line)
                    except Exception:
                        continue
                    m["_channel"] = ch
                    out.append(m)
        except OSError:
            continue
    out.sort(key=lambda m: (m.get("ts") or "", m.get("id") or ""))
    return out


def new_since(state: dict, msgs: list[dict]) -> list[dict]:
    last_ts = state.get("last_ts") or ""
    last_ids = set(state.get("last_ids") or [])
    out = []
    for m in msgs:
        ts = m.get("ts") or ""
        if ts > last_ts or (ts == last_ts and (m.get("id") or "") not in last_ids):
            out.append(m)
    return out


def advance(state: dict, sent: list[dict]) -> dict:
    if not sent:
        return state
    last_ts = sent[-1].get("ts") or ""
    state["last_ts"] = last_ts
    state["last_ids"] = [m.get("id") for m in sent if (m.get("ts") or "") == last_ts]
    return state


def cmd_relay(args) -> int:
    token = os.environ.get("TELEGRAM_HIVE_TOKEN", "").strip()
    state = load_state()
    msgs = bus_messages()
    if not token:
        print("hive: TELEGRAM_HIVE_TOKEN is not set — nothing sent (exit 0).")
        return 0

    if not state.get("last_ts"):
        # first run: prime on the current head instead of flooding the phone
        state = advance({"last_ids": []}, msgs[-1:])
        save_state(state)
        print("hive: primed at the current head — new reports will be relayed from now on.")
        return 0

    todo = [m for m in new_since(state, msgs)
            if should_relay(m, m.get("_channel", ""), args.all)]
    if args.dry_run:
        for m in todo:
            print(f"[dry-run] {pick_chat(m, state)} :: {format_line(m)}")
        return 0
    sent, failed = [], 0
    for m in todo:
        chat = pick_chat(m, state)
        if not chat:
            sent.append(m)          # nowhere to send it; do not replay forever
            continue
        try:
            tg_send(token, chat, format_line(m))
            sent.append(m)
            time.sleep(0.25)
        except Exception as e:      # noqa: BLE001
            failed += 1
            print(f"hive: send failed for {m.get('id')}: {type(e).__name__}: {e}",
                  file=sys.stderr)
    save_state(advance(state, sent))
    print(f"hive: relayed {len(sent)} message(s), {failed} failed.")
    return 0


def cmd_send(args) -> int:
    token = os.environ.get("TELEGRAM_HIVE_TOKEN", "").strip()
    if not token:
        print("hive: TELEGRAM_HIVE_TOKEN is not set — nothing sent (exit 0).")
        return 0
    state = load_state()
    chat = os.environ.get("TELEGRAM_DM_CHAT_ID") or state.get("dm_chat_id")
    if not chat:
        print("hive: no dm_chat_id in telegram/state.json — run the bridge once.")
        return 0
    tg_send(token, chat, " ".join(args.text))
    print("hive: sent.")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="hive", description="one bot, every voice")
    sub = p.add_subparsers(dest="cmd")
    r = sub.add_parser("relay", help="send what is new since the last run")
    r.add_argument("--all", action="store_true",
                   help="also mirror general talk to the group (reports always go)")
    r.add_argument("--dry-run", action="store_true")
    r.set_defaults(func=cmd_relay)
    s = sub.add_parser("send", help="send one line to the Director")
    s.add_argument("text", nargs="+")
    s.set_defaults(func=cmd_send)
    args = p.parse_args(argv)
    if not getattr(args, "func", None):
        p.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
