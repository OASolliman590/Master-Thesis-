#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

if [[ "${ALLOW_REMOTE_FULL_PIPELINE:-0}" != "1" ]]; then
  echo "Refusing remote full pipeline because ALLOW_REMOTE_FULL_PIPELINE is not 1." >&2
  echo "Use this only after retrieval outputs and manifests have been audited." >&2
  exit 3
fi

TRACK="${TRACK:-all}"
DATA_ROOT="${NMRBOX_DATA_ROOT:?Set NMRBOX_DATA_ROOT to the audited remote retrieval root.}"
case "${TRACK}" in
  all) DOWNLOAD_TAG="timer_all" ;;
  pre) DOWNLOAD_TAG="timer_pre" ;;
  delta) DOWNLOAD_TAG="timer_delta" ;;
  *)
    echo "Unsupported TRACK=${TRACK}; use all, pre, or delta." >&2
    exit 2
    ;;
esac

DOWNLOADS_ROOT_REMOTE="${DOWNLOADS_ROOT_REMOTE:-${DATA_ROOT}/retrieval/downloads_${DOWNLOAD_TAG}}"
RUN_TAG="${RUN_TAG:-nmrbox_full_pipeline_$(nmrbox_job_stamp)}"
OUT_ROOT="${OUT_ROOT:-results/full_pipeline_${RUN_TAG}}"
JOB_NAME="${JOB_NAME:-legacy_full_pipeline_${TRACK}}"
REQUEST_CPUS="${REQUEST_CPUS:-8}"
REQUEST_MEMORY="${REQUEST_MEMORY:-32GB}"
REQUEST_DISK="${REQUEST_DISK:-40GB}"
ROUTER_ALLOW_WELCH_FALLBACK="${ROUTER_ALLOW_WELCH_FALLBACK:-1}"

REMOTE_CMD="RUN_TAG='${RUN_TAG}' OUT_ROOT='${OUT_ROOT}' DOWNLOADS_ROOT='${DOWNLOADS_ROOT_REMOTE}' ROUTER_ALLOW_WELCH_FALLBACK='${ROUTER_ALLOW_WELCH_FALLBACK}' bash run_full_pipeline.sh"

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
printf 'downloads_root\t%s\n' "${DOWNLOADS_ROOT_REMOTE}"
printf 'out_root\t%s\n' "${OUT_ROOT}"
printf 'track\t%s\n' "${TRACK}"
