#!/usr/bin/env bash
set -euo pipefail

BIBALEX_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIBALEX_LOCAL_ROOT="${BIBALEX_LOCAL_ROOT:-$(cd "${BIBALEX_SCRIPT_DIR}/../.." && pwd)}"
BIBALEX_PROFILE="${BIBALEX_PROFILE:-${BIBALEX_LOCAL_ROOT}/configs/bibalex_hpc_profile.env}"

if [[ ! -f "${BIBALEX_PROFILE}" ]]; then
  echo "Missing BibaLex profile: ${BIBALEX_PROFILE}" >&2
  exit 2
fi

# shellcheck source=/dev/null
source "${BIBALEX_PROFILE}"

bibalex_ssh() {
  ssh "${BIBALEX_SSH_HOST}" "$@"
}

bibalex_stamp() {
  date -u +%Y%m%d_%H%M%S
}

bibalex_require_remote_root() {
  if [[ -z "${BIBALEX_REMOTE_ROOT:-}" ]]; then
    echo "BIBALEX_REMOTE_ROOT is empty." >&2
    exit 2
  fi
}
