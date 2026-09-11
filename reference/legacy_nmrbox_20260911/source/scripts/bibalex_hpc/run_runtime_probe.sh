#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

JOB_NAME="${JOB_NAME:-ici_runtime_probe}"

bibalex_require_remote_root

JOB_ID="$(
  bibalex_ssh "cd '${BIBALEX_REMOTE_SCRIPTS_ROOT}' && sbatch --parsable \
    --job-name='${JOB_NAME}' \
    --partition='${BIBALEX_SLURM_PARTITION}' \
    --cpus-per-task='${BIBALEX_SMOKE_CPUS}' \
    --mem='${BIBALEX_SMOKE_MEM}' \
    --time='${BIBALEX_SMOKE_TIME}' \
    --output='${BIBALEX_REMOTE_SLURM_ROOT}/${JOB_NAME}_%j.out' \
    --error='${BIBALEX_REMOTE_SLURM_ROOT}/${JOB_NAME}_%j.err' \
    --export=ALL,BIBALEX_REMOTE_ROOT='${BIBALEX_REMOTE_ROOT}',BIBALEX_CONDA_BIN='${BIBALEX_CONDA_BIN}',BIBALEX_CONDA_ENV='${BIBALEX_CONDA_ENV}',BIBALEX_R_MODULE='${BIBALEX_R_MODULE}',BIBALEX_R_LIBS_USER='${BIBALEX_R_LIBS_USER}' \
    ./runtime_probe.sh"
)"

printf 'job_id\t%s\n' "${JOB_ID}"
printf 'stdout\t%s/%s_%s.out\n' "${BIBALEX_REMOTE_SLURM_ROOT}" "${JOB_NAME}" "${JOB_ID}"
printf 'stderr\t%s/%s_%s.err\n' "${BIBALEX_REMOTE_SLURM_ROOT}" "${JOB_NAME}" "${JOB_ID}"
