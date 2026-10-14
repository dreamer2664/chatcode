#!/usr/bin/env python3
"""Mint THE kit: a copy of WORKER.md (the cold brief) with the crew's key
stamped into the block at the bottom.

The kit is **universal** (KIT-DBF340): Carlo runs this when a key rotates
and hands the SAME file to every new hire. What distinguishes one operative
from another is the name they choose when they activate — the kit itself
never changes, so there are no per-recruit IDs to track.

(The template is switchable: `--template START_HERE.md` stamps the old
field-manual copy instead.)

    python3 tools/make_field_kit.py --env-file ~/.private/keys.env \
        --out ~/field-kit.md

--env-file must define CHATCODE_TOKEN and GITHUB_TOKEN (the live keys).

SAFETY: never commit a stamped kit, never upload one anywhere but to the
crew. If it leaks, rotate the key and re-stamp — one file, one rotation,
everyone re-kitted. Issue each operative their own copy of the same file;
prefer a revocable group key so a single leak is surgical.
"""
import argparse, sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", default="WORKER.md")
    ap.add_argument("--env-file", required=True,
                    help="file with CHATCODE_TOKEN= / GITHUB_TOKEN= lines")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    env = {}
    for line in Path(args.env_file).read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip("'\"")
    for need in ("CHATCODE_TOKEN", "GITHUB_TOKEN"):
        if not env.get(need):
            sys.exit(f"missing {need} in {args.env_file}")

    doc = Path(args.template).read_text()
    if "PENDING-ISSUE" not in doc:
        sys.exit("template has no PENDING-ISSUE key block — wrong file?")
    doc = doc.replace("CHATCODE_TOKEN=PENDING-ISSUE",
                      "CHATCODE_TOKEN=" + env["CHATCODE_TOKEN"])
    doc = doc.replace("GITHUB_TOKEN=PENDING-ISSUE",
                      "GITHUB_TOKEN=" + env["GITHUB_TOKEN"])

    out = Path(args.out)
    out.write_text(doc)
    out.chmod(0o600)
    print(f"kit written: {out} (mode 600)")
    print("universal kit KIT-DBF340 — the same file for every hire; the")
    print("name they choose in §1 is their identity. never commit or upload it.")


if __name__ == "__main__":
    main()
