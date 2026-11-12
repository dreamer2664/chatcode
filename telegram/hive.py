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

Two bots, two jobs:
  @agency077_bot        the crew's general line (group / channel)
  @collectivedms077_bot the Director's private line (reports land here)

Env:
  TELEGRAM_HIVE_TOKEN   the general bot's token (repo secret; never committed)
  TELEGRAM_DM_TOKEN     the DM bot's token (falls back to the general token)
  TELEGRAM_CHAT_ID      the group chat id (auto-discovered when the bot is added)
  TELEGRAM_DM_CHAT_ID   the Director's private chat id (auto-discovered on /start)

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


def tokens() -> tuple[str, str]:
    """(general, dm). One token is enough; two keeps the King's line private."""
    general = os.environ.get("TELEGRAM_HIVE_TOKEN", "").strip()
    dm = os.environ.get("TELEGRAM_DM_TOKEN", "").strip() or general
    return general, dm


def pick_target(msg: dict, state: dict) -> tuple[str, str | None]:
    """Reports go to the Director's private line; everything else to the crew."""
    if msg.get("type") == "report":
        chat = os.environ.get("TELEGRAM_DM_CHAT_ID") or state.get("dm_chat_id")
        return "dm", (str(chat) if chat else None)
    chat = os.environ.get("TELEGRAM_CHAT_ID") or state.get("chat_id")
    return "group", (str(chat) if chat else None)


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


def tg_call(token: str, method: str, params: dict | None = None) -> dict:
    data = urllib.parse.urlencode(params or {}).encode()
    req = urllib.request.Request(f"{TG}/bot{token}/{method}", data=data)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def _chat_of(update: dict) -> dict:
    """Any chat mentioned by any kind of update (message, join, channel post)."""
    for v in update.values():
        if isinstance(v, dict):
            c = v.get("chat")
            if isinstance(c, dict) and c.get("id") is not None:
                return c
    return {}


def discover(general: str, dm: str, state: dict) -> dict:
    """Learn the chat ids from the bots themselves: add the bot / press Start."""
    notes = []
    for kind, tok in (("group", general), ("dm", dm)):
        if not tok:
            continue
        try:
            data = tg_call(tok, "getUpdates", {"limit": 50, "timeout": 0})
        except Exception as e:                              # noqa: BLE001
            notes.append(f"{kind}: getUpdates failed ({type(e).__name__})")
            continue
        for u in data.get("result", []):
            c = _chat_of(u)
            if not c:
                continue
            if c.get("type") == "private" and kind == "dm":
                state["dm_chat_id"] = c["id"]
                state["dm_name"] = c.get("first_name") or c.get("username") or ""
            elif c.get("type") in ("group", "supergroup", "channel"):
                state["chat_id"] = c["id"]
                state["chat_title"] = c.get("title") or ""
        try:
            me = tg_call(tok, "getMe", {})["result"]
            state[f"{kind}_bot"] = me.get("username", "")
        except Exception:
            pass
    if not state.get("dm_chat_id"):
        notes.append(f"DM not started — open https://t.me/{state.get('dm_bot') or 'collectivedms077_bot'} "
                     "and press Start")
    if not state.get("chat_id"):
        notes.append(f"no group yet — add @{state.get('group_bot') or 'agency077_bot'} "
                     "to the crew group and send one message")
    for n in notes:
        print(f"hive: {n}")
    return state


def cmd_relay(args) -> int:
    general, dm = tokens()
    state = load_state()
    if not general and not dm:
        print("hive: no bot token set — nothing sent (exit 0).")
        return 0
    if not args.no_discover:
        state = discover(general, dm, state)
        save_state(state)

    msgs = bus_messages()
    if not state.get("last_ts"):
        # first run: prime on the current head instead of flooding the phone
        state = advance(state, msgs[-1:])
        save_state(state)
        print("hive: primed at the current head — new reports will be relayed from now on.")
        return 0

    todo = [m for m in new_since(state, msgs)
            if should_relay(m, m.get("_channel", ""), args.all)]
    if args.dry_run:
        for m in todo:
            kind, chat = pick_target(m, state)
            print(f"[dry-run] {kind} {chat} :: {format_line(m)}")
        return 0

    sent, failed = [], 0
    for m in todo:
        kind, chat = pick_target(m, state)
        tok = dm if kind == "dm" else general
        if not chat and kind == "dm":
            # never lose the King's message: fall back to the crew line if there is one
            kind, chat = "group", state.get("chat_id")
            tok = general
        if not chat:
            print(f"hive: no place to send {m.get('id')} (no chat id yet) — holding it.",
                  file=sys.stderr)
            break                      # stop here so nothing is silently skipped
        try:
            tg_call(tok, "sendMessage", {
                "chat_id": chat, "text": format_line(m),
                "disable_web_page_preview": "true"})
            sent.append(m)
            time.sleep(0.25)
        except Exception as e:         # noqa: BLE001
            failed += 1
            print(f"hive: send failed for {m.get('id')}: {type(e).__name__}: {e}",
                  file=sys.stderr)
            break                      # retry from this point next run; nothing lost
    save_state(advance(state, sent))
    print(f"hive: relayed {len(sent)} message(s), {failed} failed.")
    return 0


def cmd_send(args) -> int:
    general, dm = tokens()
    token = dm or general
    if not token:
        print("hive: no bot token set — nothing sent (exit 0).")
        return 0
    state = load_state()
    chat = os.environ.get("TELEGRAM_DM_CHAT_ID") or state.get("dm_chat_id")
    if not chat:
        state = discover(general, dm, state)
        save_state(state)
        chat = state.get("dm_chat_id")
    if not chat:
        print("hive: the Director has not started the DM bot yet — nothing sent.")
        return 0
    tg_call(token, "sendMessage", {"chat_id": chat, "text": " ".join(args.text),
                                   "disable_web_page_preview": "true"})
    print("hive: sent.")
    return 0


def cmd_discover(args) -> int:
    general, dm = tokens()
    state = discover(general, dm, load_state())
    save_state(state)
    print(json.dumps({k: state.get(k) for k in
                      ("group_bot", "dm_bot", "chat_id", "chat_title",
                       "dm_chat_id", "dm_name")}, indent=2))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="hive", description="one bot, every voice")
    sub = p.add_subparsers(dest="cmd")
    r = sub.add_parser("relay", help="send what is new since the last run")
    r.add_argument("--all", action="store_true",
                   help="also mirror general talk to the group (reports always go)")
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("--no-discover", action="store_true",
                   help="skip learning chat ids from the bots this run")
    r.set_defaults(func=cmd_relay)
    d = sub.add_parser("discover", help="learn the chat ids (add the bot / press Start)")
    d.set_defaults(func=cmd_discover)
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
