#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/run_analysis_id_pipeline.sh [--dry-run|--preflight|--execute]

Build or run the Spec-026 analysis-id pipeline:
design -> DE -> meta -> signature -> immune -> validate -> TCGA -> interpretation -> report -> post-run audit.

Default mode is --dry-run. Preflight validates inputs/root safety without running stages.
Real execution also requires:
  ALLOW_ANALYSIS_ID_PIPELINE_RUN=1

Key environment variables:
  OUT_ROOT                 New output root. Default: results/analysis_id_pipeline_<UTC stamp>
  PYTHON_BIN               Python executable. Default: python3.13
  SAMPLE_MANIFEST          Default: configs/sample_manifest_curated.tsv
  EXPRESSION_MANIFEST      Default: results/geo_tables/geo_tables_summary.tsv
  DOWNLOADS_ROOT           Default: results/retrieval/downloads
  ANALYSIS_IDS             Optional comma/space-separated analysis IDs.
  PILOT_ONLY               1 restricts design plan to PRE/pan-ICB/ICI-combination pilot IDs.
  TCGA_MAP                 Optional TCGA map. If absent, TCGA stage writes skipped status.
  PORTABLE_R_CONDA_PREFIX  Optional spec-094 R runtime prefix; prepended to PATH for Rscript.
EOF
}

MODE="dry-run"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      MODE="dry-run"
      shift
      ;;
    --preflight)
      MODE="preflight"
      shift
      ;;
    --execute)
      MODE="execute"
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

if [[ "${MODE}" == "execute" && "${ALLOW_ANALYSIS_ID_PIPELINE_RUN:-0}" != "1" ]]; then
  echo "Refusing analysis-id pipeline execution because ALLOW_ANALYSIS_ID_PIPELINE_RUN is not 1." >&2
  echo "This protects reviewed results and prevents accidental full reruns." >&2
  exit 3
fi

if [[ -n "${PORTABLE_R_CONDA_PREFIX:-}" && -x "${PORTABLE_R_CONDA_PREFIX}/bin/Rscript" ]]; then
  export PATH="${PORTABLE_R_CONDA_PREFIX}/bin:${PATH}"
fi

STAMP="${RUN_TAG:-$(date -u +%Y%m%d_%H%M%S)}"
OUT_ROOT="${OUT_ROOT:-results/analysis_id_pipeline_${STAMP}}"
PYTHON_BIN="${PYTHON_BIN:-python3.13}"
SAMPLE_MANIFEST="${SAMPLE_MANIFEST:-configs/sample_manifest_curated.tsv}"
EXPRESSION_MANIFEST="${EXPRESSION_MANIFEST:-results/geo_tables/geo_tables_summary.tsv}"
DOWNLOADS_ROOT="${DOWNLOADS_ROOT:-results/retrieval/downloads}"
GENE_ID_MAPPING="${GENE_ID_MAPPING:-configs/gene_id_mapping_human.tsv}"
GENE_SET_REGISTRY="${GENE_SET_REGISTRY:-configs/immune_gene_sets_registry.tsv}"
CRITERIA_REGISTRY="${CRITERIA_REGISTRY:-configs/immunophenotype_criteria_registry.tsv}"
COUNT_METHOD="${COUNT_METHOD:-deseq2}"
RUN_MANIFEST="${RUN_MANIFEST:-${OUT_ROOT}/logs/run_manifest.yaml}"
ORCH_DIR="${OUT_ROOT}/orchestration"
DESIGN_DIR="${OUT_ROOT}/design"
PLAN_TSV="${ORCH_DIR}/analysis_id_pipeline_plan.tsv"
PLAN_SH="${ORCH_DIR}/analysis_id_pipeline_plan.sh"
DRY_RUN_SCOPE_NOTE="${ORCH_DIR}/analysis_id_pipeline_dry_run_scope.txt"
DECISION_MANIFEST="${ORCH_DIR}/phase3_execution_decision_manifest.tsv"
PREFLIGHT_TSV="${ORCH_DIR}/analysis_id_pipeline_preflight.tsv"
EXECUTION_PLAN="${ORCH_DIR}/analysis_execution_plan.tsv"
COMPARISON_REGISTRY="${OUT_ROOT}/comparison_registry.tsv"
POSTRUN_AUDIT_TSV="${ORCH_DIR}/analysis_id_pipeline_postrun_audit.tsv"
POSTRUN_AUDIT_MD="${ORCH_DIR}/analysis_id_pipeline_postrun_audit.md"
TCGA_MAP="${TCGA_MAP:-}"
NAIVE_MANIFEST="${NAIVE_MANIFEST:-}"
THORSSON_SUBTYPES="${THORSSON_SUBTYPES:-}"
PILOT_ONLY="${PILOT_ONLY:-0}"
ALLOW_EMPTY_SIGNATURE="${ALLOW_EMPTY_SIGNATURE:-1}"
ALLOW_WEAK_GENE_MAPPING="${ALLOW_WEAK_GENE_MAPPING:-0}"
ALLOW_WELCH_FALLBACK="${ALLOW_WELCH_FALLBACK:-0}"

case "${OUT_ROOT}" in
  *analysis_id_runs_t7_20260607_stage07_scale_provenance*)
    echo "Refusing to target the committed reviewed root: ${OUT_ROOT}" >&2
    exit 4
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

run_preflight() {
  local out_root_status="pass"
  local out_root_detail="OUT_ROOT does not exist yet."
  if [[ -e "${OUT_ROOT}" ]]; then
    if find "${OUT_ROOT}" -mindepth 1 -maxdepth 1 | read -r _; then
      out_root_status="warn"
      out_root_detail="OUT_ROOT exists and is non-empty; use a fresh dated root for Phase 3 execution."
    else
      out_root_detail="OUT_ROOT exists and is empty."
    fi
  fi
  mkdir -p "${ORCH_DIR}"
  printf 'check\tstatus\tdetail\n' > "${PREFLIGHT_TSV}"
  preflight_check mode pass "${MODE}"
  preflight_check out_root pass "${OUT_ROOT}"
  preflight_check out_root_empty "${out_root_status}" "${out_root_detail}"
  if command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    preflight_check python_bin pass "$(command -v "${PYTHON_BIN}")"
  else
    preflight_check python_bin fail "Python executable not found: ${PYTHON_BIN}"
  fi
  for item in \
    "sample_manifest:${SAMPLE_MANIFEST}:file" \
    "expression_manifest:${EXPRESSION_MANIFEST}:file" \
    "downloads_root:${DOWNLOADS_ROOT}:dir" \
    "gene_id_mapping:${GENE_ID_MAPPING}:file" \
    "gene_set_registry:${GENE_SET_REGISTRY}:file" \
    "criteria_registry:${CRITERIA_REGISTRY}:file"; do
    local name="${item%%:*}"
    local rest="${item#*:}"
    local path="${rest%:*}"
    local kind="${item##*:}"
    if [[ "${kind}" == "dir" ]]; then
      if [[ -d "${path}" ]]; then
        preflight_check "${name}" pass "${path}"
      else
        preflight_check "${name}" fail "Directory not found: ${path}"
      fi
    else
      if [[ -f "${path}" ]]; then
        preflight_check "${name}" pass "${path}"
      else
        preflight_check "${name}" fail "File not found: ${path}"
      fi
    fi
  done
  if [[ -n "${TCGA_MAP}" ]]; then
    if [[ -f "${TCGA_MAP}" ]]; then
      preflight_check tcga_map pass "${TCGA_MAP}"
    else
      preflight_check tcga_map fail "TCGA_MAP is set but file was not found: ${TCGA_MAP}"
    fi
  else
    preflight_check tcga_map warn "TCGA_MAP unset; full run will emit missing_tcga_map status for TCGA projection."
  fi
  if [[ -n "${PORTABLE_R_CONDA_PREFIX:-}" ]]; then
    if [[ -x "${PORTABLE_R_CONDA_PREFIX}/bin/Rscript" ]]; then
      preflight_check portable_r pass "${PORTABLE_R_CONDA_PREFIX}/bin/Rscript"
    else
      preflight_check portable_r fail "PORTABLE_R_CONDA_PREFIX is set but Rscript is not executable."
    fi
  else
    preflight_check portable_r warn "PORTABLE_R_CONDA_PREFIX unset; using Rscript from PATH if downstream R stages need it."
  fi
  if [[ ${#analysis_id_list[@]} -eq 0 ]]; then
    preflight_check analysis_ids warn "No ANALYSIS_IDS set; --execute will derive feasible IDs from design plan; --dry-run uses the pilot preview IDs because design outputs do not exist yet."
  else
    preflight_check analysis_ids pass "${analysis_id_list[*]}"
  fi
}

quote_cmd() {
  local quoted=()
  local arg q
  for arg in "$@"; do
    printf -v q '%q' "${arg}"
    quoted+=("${q}")
  done
  printf '%s' "${quoted[*]}"
}

append_plan() {
  local stage="$1"
  local analysis_id="$2"
  local output_dir="$3"
  local command="$4"
  printf '%s\t%s\t%s\t%s\n' "${stage}" "${analysis_id}" "${output_dir}" "${command}" >> "${PLAN_TSV}"
  printf '%s\n' "${command}" >> "${PLAN_SH}"
}

run_step() {
  local stage="$1"
  local analysis_id="$2"
  local output_dir="$3"
  shift 3
  local command
  command="$(quote_cmd "$@")"
  append_plan "${stage}" "${analysis_id}" "${output_dir}" "${command}"
  if [[ "${MODE}" == "execute" ]]; then
    echo "[RUN] ${stage} ${analysis_id}"
    bash -lc "${command}"
  else
    echo "[DRY-RUN] ${stage} ${analysis_id}: ${command}"
  fi
}

analysis_args=()
analysis_id_list=()
if [[ -n "${ANALYSIS_IDS:-}" ]]; then
  # shellcheck disable=SC2206
  analysis_id_list=(${ANALYSIS_IDS//,/ })
  for analysis_id in "${analysis_id_list[@]}"; do
    analysis_args+=(--analysis-id "${analysis_id}")
  done
fi

if [[ "${PILOT_ONLY}" == "1" ]]; then
  analysis_args+=(--pilot)
  if [[ ${#analysis_id_list[@]} -eq 0 ]]; then
    analysis_id_list=(PRE_RESPONSE PAN_ICB_RESPONSE__PRE_TREATMENT ICI_COMBINATION_RESPONSE__PRE_TREATMENT)
  fi
fi

dry_run_scope_detail=""
if [[ "${MODE}" == "dry-run" && ${#analysis_id_list[@]} -eq 0 ]]; then
  analysis_id_list=(PRE_RESPONSE PAN_ICB_RESPONSE__PRE_TREATMENT ICI_COMBINATION_RESPONSE__PRE_TREATMENT)
  dry_run_scope_detail="ANALYSIS_IDS unset; dry-run previews the pilot IDs only. In --execute mode, the launcher derives feasible analysis IDs from the Spec-026 design plan after design build/plan-runs complete."
fi

write_decision_manifest() {
  local scope_mode="design_derived_all_feasible"
  local execute_scope_detail="Approved --execute derives feasible analysis IDs from the Spec-026 design plan."
  if [[ -n "${ANALYSIS_IDS:-}" ]]; then
    scope_mode="explicit_analysis_ids"
    execute_scope_detail="Approved --execute uses the explicit ANALYSIS_IDS supplied by the caller."
  elif [[ "${PILOT_ONLY}" == "1" ]]; then
    scope_mode="pilot_only"
    execute_scope_detail="Approved --execute restricts the design plan to pilot analysis IDs."
  fi

  local tcga_behavior="missing_tcga_map_status"
  if [[ -n "${TCGA_MAP}" ]]; then
    tcga_behavior="prognostic_tcga_projection"
  fi

  local portable_r_behavior="path_rscript"
  if [[ -n "${PORTABLE_R_CONDA_PREFIX:-}" ]]; then
    portable_r_behavior="portable_r_conda_prefix"
  fi

  mkdir -p "${ORCH_DIR}"
  {
    printf 'key\tvalue\n'
    printf 'mode\t%s\n' "${MODE}"
    printf 'out_root\t%s\n' "${OUT_ROOT}"
    printf 'sample_manifest\t%s\n' "${SAMPLE_MANIFEST}"
    printf 'expression_manifest\t%s\n' "${EXPRESSION_MANIFEST}"
    printf 'downloads_root\t%s\n' "${DOWNLOADS_ROOT}"
    printf 'gene_id_mapping\t%s\n' "${GENE_ID_MAPPING}"
    printf 'gene_set_registry\t%s\n' "${GENE_SET_REGISTRY}"
    printf 'criteria_registry\t%s\n' "${CRITERIA_REGISTRY}"
    printf 'count_method\t%s\n' "${COUNT_METHOD}"
    printf 'analysis_scope_mode\t%s\n' "${scope_mode}"
    printf 'analysis_ids_requested\t%s\n' "${ANALYSIS_IDS:-<unset>}"
    printf 'analysis_ids_current_preview\t%s\n' "${analysis_id_list[*]:-pending_design_plan}"
    printf 'execute_scope_detail\t%s\n' "${execute_scope_detail}"
    printf 'dry_run_scope_note\t%s\n' "${dry_run_scope_detail:-not_applicable}"
    printf 'pilot_only\t%s\n' "${PILOT_ONLY}"
    printf 'tcga_behavior\t%s\n' "${tcga_behavior}"
    printf 'tcga_map\t%s\n' "${TCGA_MAP:-<unset>}"
    printf 'naive_manifest\t%s\n' "${NAIVE_MANIFEST:-<unset>}"
    printf 'thorsson_subtypes\t%s\n' "${THORSSON_SUBTYPES:-<unset>}"
    printf 'portable_r_behavior\t%s\n' "${portable_r_behavior}"
    printf 'portable_r_conda_prefix\t%s\n' "${PORTABLE_R_CONDA_PREFIX:-<unset>}"
    printf 'allow_empty_signature\t%s\n' "${ALLOW_EMPTY_SIGNATURE}"
    printf 'allow_weak_gene_mapping\t%s\n' "${ALLOW_WEAK_GENE_MAPPING}"
    printf 'allow_welch_fallback\t%s\n' "${ALLOW_WELCH_FALLBACK}"
    printf 'execution_gate\t%s\n' 'ALLOW_ANALYSIS_ID_PIPELINE_RUN=1 required for --execute'
    printf 'reviewed_root_guard\t%s\n' 'refuses OUT_ROOT containing analysis_id_runs_t7_20260607_stage07_scale_provenance'
    printf 'claim_boundary\t%s\n' 'spec027 claims are discovery/mechanism_hypothesis only; TCGA prognostic only; LOCO internal only'
    printf 'track_boundary\t%s\n' 'Track A derivation remains separate from Track B external candidates'
  } > "${DECISION_MANIFEST}"
}

if [[ "${MODE}" == "preflight" ]]; then
  run_preflight
  write_decision_manifest
  printf 'mode\t%s\n' "${MODE}"
  printf 'out_root\t%s\n' "${OUT_ROOT}"
  printf 'preflight_tsv\t%s\n' "${PREFLIGHT_TSV}"
  printf 'decision_manifest\t%s\n' "${DECISION_MANIFEST}"
  if [[ "${preflight_status}" -eq 0 ]]; then
    printf 'preflight_status\tpass\n'
  else
    printf 'preflight_status\tfail\n'
  fi
  exit "${preflight_status}"
fi

mkdir -p "${ORCH_DIR}" "${OUT_ROOT}/logs"

printf 'stage\tanalysis_id\toutput_dir\tcommand\n' > "${PLAN_TSV}"
{
  echo "#!/usr/bin/env bash"
  echo "set -euo pipefail"
  echo "# Generated by scripts/run_analysis_id_pipeline.sh ${MODE} at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "${PLAN_SH}"

write_decision_manifest

if [[ "${MODE}" == "dry-run" ]]; then
  {
    printf 'mode\t%s\n' "${MODE}"
    if [[ -n "${dry_run_scope_detail}" ]]; then
      printf 'scope_note\t%s\n' "${dry_run_scope_detail}"
    else
      printf 'scope_note\t%s\n' "Dry-run uses the explicit ANALYSIS_IDS/PILOT_ONLY scope supplied by the caller."
    fi
    printf 'analysis_ids\t%s\n' "${analysis_id_list[*]:-pending_design_plan}"
  } > "${DRY_RUN_SCOPE_NOTE}"
fi

run_step design_build ALL "${DESIGN_DIR}" \
  "${PYTHON_BIN}" -m src.pipeline.cli design build \
  --sample-manifest "${SAMPLE_MANIFEST}" \
  --expression-manifest "${EXPRESSION_MANIFEST}" \
  --downloads-root "${DOWNLOADS_ROOT}" \
  --check-expression-readiness \
  --out "${DESIGN_DIR}" \
  --run-manifest "${RUN_MANIFEST}"

plan_args=(
  "${PYTHON_BIN}" -m src.pipeline.cli design plan-runs
  --analysis-registry "${DESIGN_DIR}/analysis_contrast_registry.tsv"
  --analysis-membership "${DESIGN_DIR}/analysis_contrast_membership.tsv"
  --out "${ORCH_DIR}"
  --execution-root "${OUT_ROOT}"
  --sample-manifest "${SAMPLE_MANIFEST}"
  --expression-manifest "${EXPRESSION_MANIFEST}"
  --downloads-root "${DOWNLOADS_ROOT}"
  --gene-id-mapping "${GENE_ID_MAPPING}"
  --python-executable "${PYTHON_BIN}"
  --count-method "${COUNT_METHOD}"
  --run-manifest "${RUN_MANIFEST}"
)
if [[ "${ALLOW_WEAK_GENE_MAPPING}" == "1" ]]; then
  plan_args+=(--allow-weak-gene-mapping)
fi
if [[ "${ALLOW_WELCH_FALLBACK}" == "1" ]]; then
  plan_args+=(--allow-welch-fallback)
fi
if [[ ${#analysis_args[@]} -gt 0 ]]; then
  plan_args+=("${analysis_args[@]}")
fi

run_step design_plan ALL "${EXECUTION_PLAN}" "${plan_args[@]}"

if [[ "${MODE}" == "execute" ]]; then
  if [[ ! -f "${EXECUTION_PLAN}" ]]; then
    echo "Missing execution plan after design planning: ${EXECUTION_PLAN}" >&2
    exit 5
  fi
  mapfile -t analysis_id_list < <(awk -F '\t' 'NR>1 && $1 != "" {seen[$1]=1} END{for (id in seen) print id}' "${EXECUTION_PLAN}" | sort)
  if [[ ${#analysis_id_list[@]} -eq 0 ]]; then
    echo "No feasible analysis IDs in ${EXECUTION_PLAN}" >&2
    exit 5
  fi
  tail -n +2 "${EXECUTION_PLAN}" | while IFS=$'\t' read -r analysis_id _family _contrast _timing stage command _output_dir _rest; do
    if [[ "${stage}" == "stage06_de" || "${stage}" == "stage07_meta" ]]; then
      append_plan "${stage}" "${analysis_id}" "${_output_dir}" "${command}"
      echo "[RUN] ${stage} ${analysis_id}"
      bash -lc "${command}"
    fi
  done
else
  for analysis_id in "${analysis_id_list[@]}"; do
    de_args=(
      "${PYTHON_BIN}" -m src.pipeline.cli de run
      --contrast "${analysis_id}"
      --analysis-id "${analysis_id}"
      --analysis-registry "${DESIGN_DIR}/analysis_contrast_registry.tsv"
      --analysis-membership "${DESIGN_DIR}/analysis_contrast_membership.tsv"
      --sample-manifest "${SAMPLE_MANIFEST}"
      --expression-manifest "${EXPRESSION_MANIFEST}"
      --downloads-root "${DOWNLOADS_ROOT}"
      --count-method "${COUNT_METHOD}"
      --gene-id-mapping "${GENE_ID_MAPPING}"
      --comparison-registry "${COMPARISON_REGISTRY}"
      --out "${OUT_ROOT}/de"
      --run-manifest "${RUN_MANIFEST}"
    )
    if [[ "${ALLOW_WEAK_GENE_MAPPING}" == "1" ]]; then
      de_args+=(--allow-weak-gene-mapping)
    fi
    if [[ "${ALLOW_WELCH_FALLBACK}" == "1" ]]; then
      de_args+=(--allow-welch-fallback)
    fi
    run_step stage06_de "${analysis_id}" "${OUT_ROOT}/de/${analysis_id}" "${de_args[@]}"

    meta_args=(
      "${PYTHON_BIN}" -m src.pipeline.cli meta run
      --contrast "${analysis_id}"
      --analysis-id "${analysis_id}"
      --de-dir "${OUT_ROOT}/de"
      --sample-manifest "${SAMPLE_MANIFEST}"
      --comparison-registry "${COMPARISON_REGISTRY}"
      --skip-forest-plots
      --out "${OUT_ROOT}/meta"
      --run-manifest "${RUN_MANIFEST}"
    )
    run_step stage07_meta "${analysis_id}" "${OUT_ROOT}/meta/${analysis_id}" "${meta_args[@]}"
  done
fi

for analysis_id in "${analysis_id_list[@]}"; do
  signature_dir="${OUT_ROOT}/signature/${analysis_id}"
  signature_file="${signature_dir}/responder_signature_tiered.tsv"
  signature_args=(
    "${PYTHON_BIN}" -m src.pipeline.cli signature derive
    --analysis-id "${analysis_id}"
    --run-root "${OUT_ROOT}"
    --comparison-registry "${COMPARISON_REGISTRY}"
    --out "${signature_dir}"
    --run-manifest "${RUN_MANIFEST}"
  )
  if [[ "${ALLOW_EMPTY_SIGNATURE}" == "1" ]]; then
    signature_args+=(--allow-empty-signature)
  fi
  run_step signature "${analysis_id}" "${signature_dir}" "${signature_args[@]}"
done

run_step immune_score ALL "${OUT_ROOT}/immune_state" \
  "${PYTHON_BIN}" -m src.pipeline.cli immune score \
  --sample-manifest "${SAMPLE_MANIFEST}" \
  --expression-manifest "${EXPRESSION_MANIFEST}" \
  --downloads-root "${DOWNLOADS_ROOT}" \
  --gene-set-registry "${GENE_SET_REGISTRY}" \
  --out "${OUT_ROOT}/immune_state" \
  --run-manifest "${RUN_MANIFEST}"

run_step immune_effects ALL "${OUT_ROOT}/immune_state" \
  "${PYTHON_BIN}" -m src.pipeline.cli immune effects \
  --sample-manifest "${SAMPLE_MANIFEST}" \
  --immune-dir "${OUT_ROOT}/immune_state" \
  --expression-manifest "${EXPRESSION_MANIFEST}" \
  --downloads-root "${DOWNLOADS_ROOT}" \
  --allow-weak-gene-mapping \
  --out "${OUT_ROOT}/immune_state" \
  --run-manifest "${RUN_MANIFEST}"

for analysis_id in "${analysis_id_list[@]}"; do
  signature_file="${OUT_ROOT}/signature/${analysis_id}/responder_signature_tiered.tsv"
  run_step validate "${analysis_id}" "${OUT_ROOT}/validation/${analysis_id}" \
    "${PYTHON_BIN}" -m src.pipeline.cli validate run \
    --signature "${signature_file}" \
    --results-root "${OUT_ROOT}" \
    --contrast "${analysis_id}" \
    --indirect-meta "${OUT_ROOT}/meta/${analysis_id}/meta_effects.tsv" \
    --meta-loco-summary "${OUT_ROOT}/meta/${analysis_id}/meta_leave_one_out_summary.tsv" \
    --sample-manifest "${SAMPLE_MANIFEST}" \
    --out "${OUT_ROOT}/validation/${analysis_id}" \
    --run-manifest "${RUN_MANIFEST}"
done

for analysis_id in "${analysis_id_list[@]}"; do
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
    run_step tcga "${analysis_id}" "${OUT_ROOT}/tcga_projection/${analysis_id}" "${tcga_args[@]}"
  else
    skip_dir="${OUT_ROOT}/tcga_projection/${analysis_id}"
    skip_cmd="$(quote_cmd mkdir -p "${skip_dir}") && printf 'stage\tproject\tsignature_tier\tstatus\treason\tdetail\n%s\t%s\t%s\t%s\t%s\t%s\n' tcga_project '' ALL blocked missing_tcga_map 'Set TCGA_MAP to enable prognostic projection.' > $(printf '%q' "${skip_dir}/tcga_projection_status.tsv")"
    append_plan tcga_skip "${analysis_id}" "${skip_dir}" "${skip_cmd}"
    if [[ "${MODE}" == "execute" ]]; then
      bash -lc "${skip_cmd}"
    else
      echo "[DRY-RUN] tcga_skip ${analysis_id}: ${skip_cmd}"
    fi
  fi
done

for analysis_id in "${analysis_id_list[@]}"; do
  run_step interpret_enrich "${analysis_id}" "${OUT_ROOT}/interpretation/enrichment/${analysis_id}" \
    "${PYTHON_BIN}" -m src.pipeline.cli interpret enrich \
    --results-root "${OUT_ROOT}" \
    --analysis-id "${analysis_id}" \
    --collections "${GENE_SET_REGISTRY}" \
    --out "${OUT_ROOT}/interpretation" \
    --run-manifest "${RUN_MANIFEST}"

  run_step interpret_network "${analysis_id}" "${OUT_ROOT}/interpretation/network/${analysis_id}" \
    "${PYTHON_BIN}" -m src.pipeline.cli interpret network \
    --results-root "${OUT_ROOT}" \
    --analysis-id "${analysis_id}" \
    --expression-manifest "${EXPRESSION_MANIFEST}" \
    --downloads-root "${DOWNLOADS_ROOT}" \
    --out "${OUT_ROOT}/interpretation" \
    --run-manifest "${RUN_MANIFEST}"
done

run_step interpret_hub_meta ALL "${OUT_ROOT}/interpretation/hub_meta" \
  "${PYTHON_BIN}" -m src.pipeline.cli interpret hub-meta \
  --results-root "${OUT_ROOT}" \
  --out "${OUT_ROOT}/interpretation" \
  --run-manifest "${RUN_MANIFEST}"

run_step interpret_immunophenotype ALL "${OUT_ROOT}/interpretation/immunophenotype" \
  "${PYTHON_BIN}" -m src.pipeline.cli interpret immunophenotype \
  --results-root "${OUT_ROOT}" \
  --criteria-registry "${CRITERIA_REGISTRY}" \
  --out "${OUT_ROOT}/interpretation" \
  --run-manifest "${RUN_MANIFEST}"

run_step interpret_epi_infer ALL "${OUT_ROOT}/interpretation/epigenetic" \
  "${PYTHON_BIN}" -m src.pipeline.cli interpret epi-infer \
  --results-root "${OUT_ROOT}" \
  --expression-manifest "${EXPRESSION_MANIFEST}" \
  --out "${OUT_ROOT}/interpretation" \
  --run-manifest "${RUN_MANIFEST}"

run_step report ALL "${OUT_ROOT}/reports" \
  "${PYTHON_BIN}" -m src.pipeline.cli report build \
  --results-root "${OUT_ROOT}" \
  --out "${OUT_ROOT}/reports" \
  --run-manifest "${RUN_MANIFEST}"

run_step postrun_audit ALL "${POSTRUN_AUDIT_TSV}" \
  "${PYTHON_BIN}" scripts/audit_analysis_id_pipeline_run.py \
  --run-root "${OUT_ROOT}" \
  --out "${POSTRUN_AUDIT_TSV}" \
  --summary-out "${POSTRUN_AUDIT_MD}"

chmod +x "${PLAN_SH}"
printf 'mode\t%s\n' "${MODE}"
printf 'out_root\t%s\n' "${OUT_ROOT}"
printf 'plan_tsv\t%s\n' "${PLAN_TSV}"
printf 'plan_sh\t%s\n' "${PLAN_SH}"
if [[ "${MODE}" == "dry-run" ]]; then
  printf 'dry_run_scope_note\t%s\n' "${DRY_RUN_SCOPE_NOTE}"
fi
printf 'decision_manifest\t%s\n' "${DECISION_MANIFEST}"
printf 'run_manifest\t%s\n' "${RUN_MANIFEST}"
