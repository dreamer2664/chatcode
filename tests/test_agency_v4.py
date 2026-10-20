#!/usr/bin/env python3
"""The v4 agency layer: liveness, the career clock, jobs, self-ship, the register.

Every case runs against a throwaway repo (and a throwaway bare origin for ship),
with HOME redirected, no network and no token.

    python3 tests/test_agency_v4.py

Covers:
  1. pulse writes liveness/<agent>.json; tower renders the crew from it
  2. the career clock gates claims: ROOKIE (≤4h) · AGING (no new work) · RETIRED
  3. a job claim is a lease and one holder; a phase cannot close before its floor
     or without its evidence; the gate is fail-closed
  4. ship: green gate merges + verifies + writes the ledger; law-tier files and
     secrets in added lines are refused
  5. the Director's register: jargon and questions are refused, plain English passes
  6. the hive: name-first formatting, reports relayed, DMs never
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "bin" / "chatcode"
TID_RE = re.compile(r"t-\d{8}-[a-f0-9]{4}")


def iso_hours_ago(h: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ")


class Sandbox:
    def __init__(self):
        self.dir = Path(tempfile.mkdtemp(prefix="chatcode-v4-"))
        self.home = Path(tempfile.mkdtemp(prefix="chatcode-v4-home-"))

    def run(self, agent: str, *args: str):
        env = dict(os.environ, HOME=str(self.home), CHATCODE_AGENT=agent)
        return subprocess.run([sys.executable, str(CLI), "--local", str(self.dir),
                               "--agent", agent, *args],
                              capture_output=True, text=True, env=env, timeout=120)

    def init(self, *names: str):
        for n in names:
            r = self.run(n, "init", "--quiet", "--model", "mock")
            assert r.returncode == 0, r.stdout + r.stderr

    def set_joined(self, name: str, hours_ago: float):
        p = self.dir / "agents" / f"{name}.json"
        d = json.loads(p.read_text())
        d["joined_ts"] = iso_hours_ago(hours_ago)
        p.write_text(json.dumps(d, indent=2))

    def job(self, jid: str = "t-20261020-beef", phases: str = "", brief: str = "a job"):
        jd = self.dir / "jobs" / jid
        jd.mkdir(parents=True)
        (jd / "BRIEF.md").write_text(f"# BRIEF — {brief}\n")
        (jd / "PHASES.md").write_text(phases or "")
        (jd / "HANDOFF.md").write_text("# HANDOFF\n")
        (jd / "STATUS.json").write_text('{"status": "open", "owner": null}')
        (jd / "evidence").mkdir()
        return jd


PHASES_ONE = """# PHASES
| phase | deliverable | required evidence (file names) | min_hours |
|---|---|---|---|
| P1 | plan | `evidence/P1-plan.md` | 0.0 |
"""

PHASES_FLOOR = """# PHASES
| phase | deliverable | required evidence (file names) | min_hours |
|---|---|---|---|
| P1 | plan | `evidence/P1-plan.md` | 2.0 |
"""


class Liveness(unittest.TestCase):
    def test_pulse_writes_and_tower_reads_it(self):
        s = Sandbox()
        s.init("alice")
        r = s.run("alice", "pulse", "--status", "WORKING", "--note", "chunk 3 of 9")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        rec = json.loads((s.dir / "liveness" / "alice.json").read_text())
        self.assertEqual(rec["status"], "WORKING")
        self.assertEqual(rec["note"], "chunk 3 of 9")
        self.assertTrue(rec["ts"].endswith("Z"))
        r = s.run("alice", "tower", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        row = next(a for a in data["agents"] if a["agent"] == "alice")
        self.assertEqual(row["state"], "alive")
        self.assertEqual(data["counts"]["alive"], 1)

    def test_a_stale_pulse_is_stale_not_alive(self):
        s = Sandbox()
        s.init("bob")
        s.run("bob", "pulse", "--quiet")
        p = s.dir / "liveness" / "bob.json"
        rec = json.loads(p.read_text())
        rec["ts"] = iso_hours_ago(0.6)          # 36 minutes
        p.write_text(json.dumps(rec))
        data = json.loads(s.run("bob", "tower", "--json").stdout)
        row = next(a for a in data["agents"] if a["agent"] == "bob")
        self.assertEqual(row["state"], "stale")


class CareerClock(unittest.TestCase):
    def test_rookie_cannot_take_an_eight_hour_job(self):
        s = Sandbox()
        s.init("alice")
        s.set_joined("alice", 1)
        s.job()
        r = s.run("alice", "jobs", "claim", "t-20261020-beef", "--hours", "8")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("ROOKIE", r.stdout + r.stderr)

    def test_aging_and_retired_cannot_claim(self):
        s = Sandbox()
        s.init("alice")
        s.job()
        s.set_joined("alice", 50)
        r = s.run("alice", "jobs", "claim", "t-20261020-beef", "--hours", "4")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("AGING", r.stdout + r.stderr)
        s.set_joined("alice", 80)
        r = s.run("alice", "jobs", "claim", "t-20261020-beef", "--hours", "4")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("RETIRED", r.stdout + r.stderr)

    def test_a_full_agent_claims_and_a_second_agent_cannot_steal(self):
        s = Sandbox()
        s.init("alice", "bob")
        s.set_joined("alice", 10)
        s.set_joined("bob", 10)
        s.job()
        r = s.run("alice", "jobs", "claim", "t-20261020-beef", "--hours", "8")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((s.dir / "jobs/t-20261020-beef/CLAIM.alice.json").exists())
        r = s.run("bob", "jobs", "claim", "t-20261020-beef", "--hours", "8")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("held by alice", r.stdout + r.stderr)


class Phases(unittest.TestCase):
    def test_close_before_the_floor_is_refused(self):
        s = Sandbox()
        s.init("alice")
        s.set_joined("alice", 10)
        s.job(phases=PHASES_FLOOR)
        s.run("alice", "jobs", "claim", "t-20261020-beef", "--hours", "8")
        s.run("alice", "jobs", "phase", "t-20261020-beef", "start", "P1")
        (s.dir / "jobs/t-20261020-beef/evidence/P1-plan.md").write_text("plan")
        r = s.run("alice", "jobs", "phase", "t-20261020-beef", "close", "P1")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("floor not met", r.stdout + r.stderr)

    def test_close_without_evidence_is_refused(self):
        s = Sandbox()
        s.init("alice")
        s.set_joined("alice", 10)
        s.job(phases=PHASES_ONE)
        s.run("alice", "jobs", "claim", "t-20261020-beef", "--hours", "8")
        s.run("alice", "jobs", "phase", "t-20261020-beef", "start", "P1")
        r = s.run("alice", "jobs", "phase", "t-20261020-beef", "close", "P1")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no evidence", r.stdout + r.stderr)

    def test_gate_green_only_when_every_phase_is_closed_with_evidence(self):
        s = Sandbox()
        s.init("alice")
        s.set_joined("alice", 10)
        s.job(phases=PHASES_ONE)
        s.run("alice", "jobs", "claim", "t-20261020-beef", "--hours", "8")
        self.assertNotEqual(s.run("alice", "jobs", "gate", "t-20261020-beef").returncode, 0)
        s.run("alice", "jobs", "phase", "t-20261020-beef", "start", "P1")
        (s.dir / "jobs/t-20261020-beef/evidence/P1-plan.md").write_text("plan")
        r = s.run("alice", "jobs", "phase", "t-20261020-beef", "close", "P1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = s.run("alice", "jobs", "gate", "t-20261020-beef")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


@unittest.skipUnless(shutil.which("git"), "git required")
class Ship(unittest.TestCase):
    def make_repo(self):
        root = Path(tempfile.mkdtemp(prefix="chatcode-ship-"))
        bare = Path(tempfile.mkdtemp(prefix="chatcode-origin-")) / "origin.git"

        def g(*a, cwd=root):
            r = subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            return r

        subprocess.run(["git", "init", "--bare", "-b", "main", str(bare)],
                       capture_output=True, check=True)
        g("init", "-b", "main")
        g("config", "user.name", "alice")
        g("config", "user.email", "alice@agency.local")
        (root / "AGENCY.md").write_text("# Agency\n")
        (root / "SHIP_GATE.md").write_text("# gate\n$ true\n")
        (root / "board" / "tasks").mkdir(parents=True)
        g("add", ".")
        g("commit", "-m", "init")
        g("remote", "add", "origin", str(bare))
        g("push", "-u", "origin", "main")
        g("checkout", "-b", "agent/alice/t-20261020-cafe")
        return root, g

    def run_cli(self, root, *args):
        home = tempfile.mkdtemp()
        env = dict(os.environ, HOME=home, CHATCODE_AGENT="alice")
        return subprocess.run([sys.executable, str(CLI), "--local", str(root),
                               "--agent", "alice", *args],
                              capture_output=True, text=True, env=env, timeout=120)

    def test_green_ship_merges_into_main_and_writes_the_ledger(self):
        root, g = self.make_repo()
        (root / "deliverable.txt").write_text("the work\n")
        g("add", ".")
        g("commit", "-m", "feat: deliverable")
        r = self.run_cli(root, "ship", "t-20261020-cafe", "--no-push")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("SHIPPED", r.stdout)
        branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                                cwd=root, capture_output=True, text=True).stdout.strip()
        self.assertEqual(branch, "main")
        self.assertTrue((root / "deliverable.txt").exists())
        row = json.loads((root / "ledger" / "SHIPS.jsonl").read_text().splitlines()[-1])
        self.assertEqual(row["id"], "t-20261020-cafe")
        self.assertEqual(row["acceptance"].split()[0], "PENDING")

    def test_law_tier_files_cannot_ride_a_worker_ship(self):
        root, g = self.make_repo()
        (root / "AGENCY.md").write_text("# Agency\nsecret policy edit\n")
        g("add", ".")
        g("commit", "-m", "policy")
        r = self.run_cli(root, "ship", "t-20261020-cafe")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("law-tier", r.stdout + r.stderr)

    def test_a_secret_in_added_lines_is_refused(self):
        root, g = self.make_repo()
        (root / "notes.txt").write_text("github_pat_11ABCDEFG0123456789_abcdefghij\n")
        g("add", ".")
        g("commit", "-m", "oops")
        r = self.run_cli(root, "ship", "t-20261020-cafe")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("secret", (r.stdout + r.stderr).lower())


class Register(unittest.TestCase):
    def load(self):
        from importlib.machinery import SourceFileLoader
        loader = SourceFileLoader("cc", str(CLI))
        spec = importlib.util.spec_from_loader("cc", loader)
        mod = importlib.util.module_from_spec(spec)
        loader.exec_module(mod)
        return mod

    def test_plain_english_passes_and_jargon_is_refused(self):
        cc = self.load()
        good = ("Sir, the new neighbourhood is finished. I checked every render myself; "
                "the best ones are in the release link below, and the whole project is "
                "there too: https://example.com/release")
        self.assertEqual(cc.register_problems(good), [])
        bad = "Sir, t-20261020-ab12 shipped at commit 9f3ac21, PR #7 is open?"
        problems = " | ".join(cc.register_problems(bad))
        for needle in ("question", "commit", "PR"):
            self.assertIn(needle, problems)

    def test_report_refuses_then_force_records_the_violation(self):
        s = Sandbox()
        s.init("alice")
        r = s.run("alice", "report", "can you tell me what to do?")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("REFUSED", r.stdout + r.stderr)
        r = s.run("alice", "report", "--force", "Sir, I need direction: which project?")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        lines = (s.dir / "bus" / "human-carlo.jsonl").read_text().splitlines()
        msg = json.loads(lines[-1])
        self.assertEqual(msg["type"], "report")
        self.assertTrue(msg["forced"])


class Hive(unittest.TestCase):
    def load(self):
        from importlib.machinery import SourceFileLoader
        loader = SourceFileLoader("hive", str(ROOT / "telegram" / "hive.py"))
        spec = importlib.util.spec_from_loader("hive", loader)
        mod = importlib.util.module_from_spec(spec)
        loader.exec_module(mod)
        return mod

    def test_name_first_and_the_cli_prefix_is_stripped(self):
        hive = self.load()
        line = hive.format_line({"from": "vitruvius", "type": "report",
                                 "text": "Vitruvius: Sir, the town square is finished."})
        self.assertEqual(line, "Vitruvius — Sir, the town square is finished.")

    def test_reports_relay_dms_and_chatter_do_not(self):
        hive = self.load()
        report = {"from": "alice", "type": "report", "text": "Alice: Sir, done."}
        chat = {"from": "alice", "type": "say", "text": "Alice: fixed the parser"}
        self.assertTrue(hive.should_relay(report, "human-carlo"))
        self.assertFalse(hive.should_relay(chat, "general"))
        self.assertFalse(hive.should_relay(chat, "general"))  # without --all
        self.assertFalse(hive.should_relay(report, "dm-alice__bob"))
        self.assertFalse(hive.should_relay({"from": "carlo", "type": "report",
                                            "text": "x"}, "human-carlo"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
