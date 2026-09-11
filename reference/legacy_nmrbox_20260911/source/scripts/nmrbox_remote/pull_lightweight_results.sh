#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

REMOTE_PATH="${REMOTE_PATH:?Set REMOTE_PATH to a remote result/job directory to pull.}"
STAMP="$(nmrbox_job_stamp)"
DEST="${DEST:-${NMRBOX_LOCAL_ROOT}/results/nmrbox_remote_pull_${STAMP}}"

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
  --exclude "*.fastq" \
  --exclude "*.fastq.gz" \
  --exclude "*.fq" \
  --exclude "*.fq.gz" \
  --exclude "*.bam" \
  --exclude "*.sam" \
  --exclude "*.cram" \
  --exclude "*.xtc" \
  --exclude "*.trr" \
  --exclude "*.dcd" \
  --exclude "*.tpr" \
  --exclude "*" \
  "${NMRBOX_SSH_HOST}:${REMOTE_PATH}/" \
  "${DEST}/"

FILE_COUNT="$(find "${DEST}" -type f | wc -l | tr -d ' ')"
TOTAL_SIZE="$(du -sh "${DEST}" | awk '{print $1}')"

printf 'source\t%s:%s\n' "${NMRBOX_SSH_HOST}" "${REMOTE_PATH}"
printf 'destination\t%s\n' "${DEST}"
printf 'file_count\t%s\n' "${FILE_COUNT}"
printf 'total_size\t%s\n' "${TOTAL_SIZE}"
