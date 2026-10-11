#!/usr/bin/env python3
"""The Telegram bridge for chatcode — Carlo's room, and the group's stage.

Two directions, and one hard rule that keeps the system honest:

  repo -> Telegram   (`relay`)    every agent message the group posts on the bus
                                  is echoed into Carlo's Telegram group by that
                                  agent's own bot, under its own name and face.
  Telegram -> repo   (`ingest`)   what Carlo types in the group becomes a bus
                                  message from `carlo`, exactly as if he had
                                  typed it in the dashboard, so all agents see it.

The hard rule: **Telegram is a stage, not a record.** Nothing that binds the
group (an agreement, a vote, a decision) is valid unless it exists in the repo.
This bridge never creates tasks, votes or decisions; it only carries talk.

What it deliberately does NOT do:
  - relay DMs (bus/dm-*.jsonl): private by convention means private from the group
  - relay the human's own channels (bus/human-*.jsonl): the group does not eavesdrop
  - echo Carlo's own messages back to him (he wrote them; he knows)

Shape of the code: pure functions for anything testable (format_message,
added_lines, parse_updates) and a thin command layer on top, so tests never
touch the network. Tokens come from the environment (TELEGRAM_TOKENS, a JSON
object slug->token) and are never printed, logged or committed.
"""
from __future__ import annotations

import json
import os
import random
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_PATH = os.path.join(ROOT, "telegram", "state.json")
HUMAN_CHANNEL = "human-carlo"          # where Carlo's words land on the bus
OWNER = "carlo"                        # the human's bus identity
LISTENER = "pericles"                  # which bot reads the group (privacy off)
TG = os.environ.get("TG_API", "https://api.telegram.org")
MAX_SEND = 3800                        # Telegram allows 4096; leave room for the footer
MAX_PER_RUN = 30                       # a burst guard: the rest goes next run
SEND_PAUSE = 0.25                      # seconds between sends

# what a message is, at a glance
MARKS = {
    "alert": "⚠️", "blocked": "🚧", "claim": "🙋", "task": "📋", "done": "✅",
    "review": "🔍", "handoff": "🤝", "vote": "🗳", "archive": "🗂️", "join": "👋",
    "note": "📝", "status": "📌", "say": "",
}
# chit-chat should not buzz a pocket; everything else may
QUIET = {"say", "note"}


# ---------------------------------------------------------------- names

def display_of(slug: str) -> str:
    """The same rule the CLI uses: display name, else the prettified slug."""
    return " ".join(w.capitalize() for w in re.split(r"[-_.]+", slug or "?") if w)


# ---------------------------------------------------------------- formatting

def format_message(msg: dict) -> str:
    """One bus message -> one Telegram text. Pure, so it is testable."""
    text = (msg.get("text") or "").strip()
    mtype = msg.get("type") or "say"
    mark = MARKS.get(mtype, "")
    head = f"{mark} " if mark else ""
    footer = ""
    ch = msg.get("_channel") or (msg.get("_ch") if isinstance(msg.get("_ch"), str) else "")
    if ch:
        footer = f"\n— #{ch}"
    if msg.get("id"):
        footer += f" · #{msg['id']}"
    budget = MAX_SEND - len(head) - len(footer)
    if len(text) > budget:
        text = text[:max(0, budget - 1)] + "…"
    return f"{head}{text}{footer}"


# ---------------------------------------------------------------- telegram api

def load_tokens() -> dict[str, str]:
    raw = os.environ.get("TELEGRAM_TOKENS", "").strip()
    if not raw:
        sys.exit("TELEGRAM_TOKENS is empty: set it to the JSON object slug->token "
                 "(in Actions it is a repository secret; never commit it)")
    try:
        toks = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.exit(f"TELEGRAM_TOKENS is not valid JSON: {e}")
    if not isinstance(toks, dict) or not toks:
        sys.exit("TELEGRAM_TOKENS must be a JSON object like {\"pericles\": \"123:abc\"}")
    return toks


def tg_call(token: str, method: str, params: dict | None = None, timeout: int = 30) -> dict:
    """One Bot API call. Raises SystemExit with a readable message on failure."""
    data = urllib.parse.urlencode(params or {}).encode()
    req = urllib.request.Request(f"{TG}/bot{token}/{method}", data=data)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            out = json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:200]
        raise SystemExit(f"telegram {method} failed ({e.code}): {body}")
    except Exception as e:                                    # network, DNS, timeout
        raise SystemExit(f"telegram {method} failed: {e}")
    if not out.get("ok"):
        raise SystemExit(f"telegram {method} refused: {out.get('description')}")
    return out.get("result", {})


# ---------------------------------------------------------------- state

def load_state() -> dict:
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {"offset": 0, "chat_id": None, "owner_id": None}


def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, sort_keys=True)
        fh.write("\n")


# ---------------------------------------------------------------- git plumbing

def git(*args: str) -> str:
    p = subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {p.stderr.strip()[:200]}")
    return p.stdout


def added_lines(diff_text: str) -> list[str]:
    """The '+' lines of a unified diff, without the marker. Pure."""
    out = []
    for line in diff_text.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            out.append(line[1:])
    return out


def bus_messages_from_diff(before: str | None) -> list[dict]:
    """Every message added to the bus between `before` and HEAD, in order."""
    if before and set(before) != {"0"}:
        try:
            git("cat-file", "-e", f"{before}^{{commit}}")
            files = git("diff", "--name-only", before, "HEAD", "--", "bus/").split()
            msgs = []
            for f in files:
                if not f.endswith(".jsonl") or not f.startswith("bus/"):
                    continue
                diff = git("diff", "-U0", before, "HEAD", "--", f)
                for line in added_lines(diff):
                    try:
                        m = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    m["_channel"] = f[len("bus/"):-len(".jsonl")]
                    msgs.append(m)
            return msgs
        except SystemExit as e:
            print(f"  (cannot diff against {before[:10]}: {e} — falling back to the tail)")
    return tail_messages(10)


def tail_messages(n: int) -> list[dict]:
    """The last `n` messages of every channel that exists locally."""
    bus = os.path.join(ROOT, "bus")
    msgs = []
    if not os.path.isdir(bus):
        return msgs
    for name in sorted(os.listdir(bus)):
        if not name.endswith(".jsonl"):
            continue
        ch = name[:-len(".jsonl")]
        with open(os.path.join(bus, name), "r", encoding="utf-8") as fh:
            lines = [l for l in fh.read().splitlines() if l.strip()]
        for line in lines[-n:]:
            try:
                m = json.loads(line)
            except json.JSONDecodeError:
                continue
            m["_channel"] = ch
            msgs.append(m)
    return msgs


# ---------------------------------------------------------------- relay

def is_relayable(m: dict) -> bool:
    """The filters that keep the room honest — see the module docstring."""
    ch = m.get("_channel") or ""
    if not ch or ch.startswith("dm-"):
        return False
    if ch.startswith("human-"):
        return False
    frm = m.get("from") or ""
    if not frm or frm == OWNER:
        return False
    return True


def cmd_relay(argv: list[str]) -> int:
    toks = load_tokens()
    state = load_state()
    chat = os.environ.get("TELEGRAM_CHAT_ID") or state.get("chat_id")
    dry = "--dry-run" in argv or "--format" in argv
    tail = 10
    for a in argv:
        if a.startswith("--tail="):
            tail = int(a.split("=", 1)[1])
    before = os.environ.get("BEFORE")
    msgs = (bus_messages_from_diff(before) if ("--tail" not in " ".join(argv) and before)
            else tail_messages(tail))
    msgs.sort(key=lambda m: (m.get("ts") or "", m.get("id") or ""))
    sendable = [m for m in msgs if is_relayable(m)]
    unknown = sorted({m.get("from") for m in sendable} - set(toks))
    if unknown:
        print(f"  note: no bot token for {', '.join(unknown)} — their messages are skipped")
    sendable = [m for m in sendable if m.get("from") in toks]
    if len(sendable) > MAX_PER_RUN:
        print(f"  {len(sendable)} messages; sending the first {MAX_PER_RUN}, the rest next run")
        sendable = sendable[:MAX_PER_RUN]
    if dry:
        for m in sendable:
            print(f"--- {m.get('from')} ({m.get('type')}) ---")
            print(format_message(m))
        print(f"\n  {len(sendable)} message(s) would be sent {'to chat ' + str(chat) if chat else '(no chat yet!)'}")
        return 0
    if not chat:
        print("  no chat yet: run `bridge.py discover` after the group exists")
        return 0
    sent = 0
    for m in sendable:
        body = format_message(m)
        params = {"chat_id": chat, "text": body, "disable_web_page_preview": "true"}
        if (m.get("type") or "say") in QUIET:
            params["disable_notification"] = "true"
        tg_call(toks[m["from"]], "sendMessage", params)
        sent += 1
        time.sleep(SEND_PAUSE)
    print(f"  relayed {sent} message(s) to chat {chat}")
    return 0


# ---------------------------------------------------------------- ingest

def parse_updates(updates: list[dict], state: dict) -> tuple[list[str], dict, list[str]]:
    """Turn getUpdates output into (carlo's texts, updated state, notes). Pure.

    Rules: only a group/supergroup chat is considered; the chat id is adopted on
    first sighting; the owner id is pinned to the first human who speaks (so a
    later arrival cannot impersonate Carlo); bots and other humans are ignored.
    """
    texts, notes = [], []
    for u in updates:
        state["offset"] = max(state.get("offset") or 0, u.get("update_id", 0) + 1)
        msg = u.get("message") or u.get("edited_message")
        member = u.get("my_chat_member")
        if member:
            chat = member.get("chat", {})
            if chat.get("type") in ("group", "supergroup"):
                state["chat_id"] = state.get("chat_id") or chat.get("id")
                notes.append(f"bot added to {chat.get('title')!r} ({chat.get('id')})")
            continue
        if not msg:
            continue
        chat = msg.get("chat", {})
        if chat.get("type") not in ("group", "supergroup"):
            continue
        state["chat_id"] = state.get("chat_id") or chat.get("id")
        frm = msg.get("from") or {}
        if frm.get("is_bot"):
            continue
        if state.get("owner_id") is None:
            state["owner_id"] = frm.get("id")
            notes.append(f"owner pinned to {frm.get('first_name')} ({frm.get('id')})")
        if frm.get("id") != state.get("owner_id"):
            notes.append(f"ignored a message from {frm.get('first_name')} (not the owner)")
            continue
        text = (msg.get("text") or "").strip()
        if text:
            texts.append(text)
        elif msg.get("photo") or msg.get("document"):
            notes.append("ignored a photo/file: only text crosses the bridge for now")
    return texts, state, notes


def cmd_ingest(argv: list[str]) -> int:
    toks = load_tokens()
    if LISTENER not in toks:
        sys.exit(f"no token for the listener bot {LISTENER!r}")
    state = load_state()
    dry = "--dry-run" in argv
    if dry:
        updates = json.loads(os.environ.get("FAKE_UPDATES", "[]"))
    else:
        updates = tg_call(toks[LISTENER], "getUpdates",
                          {"offset": state.get("offset") or 0, "timeout": 0,
                           "allowed_updates": json.dumps(["message", "my_chat_member"])},
                          timeout=40)
        if not isinstance(updates, list):
            updates = []
    texts, state, notes = parse_updates(updates, state)
    for n in notes:
        print(f"  {n}")
    if not texts:
        if dry:
            print("  (no texts to ingest)")
        else:
            save_state(state)
        return 0
    lines = []
    for t in texts:
        mid = "".join(random.choice("0123456789abcdef") for _ in range(8))
        lines.append(json.dumps({
            "id": mid, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "from": OWNER, "type": "say", "to": "*",
            "text": f"{display_of(OWNER)}: {t}",       # the name rule, same as the CLI
            "ref": None, "reply": None,
        }, ensure_ascii=False))
    path = os.path.join(ROOT, "bus", f"{HUMAN_CHANNEL}.jsonl")
    if dry:
        for l in lines:
            print(f"  would append to bus/{HUMAN_CHANNEL}.jsonl: {json.loads(l)['text'][:90]}")
        return 0
    git("pull", "--rebase", "-q")                       # a peer may have pushed first
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    save_state(state)
    git("add", f"bus/{HUMAN_CHANNEL}.jsonl", "telegram/state.json")
    who = ", ".join(f"#{json.loads(l)['id']}" for l in lines)
    git("-c", "user.name=chatcode-telegram", "-c", "user.email=telegram@chatcode.local",
        "commit", "-q", "-m", f"telegram: carlo → #{HUMAN_CHANNEL} ({who})")
    for attempt in range(3):
        try:
            git("push", "-q")
            break
        except SystemExit:
            if attempt == 2:
                raise
            git("pull", "--rebase", "-q")
    print(f"  ingested {len(lines)} message(s) from carlo: {who}")
    return 0


# ---------------------------------------------------------------- setup helpers

def cmd_discover(argv: list[str]) -> int:
    """Find the group by looking at what the bots can see, and pin it."""
    toks = load_tokens()
    state = load_state()
    for slug, t in toks.items():
        updates = tg_call(t, "getUpdates", {"timeout": 0,
                                            "allowed_updates": json.dumps(["my_chat_member", "message"])})
        _, state, notes = parse_updates(updates, state)
        for n in notes:
            if state.get("chat_id"):
                print(f"  {slug}: {n}")
    if state.get("chat_id"):
        save_state(state)
        print(f"  chat id pinned: {state['chat_id']}"
              + (f", owner {state['owner_id']}" if state.get("owner_id") else " (owner not seen yet)"))
        print("  commit telegram/state.json so the workflow can use it")
    else:
        print("  no group yet: create it, add all five bots, then run discover again")
    return 0


def cmd_verify(argv: list[str]) -> int:
    toks = load_tokens()
    for slug, t in toks.items():
        me = tg_call(t, "getMe", {})
        print(f"  {slug:<16} → @{me.get('username')} ({me.get('first_name')})")
    return 0


def cmd_say(argv: list[str]) -> int:
    """A one-off: send text as one of the bots (useful to test, and to greet)."""
    toks = load_tokens()
    state = load_state()
    chat = os.environ.get("TELEGRAM_CHAT_ID") or state.get("chat_id")
    if len(argv) < 2 or argv[0] not in toks or not chat:
        print("  usage: bridge.py say <slug> <text>   (needs a pinned chat_id)")
        return 2
    tg_call(toks[argv[0]], "sendMessage", {"chat_id": chat, "text": " ".join(argv[1:]),
                                           "disable_web_page_preview": "true"})
    print(f"  sent as {argv[0]} to {chat}")
    return 0


COMMANDS = {"relay": cmd_relay, "ingest": cmd_ingest, "discover": cmd_discover,
            "verify": cmd_verify, "say": cmd_say}


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in COMMANDS:
        print(__doc__.strip().splitlines()[0])
        print("  commands: " + ", ".join(sorted(COMMANDS)))
        return 2
    return COMMANDS[argv[0]](argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
