#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Download FASTQ files from a deduplicated TSV URL manifest.

Required:
  --manifest <path>   TSV with a `url` column.
  --outdir <path>     Destination directory for downloaded FASTQ files.

Optional:
  --offset <n>        1-based URL index to start from (default: 1).
  --limit <n>         Maximum number of URLs to download (default: all).
  --log <path>        Log file path (default: <outdir>/download.log).

Example:
  bash scripts/retrieval/download_fastq_from_manifest.sh \
    --manifest /Volumes/T7/.../manifests/fastq_ftp_manifest_dedup.tsv \
    --outdir /Volumes/T7/.../raw/fastq_ena \
    --offset 1 \
    --limit 200
EOF
}

MANIFEST=""
OUTDIR=""
OFFSET=1
LIMIT=0
LOGFILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --manifest)
      MANIFEST="$2"
      shift 2
      ;;
    --outdir)
      OUTDIR="$2"
      shift 2
      ;;
    --offset)
      OFFSET="$2"
      shift 2
      ;;
    --limit)
      LIMIT="$2"
      shift 2
      ;;
    --log)
      LOGFILE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[error] Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$MANIFEST" || -z "$OUTDIR" ]]; then
  echo "[error] --manifest and --outdir are required." >&2
  usage
  exit 1
fi

if [[ ! -f "$MANIFEST" ]]; then
  echo "[error] Manifest not found: $MANIFEST" >&2
  exit 1
fi

mkdir -p "$OUTDIR"

if [[ -z "${LOGFILE}" ]]; then
  LOGFILE="${OUTDIR}/download.log"
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
ALL_URLS="${TMP_DIR}/all_urls.txt"
SELECTED_URLS="${TMP_DIR}/selected_urls.txt"

awk -F '\t' '
  NR == 1 {
    for (i = 1; i <= NF; i++) {
      if ($i == "url") {
        c = i
      }
    }
    next
  }
  c && $c != "" { print $c }
' "$MANIFEST" | awk '!seen[$0]++' > "$ALL_URLS"

TOTAL_URLS="$(wc -l < "$ALL_URLS" | tr -d ' ')"
if [[ "$TOTAL_URLS" -eq 0 ]]; then
  echo "[warn] No URLs found in manifest: $MANIFEST" | tee -a "$LOGFILE"
  exit 0
fi

if [[ "$OFFSET" -lt 1 ]]; then
  echo "[error] --offset must be >= 1" >&2
  exit 1
fi

tail -n +"$OFFSET" "$ALL_URLS" > "${TMP_DIR}/offset_urls.txt"

if [[ "$LIMIT" -gt 0 ]]; then
  head -n "$LIMIT" "${TMP_DIR}/offset_urls.txt" > "$SELECTED_URLS"
else
  cp "${TMP_DIR}/offset_urls.txt" "$SELECTED_URLS"
fi

SELECTED_COUNT="$(wc -l < "$SELECTED_URLS" | tr -d ' ')"
START_TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

{
  echo "[info] start_utc=${START_TS}"
  echo "[info] manifest=${MANIFEST}"
  echo "[info] outdir=${OUTDIR}"
  echo "[info] total_urls=${TOTAL_URLS}"
  echo "[info] offset=${OFFSET}"
  echo "[info] limit=${LIMIT}"
  echo "[info] selected_urls=${SELECTED_COUNT}"
} | tee -a "$LOGFILE"

wget \
  --continue \
  --no-verbose \
  --input-file="$SELECTED_URLS" \
  --directory-prefix="$OUTDIR" 2>&1 | tee -a "$LOGFILE"

END_TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "[info] end_utc=${END_TS}" | tee -a "$LOGFILE"
