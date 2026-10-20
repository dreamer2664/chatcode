#!/usr/bin/env bash
# tools/ship.sh — thin wrapper around `chatcode ship`. The gate is the authority.
# usage: bash tools/ship.sh <job-or-task-id> [--dry-run]
set -euo pipefail
ID="${1:?usage: tools/ship.sh <job-or-task-id>}"
shift || true
CLI="${CHATCODE_CLI:-bin/chatcode}"
if [ ! -x "$CLI" ] && [ -f ../chatcode/bin/chatcode ]; then CLI="../chatcode/bin/chatcode"; fi
exec python3 "$CLI" ship "$ID" "$@"
