#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

REMOTE_EXECUTION_CLASS="canary" \
JOB_NAME="${JOB_NAME:-ici_canary_backend}" \
REQUEST_CPUS="${REQUEST_CPUS:-${NMRBOX_CANARY_REQUEST_CPUS:-4}}" \
REQUEST_MEMORY="${REQUEST_MEMORY:-${NMRBOX_CANARY_REQUEST_MEMORY:-16GB}}" \
REQUEST_DISK="${REQUEST_DISK:-${NMRBOX_CANARY_REQUEST_DISK:-20GB}}" \
REMOTE_CMD="bash scripts/nmrbox_ici_canary/run_ici_canary.sh" \
"${SCRIPT_DIR}/submit_command.sh"
