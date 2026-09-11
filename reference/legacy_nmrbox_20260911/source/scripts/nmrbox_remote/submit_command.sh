#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

JOB_NAME="${JOB_NAME:-ici_remote_command}"
REQUEST_CPUS="${REQUEST_CPUS:-${NMRBOX_REQUEST_CPUS}}"
REQUEST_MEMORY="${REQUEST_MEMORY:-${NMRBOX_REQUEST_MEMORY}}"
REQUEST_DISK="${REQUEST_DISK:-${NMRBOX_REQUEST_DISK}}"
REMOTE_EXECUTION_CLASS="${REMOTE_EXECUTION_CLASS:-canary}"
PYTHON_BIN_REMOTE="${PYTHON_BIN_REMOTE:-${NMRBOX_PYTHON_BIN}}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --job-name)
      JOB_NAME="$2"
      shift 2
      ;;
    --class)
      REMOTE_EXECUTION_CLASS="$2"
      shift 2
      ;;
    --cpus)
      REQUEST_CPUS="$2"
      shift 2
      ;;
    --memory)
      REQUEST_MEMORY="$2"
      shift 2
      ;;
    --disk)
      REQUEST_DISK="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

nmrbox_require_remote_cmd
nmrbox_validate_execution_class

STAMP="$(nmrbox_job_stamp)"
REMOTE_JOB_DIR="${NMRBOX_REMOTE_JOBS_ROOT}/${JOB_NAME}_${STAMP}"
LOCAL_TMP="$(mktemp -d "${TMPDIR:-/tmp}/nmrbox_remote_job.XXXXXX")"

cat > "${LOCAL_TMP}/run_remote_command.sh" <<EOF_RUN
#!/usr/bin/env bash
set -euo pipefail
cd "${NMRBOX_REMOTE_REPO}"
export PYTHON_BIN="${PYTHON_BIN_REMOTE}"
export PATH="\$(dirname "\${PYTHON_BIN}"):\${PATH}"
export PYTHONPYCACHEPREFIX="\${PYTHONPYCACHEPREFIX:-/tmp/ici_pycache_\${USER:-unknown}_\$\$}"
export MPLCONFIGDIR="\${MPLCONFIGDIR:-${REMOTE_JOB_DIR}/matplotlib}"
mkdir -p "\${MPLCONFIGDIR}" "${REMOTE_JOB_DIR}/logs"
{
  echo "job_name	${JOB_NAME}"
  echo "execution_class	${REMOTE_EXECUTION_CLASS}"
  echo "host	\$(hostname)"
  echo "started_utc	\$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "workdir	\$(pwd)"
  echo "python_bin	\${PYTHON_BIN}"
  echo "python_resolved	\$(command -v python || true)"
  echo "remote_cmd	${REMOTE_CMD}"
} > "${REMOTE_JOB_DIR}/remote_job_metadata.tsv"
${REMOTE_CMD}
echo "finished_utc	\$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${REMOTE_JOB_DIR}/remote_job_metadata.tsv"
EOF_RUN

chmod +x "${LOCAL_TMP}/run_remote_command.sh"

cat > "${LOCAL_TMP}/submit.sub" <<EOF_SUB
universe = vanilla
executable = run_remote_command.sh
arguments =

output = ${REMOTE_JOB_DIR}/condor.\$(Cluster).\$(Process).out
error = ${REMOTE_JOB_DIR}/condor.\$(Cluster).\$(Process).err
log = ${REMOTE_JOB_DIR}/condor.\$(Cluster).log

request_cpus = ${REQUEST_CPUS}
request_memory = ${REQUEST_MEMORY}
request_disk = ${REQUEST_DISK}

getenv = True
+JobBatchName = "${JOB_NAME}"

queue 1
EOF_SUB

nmrbox_ssh "mkdir -p '${REMOTE_JOB_DIR}'"
rsync -av "${LOCAL_TMP}/" "${NMRBOX_SSH_HOST}:${REMOTE_JOB_DIR}/"
nmrbox_ssh "cd '${REMOTE_JOB_DIR}' && condor_submit submit.sub"

printf 'remote_job_dir\t%s\n' "${REMOTE_JOB_DIR}"
printf 'job_name\t%s\n' "${JOB_NAME}"
printf 'execution_class\t%s\n' "${REMOTE_EXECUTION_CLASS}"
printf 'request_cpus\t%s\n' "${REQUEST_CPUS}"
printf 'request_memory\t%s\n' "${REQUEST_MEMORY}"
printf 'request_disk\t%s\n' "${REQUEST_DISK}"
