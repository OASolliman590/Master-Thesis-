#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

TRACK="${TRACK:-all}"
STAMP="${NMRBOX_DATA_STAMP:-$(nmrbox_job_stamp)}"
DATA_ROOT="${NMRBOX_DATA_ROOT:-${NMRBOX_REMOTE_DATA_ROOT}/geo_retrieval_${STAMP}}"
JOB_NAME="${JOB_NAME:-geo_retrieval_health_${TRACK}}"
REQUEST_CPUS="${REQUEST_CPUS:-2}"
REQUEST_MEMORY="${REQUEST_MEMORY:-8GB}"
REQUEST_DISK="${REQUEST_DISK:-10GB}"

REMOTE_CMD="bash scripts/run_timer_t7_download_full.sh '${DATA_ROOT}' --health-only --track=${TRACK}"

ALLOW_REMOTE_PIPELINE_RUN=1 \
REMOTE_EXECUTION_CLASS=targeted \
JOB_NAME="${JOB_NAME}" \
REQUEST_CPUS="${REQUEST_CPUS}" \
REQUEST_MEMORY="${REQUEST_MEMORY}" \
REQUEST_DISK="${REQUEST_DISK}" \
REMOTE_CMD="${REMOTE_CMD}" \
bash "${SCRIPT_DIR}/submit_command.sh" \
  --class targeted \
  --job-name "${JOB_NAME}" \
  --cpus "${REQUEST_CPUS}" \
  --memory "${REQUEST_MEMORY}" \
  --disk "${REQUEST_DISK}"

printf 'data_root\t%s\n' "${DATA_ROOT}"
printf 'track\t%s\n' "${TRACK}"
printf 'mode\t%s\n' "health-only"
