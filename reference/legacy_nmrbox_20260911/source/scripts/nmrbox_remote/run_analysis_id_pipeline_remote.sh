#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

usage() {
  cat <<'EOF'
Usage: scripts/nmrbox_remote/run_analysis_id_pipeline_remote.sh [--preflight|--submit]

Preflight is local-only: it writes an NMRbox Condor submission preview and
readiness TSV without SSH, rsync, condor_submit, or pipeline execution.

Submission requires:
  ALLOW_NMRBOX_ANALYSIS_ID_PIPELINE=1
  NMRBOX_DATA_ROOT=/home/nmrbox/0000/osoliman/.../<audited_retrieval_root>
EOF
}

MODE="submit"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --preflight)
      MODE="preflight"
      shift
      ;;
    --submit)
      MODE="submit"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

STAMP="${RUN_TAG:-$(nmrbox_job_stamp)}"
JOB_NAME="${JOB_NAME:-analysis_id_pipeline_${STAMP}}"
REQUEST_CPUS="${REQUEST_CPUS:-${NMRBOX_TARGETED_REQUEST_CPUS:-8}}"
REQUEST_MEMORY="${REQUEST_MEMORY:-${NMRBOX_TARGETED_REQUEST_MEMORY:-32GB}}"
REQUEST_DISK="${REQUEST_DISK:-${NMRBOX_TARGETED_REQUEST_DISK:-40GB}}"
TRACK="${TRACK:-all}"
DATA_ROOT="${NMRBOX_DATA_ROOT:-}"
DOWNLOADS_ROOT_REMOTE="${DOWNLOADS_ROOT_REMOTE:-${DATA_ROOT}/retrieval/downloads_timer_${TRACK}}"
OUT_ROOT_REMOTE="${OUT_ROOT_REMOTE:-${NMRBOX_REMOTE_REPO}/results/analysis_id_pipeline_${STAMP}}"
PORTABLE_R_CONDA_PREFIX="${PORTABLE_R_CONDA_PREFIX-${NMRBOX_PORTABLE_R_CONDA_PREFIX}}"
R_LIBS_USER_REMOTE="${R_LIBS_USER_REMOTE:-${NMRBOX_R_LIBS_USER:-${NMRBOX_REMOTE_ROOT}/R_libs/4.1}}"
REMOTE_JOB_DIR="${NMRBOX_REMOTE_JOBS_ROOT}/${JOB_NAME}_${STAMP}"
PREFLIGHT_DIR="${NMRBOX_PREFLIGHT_OUT:-runtime_audits/nmrbox_analysis_id_pipeline_preflight_${STAMP}}"
PREFLIGHT_TSV="${PREFLIGHT_DIR}/nmrbox_analysis_id_pipeline_preflight.tsv"
PREFLIGHT_SCRIPT="${PREFLIGHT_DIR}/run_${JOB_NAME}.sh"
PREFLIGHT_SUBMIT="${PREFLIGHT_DIR}/submit.sub"
SUBMISSION_MANIFEST="${PREFLIGHT_DIR}/nmrbox_analysis_id_submission_preview_manifest.tsv"

case "${TRACK}" in
  all|pre|delta)
    ;;
  *)
    echo "Unsupported TRACK=${TRACK}; use all, pre, or delta." >&2
    exit 2
    ;;
esac

write_remote_script() {
  local target="$1"
  cat > "${target}" <<EOF_REMOTE
#!/usr/bin/env bash
set -euo pipefail

export PYTHONNOUSERSITE=1
cd '${NMRBOX_REMOTE_REPO}'
export PYTHON_BIN='${NMRBOX_PYTHON_BIN}'
export PATH="\$(dirname "\${PYTHON_BIN}"):\${PATH}"
export PYTHONPYCACHEPREFIX="\${PYTHONPYCACHEPREFIX:-/tmp/ici_pycache_\${USER:-unknown}_\$\$}"
export MPLCONFIGDIR="\${MPLCONFIGDIR:-${REMOTE_JOB_DIR}/matplotlib}"
export R_LIBS_USER='${R_LIBS_USER_REMOTE}'
mkdir -p "\${R_LIBS_USER}"
export PORTABLE_R_CONDA_PREFIX='${PORTABLE_R_CONDA_PREFIX}'
if [[ -n "\${PORTABLE_R_CONDA_PREFIX:-}" && -x "\${PORTABLE_R_CONDA_PREFIX}/bin/Rscript" ]]; then
  export PATH="\${PORTABLE_R_CONDA_PREFIX}/bin:\${PATH}"
fi
export RUN_TAG='${STAMP}'
export OUT_ROOT='${OUT_ROOT_REMOTE}'
export SAMPLE_MANIFEST='${SAMPLE_MANIFEST:-configs/sample_manifest_curated.tsv}'
export EXPRESSION_MANIFEST='${EXPRESSION_MANIFEST:-results/geo_tables/geo_tables_summary.tsv}'
export DOWNLOADS_ROOT='${DOWNLOADS_ROOT_REMOTE}'
export GENE_ID_MAPPING='${GENE_ID_MAPPING:-configs/gene_id_mapping_human.tsv}'
export GENE_SET_REGISTRY='${GENE_SET_REGISTRY:-configs/immune_gene_sets_registry.tsv}'
export CRITERIA_REGISTRY='${CRITERIA_REGISTRY:-configs/immunophenotype_criteria_registry.tsv}'
export COUNT_METHOD='${COUNT_METHOD:-deseq2}'
export RUN_MANIFEST="\${OUT_ROOT}/logs/run_manifest.yaml"
export ALLOW_ANALYSIS_ID_PIPELINE_RUN=1
export PILOT_ONLY='${PILOT_ONLY:-0}'
export ANALYSIS_IDS='${ANALYSIS_IDS:-}'
export TCGA_MAP='${TCGA_MAP:-}'
export NAIVE_MANIFEST='${NAIVE_MANIFEST:-}'
export THORSSON_SUBTYPES='${THORSSON_SUBTYPES:-}'
export ALLOW_EMPTY_SIGNATURE='${ALLOW_EMPTY_SIGNATURE:-1}'
export ALLOW_WEAK_GENE_MAPPING='${ALLOW_WEAK_GENE_MAPPING:-0}'
export ALLOW_WELCH_FALLBACK='${ALLOW_WELCH_FALLBACK:-0}'

mkdir -p "\${OUT_ROOT}/orchestration" "\${OUT_ROOT}/logs" '${REMOTE_JOB_DIR}/logs' "\${MPLCONFIGDIR}"
{
  printf 'key\tvalue\n'
  printf 'backend\tnmrbox_condor_single_job\n'
  printf 'condor_cluster_id\t%s\n' "\${CLUSTER:-unknown}"
  printf 'condor_process_id\t%s\n' "\${PROCESS:-unknown}"
  printf 'job_name\t%s\n' '${JOB_NAME}'
  printf 'run_tag\t%s\n' "\${RUN_TAG}"
  printf 'out_root\t%s\n' "\${OUT_ROOT}"
  printf 'remote_job_dir\t%s\n' '${REMOTE_JOB_DIR}'
  printf 'downloads_root\t%s\n' "\${DOWNLOADS_ROOT}"
  printf 'portable_r_conda_prefix\t%s\n' "\${PORTABLE_R_CONDA_PREFIX:-<unset>}"
  printf 'r_libs_user\t%s\n' "\${R_LIBS_USER:-<unset>}"
  printf 'sample_manifest\t%s\n' "\${SAMPLE_MANIFEST}"
  printf 'expression_manifest\t%s\n' "\${EXPRESSION_MANIFEST}"
  printf 'gene_id_mapping\t%s\n' "\${GENE_ID_MAPPING}"
  printf 'gene_set_registry\t%s\n' "\${GENE_SET_REGISTRY}"
  printf 'criteria_registry\t%s\n' "\${CRITERIA_REGISTRY}"
  printf 'count_method\t%s\n' "\${COUNT_METHOD}"
  printf 'analysis_ids\t%s\n' "\${ANALYSIS_IDS:-<unset>}"
  printf 'pilot_only\t%s\n' "\${PILOT_ONLY}"
  printf 'tcga_map\t%s\n' "\${TCGA_MAP:-<unset>}"
  printf 'allow_empty_signature\t%s\n' "\${ALLOW_EMPTY_SIGNATURE}"
  printf 'allow_weak_gene_mapping\t%s\n' "\${ALLOW_WEAK_GENE_MAPPING}"
  printf 'allow_welch_fallback\t%s\n' "\${ALLOW_WELCH_FALLBACK}"
  printf 'request_cpus\t%s\n' '${REQUEST_CPUS}'
  printf 'request_memory\t%s\n' '${REQUEST_MEMORY}'
  printf 'request_disk\t%s\n' '${REQUEST_DISK}'
  printf 'execution_gate\tALLOW_NMRBOX_ANALYSIS_ID_PIPELINE=1 outer gate; ALLOW_ANALYSIS_ID_PIPELINE_RUN=1 inner gate\n'
  printf 'claim_boundary\tspec027 claims are discovery/mechanism_hypothesis only; TCGA prognostic only; LOCO internal only\n'
  printf 'track_boundary\tTrack A derivation remains separate from Track B external candidates\n'
} > "\${OUT_ROOT}/orchestration/nmrbox_condor_submission_manifest.tsv"

bash scripts/run_analysis_id_pipeline.sh --execute
EOF_REMOTE
}

write_submit_file() {
  local target="$1"
  cat > "${target}" <<EOF_SUB
universe = vanilla
executable = run_${JOB_NAME}.sh
arguments =

output = ${REMOTE_JOB_DIR}/condor.\$(Cluster).\$(Process).out
error = ${REMOTE_JOB_DIR}/condor.\$(Cluster).\$(Process).err
log = ${REMOTE_JOB_DIR}/condor.\$(Cluster).log

request_cpus = ${REQUEST_CPUS}
request_memory = ${REQUEST_MEMORY}
request_disk = ${REQUEST_DISK}

getenv = True
environment = "CLUSTER=\$(Cluster) PROCESS=\$(Process)"
+JobBatchName = "${JOB_NAME}"

queue 1
EOF_SUB
}

preflight_status=0
preflight_check() {
  local check_name="$1"
  local status="$2"
  local detail="$3"
  printf '%s\t%s\t%s\n' "${check_name}" "${status}" "${detail}" >> "${PREFLIGHT_TSV}"
  if [[ "${status}" != "pass" && "${status}" != "warn" ]]; then
    preflight_status=1
  fi
}

write_submission_manifest() {
  {
    printf 'key\tvalue\n'
    printf 'mode\t%s\n' "${MODE}"
    printf 'network_action_preflight\tnone\n'
    printf 'ssh_host\t%s\n' "${NMRBOX_SSH_HOST}"
    printf 'remote_repo\t%s\n' "${NMRBOX_REMOTE_REPO}"
    printf 'remote_job_dir\t%s\n' "${REMOTE_JOB_DIR}"
    printf 'out_root_remote\t%s\n' "${OUT_ROOT_REMOTE}"
    printf 'data_root\t%s\n' "${DATA_ROOT:-<unset>}"
    printf 'downloads_root_remote\t%s\n' "${DOWNLOADS_ROOT_REMOTE:-<unset>}"
    printf 'run_tag\t%s\n' "${STAMP}"
    printf 'track\t%s\n' "${TRACK}"
    printf 'job_name\t%s\n' "${JOB_NAME}"
    printf 'request_cpus\t%s\n' "${REQUEST_CPUS}"
    printf 'request_memory\t%s\n' "${REQUEST_MEMORY}"
    printf 'request_disk\t%s\n' "${REQUEST_DISK}"
    printf 'portable_r_conda_prefix\t%s\n' "${PORTABLE_R_CONDA_PREFIX:-<unset>}"
    printf 'r_libs_user\t%s\n' "${R_LIBS_USER_REMOTE:-<unset>}"
    printf 'python_bin\t%s\n' "${NMRBOX_PYTHON_BIN}"
    printf 'sample_manifest\t%s\n' "${SAMPLE_MANIFEST:-configs/sample_manifest_curated.tsv}"
    printf 'expression_manifest\t%s\n' "${EXPRESSION_MANIFEST:-results/geo_tables/geo_tables_summary.tsv}"
    printf 'gene_id_mapping\t%s\n' "${GENE_ID_MAPPING:-configs/gene_id_mapping_human.tsv}"
    printf 'gene_set_registry\t%s\n' "${GENE_SET_REGISTRY:-configs/immune_gene_sets_registry.tsv}"
    printf 'criteria_registry\t%s\n' "${CRITERIA_REGISTRY:-configs/immunophenotype_criteria_registry.tsv}"
    printf 'count_method\t%s\n' "${COUNT_METHOD:-deseq2}"
    printf 'allow_empty_signature\t%s\n' "${ALLOW_EMPTY_SIGNATURE:-1}"
    printf 'allow_weak_gene_mapping\t%s\n' "${ALLOW_WEAK_GENE_MAPPING:-0}"
    printf 'allow_welch_fallback\t%s\n' "${ALLOW_WELCH_FALLBACK:-0}"
    printf 'analysis_ids\t%s\n' "${ANALYSIS_IDS:-<unset>}"
    printf 'pilot_only\t%s\n' "${PILOT_ONLY:-0}"
    printf 'tcga_map\t%s\n' "${TCGA_MAP:-<unset>}"
    printf 'naive_manifest\t%s\n' "${NAIVE_MANIFEST:-<unset>}"
    printf 'thorsson_subtypes\t%s\n' "${THORSSON_SUBTYPES:-<unset>}"
    printf 'execution_gate\tALLOW_NMRBOX_ANALYSIS_ID_PIPELINE=1 required for --submit\n'
    printf 'inner_execution_gate\tALLOW_ANALYSIS_ID_PIPELINE_RUN=1 set inside remote job\n'
    printf 'reviewed_root_guard\tOUT_ROOT_REMOTE must not target the committed reviewed root\n'
    printf 'claim_boundary\tspec 027 claims are discovery/mechanism-hypothesis only; TCGA prognostic only; LOCO internal only\n'
    printf 'track_boundary\tTrack A signature derivation remains separate from Track B external candidates\n'
  } > "${SUBMISSION_MANIFEST}"
}

run_preflight() {
  mkdir -p "${PREFLIGHT_DIR}"
  printf 'check\tstatus\tdetail\n' > "${PREFLIGHT_TSV}"
  preflight_check mode pass "${MODE}"
  preflight_check ssh_host pass "${NMRBOX_SSH_HOST}"
  preflight_check remote_repo pass "${NMRBOX_REMOTE_REPO}"
  preflight_check remote_job_dir pass "${REMOTE_JOB_DIR}"
  preflight_check out_root_remote pass "${OUT_ROOT_REMOTE}"
  preflight_check condor_resources pass "cpus=${REQUEST_CPUS};memory=${REQUEST_MEMORY};disk=${REQUEST_DISK}"
  if [[ -n "${DATA_ROOT}" ]]; then
    preflight_check data_root pass "${DATA_ROOT}"
    preflight_check downloads_root pass "${DOWNLOADS_ROOT_REMOTE}"
  else
    preflight_check data_root fail "Set NMRBOX_DATA_ROOT to the audited remote retrieval root before submission."
  fi
  if [[ "${OUT_ROOT_REMOTE}" == *analysis_id_runs_t7_20260607_stage07_scale_provenance* ]]; then
    preflight_check reviewed_root_guard fail "OUT_ROOT_REMOTE targets the committed reviewed root."
  else
    preflight_check reviewed_root_guard pass "OUT_ROOT_REMOTE is a new analysis-id pipeline root."
  fi
  if [[ -n "${PORTABLE_R_CONDA_PREFIX}" ]]; then
    preflight_check portable_r pass "${PORTABLE_R_CONDA_PREFIX}"
  else
    preflight_check portable_r warn "PORTABLE_R_CONDA_PREFIX unset; remote execution will rely on PATH Rscript."
  fi
  write_remote_script "${PREFLIGHT_SCRIPT}"
  chmod +x "${PREFLIGHT_SCRIPT}"
  write_submit_file "${PREFLIGHT_SUBMIT}"
  preflight_check local_preview_script pass "${PREFLIGHT_SCRIPT}"
  preflight_check local_submit_file pass "${PREFLIGHT_SUBMIT}"
  write_submission_manifest
  preflight_check submission_preview_manifest pass "${SUBMISSION_MANIFEST}"
}

if [[ "${MODE}" == "preflight" ]]; then
  run_preflight
  printf 'mode\t%s\n' "${MODE}"
  printf 'preflight_tsv\t%s\n' "${PREFLIGHT_TSV}"
  printf 'preview_script\t%s\n' "${PREFLIGHT_SCRIPT}"
  printf 'submit_file\t%s\n' "${PREFLIGHT_SUBMIT}"
  printf 'submission_manifest\t%s\n' "${SUBMISSION_MANIFEST}"
  if [[ "${preflight_status}" -eq 0 ]]; then
    printf 'preflight_status\tpass\n'
  else
    printf 'preflight_status\tfail\n'
  fi
  exit "${preflight_status}"
fi

if [[ "${ALLOW_NMRBOX_ANALYSIS_ID_PIPELINE:-0}" != "1" ]]; then
  echo "Refusing NMRbox analysis-id pipeline submission because ALLOW_NMRBOX_ANALYSIS_ID_PIPELINE is not 1." >&2
  echo "Ask for explicit approval before any HPC action or full pipeline run." >&2
  exit 3
fi

if [[ -z "${DATA_ROOT}" ]]; then
  echo "Set NMRBOX_DATA_ROOT to the audited remote retrieval root." >&2
  exit 2
fi

LOCAL_TMP="$(mktemp -d "${TMPDIR:-/tmp}/nmrbox_analysis_id_pipeline.XXXXXX")"
write_remote_script "${LOCAL_TMP}/run_${JOB_NAME}.sh"
write_submit_file "${LOCAL_TMP}/submit.sub"
chmod +x "${LOCAL_TMP}/run_${JOB_NAME}.sh"

nmrbox_ssh "mkdir -p '${REMOTE_JOB_DIR}'"
rsync -av "${LOCAL_TMP}/" "${NMRBOX_SSH_HOST}:${REMOTE_JOB_DIR}/"
SUBMIT_OUTPUT="$(nmrbox_ssh "cd '${REMOTE_JOB_DIR}' && condor_submit submit.sub")"
printf '%s\n' "${SUBMIT_OUTPUT}"
CLUSTER_ID="$(printf '%s\n' "${SUBMIT_OUTPUT}" | awk '/submitted to cluster/ {gsub(/\./, "", $NF); print $NF; exit}')"

printf 'cluster_id\t%s\n' "${CLUSTER_ID:-unknown}"
printf 'remote_job_dir\t%s\n' "${REMOTE_JOB_DIR}"
printf 'out_root\t%s\n' "${OUT_ROOT_REMOTE}"
printf 'downloads_root\t%s\n' "${DOWNLOADS_ROOT_REMOTE}"
printf 'track\t%s\n' "${TRACK}"
printf 'stdout\t%s/condor.<cluster>.0.out\n' "${REMOTE_JOB_DIR}"
printf 'stderr\t%s/condor.<cluster>.0.err\n' "${REMOTE_JOB_DIR}"
printf 'log\t%s/condor.<cluster>.log\n' "${REMOTE_JOB_DIR}"
