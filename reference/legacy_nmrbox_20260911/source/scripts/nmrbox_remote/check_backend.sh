#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

nmrbox_ssh "hostname; whoami; pwd"
nmrbox_ssh "condor_q ${NMRBOX_USER} -nobatch"
nmrbox_ssh "test -d '${NMRBOX_REMOTE_REPO}' && echo remote_repo_ok || echo remote_repo_missing:'${NMRBOX_REMOTE_REPO}'"
nmrbox_ssh "test -x '${NMRBOX_PYTHON_BIN}' && '${NMRBOX_PYTHON_BIN}' - <<'PY'
import importlib
import sys
print('python_executable', sys.executable)
print('python_version', sys.version.replace('\n', ' '))
for module in ['pytest', 'pandas', 'numpy', 'scipy', 'statsmodels', 'matplotlib', 'yaml']:
    try:
        importlib.import_module(module)
    except Exception as exc:
        print(module, 'failed', exc.__class__.__name__, str(exc).splitlines()[0])
    else:
        print(module, 'ok')
PY"
nmrbox_ssh "Rscript --version 2>&1 | head -1 || true"
