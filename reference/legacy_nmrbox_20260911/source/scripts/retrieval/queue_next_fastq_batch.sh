#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 4 || $# -gt 6 ]]; then
  echo "Usage: $0 <watch_pattern> <manifest> <outdir> <logfile> [offset] [limit]" >&2
  exit 1
fi

WATCH_PATTERN="$1"
MANIFEST="$2"
OUTDIR="$3"
LOGFILE="$4"
OFFSET="${5:-211}"
LIMIT="${6:-200}"

SCRIPT="/Users/omara.soliman/Desktop/Research/11- Epigenetic's Master Thesis/2-Experimental/Computation Arm/06_analysis_pipeline_repo/scripts/retrieval/download_fastq_from_manifest.sh"

while pgrep -f "$WATCH_PATTERN" >/dev/null; do
  sleep 30
done

bash "$SCRIPT" \
  --manifest "$MANIFEST" \
  --outdir "$OUTDIR" \
  --offset "$OFFSET" \
  --limit "$LIMIT" \
  --log "$LOGFILE"
