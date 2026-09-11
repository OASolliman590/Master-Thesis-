#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${ROOT:-$(cd "${SCRIPT_DIR}/../.." && pwd)}"
BASE_PYTHON="${BASE_PYTHON:-python3.13}"
ENV_DIR="${ENV_DIR:-${HOME}/ici_thesis_pipeline_pyenv}"

if ! command -v "${BASE_PYTHON}" >/dev/null 2>&1; then
  echo "Missing BASE_PYTHON=${BASE_PYTHON}" >&2
  exit 2
fi

"${BASE_PYTHON}" -m venv "${ENV_DIR}"
"${ENV_DIR}/bin/python" -m pip install --upgrade pip
"${ENV_DIR}/bin/python" -m pip install -r "${ROOT}/scripts/nmrbox_ici_canary/requirements-canary.txt"
"${ENV_DIR}/bin/python" - <<'PY'
import importlib
for module in ["pytest", "pandas", "numpy", "scipy", "statsmodels", "matplotlib", "yaml"]:
    importlib.import_module(module)
print("nmrbox_canary_python_env_ok")
PY

printf 'python_bin\t%s\n' "${ENV_DIR}/bin/python"
