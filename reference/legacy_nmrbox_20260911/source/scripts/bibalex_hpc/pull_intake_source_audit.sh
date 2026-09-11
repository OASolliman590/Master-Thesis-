#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

REMOTE_AUDIT_ROOT="${REMOTE_AUDIT_ROOT:?Set REMOTE_AUDIT_ROOT to the BibaLex intake_source_audit_* path.}"
LOCAL_AUDIT_ROOT="${LOCAL_AUDIT_ROOT:-${BIBALEX_LOCAL_ROOT}/runtime_audits/$(basename "${REMOTE_AUDIT_ROOT}")}"

mkdir -p "${LOCAL_AUDIT_ROOT}"

rsync -av \
  --include="*/" \
  --include="*.tsv" \
  --include="*.md" \
  --include="*.yaml" \
  --include="*.yml" \
  --include="*.json" \
  --include="*.log" \
  --include="*.out" \
  --include="*.err" \
  --exclude="*" \
  "${BIBALEX_SSH_HOST}:${REMOTE_AUDIT_ROOT}/" \
  "${LOCAL_AUDIT_ROOT}/"

FILE_COUNT="$(find "${LOCAL_AUDIT_ROOT}" -type f | wc -l | tr -d ' ')"
TOTAL_SIZE="$(du -sh "${LOCAL_AUDIT_ROOT}" | awk '{print $1}')"

printf 'remote_audit_root\t%s\n' "${REMOTE_AUDIT_ROOT}"
printf 'local_audit_root\t%s\n' "${LOCAL_AUDIT_ROOT}"
printf 'file_count\t%s\n' "${FILE_COUNT}"
printf 'total_size\t%s\n' "${TOTAL_SIZE}"
