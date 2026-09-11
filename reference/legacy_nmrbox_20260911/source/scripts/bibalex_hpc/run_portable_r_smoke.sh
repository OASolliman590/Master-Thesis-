#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

JOB_NAME="${JOB_NAME:-ici_portable_r_smoke}"
bibalex_require_remote_root

REMOTE_SCRIPT="${BIBALEX_REMOTE_SCRIPTS_ROOT}/run_portable_r_smoke_${JOB_NAME}.sh"
REMOTE_OUT_DIR="${REMOTE_OUT_DIR:-${BIBALEX_REMOTE_ROOT}/runtime_audits/${JOB_NAME}_$(bibalex_stamp)}"
PORTABLE_R_CONDA_ENV="${PORTABLE_R_CONDA_ENV:-${BIBALEX_PORTABLE_R_CONDA_ENV:-ici-r-bioconductor}}"
PORTABLE_R_CONDA_PREFIX="${PORTABLE_R_CONDA_PREFIX:-${BIBALEX_PORTABLE_R_CONDA_PREFIX:-}}"
PORTABLE_R_CONDA_BIN="${PORTABLE_R_CONDA_BIN:-${BIBALEX_CONDA_BIN}}"
USE_SITE_R="${USE_SITE_R:-0}"

if [[ "${USE_SITE_R}" == "1" ]]; then
  REMOTE_R_SETUP="source /etc/profile.d/modules.sh 2>/dev/null || true
module load '${BIBALEX_R_MODULE}'
export R_LIBS_USER='${BIBALEX_R_LIBS_USER}'
export BACKEND_NAME='bibalex_site_r'
export OUT_DIR='${REMOTE_OUT_DIR}'
cd '${BIBALEX_REMOTE_REPO}'
bash scripts/runtime_probe/run_portable_r_smoke.sh"
else
  REMOTE_R_SETUP="export CONDA_BIN='${PORTABLE_R_CONDA_BIN}'
export CONDA_ENV_NAME='${PORTABLE_R_CONDA_ENV}'
export CONDA_ENV_PREFIX='${PORTABLE_R_CONDA_PREFIX}'
export BACKEND_NAME='bibalex_portable_r'
export OUT_DIR='${REMOTE_OUT_DIR}'
cd '${BIBALEX_REMOTE_REPO}'
bash scripts/runtime_probe/run_portable_r_smoke.sh"
fi

bibalex_ssh "mkdir -p '${BIBALEX_REMOTE_SLURM_ROOT}' '${BIBALEX_REMOTE_SCRIPTS_ROOT}' '${REMOTE_OUT_DIR}'"

cat > /tmp/ici_bibalex_portable_r_smoke.sh <<EOF_REMOTE
#!/usr/bin/env bash
#SBATCH --job-name=${JOB_NAME}
#SBATCH --partition=${BIBALEX_SLURM_PARTITION}
#SBATCH --cpus-per-task=${BIBALEX_SMOKE_CPUS}
#SBATCH --mem=${BIBALEX_SMOKE_MEM}
#SBATCH --time=${BIBALEX_SMOKE_TIME}
#SBATCH --output=${BIBALEX_REMOTE_SLURM_ROOT}/${JOB_NAME}_%j.out
#SBATCH --error=${BIBALEX_REMOTE_SLURM_ROOT}/${JOB_NAME}_%j.err

set -euo pipefail
${REMOTE_R_SETUP}
EOF_REMOTE

scp /tmp/ici_bibalex_portable_r_smoke.sh "${BIBALEX_SSH_HOST}:${REMOTE_SCRIPT}"
bibalex_ssh "chmod +x '${REMOTE_SCRIPT}' && sbatch '${REMOTE_SCRIPT}'"

printf 'remote_script\t%s\n' "${REMOTE_SCRIPT}"
printf 'remote_out_dir\t%s\n' "${REMOTE_OUT_DIR}"
printf 'job_name\t%s\n' "${JOB_NAME}"
