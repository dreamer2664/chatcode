#!/usr/bin/env python3
"""Every `bin/chatcode <sub>` written in CHEATSHEET.md must be a real subcommand.

For each distinct subcommand mentioned in a `bin/chatcode <sub>` example, run
`bin/chatcode <sub> --help` and require exit 0 with no argparse error.
Run: python3 tests/test_cheatsheet_commands.py
"""
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "bin" / "chatcode"
CHEATSHEET = ROOT / "CHEATSHEET.md"

# "bin/chatcode <sub>" — the sub is a lowercase word right after the path.
SUB_RE = re.compile(r"bin/chatcode\s+([a-z][a-z-]*)")


def mentioned_subcommands(text):
    return sorted({m.group(1) for m in SUB_RE.finditer(text)})


def check_subcommand(sub):
    """Return None if `chatcode <sub> --help` resolves, else a short reason."""
    proc = subprocess.run([sys.executable, str(CLI), sub, "--help"],
                          capture_output=True, text=True, timeout=60, cwd=ROOT)
    err = proc.stderr
    if proc.returncode != 0 or "invalid choice" in err or "usage:" in err and "error:" in err:
        return f"rc={proc.returncode} {err.strip().splitlines()[-1] if err.strip() else ''}"
    return None


def find_broken(text):
    broken = {}
    for sub in mentioned_subcommands(text):
        reason = check_subcommand(sub)
        if reason:
            broken[sub] = reason
    return broken


class CheatsheetCommandsTest(unittest.TestCase):
    def test_real_cheatsheet_commands_resolve(self):
        text = CHEATSHEET.read_text(encoding="utf-8")
        self.assertTrue(mentioned_subcommands(text), "no `bin/chatcode <sub>` examples found")
        broken = find_broken(text)
        self.assertEqual(broken, {}, f"CHEATSHEET names commands the CLI does not have: {broken}")

    def test_fake_command_is_caught(self):
        # Scratch copy: the real cheatsheet plus one invented command line.
        text = CHEATSHEET.read_text(encoding="utf-8") + "\npython3 bin/chatcode frobnicate-nonexistent\n"
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "CHEATSHEET.md"
            p.write_text(text, encoding="utf-8")
            broken = find_broken(p.read_text(encoding="utf-8"))
        self.assertIn("frobnicate-nonexistent", broken)
        self.assertEqual(set(broken), {"frobnicate-nonexistent"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
