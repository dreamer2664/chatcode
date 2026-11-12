#!/usr/bin/env bash
# tools/pulse.sh — liveness that cannot be forgotten.
# Run ONCE at session start:   nohup bash tools/pulse.sh >/tmp/pulse.log 2>&1 &
# Every ~20 minutes: one pulse file + every lease you hold is refreshed.
set -uo pipefail
ME="${CHATCODE_AGENT:?set CHATCODE_AGENT first}"
INTERVAL="${PULSE_INTERVAL:-1200}"          # 20 min, inside the 45-min death window
NOTE="${PULSE_NOTE:-still working}"
CLI="${CHATCODE_CLI:-python3 bin/chatcode}"

echo "pulse: agent=$ME interval=${INTERVAL}s pid=$$"
while true; do
  $CLI pulse --status WORKING --note "$NOTE" --quiet >/dev/null 2>&1 || true
  # a board write is also a heartbeat: refresh every lease we hold
  for id in $($CLI tasks list --mine 2>/dev/null | grep -oE 't-[0-9]{8}-[0-9a-z]{4}' | sort -u); do
    $CLI tasks heartbeat "$id" --note "pulse $(date -u +%FT%TZ); still working" >/dev/null 2>&1 || true
  done
  sleep "$INTERVAL"
done
