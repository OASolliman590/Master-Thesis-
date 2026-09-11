#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

echo "Local root:  ${NMRBOX_LOCAL_ROOT}"
echo "Remote repo: ${NMRBOX_SSH_HOST}:${NMRBOX_REMOTE_REPO}"

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
  "${NMRBOX_LOCAL_ROOT}/" \
  "${NMRBOX_SSH_HOST}:${NMRBOX_REMOTE_REPO}/"

echo "Remote code sync completed."
