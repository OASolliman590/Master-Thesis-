#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

if [[ "${ALLOW_BIBALEX_DATA_DOWNLOAD:-0}" != "1" ]]; then
  echo "Refusing full BibaLex processed GEO/SRA retrieval because ALLOW_BIBALEX_DATA_DOWNLOAD is not 1." >&2
  echo "Run and audit the health job first, then set ALLOW_BIBALEX_DATA_DOWNLOAD=1." >&2
  exit 3
fi

TRACK="${TRACK:-all}"
STAMP="${BIBALEX_DATA_STAMP:-$(bibalex_stamp)}"
DATA_ROOT="${BIBALEX_DATA_ROOT:-${BIBALEX_REMOTE_DATA_ROOT}/geo_retrieval_${STAMP}}"
JOB_NAME="${JOB_NAME:-geo_retrieval_full_${TRACK}}"
REQUEST_CPUS="${REQUEST_CPUS:-4}"
REQUEST_MEM="${REQUEST_MEM:-16G}"
REQUEST_TIME="${REQUEST_TIME:-08:00:00}"

case "${TRACK}" in
  all|pre|delta)
    ;;
  *)
    echo "Unsupported TRACK=${TRACK}; use all, pre, or delta." >&2
    exit 2
    ;;
esac

bibalex_require_remote_root

REMOTE_SCRIPT="${BIBALEX_REMOTE_SCRIPTS_ROOT}/run_${JOB_NAME}.sh"

bibalex_ssh "mkdir -p '${BIBALEX_REMOTE_SCRIPTS_ROOT}' '${BIBALEX_REMOTE_SLURM_ROOT}' '${DATA_ROOT}' && chmod 700 '${BIBALEX_REMOTE_ROOT}'"

cat > /tmp/ici_bibalex_geo_full.sh <<EOF_REMOTE
#!/usr/bin/env bash
#SBATCH --job-name=${JOB_NAME}
#SBATCH --partition=${BIBALEX_SLURM_PARTITION}
#SBATCH --cpus-per-task=${REQUEST_CPUS}
#SBATCH --mem=${REQUEST_MEM}
#SBATCH --time=${REQUEST_TIME}
#SBATCH --output=${BIBALEX_REMOTE_SLURM_ROOT}/${JOB_NAME}_%j.out
#SBATCH --error=${BIBALEX_REMOTE_SLURM_ROOT}/${JOB_NAME}_%j.err

set -euo pipefail
export PYTHONNOUSERSITE=1
cd '${BIBALEX_REMOTE_REPO}'
echo "conda_bin	${BIBALEX_CONDA_BIN}"
echo "conda_env	${BIBALEX_CONDA_ENV}"
echo "data_root	${DATA_ROOT}"
echo "track	${TRACK}"
'${BIBALEX_CONDA_BIN}' run -n '${BIBALEX_CONDA_ENV}' bash scripts/run_timer_t7_download_full.sh '${DATA_ROOT}' --track=${TRACK}
EOF_REMOTE

scp /tmp/ici_bibalex_geo_full.sh "${BIBALEX_SSH_HOST}:${REMOTE_SCRIPT}"
JOB_ID="$(bibalex_ssh "chmod +x '${REMOTE_SCRIPT}' && sbatch --parsable '${REMOTE_SCRIPT}'")"

printf 'job_id\t%s\n' "${JOB_ID}"
printf 'remote_script\t%s\n' "${REMOTE_SCRIPT}"
printf 'data_root\t%s\n' "${DATA_ROOT}"
printf 'track\t%s\n' "${TRACK}"
printf 'mode\t%s\n' "full-processed-retrieval"
printf 'stdout\t%s/%s_%s.out\n' "${BIBALEX_REMOTE_SLURM_ROOT}" "${JOB_NAME}" "${JOB_ID}"
printf 'stderr\t%s/%s_%s.err\n' "${BIBALEX_REMOTE_SLURM_ROOT}" "${JOB_NAME}" "${JOB_ID}"
