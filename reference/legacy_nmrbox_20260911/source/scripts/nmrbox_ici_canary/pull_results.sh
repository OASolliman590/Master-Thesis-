#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${ROOT:-$(cd "${SCRIPT_DIR}/../.." && pwd)}"
REMOTE="${REMOTE:-beryllium.nmrbox.org}"
REMOTE_DIR="${REMOTE_DIR:?Set REMOTE_DIR to the remote bundle root, for example ~/ici_thesis_pipeline_canary/ici_thesis_pipeline_canary}"
STAMP="$(date -u +%Y%m%d_%H%M%S)"
DEST="${DEST:-${ROOT}/results/nmrbox_remote_pull_${STAMP}}"

mkdir -p "${DEST}"

rsync -av \
  --include "*/" \
  --include "*.tsv" \
  --include "*.csv" \
  --include "*.md" \
  --include "*.txt" \
  --include "*.log" \
  --include "*.out" \
  --include "*.err" \
  --include "*.yaml" \
  --include "*.yml" \
  --include "*.json" \
  --include "*.html" \
  --include "*.svg" \
  --include "*.png" \
  --include "*.pdf" \
  --exclude "*" \
  "${REMOTE}:${REMOTE_DIR}/" \
  "${DEST}/"

FILE_COUNT="$(find "${DEST}" -type f | wc -l | tr -d ' ')"
TOTAL_SIZE="$(du -sh "${DEST}" | awk '{print $1}')"

printf 'source\t%s:%s\n' "${REMOTE}" "${REMOTE_DIR}"
printf 'destination\t%s\n' "${DEST}"
printf 'file_count\t%s\n' "${FILE_COUNT}"
printf 'total_size\t%s\n' "${TOTAL_SIZE}"
