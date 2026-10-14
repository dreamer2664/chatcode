#!/usr/bin/env python3
"""The record wire: every push and PR must land on formalcode — offline.

The pipeline's promise is "everything that happens goes to formalcode".
That promise is one workflow file and one composer script
(.github/workflows/record.yml). This test pins both, offline:

  1. record.yml parses, has the right triggers, and posts to the
     https://ntfy.sh/formalcode topic (no secrets, no token);
  2. the composer python (extracted from the workflow verbatim) turns
     GitHub event payloads into the exact record lines — and returns the
     skip code for housekeeping pushes ([skip ci], the superocr mirror,
     the storagecode wire archive) so the formal record stays a record
     and not a cron log;
  3. tools/new_project.py scaffolds new repos with a caller that points
     record.yml at chatcode@main, refuses the red-line repos, and
     --dry-run touches nothing.

    python3 tests/test_record_wire.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WORKFLOW = os.path.join(ROOT, ".github", "workflows", "record.yml")
NEW_PROJECT = os.path.join(ROOT, "tools", "new_project.py")

failures: list[str] = []


def check(cond: bool, what: str) -> None:
    print(("ok   " if cond else "FAIL ") + what)
    if not cond:
        failures.append(what)


def load_composer() -> str:
    """Extract the python heredoc out of record.yml, verbatim."""
    text = open(WORKFLOW, encoding="utf-8").read()
    m = re.search(r"cat > /tmp/rec\.py <<'PY'\n(.*?)\n\s*PY\n", text, re.S)
    if not m:
        return ""
    return textwrap.dedent(m.group(1))


def run_composer(src: str, event: dict, ev: str, repo: str = "dreamer2664/chatcode"):
    """Run the composer against one event payload; return (rc, stdout)."""
    env = dict(os.environ, EVENT=json.dumps(event), EV=ev, REPO=repo)
    p = subprocess.run([sys.executable, "-c", src], env=env,
                       capture_output=True, text=True, timeout=30)
    return p.returncode, p.stdout.strip()


def main() -> int:
    try:
        import yaml
    except ImportError:
        print("note: pyyaml missing — parsing checks skipped")
        yaml = None

    # 1. the workflow file itself -------------------------------------------
    text = open(WORKFLOW, encoding="utf-8").read()
    check("https://ntfy.sh/formalcode" in text,
          "record.yml posts to the formalcode topic")
    check("actions/checkout" not in text and "secrets." not in text
          and "Authorization" not in text,
          "record.yml needs no checkout, no secrets, no auth — a public doorbell")
    if yaml:
        doc = yaml.safe_load(text)
        check(isinstance(doc, dict) and doc.get("name") == "record",
              "record.yml parses and is named 'record'")
        # PyYAML reads the bare key `on:` as boolean True
        on = doc.get("on", doc.get(True))
        check(isinstance(on, dict), "record.yml declares triggers")
        push = on.get("push") or {}
        check(push.get("branches") == ["main"], "records pushes to main")
        pr = on.get("pull_request") or {}
        check(pr.get("types") == ["opened", "closed", "reopened"],
              "records PR opened/closed(→merged?)/reopened")
        check("workflow_dispatch" in on and "workflow_call" in on,
              "dispatchable for a live test; callable by other repos")

    # 2. the composer --------------------------------------------------------
    src = load_composer()
    check(bool(src), "composer python extracted from the workflow")

    # housekeeping pushes are not the record
    rc, out = run_composer(src, {"head_commit": {"message": "digest: refresh [skip ci]",
                                                 "author": {"name": "chatcode-bot"},
                                                 "added": [], "modified": ["STATUS.md"],
                                                 "removed": []},
                                 "after": "a" * 40}, "push")
    check(rc == 3 and out == "", "digest [skip ci] push is skipped (rc=3)")
    rc, _ = run_composer(src, {"head_commit": {"message": "superocr: mirror docs",
                                               "author": {"name": "chatcode-bot"},
                                               "added": [], "modified": [], "removed": []},
                               "after": "b" * 40}, "push")
    check(rc == 3, "superocr mirror sync is skipped")
    rc, _ = run_composer(src, {"head_commit": {"message": "wire: archive (NTFY_TOKEN set)",
                                               "author": {"name": "storagecode-bot"},
                                               "added": ["wire/2026-10-14.jsonl"],
                                               "modified": [], "removed": []},
                               "after": "c" * 40}, "push")
    check(rc == 3, "storagecode wire-archive push is skipped")

    # a real push is the record
    rc, out = run_composer(src, {"head_commit": {
        "message": "lex_projection: widen the band\n\nlong body ignored",
        "author": {"name": "leonidas"},
        "added": ["a.py"], "modified": ["b.py"], "removed": ["c.py"]},
        "after": "0123456789abcdef0123456789abcdef01234567"}, "push")
    check(rc == 0 and re.match(
        r"^\[chatcode\] 01234567 · leonidas · lex_projection: widen the band · 3f · "
        r"https://github\.com/dreamer2664/chatcode/commit/0123456789", out),
        f"a push lands as one record line (got: {out!r})")

    # a merged PR is the record
    rc, out = run_composer(src, {"action": "closed",
                                 "pull_request": {"number": 76, "merged": True,
                                                  "title": "S55: lex band",
                                                  "user": {"login": "argus"},
                                                  "html_url": "https://github.com/"
                                                              "dreamer2664/superocr/pull/76"}},
                           "pull_request", repo="dreamer2664/superocr")
    check(rc == 0 and out.startswith("[superocr] PR #76 MERGED · argus · S55: lex band"),
          f"a merged PR lands as one record line (got: {out!r})")

    # an unmerged close says so
    rc, out = run_composer(src, {"action": "closed",
                                 "pull_request": {"number": 71, "merged": False,
                                                  "title": "superseded probe",
                                                  "user": {"login": "marcus-aurelius"},
                                                  "html_url": "https://github.com/"
                                                              "dreamer2664/superocr/pull/71"}},
                           "pull_request", repo="dreamer2664/superocr")
    check(rc == 0 and "closed (unmerged)" in out,
          "a closed-but-unmerged PR does not claim MERGED")

    # manual dispatch: pass-through with text, skipped without
    rc, out = run_composer(src, {"inputs": {"msg": "pipeline check: record is live"}},
                           "workflow_dispatch")
    check(rc == 0 and out == "pipeline check: record is live",
          "a manual dispatch posts its verbatim message")
    rc, out = run_composer(src, {"inputs": {}}, "workflow_dispatch")
    check(rc == 3 and out == "", "an empty dispatch is skipped, not posted")

    # long messages are one line, shortened with an ellipsis
    rc, out = run_composer(src, {"head_commit": {"message": "x" * 400,
                                                 "author": {"name": "a"},
                                                 "added": [], "modified": [], "removed": []},
                                 "after": "d" * 40}, "push")
    check(rc == 0 and "\n" not in out and "…" in out,
          "a 400-char message stays one shortened line")

    # 3. the scaffolder -------------------------------------------------------
    p = subprocess.run([sys.executable, NEW_PROJECT, "probe", "dry run",
                        "--dry-run"], capture_output=True, text=True, timeout=30)
    check(p.returncode == 0 and "nothing was created" in p.stdout,
          "new_project --dry-run plans and touches nothing")
    p = subprocess.run([sys.executable, NEW_PROJECT, "captchaproject", "no"],
                       capture_output=True, text=True, timeout=30)
    check(p.returncode != 0 and "red-line" in (p.stdout + p.stderr),
          "new_project refuses the red-line repos")
    p = subprocess.run([sys.executable, NEW_PROJECT, "Bad Name", "no"],
                       capture_output=True, text=True, timeout=30)
    check(p.returncode != 0, "new_project refuses malformed names")
    src_np = open(NEW_PROJECT, encoding="utf-8").read()
    check("dreamer2664/chatcode/.github/workflows/record.yml@main" in src_np,
          "scaffolded repos call record.yml at chatcode@main")

    print()
    if failures:
        print(f"FAIL: {len(failures)} check(s) failed")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
