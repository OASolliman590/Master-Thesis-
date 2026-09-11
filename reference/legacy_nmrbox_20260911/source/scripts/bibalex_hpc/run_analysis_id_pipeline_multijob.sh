#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

usage() {
  cat <<'EOF'
Usage: scripts/bibalex_hpc/run_analysis_id_pipeline_multijob.sh [--preflight|--submit-multijob]

Preflight is local-only: it writes a BibaLex multi-job submission preview and
dependency-aware Slurm scripts without SSH, scp, sbatch, or full pipeline execution.

Submission requires:
  ALLOW_BIBALEX_ANALYSIS_ID_MULTIJOB=1
  BIBALEX_DATA_ROOT=/cluster/users/<user>/.../<audited_retrieval_root>

This is the staged Slurm alternative to run_analysis_id_pipeline.sh:
  design -> fanout -> per-analysis jobs + immune job -> final interpretation/report
EOF
}

MODE="submit-multijob"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --preflight)
      MODE="preflight"
      shift
      ;;
    --submit-multijob)
      MODE="submit-multijob"
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
ANALYSIS_CPUS="${ANALYSIS_CPUS:-8}"
ANALYSIS_MEM="${ANALYSIS_MEM:-48G}"
ANALYSIS_TIME="${ANALYSIS_TIME:-24:00:00}"
FINAL_CPUS="${FINAL_CPUS:-4}"
FINAL_MEM="${FINAL_MEM:-24G}"
FINAL_TIME="${FINAL_TIME:-08:00:00}"
TRACK="${TRACK:-all}"
DATA_ROOT="${BIBALEX_DATA_ROOT:-}"
DOWNLOADS_ROOT_REMOTE="${DOWNLOADS_ROOT_REMOTE:-${DATA_ROOT}/retrieval/downloads_timer_${TRACK}}"
OUT_ROOT_REMOTE="${OUT_ROOT_REMOTE:-${BIBALEX_REMOTE_REPO}/results/analysis_id_pipeline_${STAMP}}"
PORTABLE_R_CONDA_PREFIX="${PORTABLE_R_CONDA_PREFIX:-${BIBALEX_PORTABLE_R_CONDA_PREFIX}}"
PREFLIGHT_DIR="${BIBALEX_PREFLIGHT_OUT:-runtime_audits/bibalex_analysis_id_pipeline_multijob_preflight_${STAMP}}"
PREFLIGHT_TSV="${PREFLIGHT_DIR}/bibalex_analysis_id_multijob_preflight.tsv"
SUBMISSION_MANIFEST="${PREFLIGHT_DIR}/bibalex_analysis_id_multijob_submission_preview_manifest.tsv"

REMOTE_PREFIX="${BIBALEX_REMOTE_SCRIPTS_ROOT}/${JOB_NAME}"
REMOTE_DESIGN_SCRIPT="${REMOTE_PREFIX}_00_design.sh"
REMOTE_FANOUT_SCRIPT="${REMOTE_PREFIX}_10_submit_fanout.sh"
REMOTE_ANALYSIS_SCRIPT="${REMOTE_PREFIX}_20_analysis_task.sh"
REMOTE_IMMUNE_SCRIPT="${REMOTE_PREFIX}_30_immune_task.sh"
REMOTE_FINALIZE_SCRIPT="${REMOTE_PREFIX}_40_finalize.sh"
REMOTE_SUBMITTER="${BIBALEX_REMOTE_SCRIPTS_ROOT}/submit_${JOB_NAME}.sh"

LOCAL_DESIGN_SCRIPT="${PREFLIGHT_DIR}/${JOB_NAME}_00_design.sh"
LOCAL_FANOUT_SCRIPT="${PREFLIGHT_DIR}/${JOB_NAME}_10_submit_fanout.sh"
LOCAL_ANALYSIS_SCRIPT="${PREFLIGHT_DIR}/${JOB_NAME}_20_analysis_task.sh"
LOCAL_IMMUNE_SCRIPT="${PREFLIGHT_DIR}/${JOB_NAME}_30_immune_task.sh"
LOCAL_FINALIZE_SCRIPT="${PREFLIGHT_DIR}/${JOB_NAME}_40_finalize.sh"
LOCAL_SUBMITTER="${PREFLIGHT_DIR}/submit_${JOB_NAME}.sh"

case "${TRACK}" in
  all|pre|delta)
    ;;
  *)
    echo "Unsupported TRACK=${TRACK}; use all, pre, or delta." >&2
    exit 2
    ;;
esac

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

write_remote_env_block() {
  cat <<EOF_ENV
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
export ANALYSIS_IDS='${ANALYSIS_IDS:-}'
export PILOT_ONLY='${PILOT_ONLY:-0}'
export TCGA_MAP='${TCGA_MAP:-}'
export NAIVE_MANIFEST='${NAIVE_MANIFEST:-}'
export THORSSON_SUBTYPES='${THORSSON_SUBTYPES:-}'
export ALLOW_ANALYSIS_ID_PIPELINE_RUN=1
export ALLOW_EMPTY_SIGNATURE='${ALLOW_EMPTY_SIGNATURE:-1}'
export ALLOW_WEAK_GENE_MAPPING='${ALLOW_WEAK_GENE_MAPPING:-0}'
export ALLOW_WELCH_FALLBACK='${ALLOW_WELCH_FALLBACK:-0}'
EOF_ENV
}

write_design_script() {
  local target="$1"
  cat > "${target}" <<EOF_DESIGN
#!/usr/bin/env bash
#SBATCH --job-name=${JOB_NAME}_design
#SBATCH --partition=${BIBALEX_SLURM_PARTITION}
#SBATCH --cpus-per-task=${REQUEST_CPUS}
#SBATCH --mem=${REQUEST_MEM}
#SBATCH --time=${REQUEST_TIME}
#SBATCH --output=${BIBALEX_REMOTE_SLURM_ROOT}/${JOB_NAME}_design_%j.out
#SBATCH --error=${BIBALEX_REMOTE_SLURM_ROOT}/${JOB_NAME}_design_%j.err

$(write_remote_env_block)
mkdir -p "\${OUT_ROOT}/orchestration" "\${OUT_ROOT}/logs/job_manifests"
export RUN_MANIFEST="\${OUT_ROOT}/logs/job_manifests/design.jsonl"
bash scripts/run_analysis_id_pipeline.sh --preflight

analysis_args=()
if [[ -n "\${ANALYSIS_IDS:-}" ]]; then
  # shellcheck disable=SC2206
  analysis_id_list=(\${ANALYSIS_IDS//,/ })
  for analysis_id in "\${analysis_id_list[@]}"; do
    analysis_args+=(--analysis-id "\${analysis_id}")
  done
elif [[ "\${PILOT_ONLY}" == "1" ]]; then
  analysis_args+=(--pilot)
fi

"\${PYTHON_BIN}" -m src.pipeline.cli design build \\
  --sample-manifest "\${SAMPLE_MANIFEST}" \\
  --expression-manifest "\${EXPRESSION_MANIFEST}" \\
  --downloads-root "\${DOWNLOADS_ROOT}" \\
  --check-expression-readiness \\
  --out "\${OUT_ROOT}/design" \\
  --run-manifest "\${RUN_MANIFEST}"

"\${PYTHON_BIN}" -m src.pipeline.cli design plan-runs \\
  --analysis-registry "\${OUT_ROOT}/design/analysis_contrast_registry.tsv" \\
  --analysis-membership "\${OUT_ROOT}/design/analysis_contrast_membership.tsv" \\
  --out "\${OUT_ROOT}/orchestration" \\
  --execution-root "\${OUT_ROOT}" \\
  --sample-manifest "\${SAMPLE_MANIFEST}" \\
  --expression-manifest "\${EXPRESSION_MANIFEST}" \\
  --downloads-root "\${DOWNLOADS_ROOT}" \\
  --gene-id-mapping "\${GENE_ID_MAPPING}" \\
  --python-executable "\${PYTHON_BIN}" \\
  --count-method "\${COUNT_METHOD}" \\
  --run-manifest "\${RUN_MANIFEST}" \\
  "\${analysis_args[@]}"
EOF_DESIGN
}

write_fanout_script() {
  local target="$1"
  cat > "${target}" <<EOF_FANOUT
#!/usr/bin/env bash
#SBATCH --job-name=${JOB_NAME}_fanout
#SBATCH --partition=${BIBALEX_SLURM_PARTITION}
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=01:00:00
#SBATCH --output=${BIBALEX_REMOTE_SLURM_ROOT}/${JOB_NAME}_fanout_%j.out
#SBATCH --error=${BIBALEX_REMOTE_SLURM_ROOT}/${JOB_NAME}_fanout_%j.err

$(write_remote_env_block)
mkdir -p "\${OUT_ROOT}/orchestration"
plan="\${OUT_ROOT}/orchestration/analysis_execution_plan.tsv"
if [[ -n "\${ANALYSIS_IDS:-}" ]]; then
  # shellcheck disable=SC2206
  analysis_id_list=(\${ANALYSIS_IDS//,/ })
elif [[ "\${PILOT_ONLY}" == "1" ]]; then
  analysis_id_list=(PRE_RESPONSE PAN_ICB_RESPONSE__PRE_TREATMENT ICI_COMBINATION_RESPONSE__PRE_TREATMENT)
else
  if [[ ! -s "\${plan}" ]]; then
    echo "Missing analysis execution plan: \${plan}" >&2
    exit 2
  fi
  mapfile -t analysis_id_list < <(awk -F '\\t' 'NR > 1 && \$1 != "" {print \$1}' "\${plan}" | sort -u)
fi
if [[ \${#analysis_id_list[@]} -eq 0 ]]; then
  echo "No analysis IDs available for multi-job fanout." >&2
  exit 2
fi

printf 'analysis_id\\n' > "\${OUT_ROOT}/orchestration/multijob_analysis_ids.tsv"
printf '%s\\n' "\${analysis_id_list[@]}" >> "\${OUT_ROOT}/orchestration/multijob_analysis_ids.tsv"

plan_tsv="\${OUT_ROOT}/orchestration/analysis_id_pipeline_plan.tsv"
tcga_stage="tcga_skip"
if [[ -n "\${TCGA_MAP}" ]]; then
  tcga_stage="tcga"
fi
{
  printf 'stage\\tanalysis_id\\toutput_dir\\tcommand\\n'
  printf 'design_build\\tALL\\t%s\\t%s\\n' "\${OUT_ROOT}/design" 'multi-job design task: design build'
  printf 'design_plan\\tALL\\t%s\\t%s\\n' "\${OUT_ROOT}/orchestration/analysis_execution_plan.tsv" 'multi-job design task: design plan-runs'
  printf 'immune_score\\tALL\\t%s\\t%s\\n' "\${OUT_ROOT}/immune_state" 'multi-job immune task: immune score'
  printf 'immune_effects\\tALL\\t%s\\t%s\\n' "\${OUT_ROOT}/immune_state" 'multi-job immune task: immune effects'
  for analysis_id in "\${analysis_id_list[@]}"; do
    printf 'stage06_de\\t%s\\t%s\\t%s\\n' "\${analysis_id}" "\${OUT_ROOT}/de/\${analysis_id}" 'multi-job analysis task: de run'
    printf 'stage07_meta\\t%s\\t%s\\t%s\\n' "\${analysis_id}" "\${OUT_ROOT}/meta/\${analysis_id}" 'multi-job analysis task: meta run'
    printf 'signature\\t%s\\t%s\\t%s\\n' "\${analysis_id}" "\${OUT_ROOT}/signature/\${analysis_id}" 'multi-job analysis task: signature derive'
    printf 'validate\\t%s\\t%s\\t%s\\n' "\${analysis_id}" "\${OUT_ROOT}/validation/\${analysis_id}" 'multi-job analysis task: validate run'
    printf '%s\\t%s\\t%s\\t%s\\n' "\${tcga_stage}" "\${analysis_id}" "\${OUT_ROOT}/tcga_projection/\${analysis_id}" "multi-job analysis task: \${tcga_stage}"
    printf 'interpret_enrich\\t%s\\t%s\\t%s\\n' "\${analysis_id}" "\${OUT_ROOT}/interpretation/enrichment/\${analysis_id}" 'multi-job analysis task: interpret enrich'
  printf 'interpret_network\\t%s\\t%s\\t%s\\n' "\${analysis_id}" "\${OUT_ROOT}/interpretation/network/\${analysis_id}" 'multi-job analysis task: interpret network'
  done
  printf 'comparison_registry_merge\\tALL\\t%s\\t%s\\n' "\${OUT_ROOT}/comparison_registry.tsv" 'multi-job final task: merge per-analysis comparison registries'
  printf 'interpret_hub_meta\\tALL\\t%s\\t%s\\n' "\${OUT_ROOT}/interpretation/hub_meta" 'multi-job final task: interpret hub-meta'
  printf 'interpret_immunophenotype\\tALL\\t%s\\t%s\\n' "\${OUT_ROOT}/interpretation/immunophenotype" 'multi-job final task: interpret immunophenotype'
  printf 'interpret_epi_infer\\tALL\\t%s\\t%s\\n' "\${OUT_ROOT}/interpretation/epigenetic" 'multi-job final task: interpret epi-infer'
  printf 'report\\tALL\\t%s\\t%s\\n' "\${OUT_ROOT}/reports" 'multi-job final task: report build'
  printf 'run_manifest_merge\\tALL\\t%s\\t%s\\n' "\${OUT_ROOT}/logs/run_manifest.yaml" 'multi-job final task: merge per-job run manifests'
  printf 'postrun_audit\\tALL\\t%s\\t%s\\n' "\${OUT_ROOT}/orchestration/analysis_id_pipeline_postrun_audit.tsv" 'multi-job final task: completed-run audit'
} > "\${plan_tsv}"

IMMUNE_JOB="\$(sbatch --parsable --dependency=afterok:\${SLURM_JOB_ID} '${REMOTE_IMMUNE_SCRIPT}')"
analysis_jobs=()
for analysis_id in "\${analysis_id_list[@]}"; do
  job_id="\$(sbatch --parsable --dependency=afterok:\${SLURM_JOB_ID} --export=ALL,ANALYSIS_ID="\${analysis_id}" '${REMOTE_ANALYSIS_SCRIPT}')"
  analysis_jobs+=("\${job_id}")
done
dependency_ids=("\${IMMUNE_JOB}" "\${analysis_jobs[@]}")
dependency="\$(IFS=:; echo "\${dependency_ids[*]}")"
FINAL_JOB="\$(sbatch --parsable --dependency=afterok:\${dependency} '${REMOTE_FINALIZE_SCRIPT}')"
{
  printf 'key\\tvalue\\n'
  printf 'design_job_id\\t%s\\n' "\${SLURM_JOB_ID}"
  printf 'immune_job_id\\t%s\\n' "\${IMMUNE_JOB}"
  printf 'analysis_job_ids\\t%s\\n' "\$(IFS=,; echo "\${analysis_jobs[*]}")"
  printf 'final_job_id\\t%s\\n' "\${FINAL_JOB}"
  printf 'analysis_ids\\t%s\\n' "\$(IFS=' '; echo "\${analysis_id_list[*]}")"
  printf 'comparison_registry_strategy\\tper_analysis_shards_final_merge\\n'
  printf 'run_manifest_strategy\\tper_job_shards_final_merge\\n'
  printf 'claim_boundary\\tspec027 discovery/mechanism_hypothesis only; TCGA prognostic only; LOCO internal only\\n'
  printf 'track_boundary\\tTrack A derivation remains separate from Track B external candidates\\n'
} > "\${OUT_ROOT}/orchestration/bibalex_multijob_submission_manifest.tsv"
EOF_FANOUT
}

write_analysis_script() {
  local target="$1"
  cat > "${target}" <<'EOF_ANALYSIS'
#!/usr/bin/env bash
EOF_ANALYSIS
  cat >> "${target}" <<EOF_ANALYSIS_HEAD
#SBATCH --job-name=${JOB_NAME}_analysis
#SBATCH --partition=${BIBALEX_SLURM_PARTITION}
#SBATCH --cpus-per-task=${ANALYSIS_CPUS}
#SBATCH --mem=${ANALYSIS_MEM}
#SBATCH --time=${ANALYSIS_TIME}
#SBATCH --output=${BIBALEX_REMOTE_SLURM_ROOT}/${JOB_NAME}_analysis_%j.out
#SBATCH --error=${BIBALEX_REMOTE_SLURM_ROOT}/${JOB_NAME}_analysis_%j.err

$(write_remote_env_block)
EOF_ANALYSIS_HEAD
cat >> "${target}" <<'EOF_ANALYSIS_BODY'
analysis_id="${ANALYSIS_ID:?Set ANALYSIS_ID for the per-analysis task.}"
job_manifest_dir="${OUT_ROOT}/logs/job_manifests"
mkdir -p "${job_manifest_dir}"
export RUN_MANIFEST="${job_manifest_dir}/analysis_${analysis_id}.jsonl"
registry_dir="${OUT_ROOT}/comparison_registry_by_analysis"
mkdir -p "${registry_dir}"
analysis_comparison_registry="${registry_dir}/${analysis_id}.tsv"

"${PYTHON_BIN}" -m src.pipeline.cli de run \
  --contrast "${analysis_id}" \
  --analysis-id "${analysis_id}" \
  --analysis-registry "${OUT_ROOT}/design/analysis_contrast_registry.tsv" \
  --analysis-membership "${OUT_ROOT}/design/analysis_contrast_membership.tsv" \
  --sample-manifest "${SAMPLE_MANIFEST}" \
  --expression-manifest "${EXPRESSION_MANIFEST}" \
  --downloads-root "${DOWNLOADS_ROOT}" \
  --count-method "${COUNT_METHOD}" \
  --gene-id-mapping "${GENE_ID_MAPPING}" \
  --comparison-registry "${analysis_comparison_registry}" \
  --out "${OUT_ROOT}/de" \
  --run-manifest "${RUN_MANIFEST}"

"${PYTHON_BIN}" -m src.pipeline.cli meta run \
  --contrast "${analysis_id}" \
  --analysis-id "${analysis_id}" \
  --de-dir "${OUT_ROOT}/de" \
  --sample-manifest "${SAMPLE_MANIFEST}" \
  --comparison-registry "${analysis_comparison_registry}" \
  --skip-forest-plots \
  --out "${OUT_ROOT}/meta" \
  --run-manifest "${RUN_MANIFEST}"

signature_args=()
if [[ "${ALLOW_EMPTY_SIGNATURE}" == "1" ]]; then
  signature_args+=(--allow-empty-signature)
fi
"${PYTHON_BIN}" -m src.pipeline.cli signature derive \
  --analysis-id "${analysis_id}" \
  --run-root "${OUT_ROOT}" \
  --comparison-registry "${analysis_comparison_registry}" \
  --out "${OUT_ROOT}/signature/${analysis_id}" \
  --run-manifest "${RUN_MANIFEST}" \
  "${signature_args[@]}"

"${PYTHON_BIN}" -m src.pipeline.cli validate run \
  --signature "${OUT_ROOT}/signature/${analysis_id}/responder_signature_tiered.tsv" \
  --results-root "${OUT_ROOT}" \
  --contrast "${analysis_id}" \
  --indirect-meta "${OUT_ROOT}/meta/${analysis_id}/meta_effects.tsv" \
  --meta-loco-summary "${OUT_ROOT}/meta/${analysis_id}/meta_leave_one_out_summary.tsv" \
  --sample-manifest "${SAMPLE_MANIFEST}" \
  --out "${OUT_ROOT}/validation/${analysis_id}" \
  --run-manifest "${RUN_MANIFEST}"

if [[ -n "${TCGA_MAP}" ]]; then
  tcga_args=(
    "${PYTHON_BIN}" -m src.pipeline.cli tcga project
    --signature "${OUT_ROOT}/signature/${analysis_id}/responder_signature_tiered.tsv"
    --tcga-map "${TCGA_MAP}"
    --tier-signatures-dir "${OUT_ROOT}/signature/${analysis_id}"
    --out "${OUT_ROOT}/tcga_projection/${analysis_id}"
    --run-manifest "${RUN_MANIFEST}"
  )
  if [[ -n "${NAIVE_MANIFEST}" ]]; then
    tcga_args+=(--naive-manifest "${NAIVE_MANIFEST}")
  fi
  if [[ -n "${THORSSON_SUBTYPES}" ]]; then
    tcga_args+=(--thorsson-subtypes "${THORSSON_SUBTYPES}")
  fi
  "${tcga_args[@]}"
else
  skip_dir="${OUT_ROOT}/tcga_projection/${analysis_id}"
  mkdir -p "${skip_dir}"
  printf 'stage\tproject\tsignature_tier\tstatus\treason\tdetail\n%s\t%s\t%s\t%s\t%s\t%s\n' \
    tcga_project '' ALL blocked missing_tcga_map 'Set TCGA_MAP to enable prognostic projection.' \
    > "${skip_dir}/tcga_projection_status.tsv"
fi

"${PYTHON_BIN}" -m src.pipeline.cli interpret enrich \
  --results-root "${OUT_ROOT}" \
  --analysis-id "${analysis_id}" \
  --collections "${GENE_SET_REGISTRY}" \
  --out "${OUT_ROOT}/interpretation" \
  --run-manifest "${RUN_MANIFEST}"

"${PYTHON_BIN}" -m src.pipeline.cli interpret network \
  --results-root "${OUT_ROOT}" \
  --analysis-id "${analysis_id}" \
  --expression-manifest "${EXPRESSION_MANIFEST}" \
  --downloads-root "${DOWNLOADS_ROOT}" \
  --out "${OUT_ROOT}/interpretation" \
  --run-manifest "${RUN_MANIFEST}"
EOF_ANALYSIS_BODY
}

write_immune_script() {
  local target="$1"
  cat > "${target}" <<EOF_IMMUNE
#!/usr/bin/env bash
#SBATCH --job-name=${JOB_NAME}_immune
#SBATCH --partition=${BIBALEX_SLURM_PARTITION}
#SBATCH --cpus-per-task=${REQUEST_CPUS}
#SBATCH --mem=${REQUEST_MEM}
#SBATCH --time=${REQUEST_TIME}
#SBATCH --output=${BIBALEX_REMOTE_SLURM_ROOT}/${JOB_NAME}_immune_%j.out
#SBATCH --error=${BIBALEX_REMOTE_SLURM_ROOT}/${JOB_NAME}_immune_%j.err

$(write_remote_env_block)
job_manifest_dir="\${OUT_ROOT}/logs/job_manifests"
mkdir -p "\${job_manifest_dir}"
export RUN_MANIFEST="\${job_manifest_dir}/immune.jsonl"
immune_effect_args=()
if [[ "\${ALLOW_WEAK_GENE_MAPPING}" == "1" ]]; then
  immune_effect_args+=(--allow-weak-gene-mapping)
fi
"\${PYTHON_BIN}" -m src.pipeline.cli immune score \\
  --sample-manifest "\${SAMPLE_MANIFEST}" \\
  --expression-manifest "\${EXPRESSION_MANIFEST}" \\
  --downloads-root "\${DOWNLOADS_ROOT}" \\
  --gene-set-registry "\${GENE_SET_REGISTRY}" \\
  --out "\${OUT_ROOT}/immune_state" \\
  --run-manifest "\${RUN_MANIFEST}"

"\${PYTHON_BIN}" -m src.pipeline.cli immune effects \\
  --sample-manifest "\${SAMPLE_MANIFEST}" \\
  --immune-dir "\${OUT_ROOT}/immune_state" \\
  --expression-manifest "\${EXPRESSION_MANIFEST}" \\
  --downloads-root "\${DOWNLOADS_ROOT}" \\
  "\${immune_effect_args[@]}" \\
  --out "\${OUT_ROOT}/immune_state" \\
  --run-manifest "\${RUN_MANIFEST}"
EOF_IMMUNE
}

write_finalize_script() {
  local target="$1"
  cat > "${target}" <<EOF_FINAL
#!/usr/bin/env bash
#SBATCH --job-name=${JOB_NAME}_final
#SBATCH --partition=${BIBALEX_SLURM_PARTITION}
#SBATCH --cpus-per-task=${FINAL_CPUS}
#SBATCH --mem=${FINAL_MEM}
#SBATCH --time=${FINAL_TIME}
#SBATCH --output=${BIBALEX_REMOTE_SLURM_ROOT}/${JOB_NAME}_final_%j.out
#SBATCH --error=${BIBALEX_REMOTE_SLURM_ROOT}/${JOB_NAME}_final_%j.err

$(write_remote_env_block)
job_manifest_dir="\${OUT_ROOT}/logs/job_manifests"
canonical_run_manifest="\${OUT_ROOT}/logs/run_manifest.yaml"
mkdir -p "\${job_manifest_dir}"
export RUN_MANIFEST="\${job_manifest_dir}/finalize.jsonl"

registry_dir="\${OUT_ROOT}/comparison_registry_by_analysis"
registry_out="\${OUT_ROOT}/comparison_registry.tsv"
if [[ ! -d "\${registry_dir}" ]]; then
  echo "Missing per-analysis comparison registry directory: \${registry_dir}" >&2
  exit 2
fi
mapfile -t registry_files < <(find "\${registry_dir}" -maxdepth 1 -type f -name '*.tsv' | sort)
if [[ \${#registry_files[@]} -eq 0 ]]; then
  echo "No per-analysis comparison registries found in \${registry_dir}" >&2
  exit 2
fi
registry_tmp="\${OUT_ROOT}/comparison_registry.tsv.tmp"
: > "\${registry_tmp}"
first_registry=1
for registry_file in "\${registry_files[@]}"; do
  if [[ ! -s "\${registry_file}" ]]; then
    continue
  fi
  if [[ "\${first_registry}" -eq 1 ]]; then
    cat "\${registry_file}" >> "\${registry_tmp}"
    first_registry=0
  else
    tail -n +2 "\${registry_file}" >> "\${registry_tmp}"
  fi
done
if [[ ! -s "\${registry_tmp}" ]]; then
  echo "Merged comparison registry is empty after reading \${registry_dir}" >&2
  exit 2
fi
mv "\${registry_tmp}" "\${registry_out}"

"\${PYTHON_BIN}" -m src.pipeline.cli interpret hub-meta \\
  --results-root "\${OUT_ROOT}" \\
  --out "\${OUT_ROOT}/interpretation" \\
  --run-manifest "\${RUN_MANIFEST}"

"\${PYTHON_BIN}" -m src.pipeline.cli interpret immunophenotype \\
  --results-root "\${OUT_ROOT}" \\
  --criteria-registry "\${CRITERIA_REGISTRY}" \\
  --out "\${OUT_ROOT}/interpretation" \\
  --run-manifest "\${RUN_MANIFEST}"

"\${PYTHON_BIN}" -m src.pipeline.cli interpret epi-infer \\
  --results-root "\${OUT_ROOT}" \\
  --expression-manifest "\${EXPRESSION_MANIFEST}" \\
  --out "\${OUT_ROOT}/interpretation" \\
  --run-manifest "\${RUN_MANIFEST}"

"\${PYTHON_BIN}" -m src.pipeline.cli report build \\
  --results-root "\${OUT_ROOT}" \\
  --out "\${OUT_ROOT}/reports" \\
  --run-manifest "\${RUN_MANIFEST}"

manifest_tmp="\${OUT_ROOT}/logs/run_manifest.yaml.tmp"
: > "\${manifest_tmp}"
manifest_inputs=()
for required_manifest in "\${job_manifest_dir}/design.jsonl" "\${job_manifest_dir}/immune.jsonl"; do
  if [[ -s "\${required_manifest}" ]]; then
    manifest_inputs+=("\${required_manifest}")
  else
    echo "Missing or empty run manifest shard: \${required_manifest}" >&2
    exit 2
  fi
done
mapfile -t analysis_manifest_files < <(find "\${job_manifest_dir}" -maxdepth 1 -type f -name 'analysis_*.jsonl' | sort)
if [[ \${#analysis_manifest_files[@]} -eq 0 ]]; then
  echo "No per-analysis run manifest shards found in \${job_manifest_dir}" >&2
  exit 2
fi
manifest_inputs+=("\${analysis_manifest_files[@]}")
if [[ -s "\${RUN_MANIFEST}" ]]; then
  manifest_inputs+=("\${RUN_MANIFEST}")
else
  echo "Missing or empty run manifest shard: \${RUN_MANIFEST}" >&2
  exit 2
fi
for manifest_file in "\${manifest_inputs[@]}"; do
  cat "\${manifest_file}" >> "\${manifest_tmp}"
done
if [[ ! -s "\${manifest_tmp}" ]]; then
  echo "Merged run manifest is empty after reading \${job_manifest_dir}" >&2
  exit 2
fi
mv "\${manifest_tmp}" "\${canonical_run_manifest}"

"\${PYTHON_BIN}" scripts/audit_analysis_id_pipeline_run.py \\
  --run-root "\${OUT_ROOT}" \\
  --out "\${OUT_ROOT}/orchestration/analysis_id_pipeline_postrun_audit.tsv" \\
  --summary-out "\${OUT_ROOT}/orchestration/analysis_id_pipeline_postrun_audit.md"
EOF_FINAL
}

write_submitter() {
  local target="$1"
  cat > "${target}" <<EOF_SUBMIT
#!/usr/bin/env bash
set -euo pipefail
mkdir -p '${BIBALEX_REMOTE_SLURM_ROOT}'
DESIGN_JOB="\$(sbatch --parsable '${REMOTE_DESIGN_SCRIPT}')"
FANOUT_JOB="\$(sbatch --parsable --dependency=afterok:\${DESIGN_JOB} '${REMOTE_FANOUT_SCRIPT}')"
printf 'design_job_id\\t%s\\n' "\${DESIGN_JOB}"
printf 'fanout_job_id\\t%s\\n' "\${FANOUT_JOB}"
printf 'remote_out_root\\t%s\\n' '${OUT_ROOT_REMOTE}'
printf 'fanout_note\\t%s\\n' 'fanout job submits immune, per-analysis, and final/report jobs after design succeeds'
EOF_SUBMIT
}

write_all_scripts() {
  mkdir -p "${PREFLIGHT_DIR}"
  write_design_script "${LOCAL_DESIGN_SCRIPT}"
  write_fanout_script "${LOCAL_FANOUT_SCRIPT}"
  write_analysis_script "${LOCAL_ANALYSIS_SCRIPT}"
  write_immune_script "${LOCAL_IMMUNE_SCRIPT}"
  write_finalize_script "${LOCAL_FINALIZE_SCRIPT}"
  write_submitter "${LOCAL_SUBMITTER}"
  chmod +x "${LOCAL_DESIGN_SCRIPT}" "${LOCAL_FANOUT_SCRIPT}" "${LOCAL_ANALYSIS_SCRIPT}" "${LOCAL_IMMUNE_SCRIPT}" "${LOCAL_FINALIZE_SCRIPT}" "${LOCAL_SUBMITTER}"
}

write_submission_manifest() {
  {
    printf 'key\tvalue\n'
    printf 'mode\t%s\n' "${MODE}"
    printf 'multi_job_strategy\tdependency_fanout\n'
    printf 'network_action_preflight\tnone\n'
    printf 'ssh_host\t%s\n' "${BIBALEX_SSH_HOST}"
    printf 'remote_root\t%s\n' "${BIBALEX_REMOTE_ROOT}"
    printf 'remote_repo\t%s\n' "${BIBALEX_REMOTE_REPO}"
    printf 'out_root_remote\t%s\n' "${OUT_ROOT_REMOTE}"
    printf 'data_root\t%s\n' "${DATA_ROOT:-<unset>}"
    printf 'downloads_root_remote\t%s\n' "${DOWNLOADS_ROOT_REMOTE:-<unset>}"
    printf 'run_tag\t%s\n' "${STAMP}"
    printf 'track\t%s\n' "${TRACK}"
    printf 'job_name\t%s\n' "${JOB_NAME}"
    printf 'remote_submitter\t%s\n' "${REMOTE_SUBMITTER}"
    printf 'remote_design_script\t%s\n' "${REMOTE_DESIGN_SCRIPT}"
    printf 'remote_fanout_script\t%s\n' "${REMOTE_FANOUT_SCRIPT}"
    printf 'remote_analysis_script\t%s\n' "${REMOTE_ANALYSIS_SCRIPT}"
    printf 'remote_immune_script\t%s\n' "${REMOTE_IMMUNE_SCRIPT}"
    printf 'remote_finalize_script\t%s\n' "${REMOTE_FINALIZE_SCRIPT}"
    printf 'slurm_partition\t%s\n' "${BIBALEX_SLURM_PARTITION}"
    printf 'slurm_cpus\t%s\n' "${REQUEST_CPUS}"
    printf 'slurm_mem\t%s\n' "${REQUEST_MEM}"
    printf 'slurm_time\t%s\n' "${REQUEST_TIME}"
    printf 'analysis_cpus\t%s\n' "${ANALYSIS_CPUS}"
    printf 'analysis_mem\t%s\n' "${ANALYSIS_MEM}"
    printf 'analysis_time\t%s\n' "${ANALYSIS_TIME}"
    printf 'final_cpus\t%s\n' "${FINAL_CPUS}"
    printf 'final_mem\t%s\n' "${FINAL_MEM}"
    printf 'final_time\t%s\n' "${FINAL_TIME}"
    printf 'portable_r_conda_prefix\t%s\n' "${PORTABLE_R_CONDA_PREFIX:-<unset>}"
    printf 'conda_bin\t%s\n' "${BIBALEX_CONDA_BIN}"
    printf 'conda_env\t%s\n' "${BIBALEX_CONDA_ENV}"
    printf 'analysis_ids\t%s\n' "${ANALYSIS_IDS:-<unset>}"
    printf 'pilot_only\t%s\n' "${PILOT_ONLY:-0}"
    printf 'tcga_map\t%s\n' "${TCGA_MAP:-<unset>}"
    printf 'comparison_registry_strategy\tper_analysis_shards_final_merge\n'
    printf 'run_manifest_strategy\tper_job_shards_final_merge\n'
    printf 'execution_gate\tALLOW_BIBALEX_ANALYSIS_ID_MULTIJOB=1 required for --submit-multijob\n'
    printf 'inner_execution_gate\tALLOW_ANALYSIS_ID_PIPELINE_RUN=1 set inside remote jobs\n'
    printf 'reviewed_root_guard\tOUT_ROOT_REMOTE must not target the committed reviewed root\n'
    printf 'claim_boundary\tspec 027 claims are discovery/mechanism-hypothesis only; TCGA prognostic only; LOCO internal only\n'
    printf 'track_boundary\tTrack A signature derivation remains separate from Track B external candidates\n'
  } > "${SUBMISSION_MANIFEST}"
}

run_preflight() {
  mkdir -p "${PREFLIGHT_DIR}"
  printf 'check\tstatus\tdetail\n' > "${PREFLIGHT_TSV}"
  preflight_check mode pass "${MODE}"
  preflight_check multi_job_strategy pass "dependency_fanout"
  preflight_check network_action_preflight pass "none"
  preflight_check ssh_host pass "${BIBALEX_SSH_HOST}"
  preflight_check remote_root pass "${BIBALEX_REMOTE_ROOT}"
  preflight_check remote_repo pass "${BIBALEX_REMOTE_REPO}"
  preflight_check out_root_remote pass "${OUT_ROOT_REMOTE}"
  preflight_check slurm_resources pass "partition=${BIBALEX_SLURM_PARTITION};cpus=${REQUEST_CPUS};mem=${REQUEST_MEM};time=${REQUEST_TIME};analysis_cpus=${ANALYSIS_CPUS};analysis_mem=${ANALYSIS_MEM};final_cpus=${FINAL_CPUS};final_mem=${FINAL_MEM}"
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
  write_all_scripts
  preflight_check local_design_script pass "${LOCAL_DESIGN_SCRIPT}"
  preflight_check local_fanout_script pass "${LOCAL_FANOUT_SCRIPT}"
  preflight_check local_analysis_script pass "${LOCAL_ANALYSIS_SCRIPT}"
  preflight_check local_immune_script pass "${LOCAL_IMMUNE_SCRIPT}"
  preflight_check local_finalize_script pass "${LOCAL_FINALIZE_SCRIPT}"
  preflight_check local_submitter pass "${LOCAL_SUBMITTER}"
  write_submission_manifest
  preflight_check multijob_submission_preview_manifest pass "${SUBMISSION_MANIFEST}"
}

if [[ "${MODE}" == "preflight" ]]; then
  run_preflight
  printf 'mode\t%s\n' "${MODE}"
  printf 'preflight_tsv\t%s\n' "${PREFLIGHT_TSV}"
  printf 'submission_manifest\t%s\n' "${SUBMISSION_MANIFEST}"
  printf 'local_submitter\t%s\n' "${LOCAL_SUBMITTER}"
  if [[ "${preflight_status}" -eq 0 ]]; then
    printf 'preflight_status\tpass\n'
  else
    printf 'preflight_status\tfail\n'
  fi
  exit "${preflight_status}"
fi

if [[ "${ALLOW_BIBALEX_ANALYSIS_ID_MULTIJOB:-0}" != "1" ]]; then
  echo "Refusing BibaLex analysis-id multi-job submission because ALLOW_BIBALEX_ANALYSIS_ID_MULTIJOB is not 1." >&2
  echo "Ask for explicit approval before any HPC action or full pipeline run." >&2
  exit 3
fi

if [[ -z "${DATA_ROOT}" ]]; then
  echo "Set BIBALEX_DATA_ROOT to the audited remote retrieval root." >&2
  exit 2
fi

run_preflight
if [[ "${preflight_status}" -ne 0 ]]; then
  echo "Refusing submission because multi-job preflight failed. See ${PREFLIGHT_TSV}" >&2
  exit 1
fi

bibalex_ssh "mkdir -p '${BIBALEX_REMOTE_SCRIPTS_ROOT}' '${BIBALEX_REMOTE_SLURM_ROOT}' && chmod 700 '${BIBALEX_REMOTE_ROOT}'"
scp "${LOCAL_DESIGN_SCRIPT}" "${BIBALEX_SSH_HOST}:${REMOTE_DESIGN_SCRIPT}"
scp "${LOCAL_FANOUT_SCRIPT}" "${BIBALEX_SSH_HOST}:${REMOTE_FANOUT_SCRIPT}"
scp "${LOCAL_ANALYSIS_SCRIPT}" "${BIBALEX_SSH_HOST}:${REMOTE_ANALYSIS_SCRIPT}"
scp "${LOCAL_IMMUNE_SCRIPT}" "${BIBALEX_SSH_HOST}:${REMOTE_IMMUNE_SCRIPT}"
scp "${LOCAL_FINALIZE_SCRIPT}" "${BIBALEX_SSH_HOST}:${REMOTE_FINALIZE_SCRIPT}"
scp "${LOCAL_SUBMITTER}" "${BIBALEX_SSH_HOST}:${REMOTE_SUBMITTER}"

JOB_OUTPUT="$(bibalex_ssh "chmod +x '${REMOTE_DESIGN_SCRIPT}' '${REMOTE_FANOUT_SCRIPT}' '${REMOTE_ANALYSIS_SCRIPT}' '${REMOTE_IMMUNE_SCRIPT}' '${REMOTE_FINALIZE_SCRIPT}' '${REMOTE_SUBMITTER}' && '${REMOTE_SUBMITTER}'")"
printf '%s\n' "${JOB_OUTPUT}"
printf 'remote_submitter\t%s\n' "${REMOTE_SUBMITTER}"
printf 'out_root\t%s\n' "${OUT_ROOT_REMOTE}"
printf 'downloads_root\t%s\n' "${DOWNLOADS_ROOT_REMOTE}"
