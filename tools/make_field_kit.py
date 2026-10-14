#!/usr/bin/env python3
"""Mint a per-recruit FIELD KIT: a copy of WORKER.md (the cold brief)
with one operative's access key embedded. Carlo runs this, sends the ONE
output file to the recruit, and sends nothing else.

(The template is switchable: `--template START_HERE.md` mints the old
field-manual kit instead.)

    python3 tools/make_field_kit.py --env-file ~/.private/keys.env \
        --out ~/field-kit.md

--env-file must define CHATCODE_TOKEN and GITHUB_TOKEN (the key the
recruit will use). A unique KIT-ID is stamped into the copy; Carlo
keeps the ID (IDs are not secret — keys are) and tells the Handlers,
who match it against the recruit's confirmation flare.

SAFETY: never commit a minted kit, never upload one anywhere but to
its recruit. If a kit leaks, rotate the key it carries. Prefer issuing
each recruit their own least-privilege key so revocation is surgical.
"""
import argparse, secrets, sys
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
    kit_id = "KIT-" + secrets.token_hex(3).upper()
    doc = doc.replace("KIT-ID: PENDING-ISSUE", f"KIT-ID: {kit_id}")
    doc = doc.replace("CHATCODE_TOKEN=PENDING-ISSUE",
                      "CHATCODE_TOKEN=" + env["CHATCODE_TOKEN"])
    doc = doc.replace("GITHUB_TOKEN=PENDING-ISSUE",
                      "GITHUB_TOKEN=" + env["GITHUB_TOKEN"])

    out = Path(args.out)
    out.write_text(doc)
    out.chmod(0o600)
    print(f"field kit minted: {out} (mode 600)")
    print(f"KIT-ID: {kit_id}  <- give this ID to the Handlers; "
          f"record it next to the recruit in your private notes")
    print("send the recruit ONLY that file. never commit or upload it.")


if __name__ == "__main__":
    main()
