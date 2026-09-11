#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

if [[ "${ALLOW_REMOTE_DATA_DOWNLOAD:-0}" != "1" ]]; then
  echo "Refusing full remote data download because ALLOW_REMOTE_DATA_DOWNLOAD is not 1." >&2
  echo "Run the health job first, inspect it, then set ALLOW_REMOTE_DATA_DOWNLOAD=1." >&2
  exit 3
fi

TRACK="${TRACK:-all}"
STAMP="${NMRBOX_DATA_STAMP:-$(nmrbox_job_stamp)}"
DATA_ROOT="${NMRBOX_DATA_ROOT:-${NMRBOX_REMOTE_DATA_ROOT}/geo_retrieval_${STAMP}}"
JOB_NAME="${JOB_NAME:-geo_retrieval_full_${TRACK}}"
REQUEST_CPUS="${REQUEST_CPUS:-4}"
REQUEST_MEMORY="${REQUEST_MEMORY:-16GB}"
REQUEST_DISK="${REQUEST_DISK:-40GB}"

REMOTE_CMD="bash scripts/run_timer_t7_download_full.sh '${DATA_ROOT}' --track=${TRACK}"

ALLOW_REMOTE_PIPELINE_RUN=1 \
REMOTE_EXECUTION_CLASS=full \
JOB_NAME="${JOB_NAME}" \
REQUEST_CPUS="${REQUEST_CPUS}" \
REQUEST_MEMORY="${REQUEST_MEMORY}" \
REQUEST_DISK="${REQUEST_DISK}" \
REMOTE_CMD="${REMOTE_CMD}" \
bash "${SCRIPT_DIR}/submit_command.sh" \
  --class full \
  --job-name "${JOB_NAME}" \
  --cpus "${REQUEST_CPUS}" \
  --memory "${REQUEST_MEMORY}" \
  --disk "${REQUEST_DISK}"

printf 'data_root\t%s\n' "${DATA_ROOT}"
printf 'track\t%s\n' "${TRACK}"
printf 'mode\t%s\n' "full-download"
