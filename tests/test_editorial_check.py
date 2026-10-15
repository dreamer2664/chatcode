#!/usr/bin/env python3
"""Tests for editorial_check.py — the live registry plus adversarial examples.

The card asks for refusal tests, not just a happy path: duplicate premise,
unsourced claim, inaccessible/unlicensed asset, stale owner, plus the real
campaign registry must pass.
"""
import copy, json, os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import editorial_check as ec

REG_PATH = os.path.join(HERE, "..", "projects", "youtube-training",
                        "editorial", "slate-registry.json")

def base_reg():
    return {
        "slots": [
            {"slot": "YT01", "task": "t-20261015-34fa", "owner": "a",
             "status": "reserved", "premise_key": "git object database and DAG history",
             "sources_verified": "2026-10-15 by a"},
            {"slot": "YT02", "task": "t-20261015-4b76", "owner": None,
             "status": "pitched-unclaimed", "premise_key": "hashing files to check integrity by hand",
             "sources_verified": "2026-10-15 by b"},
        ]
    }

def fails(findings, needle):
    return any(l == "FAIL" and needle in m for l, m in findings)

class EditorialCheckTest(unittest.TestCase):
    def test_real_campaign_registry_is_consistent(self):
        with open(os.path.normpath(REG_PATH)) as fh:
            reg = json.load(fh)
        findings = ec.check_registry(reg)
        self.assertEqual([m for l, m in findings if l == "FAIL"], [],
                         "the live slate must pass its own checker")
        self.assertEqual(len(reg["slots"]), 10, "campaign needs ten slots registered")

    def test_duplicate_premise_key_refused(self):
        reg = base_reg()
        reg["slots"][1]["premise_key"] = reg["slots"][0]["premise_key"]
        self.assertTrue(fails(ec.check_registry(reg), "duplicate premise_key"))

    def test_near_duplicate_premise_needs_differentiation(self):
        reg = base_reg()
        reg["slots"][1]["premise_key"] = "git object database and DAG of history"
        self.assertTrue(fails(ec.check_registry(reg), "without a recorded differentiation"))
        reg["slots"][1]["differentiation"] = ("YT01 explains storage; YT02 is a hands-on terminal "
                                              "tutorial for non-programmers")
        findings = ec.check_registry(reg)
        self.assertFalse(fails(findings, "differentiation"))
        self.assertTrue(any(l == "info" for l, _ in findings), "kept on the record, not silently dropped")

    def test_unsourced_pitch_refused(self):
        reg = base_reg()
        del reg["slots"][1]["sources_verified"]
        self.assertTrue(fails(ec.check_registry(reg), "sources_verified record required"))

    def test_inaccessible_and_unlicensed_assets_refused(self):
        reg = base_reg()
        reg["slots"][0]["assets"] = [
            {"name": "1956 newsreel", "availability": "unavailable", "license": "unknown"},
            {"name": "hero photo", "availability": "ok", "license": "found on google"},
        ]
        findings = ec.check_registry(reg)
        self.assertTrue(fails(findings, "inaccessible assets cannot anchor a film"))
        self.assertTrue(fails(findings, "'found on Google' is not permission"))
        reg["slots"][0]["assets"] = [{"name": "hero photo", "availability": "ok",
                                      "license": "CC BY 4.0, attribution recorded"}]
        self.assertFalse(fails(ec.check_registry(reg), "license"))

    def test_stale_owner_and_malformed_ids_refused(self):
        reg = base_reg()
        reg["slots"][1]["owner"] = "ghost"  # status still pitched-unclaimed
        findings = ec.check_registry(reg)
        self.assertTrue(fails(findings, "stale registry"))
        reg = base_reg()
        reg["slots"][1]["slot"] = "YT2"
        self.assertTrue(fails(ec.check_registry(reg), "slot id must look like"))
        reg = base_reg()
        reg["slots"][1]["task"] = reg["slots"][0]["task"]
        self.assertTrue(fails(ec.check_registry(reg), "one card, one slot"))

    def test_rejected_claims_are_kept_on_the_record(self):
        """A rejected weak claim must be recorded, not quietly deleted — the
        campaign's research example depends on the refusal being visible."""
        with open(os.path.normpath(REG_PATH)) as fh:
            reg = json.load(fh)
        self.assertTrue(reg.get("rejected"), "registry must record rejected claims")
        r = reg["rejected"][0]
        self.assertIn("Einstein", r["premise"])
        self.assertTrue(r["reason"] and r["rejected_by"] and r["date"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
