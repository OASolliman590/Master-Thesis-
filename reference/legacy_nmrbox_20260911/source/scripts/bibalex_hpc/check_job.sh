#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

JOB_ID="${1:?Usage: bash scripts/bibalex_hpc/check_job.sh <slurm_job_id>}"
JOB_NAME="${JOB_NAME:-ici_env_bootstrap}"

bibalex_ssh "
set -euo pipefail
echo '== squeue =='
squeue -j '${JOB_ID}' || true
echo '== sacct =='
sacct -j '${JOB_ID}' --format=JobID,JobName%30,State,ExitCode,Elapsed,MaxRSS,ReqMem,NCPUS -P 2>/dev/null || true
echo '== stdout tail =='
tail -80 '${BIBALEX_REMOTE_SLURM_ROOT}/${JOB_NAME}_${JOB_ID}.out' 2>/dev/null || true
echo '== stderr tail =='
tail -80 '${BIBALEX_REMOTE_SLURM_ROOT}/${JOB_NAME}_${JOB_ID}.err' 2>/dev/null || true
"
