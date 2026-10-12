#!/usr/bin/env python3
"""keys_ask.py — the registered key-use wrapper (room decision t-ef72).

Every helper call to the Gemini API goes through here:

  1. reads YOUR private keys   (default ~/.gemini_keys.txt, one per line)
  2. rotates keys and models   (429/503 -> next key; 404 -> next model)
  3. registers the call        (fingerprints only, never the key) into
     keys/usage/<agent>.jsonl and best-effort pushes it so the whole floor
     can check: keys/USAGE.md or `python3 tools/keys_usage.py`
  4. enforces a daily cap      (keys/budget.json; default 300 calls/day)

Usage:
  python3 tools/keys_ask.py "explain this traceback: ..."
  python3 tools/keys_ask.py --image data/pic.png "what does this image say"
  python3 tools/keys_ask.py --usage

Rules: keys never appear on the bus/repo/logs; helper use only (Iris belongs
to the lead); if it is not through this wrapper, it is not registered.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = ("https://generativelanguage.googleapis.com/v1beta/models/"
       "{model}:generateContent")
MODEL_CHAIN = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash",
               "gemini-3.5-flash", "gemini-3.1-flash-lite",
               "gemini-3-flash-preview"]
THINKING_OK = {"gemini-3.6-flash", "gemini-3.5-flash",
               "gemini-3.1-flash-lite", "gemini-3-flash-preview"}
PACE_S = 1.2
WT = Path.home() / ".keys-usage-wt"     # small clean worktree for safe pushes


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def fp(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:12]


def load_keys(path: Path):
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def normalize(name: str) -> str:
    return name.strip().lower().replace(" ", "-")


def agent_name(args) -> str:
    if getattr(args, "agent", None):
        return normalize(args.agent)
    env = os.environ.get("CHATCODE_AGENT")
    if env:
        return normalize(env)
    try:
        r = subprocess.run(["git", "-C", str(ROOT), "config", "user.name"],
                           capture_output=True, text=True, timeout=10)
        if r.stdout.strip():
            return normalize(r.stdout)
    except Exception:
        pass
    return "unknown"


def usage_path(agent: str) -> Path:
    return ROOT / "keys" / "usage" / f"{agent}.jsonl"


def log_line(agent: str, rec: dict) -> None:
    f = usage_path(agent)
    f.parent.mkdir(parents=True, exist_ok=True)
    with open(f, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def used_today(agent: str) -> int:
    f = usage_path(agent)
    if not f.exists():
        return 0
    n = 0
    for line in f.read_text(encoding="utf-8").splitlines():
        try:
            if json.loads(line).get("ts", "").startswith(today()):
                n += 1
        except Exception:
            pass
    return n


def cap_for(agent: str) -> int:
    cap = 300
    try:
        b = json.loads((ROOT / "keys" / "budget.json").read_text())
        cap = int(b.get("per_agent", {}).get(agent, b.get("default_per_day", 300)))
    except Exception:
        pass
    env = os.environ.get("KEYS_ASK_CAP")
    if env:
        cap = int(env)
    return cap


def ensure_wt() -> bool:
    if (WT / ".git").exists():
        return True
    try:
        subprocess.run(["git", "-C", str(ROOT), "fetch", "-q", "origin"],
                       capture_output=True, timeout=90)
        subprocess.run(["git", "-C", str(ROOT), "worktree", "add", "--detach",
                        str(WT), "origin/main"], capture_output=True,
                       text=True, timeout=120)
    except Exception:
        pass
    return (WT / ".git").exists()


def push_usage(agent: str) -> str:
    """Push the agent's usage file from a dedicated clean worktree.

    Never pushes the caller's own branch: a separate worktree (pinned to
    origin/main) carries ONLY the usage lines."""
    if not ensure_wt():
        return "no push (no git checkout here; usage stays local)"
    w = str(WT)
    src = usage_path(agent)
    dst = WT / "keys" / "usage" / f"{agent}.jsonl"
    for _ in range(4):
        subprocess.run(["git", "-C", w, "fetch", "-q", "origin"],
                       capture_output=True, timeout=90)
        subprocess.run(["git", "-C", w, "checkout", "-q", "--detach",
                        "origin/main"], capture_output=True, timeout=60)
        have = set()
        if dst.exists():
            have = set(dst.read_text(encoding="utf-8").splitlines())
        missing = []
        if src.exists():
            for ln in src.read_text(encoding="utf-8").splitlines():
                if ln.strip() and ln not in have:
                    missing.append(ln)
        if missing:
            dst.parent.mkdir(parents=True, exist_ok=True)
            with open(dst, "a", encoding="utf-8") as fh:
                for ln in missing:
                    fh.write(ln + "\n")
            subprocess.run(["git", "-C", w, "add",
                            f"keys/usage/{agent}.jsonl"], capture_output=True)
            subprocess.run(["git", "-C", w, "-c", f"user.name={agent}",
                            "-c", f"user.email={agent}@chatcode.local",
                            "commit", "-q", "-m", f"usage: {agent}"],
                           capture_output=True, timeout=60)
        r = subprocess.run(["git", "-C", w, "push", "-q", "origin", "HEAD:main"],
                           capture_output=True, text=True, timeout=90)
        if r.returncode == 0:
            return "pushed"
        time.sleep(1.5)
    return "push pending (will retry next call)"


def call_api(model: str, key: str, parts: list, timeout: int = 40):
    gc = {"temperature": 0.0}
    if model in THINKING_OK:
        gc["thinkingConfig"] = {"thinkingBudget": 0}
    body = json.dumps({"contents": [{"parts": parts}],
                       "generationConfig": gc}).encode()
    url = API.format(model=model) + f"?key={key}"
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        out = json.load(r)
    return out["candidates"][0]["content"]["parts"][0].get("text", "")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt", nargs="*")
    ap.add_argument("--image")
    ap.add_argument("--agent")
    ap.add_argument("--model")
    ap.add_argument("--keys-file", default=os.environ.get(
        "GEMINI_KEYS_FILE", str(Path.home() / ".gemini_keys.txt")))
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--usage", action="store_true")
    a = ap.parse_args()

    if a.usage:
        return subprocess.run([sys.executable, str(ROOT / "tools" /
                                                  "keys_usage.py")]).returncode

    have = used_today(agent_name(a))
    cap = cap_for(agent_name(a))
    if have >= cap and not os.environ.get("KEYS_ASK_IGNORE_CAP"):
        print(f"keys_ask: daily cap reached ({have}/{cap}) - keys/budget.json; "
              "ask the lead to raise it.", file=sys.stderr)
        return 3

    keys = load_keys(Path(a.keys_file))
    if not keys:
        print(f"keys_ask: no keys found in {a.keys_file} - save your 5 keys "
              "there (one per line), then retry.", file=sys.stderr)
        return 2

    text = " ".join(a.prompt).strip()
    if not text and not a.image:
        print("keys_ask: nothing to ask (pass a prompt and/or --image)",
              file=sys.stderr)
        return 2
    parts = []
    if text:
        parts.append({"text": text})
    if a.image:
        blob = Path(a.image).read_bytes()
        ext = Path(a.image).suffix.lower().lstrip(".") or "png"
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                "webp": "image/webp"}.get(ext, f"image/{ext}")
        parts.append({"inline_data": {"mime_type": mime,
                                      "data": base64.b64encode(blob).decode()}})

    agent = agent_name(a)
    chain = [a.model] if a.model else MODEL_CHAIN
    dead = set()
    errors = []
    for model in chain:
        for key in keys:
            if key in dead:
                continue
            t0 = time.time()
            try:
                out = call_api(model, key, parts)
                log_line(agent, {"ts": now_iso(), "agent": agent,
                                 "key_fp": fp(key), "model": model, "ok": True,
                                 "ms": int((time.time() - t0) * 1000),
                                 "chars": len(out), "kind": "helper"})
                status = push_usage(agent) if not a.no_push else "local only"
                print(out)
                print(f"[keys_ask: {agent} · {model} · {status}]", file=sys.stderr)
                return 0
            except urllib.error.HTTPError as e:
                code = e.code
                msg = e.read().decode("utf-8", "replace")[:160]
                errors.append(f"[{model}] HTTP {code}: {msg}")
                if code in (401, 403):
                    dead.add(key)
                elif code == 404:
                    break
                log_line(agent, {"ts": now_iso(), "agent": agent,
                                 "key_fp": fp(key), "model": model, "ok": False,
                                 "ms": int((time.time() - t0) * 1000),
                                 "err": f"HTTP {code}", "kind": "helper"})
            except Exception as e:
                errors.append(f"[{model}] {type(e).__name__}: {e}")
                log_line(agent, {"ts": now_iso(), "agent": agent,
                                 "key_fp": fp(key), "model": model, "ok": False,
                                 "ms": int((time.time() - t0) * 1000),
                                 "err": type(e).__name__, "kind": "helper"})
            time.sleep(PACE_S)
    print("keys_ask: every key/model failed.", file=sys.stderr)
    for e in errors[-6:]:
        print("  " + e, file=sys.stderr)
    status = push_usage(agent) if not a.no_push else "local only"
    return 1


if __name__ == "__main__":
    sys.exit(main())
