#!/usr/bin/env bash
# tools/bootstrap.sh — 90 seconds: the tools a fresh box is missing + a profile.
# Run once at session start. Safe to re-run. Never needs a human.
set -uo pipefail
echo "bootstrap: agent=${CHATCODE_AGENT:-unnamed} $(date -u +%FT%TZ)"

SUDO=""; [ "$(id -u)" != "0" ] && command -v sudo >/dev/null && SUDO="sudo"
NEED=()
command -v ffmpeg  >/dev/null || NEED+=(ffmpeg)
command -v time    >/dev/null || NEED+=(time)
command -v jq      >/dev/null || NEED+=(jq)
if ! command -v blender >/dev/null && [ "${WITH_BLENDER:-0}" = "1" ]; then NEED+=(blender); fi
if [ ${#NEED[@]} -gt 0 ]; then
  echo "installing: ${NEED[*]}"
  $SUDO apt-get update -qq >/dev/null 2>&1 || true
  $SUDO apt-get install -y -qq --no-install-recommends "${NEED[@]}" >/dev/null 2>&1 \
    || echo "warn: some installs failed — work with what is here, or retry once"
fi

echo
echo "PROFILE (paste this into your first checkpoint — it is evidence)"
echo "  when:    $(date -u +%FT%TZ)"
echo "  cpu:     $(nproc 2>/dev/null || echo '?') cores"
echo "  ram:     $(awk '/MemTotal/{printf "%.1f GB", $2/1048576}' /proc/meminfo 2>/dev/null || echo '?')"
echo "  swap:    $(awk '/SwapTotal/{printf "%.0f MB", $2/1024}' /proc/meminfo 2>/dev/null || echo '?')"
echo "  disk:    $(df -h . 2>/dev/null | awk 'NR==2{print $4" free"}')"
echo "  python:  $(python3 -V 2>&1)"
echo "  node:    $(node -v 2>/dev/null || echo '—')"
echo "  ffmpeg:  $(ffmpeg -version 2>/dev/null | head -1 || echo '—')"
echo "  blender: $(blender -v 2>/dev/null | head -1 || echo '—')"
echo
echo "doctrine: ≤1.2GB per process, no swap, only what you push survives (AGENCY.md §2)."
