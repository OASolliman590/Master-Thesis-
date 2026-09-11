#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

JOB_NAME="${JOB_NAME:-ici_portable_r_smoke}"
PORTABLE_R_CONDA_ENV="${PORTABLE_R_CONDA_ENV:-${NMRBOX_PORTABLE_R_CONDA_ENV:-ici-r-bioconductor}}"
PORTABLE_R_CONDA_PREFIX="${PORTABLE_R_CONDA_PREFIX:-${NMRBOX_PORTABLE_R_CONDA_PREFIX:-}}"
REMOTE_OUT_DIR="${REMOTE_OUT_DIR:-${NMRBOX_REMOTE_ROOT}/runtime_audits/${JOB_NAME}_$(nmrbox_job_stamp)}"

REMOTE_CMD="mkdir -p '${REMOTE_OUT_DIR}' && export CONDA_ENV_NAME='${PORTABLE_R_CONDA_ENV}' CONDA_ENV_PREFIX='${PORTABLE_R_CONDA_PREFIX}' BACKEND_NAME='nmrbox_portable_r' OUT_DIR='${REMOTE_OUT_DIR}' && bash scripts/runtime_probe/run_portable_r_smoke.sh"
REMOTE_CMD="${REMOTE_CMD}" \
REMOTE_EXECUTION_CLASS="canary" \
JOB_NAME="${JOB_NAME}" \
REQUEST_CPUS="${NMRBOX_CANARY_REQUEST_CPUS}" \
REQUEST_MEMORY="${NMRBOX_CANARY_REQUEST_MEMORY}" \
REQUEST_DISK="${NMRBOX_CANARY_REQUEST_DISK}" \
bash "${SCRIPT_DIR}/submit_command.sh"

printf 'remote_out_dir\t%s\n' "${REMOTE_OUT_DIR}"
