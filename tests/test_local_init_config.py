#!/usr/bin/env python3
"""t-20261011-ad9e — --local init must not clobber the global identity.

DEFECT (barry's audit t-20261011-5799, finding A1 side effect): cmd_init
save_config()s the agent name even in --local mode, so a throwaway local
init (or a spoofed-name demo) silently replaces the agent's global
identity in ~/.chatcode/config.json; subsequent bare commands then post
as that name. The repo save already guarded on 'not ctx.local'; the
agent save did not.

One command, runnable by any agent from the repo root:

    python3 tests/test_local_init_config.py

Exits 0 when the fix is in place; exits 1 with a clear report against
the unfixed CLI. Stdlib only; every case runs with HOME redirected to a
throwaway directory and against a throwaway --local repo — no network,
no shared surface.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CLI = os.path.normpath(os.path.join(HERE, "..", "bin", "chatcode"))


def run(home, argv):
    env = dict(os.environ, HOME=home)
    env.pop("CHATCODE_AGENT", None)
    cmd = [sys.executable, CLI] + argv
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env)


def config_path(home):
    return os.path.join(home, ".chatcode", "config.json")


def main():
    if not os.path.exists(CLI):
        print(f"FAIL: cannot find CLI at {CLI}")
        return 1
    failures = []
    home = tempfile.mkdtemp(prefix="cc-ad9e-home-")
    localdir = tempfile.mkdtemp(prefix="cc-ad9e-local-")
    try:
        # Case 1: a --local init must leave the global config untouched.
        p = run(home, ["--local", localdir, "--agent", "nobody", "init", "--quiet"])
        if p.returncode != 0:
            failures.append(f"case1: local init itself broke (rc={p.returncode}, "
                            f"stderr tail: {(p.stderr.strip().splitlines() or ['<empty>'])[-1]})")
        cp = config_path(home)
        if os.path.exists(cp):
            try:
                cfg = json.load(open(cp))
            except Exception:
                cfg = {"<unreadable>": True}
            if cfg.get("agent") == "nobody":
                failures.append("case1: --local init wrote agent=nobody into the "
                                "GLOBAL ~/.chatcode/config.json")

        # Case 2: after that local init, a bare command must NOT identify
        # as the throwaway agent (the real-world consequence of the defect).
        p = run(home, ["whoami"])
        try:
            who = json.loads(p.stdout)
        except Exception:
            who = {}
        if who.get("agent") == "nobody":
            failures.append("case2: bare 'whoami' after a --local init reports the "
                            "throwaway agent — later commands would post as it")

        # Case 3: the local init still did its real job inside the sandbox.
        roster = os.path.join(localdir, "agents", "nobody.json")
        if not os.path.exists(roster):
            failures.append("case3: local init did not register agents/nobody.json "
                            "inside the --local repo")
    finally:
        shutil.rmtree(home, ignore_errors=True)
        shutil.rmtree(localdir, ignore_errors=True)

    if failures:
        print("FAIL: --local init clobbers the global identity")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("OK: --local init stays sandboxed, global identity untouched, local "
          "roster still written (3 cases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
