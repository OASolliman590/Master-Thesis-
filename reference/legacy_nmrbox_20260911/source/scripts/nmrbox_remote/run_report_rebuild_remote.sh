#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

STAMP="$(nmrbox_job_stamp)"
REPORT_OUT="results/nmrbox_remote_report_rebuild_${STAMP}"

REMOTE_EXECUTION_CLASS="report" \
JOB_NAME="${JOB_NAME:-ici_report_rebuild}" \
REQUEST_CPUS="${REQUEST_CPUS:-${NMRBOX_CANARY_REQUEST_CPUS:-4}}" \
REQUEST_MEMORY="${REQUEST_MEMORY:-${NMRBOX_CANARY_REQUEST_MEMORY:-16GB}}" \
REQUEST_DISK="${REQUEST_DISK:-${NMRBOX_CANARY_REQUEST_DISK:-20GB}}" \
REMOTE_CMD="\${PYTHON_BIN} -m pipeline.cli report build --results-root ${NMRBOX_REVIEWED_RUN_ROOT} --out ${REPORT_OUT} --figure-root ${NMRBOX_REVIEWED_FIGURE_ROOT} --run-manifest ${REPORT_OUT}/report_build.yaml" \
"${SCRIPT_DIR}/submit_command.sh"
