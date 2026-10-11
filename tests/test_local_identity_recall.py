#!/usr/bin/env python3
"""t-20261011-3207 — a --local session remembers its agent.

DEFECT (on current main, found while reviewing #11 / t-ad9e): a local sandbox
writes agents/<name>.json and nothing else that says "this is you". Ctx
resolves the agent as --agent or CHATCODE_AGENT or the GLOBAL config, and
nothing reads the local roster, so:

    chatcode --local R --agent nobody init --quiet
    chatcode --local R whoami            ->  agent: null   (roster has nobody.json)

and worse, a global config on the machine wrongly WINS over the sandbox:

    HOME with {"agent": "globalguy"}, local roster = [nobody]
    chatcode --local R whoami            ->  agent: "globalguy"   (wrong sandbox)

FIX under test: in --local mode, when neither --agent nor CHATCODE_AGENT is
set and the local roster holds EXACTLY ONE agent, use that name. Zero or
several entries stay silent (no guessing). Precedence:
    --agent/--name  >  CHATCODE_AGENT  >  local single-entry roster  >  global

One command, runnable by any agent from the repo root:

    python3 tests/test_local_identity_recall.py

Exits 0 when the fix is in place; exits 1 with a clear report on the old CLI.
Stdlib only, HOME redirected per case, no network, throwaway --local repos.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CLI = os.path.normpath(os.path.join(HERE, "..", "bin", "chatcode"))
LEAKY = ("CHATCODE_AGENT", "CHATCODE_CHANNEL", "CHATCODE_REPO",
         "CHATCODE_BRANCH", "CHATCODE_TOKEN", "GITHUB_TOKEN")


def run(home, argv, cwd=None):
    env = {k: v for k, v in os.environ.items() if k not in LEAKY}
    env["HOME"] = home
    cmd = [sys.executable, CLI] + argv
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                          env=env, cwd=cwd or home)


def whoami_agent(home, argv, cwd=None):
    """Run `whoami`, return the agent field (None if unset, 'ERR:...' on crash)."""
    p = run(home, argv + ["whoami"], cwd=cwd)
    if p.returncode != 0:
        return f"ERR:rc={p.returncode}:{p.stderr.strip().splitlines()[-1:] }"
    try:
        return json.loads(p.stdout)["agent"]
    except Exception:
        return f"ERR:unparseable:{p.stdout[:80]!r}"


def make_local_repo(agents):
    root = tempfile.mkdtemp(prefix="cc-localid-")
    os.makedirs(os.path.join(root, "agents"))
    for name in agents:
        with open(os.path.join(root, "agents", f"{name}.json"), "w") as fh:
            json.dump({"name": name, "kind": "ai", "role": "worker",
                       "status": "active"}, fh)
    return root


def write_global(home, agent):
    d = os.path.join(home, ".chatcode")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "config.json"), "w") as fh:
        json.dump({"agent": agent}, fh)


def main():
    if not os.path.exists(CLI):
        print(f"FAIL: cannot find CLI at {CLI}")
        return 1
    failures = []
    homes, roots = [], []
    try:
        # case 1 (RED on main): init --agent nobody, then recall without any flag
        h = tempfile.mkdtemp(prefix="cc-home-"); homes.append(h)
        r = tempfile.mkdtemp(prefix="cc-root-"); shutil.rmtree(r); roots.append(r)
        p = run(h, ["--local", r, "--agent", "nobody", "init", "--quiet"])
        if p.returncode != 0:
            failures.append(f"case1: local init failed rc={p.returncode}: {p.stderr[-120:]}")
        got = whoami_agent(h, ["--local", r])
        if got != "nobody":
            failures.append(
                f"case1: local session did not remember its agent (got {got!r}, "
                "want 'nobody' from the local roster)")

        # case 2: two agents in the local roster -> no guessing
        h = tempfile.mkdtemp(prefix="cc-home-"); homes.append(h)
        r = tempfile.mkdtemp(prefix="cc-root-"); shutil.rmtree(r); roots.append(r)
        for who in ("nobody", "other"):
            run(h, ["--local", r, "--agent", who, "init", "--quiet"])
        got = whoami_agent(h, ["--local", r])
        if got is not None:
            failures.append(f"case2: two-entry roster guessed {got!r}; must stay null")

        # case 3: an explicit --agent still wins over the roster
        got = whoami_agent(h, ["--local", r, "--agent", "alice"])
        if got != "alice":
            failures.append(f"case3: --agent overridden by roster (got {got!r}, want 'alice')")

        # case 4: CHATCODE_AGENT still wins over the roster
        env = {k: v for k, v in os.environ.items() if k not in LEAKY}
        env.update(HOME=h, CHATCODE_AGENT="envguy")
        p = subprocess.run([sys.executable, CLI, "--local", r, "whoami"],
                           capture_output=True, text=True, timeout=60, env=env)
        try:
            got = json.loads(p.stdout)["agent"]
        except Exception:
            got = f"ERR:{p.stdout[:60]!r}"
        if got != "envguy":
            failures.append(f"case4: CHATCODE_AGENT overridden by roster (got {got!r})")

        # case 5 (RED on main): the sandbox roster beats a global config
        h = tempfile.mkdtemp(prefix="cc-home-"); homes.append(h)
        r = make_local_repo(["nobody"]); roots.append(r)
        write_global(h, "globalguy")
        got = whoami_agent(h, ["--local", r])
        if got != "nobody":
            failures.append(
                f"case5: global config won inside --local (got {got!r}, want 'nobody' "
                "from the sandbox roster)")

        # case 6: outside --local nothing changes — global config still applies
        got = whoami_agent(h, [])
        if got != "globalguy":
            failures.append(f"case6: non-local resolution changed (got {got!r}, want 'globalguy')")

        if failures:
            print("FAIL: --local sessions do not remember their agent")
            for f in failures:
                print(f"  - {f}")
            return 1
        print("OK: local identity recall — single-entry roster remembered, "
              "two entries stay silent, flag/env still win, non-local untouched "
              "(6 cases)")
        return 0
    finally:
        for d in homes + roots:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
