#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

usage() {
  cat <<'EOF'
Usage: scripts/bibalex_hpc/run_analysis_id_pipeline.sh [--preflight|--submit]

Preflight is local-only: it writes a BibaLex submission preview and readiness TSV
without SSH, scp, sbatch, or full pipeline execution.

Submission requires:
  ALLOW_BIBALEX_ANALYSIS_ID_PIPELINE=1
  BIBALEX_DATA_ROOT=/cluster/users/<user>/.../<audited_retrieval_root>
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

bibalex_require_remote_root

STAMP="${RUN_TAG:-$(bibalex_stamp)}"
JOB_NAME="${JOB_NAME:-analysis_id_pipeline_${STAMP}}"
REQUEST_CPUS="${REQUEST_CPUS:-8}"
REQUEST_MEM="${REQUEST_MEM:-48G}"
REQUEST_TIME="${REQUEST_TIME:-24:00:00}"
TRACK="${TRACK:-all}"
DATA_ROOT="${BIBALEX_DATA_ROOT:-}"
DOWNLOADS_ROOT_REMOTE="${DOWNLOADS_ROOT_REMOTE:-${DATA_ROOT}/retrieval/downloads_timer_${TRACK}}"
OUT_ROOT_REMOTE="${OUT_ROOT_REMOTE:-${BIBALEX_REMOTE_REPO}/results/analysis_id_pipeline_${STAMP}}"
PORTABLE_R_CONDA_PREFIX="${PORTABLE_R_CONDA_PREFIX:-${BIBALEX_PORTABLE_R_CONDA_PREFIX}}"
REMOTE_SCRIPT="${BIBALEX_REMOTE_SCRIPTS_ROOT}/run_${JOB_NAME}.sh"
PREFLIGHT_DIR="${BIBALEX_PREFLIGHT_OUT:-runtime_audits/bibalex_analysis_id_pipeline_preflight_${STAMP}}"
PREFLIGHT_TSV="${PREFLIGHT_DIR}/bibalex_analysis_id_pipeline_preflight.tsv"
PREFLIGHT_SCRIPT="${PREFLIGHT_DIR}/run_${JOB_NAME}.sh"
SUBMISSION_MANIFEST="${PREFLIGHT_DIR}/bibalex_analysis_id_submission_preview_manifest.tsv"

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
PY_IN_ENV="\$('${BIBALEX_CONDA_BIN}' run -n '${BIBALEX_CONDA_ENV}' python - <<'PY'
import sys
print(sys.executable)
PY
)"
export PYTHON_BIN="\${PY_IN_ENV}"
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
mkdir -p "\${OUT_ROOT}/orchestration"
{
  printf 'key\tvalue\n'
  printf 'backend\tbibalex_single_job\n'
  printf 'slurm_job_id\t%s\n' "\${SLURM_JOB_ID:-unknown}"
  printf 'job_name\t%s\n' '${JOB_NAME}'
  printf 'run_tag\t%s\n' "\${RUN_TAG}"
  printf 'out_root\t%s\n' "\${OUT_ROOT}"
  printf 'downloads_root\t%s\n' "\${DOWNLOADS_ROOT}"
  printf 'portable_r_conda_prefix\t%s\n' "\${PORTABLE_R_CONDA_PREFIX:-<unset>}"
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
  printf 'execution_gate\tALLOW_BIBALEX_ANALYSIS_ID_PIPELINE=1 outer gate; ALLOW_ANALYSIS_ID_PIPELINE_RUN=1 inner gate\n'
  printf 'claim_boundary\tspec027 claims are discovery/mechanism_hypothesis only; TCGA prognostic only; LOCO internal only\n'
  printf 'track_boundary\tTrack A derivation remains separate from Track B external candidates\n'
} > "\${OUT_ROOT}/orchestration/bibalex_singlejob_submission_manifest.tsv"
bash scripts/run_analysis_id_pipeline.sh --execute
EOF_REMOTE
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
    printf 'ssh_host\t%s\n' "${BIBALEX_SSH_HOST}"
    printf 'remote_root\t%s\n' "${BIBALEX_REMOTE_ROOT}"
    printf 'remote_repo\t%s\n' "${BIBALEX_REMOTE_REPO}"
    printf 'remote_script\t%s\n' "${REMOTE_SCRIPT}"
    printf 'out_root_remote\t%s\n' "${OUT_ROOT_REMOTE}"
    printf 'data_root\t%s\n' "${DATA_ROOT:-<unset>}"
    printf 'downloads_root_remote\t%s\n' "${DOWNLOADS_ROOT_REMOTE:-<unset>}"
    printf 'run_tag\t%s\n' "${STAMP}"
    printf 'track\t%s\n' "${TRACK}"
    printf 'job_name\t%s\n' "${JOB_NAME}"
    printf 'slurm_partition\t%s\n' "${BIBALEX_SLURM_PARTITION}"
    printf 'slurm_cpus\t%s\n' "${REQUEST_CPUS}"
    printf 'slurm_mem\t%s\n' "${REQUEST_MEM}"
    printf 'slurm_time\t%s\n' "${REQUEST_TIME}"
    printf 'slurm_stdout\t%s/%s_<job_id>.out\n' "${BIBALEX_REMOTE_SLURM_ROOT}" "${JOB_NAME}"
    printf 'slurm_stderr\t%s/%s_<job_id>.err\n' "${BIBALEX_REMOTE_SLURM_ROOT}" "${JOB_NAME}"
    printf 'portable_r_conda_prefix\t%s\n' "${PORTABLE_R_CONDA_PREFIX:-<unset>}"
    printf 'conda_bin\t%s\n' "${BIBALEX_CONDA_BIN}"
    printf 'conda_env\t%s\n' "${BIBALEX_CONDA_ENV}"
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
    printf 'execution_gate\tALLOW_BIBALEX_ANALYSIS_ID_PIPELINE=1 required for --submit\n'
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
  preflight_check ssh_host pass "${BIBALEX_SSH_HOST}"
  preflight_check remote_root pass "${BIBALEX_REMOTE_ROOT}"
  preflight_check remote_repo pass "${BIBALEX_REMOTE_REPO}"
  preflight_check remote_script pass "${REMOTE_SCRIPT}"
  preflight_check out_root_remote pass "${OUT_ROOT_REMOTE}"
  preflight_check slurm_resources pass "partition=${BIBALEX_SLURM_PARTITION};cpus=${REQUEST_CPUS};mem=${REQUEST_MEM};time=${REQUEST_TIME}"
  if [[ -n "${DATA_ROOT}" ]]; then
    preflight_check data_root pass "${DATA_ROOT}"
    preflight_check downloads_root pass "${DOWNLOADS_ROOT_REMOTE}"
  else
    preflight_check data_root fail "Set BIBALEX_DATA_ROOT to the audited remote retrieval root before submission."
  fi
  if [[ "${OUT_ROOT_REMOTE}" == *analysis_id_runs_t7_20260607_stage07_scale_provenance* ]]; then
    preflight_check reviewed_root_guard fail "OUT_ROOT_REMOTE targets the committed reviewed root."
  else
    preflight_check reviewed_root_guard pass "OUT_ROOT_REMOTE is a new analysis-id pipeline root."
  fi
  if [[ -n "${PORTABLE_R_CONDA_PREFIX}" ]]; then
    preflight_check portable_r pass "${PORTABLE_R_CONDA_PREFIX}"
  else
    preflight_check portable_r warn "PORTABLE_R_CONDA_PREFIX unset; remote execution will rely on PATH/module R."
  fi
  write_remote_script "${PREFLIGHT_SCRIPT}"
  chmod +x "${PREFLIGHT_SCRIPT}"
  preflight_check local_preview_script pass "${PREFLIGHT_SCRIPT}"
  write_submission_manifest
  preflight_check submission_preview_manifest pass "${SUBMISSION_MANIFEST}"
}

if [[ "${MODE}" == "preflight" ]]; then
  run_preflight
  printf 'mode\t%s\n' "${MODE}"
  printf 'preflight_tsv\t%s\n' "${PREFLIGHT_TSV}"
  printf 'preview_script\t%s\n' "${PREFLIGHT_SCRIPT}"
  printf 'submission_manifest\t%s\n' "${SUBMISSION_MANIFEST}"
  if [[ "${preflight_status}" -eq 0 ]]; then
    printf 'preflight_status\tpass\n'
  else
    printf 'preflight_status\tfail\n'
  fi
  exit "${preflight_status}"
fi

if [[ "${ALLOW_BIBALEX_ANALYSIS_ID_PIPELINE:-0}" != "1" ]]; then
  echo "Refusing BibaLex analysis-id pipeline submission because ALLOW_BIBALEX_ANALYSIS_ID_PIPELINE is not 1." >&2
  echo "Ask for explicit approval before any HPC action or full pipeline run." >&2
  exit 3
fi

if [[ -z "${DATA_ROOT}" ]]; then
  echo "Set BIBALEX_DATA_ROOT to the audited remote retrieval root." >&2
  exit 2
fi

bibalex_ssh "mkdir -p '${BIBALEX_REMOTE_SCRIPTS_ROOT}' '${BIBALEX_REMOTE_SLURM_ROOT}' && chmod 700 '${BIBALEX_REMOTE_ROOT}'"

write_remote_script /tmp/ici_bibalex_analysis_id_pipeline.sh

scp /tmp/ici_bibalex_analysis_id_pipeline.sh "${BIBALEX_SSH_HOST}:${REMOTE_SCRIPT}"
JOB_ID="$(bibalex_ssh "chmod +x '${REMOTE_SCRIPT}' && sbatch --parsable '${REMOTE_SCRIPT}'")"

printf 'job_id\t%s\n' "${JOB_ID}"
printf 'remote_script\t%s\n' "${REMOTE_SCRIPT}"
printf 'out_root\t%s\n' "${OUT_ROOT_REMOTE}"
printf 'downloads_root\t%s\n' "${DOWNLOADS_ROOT_REMOTE}"
printf 'track\t%s\n' "${TRACK}"
printf 'stdout\t%s/%s_%s.out\n' "${BIBALEX_REMOTE_SLURM_ROOT}" "${JOB_NAME}" "${JOB_ID}"
printf 'stderr\t%s/%s_%s.err\n' "${BIBALEX_REMOTE_SLURM_ROOT}" "${JOB_NAME}" "${JOB_ID}"
