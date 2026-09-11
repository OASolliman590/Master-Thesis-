#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

bibalex_ssh "
set -euo pipefail
printf 'host\t%s\n' \"\$(hostname)\"
printf 'user\t%s\n' \"\$(id -un)\"
printf 'home\t%s\n' \"\$HOME\"
printf 'remote_root\t%s\n' '${BIBALEX_REMOTE_ROOT}'
printf 'df_remote_parent\n'
df -h '${BIBALEX_REMOTE_ROOT%/*}' 2>/dev/null || df -h \"\$HOME\"
printf 'scheduler\n'
command -v sbatch
command -v squeue
squeue -u '${BIBALEX_USER}' || true
printf 'python_env\n'
PYTHONNOUSERSITE=1 '${BIBALEX_CONDA_BIN}' run -n '${BIBALEX_CONDA_ENV}' python -c 'import sys, numpy, pandas, scipy, statsmodels, matplotlib, yaml; print(sys.version.split()[0], numpy.__version__, pandas.__version__, scipy.__version__, statsmodels.__version__, matplotlib.__version__)'
printf 'r_module\n'
source /etc/profile.d/modules.sh 2>/dev/null || true
module load '${BIBALEX_R_MODULE}'
command -v Rscript
Rscript --version
"
