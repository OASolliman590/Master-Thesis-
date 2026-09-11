#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

JOB_NAME="${JOB_NAME:-ici_create_portable_r}"
PORTABLE_R_CONDA_ENV="${PORTABLE_R_CONDA_ENV:-${BIBALEX_PORTABLE_R_CONDA_ENV:-ici-r-bioconductor}}"
PORTABLE_R_CONDA_PREFIX="${PORTABLE_R_CONDA_PREFIX:-${BIBALEX_PORTABLE_R_CONDA_PREFIX:-}}"
PORTABLE_R_CONDA_BIN="${PORTABLE_R_CONDA_BIN:-${BIBALEX_CONDA_BIN}}"
REMOTE_ENV_FILE="${BIBALEX_REMOTE_SCRIPTS_ROOT}/ici-r-bioconductor.yml"
REMOTE_CREATE_SCRIPT="${BIBALEX_REMOTE_SCRIPTS_ROOT}/create_ici_r_conda_env.sh"

bibalex_require_remote_root

bibalex_ssh "mkdir -p '${BIBALEX_REMOTE_SCRIPTS_ROOT}' '${BIBALEX_REMOTE_SLURM_ROOT}' && chmod 700 '${BIBALEX_REMOTE_ROOT}'"

rsync -av \
  "${BIBALEX_LOCAL_ROOT}/envs/ici-r-bioconductor.yml" \
  "${BIBALEX_LOCAL_ROOT}/scripts/runtime_probe/create_ici_r_conda_env.sh" \
  "${BIBALEX_SSH_HOST}:${BIBALEX_REMOTE_SCRIPTS_ROOT}/"

JOB_ID="$(
  bibalex_ssh "cd '${BIBALEX_REMOTE_SCRIPTS_ROOT}' && sbatch --parsable \
    --job-name='${JOB_NAME}' \
    --partition='${BIBALEX_SLURM_PARTITION}' \
    --cpus-per-task='${BIBALEX_BOOTSTRAP_CPUS}' \
    --mem='${BIBALEX_BOOTSTRAP_MEM}' \
    --time='${BIBALEX_BOOTSTRAP_TIME}' \
    --output='${BIBALEX_REMOTE_SLURM_ROOT}/${JOB_NAME}_%j.out' \
    --error='${BIBALEX_REMOTE_SLURM_ROOT}/${JOB_NAME}_%j.err' \
    --export=ALL,CONDA_BIN='${PORTABLE_R_CONDA_BIN}',CONDA_ENV_NAME='${PORTABLE_R_CONDA_ENV}',CONDA_ENV_PREFIX='${PORTABLE_R_CONDA_PREFIX}',ENV_FILE='${REMOTE_ENV_FILE}' \
    '${REMOTE_CREATE_SCRIPT}'"
)"

printf 'job_id\t%s\n' "${JOB_ID}"
printf 'remote_root\t%s\n' "${BIBALEX_REMOTE_ROOT}"
printf 'conda_env_prefix\t%s\n' "${PORTABLE_R_CONDA_PREFIX}"
printf 'stdout\t%s/%s_%s.out\n' "${BIBALEX_REMOTE_SLURM_ROOT}" "${JOB_NAME}" "${JOB_ID}"
printf 'stderr\t%s/%s_%s.err\n' "${BIBALEX_REMOTE_SLURM_ROOT}" "${JOB_NAME}" "${JOB_ID}"
