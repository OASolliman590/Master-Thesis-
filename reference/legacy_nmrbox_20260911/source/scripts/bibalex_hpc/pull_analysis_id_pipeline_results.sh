#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

usage() {
  cat <<'EOF'
Usage: scripts/bibalex_hpc/pull_analysis_id_pipeline_results.sh [--preflight|--pull]

Preflight is local-only and writes the planned rsync source/destination/filters.
Pull requires:
  ALLOW_BIBALEX_PULL_ANALYSIS_ID_RESULTS=1
  REMOTE_RUN_ROOT=/cluster/users/<user>/.../results/analysis_id_pipeline_<tag>

The pull includes only lightweight reports/tables/logs/figures and excludes raw
sequencing files, compressed raw artifacts, and retrieval downloads.
EOF
}

MODE="preflight"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --preflight)
      MODE="preflight"
      shift
      ;;
    --pull)
      MODE="pull"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

STAMP="${RUN_TAG:-$(bibalex_stamp)}"
REMOTE_RUN_ROOT="${REMOTE_RUN_ROOT:-}"
REMOTE_LABEL="$(basename "${REMOTE_RUN_ROOT:-analysis_id_pipeline_unknown}")"
DEST="${DEST:-${BIBALEX_LOCAL_ROOT}/results/bibalex_analysis_id_pull_${REMOTE_LABEL}_${STAMP}}"
PREVIEW_DIR="${BIBALEX_PULL_PREVIEW_OUT:-runtime_audits/bibalex_analysis_id_pull_preview_${STAMP}}"
PREVIEW_TSV="${PREVIEW_DIR}/bibalex_analysis_id_pull_preview.tsv"

RSYNC_FILTERS=(
  "--include=*/"
  "--exclude=retrieval/downloads*/***"
  "--exclude=downloads*/***"
  "--exclude=*.fastq"
  "--exclude=*.fastq.gz"
  "--exclude=*.fq"
  "--exclude=*.fq.gz"
  "--exclude=*.bam"
  "--exclude=*.sam"
  "--exclude=*.cram"
  "--exclude=*.h5"
  "--exclude=*.h5ad"
  "--exclude=*.loom"
  "--exclude=*.rds"
  "--exclude=*.RDS"
  "--exclude=*.gz"
  "--exclude=*.zip"
  "--exclude=*.tar"
  "--exclude=*.tar.gz"
  "--include=*.tsv"
  "--include=*.csv"
  "--include=*.md"
  "--include=*.txt"
  "--include=*.log"
  "--include=*.out"
  "--include=*.err"
  "--include=*.yaml"
  "--include=*.yml"
  "--include=*.json"
  "--include=*.html"
  "--include=*.svg"
  "--include=*.png"
  "--include=*.pdf"
  "--exclude=*"
)

write_preview() {
  mkdir -p "${PREVIEW_DIR}"
  {
    printf 'key\tvalue\n'
    printf 'mode\t%s\n' "${MODE}"
    printf 'ssh_host\t%s\n' "${BIBALEX_SSH_HOST}"
    printf 'remote_run_root\t%s\n' "${REMOTE_RUN_ROOT:-MISSING}"
    printf 'destination\t%s\n' "${DEST}"
    printf 'preview_tsv\t%s\n' "${PREVIEW_TSV}"
    printf 'network_action\t%s\n' "$([[ "${MODE}" == "pull" ]] && echo "rsync gated" || echo "none")"
    printf 'include_extensions\t%s\n' 'tsv,csv,md,txt,log,out,err,yaml,yml,json,html,svg,png,pdf'
    printf 'excluded_payloads\t%s\n' 'retrieval/downloads,fastq,bam,sam,cram,h5,h5ad,loom,rds,gz,zip,tar'
  } > "${PREVIEW_TSV}"
}

if [[ -z "${REMOTE_RUN_ROOT}" ]]; then
  write_preview
  echo "Set REMOTE_RUN_ROOT to the completed remote analysis-id run root." >&2
  printf 'preview_tsv\t%s\n' "${PREVIEW_TSV}"
  exit 2
fi

write_preview

if [[ "${MODE}" == "preflight" ]]; then
  printf 'mode\t%s\n' "${MODE}"
  printf 'preview_tsv\t%s\n' "${PREVIEW_TSV}"
  printf 'source\t%s:%s\n' "${BIBALEX_SSH_HOST}" "${REMOTE_RUN_ROOT}"
  printf 'destination\t%s\n' "${DEST}"
  printf 'pull_status\tpreview_only\n'
  exit 0
fi

if [[ "${ALLOW_BIBALEX_PULL_ANALYSIS_ID_RESULTS:-0}" != "1" ]]; then
  echo "Refusing BibaLex result pull because ALLOW_BIBALEX_PULL_ANALYSIS_ID_RESULTS is not 1." >&2
  echo "This prevents accidental network syncs or large pulls." >&2
  printf 'preview_tsv\t%s\n' "${PREVIEW_TSV}"
  exit 3
fi

mkdir -p "${DEST}"

rsync -av \
  "${RSYNC_FILTERS[@]}" \
  "${BIBALEX_SSH_HOST}:${REMOTE_RUN_ROOT%/}/" \
  "${DEST}/"

FILE_COUNT="$(find "${DEST}" -type f | wc -l | tr -d ' ')"
TOTAL_SIZE="$(du -sh "${DEST}" | awk '{print $1}')"

printf 'source\t%s:%s\n' "${BIBALEX_SSH_HOST}" "${REMOTE_RUN_ROOT}"
printf 'destination\t%s\n' "${DEST}"
printf 'file_count\t%s\n' "${FILE_COUNT}"
printf 'total_size\t%s\n' "${TOTAL_SIZE}"
