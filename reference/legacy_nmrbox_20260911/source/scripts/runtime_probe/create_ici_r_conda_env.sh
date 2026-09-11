#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "${SCRIPT_DIR}/../.." && pwd)}"
ENV_FILE="${ENV_FILE:-${REPO_ROOT}/envs/ici-r-bioconductor.yml}"
ENV_NAME="${CONDA_ENV_NAME:-ici-r-bioconductor}"
ENV_PREFIX="${CONDA_ENV_PREFIX:-}"
CONDA_BIN="${CONDA_BIN:-conda}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing environment file: ${ENV_FILE}" >&2
  exit 2
fi

if ! command -v "${CONDA_BIN}" >/dev/null 2>&1 && [[ ! -x "${CONDA_BIN}" ]]; then
  echo "Conda executable not found: ${CONDA_BIN}" >&2
  exit 2
fi

echo "env_file	${ENV_FILE}"
echo "env_name	${ENV_NAME}"
echo "env_prefix	${ENV_PREFIX}"
echo "conda_bin	${CONDA_BIN}"
echo "started_utc	$(date -u +%Y-%m-%dT%H:%M:%SZ)"

if [[ -n "${ENV_PREFIX}" ]]; then
  mkdir -p "$(dirname "${ENV_PREFIX}")"
  if [[ -d "${ENV_PREFIX}/conda-meta" ]]; then
    echo "action	update_prefix"
    "${CONDA_BIN}" env update -p "${ENV_PREFIX}" -f "${ENV_FILE}" --prune
  else
    echo "action	create_prefix"
    "${CONDA_BIN}" env create -p "${ENV_PREFIX}" -f "${ENV_FILE}"
  fi
  "${CONDA_BIN}" run -p "${ENV_PREFIX}" Rscript -e 'cat(R.version.string, "\n")'
else
  if "${CONDA_BIN}" env list | awk '{print $1}' | grep -Fxq "${ENV_NAME}"; then
    echo "action	update_name"
    "${CONDA_BIN}" env update -n "${ENV_NAME}" -f "${ENV_FILE}" --prune
  else
    echo "action	create_name"
    "${CONDA_BIN}" env create -n "${ENV_NAME}" -f "${ENV_FILE}"
  fi
  "${CONDA_BIN}" run -n "${ENV_NAME}" Rscript -e 'cat(R.version.string, "\n")'
fi

echo "finished_utc	$(date -u +%Y-%m-%dT%H:%M:%SZ)"
