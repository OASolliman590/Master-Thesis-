#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

JOB_NAME="${JOB_NAME:-ici_recover_gsva}"

bibalex_require_remote_root

bibalex_ssh "mkdir -p '${BIBALEX_REMOTE_SCRIPTS_ROOT}' '${BIBALEX_REMOTE_SLURM_ROOT}' && chmod 700 '${BIBALEX_REMOTE_ROOT}'"

rsync -av \
  "${SCRIPT_DIR}/recover_gsva_runtime.sh" \
  "${SCRIPT_DIR}/runtime_probe.sh" \
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
    --export=ALL,BIBALEX_REMOTE_ROOT='${BIBALEX_REMOTE_ROOT}',BIBALEX_R_MODULE='${BIBALEX_R_MODULE}',BIBALEX_R_LIBS_USER='${BIBALEX_R_LIBS_USER}' \
    ./recover_gsva_runtime.sh"
)"

printf 'job_id\t%s\n' "${JOB_ID}"
printf 'remote_root\t%s\n' "${BIBALEX_REMOTE_ROOT}"
printf 'stdout\t%s/%s_%s.out\n' "${BIBALEX_REMOTE_SLURM_ROOT}" "${JOB_NAME}" "${JOB_ID}"
printf 'stderr\t%s/%s_%s.err\n' "${BIBALEX_REMOTE_SLURM_ROOT}" "${JOB_NAME}" "${JOB_ID}"
