#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

bibalex_require_remote_root

echo "Local root:  ${BIBALEX_LOCAL_ROOT}"
echo "Remote repo: ${BIBALEX_SSH_HOST}:${BIBALEX_REMOTE_REPO}"

bibalex_ssh "mkdir -p '${BIBALEX_REMOTE_REPO}' && chmod 700 '${BIBALEX_REMOTE_ROOT}'"

rsync -av \
  --exclude ".git/" \
  --exclude ".DS_Store" \
  --exclude ".pytest_cache/" \
  --exclude ".venv/" \
  --exclude "venv/" \
  --exclude "node_modules/" \
  --exclude "__pycache__/" \
  --exclude "*.pyc" \
  --exclude "results/" \
  --exclude "reports/" \
  --exclude "figures/" \
  --exclude "logs/" \
  --exclude "work/" \
  --exclude "runtime_audits/" \
  --exclude "inputs/cibersortx/" \
  "${BIBALEX_LOCAL_ROOT}/" \
  "${BIBALEX_SSH_HOST}:${BIBALEX_REMOTE_REPO}/"

echo "Remote code sync completed."
