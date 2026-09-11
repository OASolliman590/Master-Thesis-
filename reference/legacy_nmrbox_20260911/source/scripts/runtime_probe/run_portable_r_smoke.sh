#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "${SCRIPT_DIR}/../.." && pwd)}"
SMOKE_R="${REPO_ROOT}/scripts/runtime_probe/portable_r_smoke.R"
BACKEND_NAME="${BACKEND_NAME:-local}"
STAMP="${RUNTIME_SMOKE_STAMP:-$(date -u +%Y%m%d_%H%M%S)}"
OUT_DIR="${OUT_DIR:-${REPO_ROOT}/runtime_audits/${BACKEND_NAME}_${STAMP}}"

if [[ ! -f "${SMOKE_R}" ]]; then
  echo "Missing smoke test: ${SMOKE_R}" >&2
  exit 2
fi

mkdir -p "${OUT_DIR}"

if [[ -n "${APPTAINER_IMAGE:-}" ]]; then
  APPTAINER_BIN="${APPTAINER_BIN:-apptainer}"
  R_CMD=("${APPTAINER_BIN}" exec "${APPTAINER_IMAGE}" Rscript)
elif [[ -n "${CONDA_ENV_NAME:-}" || -n "${CONDA_ENV_PREFIX:-}" ]]; then
  CONDA_BIN="${CONDA_BIN:-conda}"
  if [[ -n "${CONDA_ENV_PREFIX:-}" ]]; then
    R_CMD=("${CONDA_BIN}" run -p "${CONDA_ENV_PREFIX}" Rscript)
  else
    R_CMD=("${CONDA_BIN}" run -n "${CONDA_ENV_NAME}" Rscript)
  fi
else
  R_SCRIPT_BIN="${R_SCRIPT_BIN:-Rscript}"
  R_CMD=("${R_SCRIPT_BIN}")
fi

{
  printf 'backend\t%s\n' "${BACKEND_NAME}"
  printf 'started_utc\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'repo_root\t%s\n' "${REPO_ROOT}"
  printf 'out_dir\t%s\n' "${OUT_DIR}"
  printf 'r_command\t%s\n' "${R_CMD[*]}"
  printf 'conda_env_name\t%s\n' "${CONDA_ENV_NAME:-}"
  printf 'conda_env_prefix\t%s\n' "${CONDA_ENV_PREFIX:-}"
  printf 'apptainer_image\t%s\n' "${APPTAINER_IMAGE:-}"
} > "${OUT_DIR}/runtime_invocation.tsv"

"${R_CMD[@]}" "${SMOKE_R}" --out-dir "${OUT_DIR}"

printf 'finished_utc\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUT_DIR}/runtime_invocation.tsv"
printf 'runtime_smoke_out\t%s\n' "${OUT_DIR}"
