#!/usr/bin/env bash
set -euo pipefail

NMRBOX_REMOTE_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NMRBOX_LOCAL_ROOT="${NMRBOX_LOCAL_ROOT:-$(cd "${NMRBOX_REMOTE_SCRIPT_DIR}/../.." && pwd)}"
NMRBOX_PROFILE="${NMRBOX_PROFILE:-${NMRBOX_LOCAL_ROOT}/configs/nmrbox_remote_profile.env}"

if [[ ! -f "${NMRBOX_PROFILE}" ]]; then
  echo "Missing NMRbox profile: ${NMRBOX_PROFILE}" >&2
  exit 2
fi

# shellcheck source=/dev/null
source "${NMRBOX_PROFILE}"

nmrbox_require_remote_cmd() {
  if [[ -z "${REMOTE_CMD:-}" ]]; then
    echo "Set REMOTE_CMD to the command to run under NMRBOX_REMOTE_REPO." >&2
    exit 2
  fi
}

nmrbox_validate_execution_class() {
  local class="${REMOTE_EXECUTION_CLASS:-canary}"
  case "${class}" in
    canary|report)
      return 0
      ;;
    targeted|full)
      if [[ "${ALLOW_REMOTE_PIPELINE_RUN:-0}" != "1" ]]; then
        echo "Refusing ${class} remote run because ALLOW_REMOTE_PIPELINE_RUN is not 1." >&2
        echo "This protects reviewed results and large data transfers." >&2
        exit 3
      fi
      ;;
    *)
      echo "Unknown REMOTE_EXECUTION_CLASS=${class}; use canary, report, targeted, or full." >&2
      exit 2
      ;;
  esac
}

nmrbox_ssh() {
  ssh "${NMRBOX_SSH_HOST}" "$@"
}

nmrbox_job_stamp() {
  date -u +%Y%m%d_%H%M%S
}
