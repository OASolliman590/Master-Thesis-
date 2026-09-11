#!/usr/bin/env bash
set -euo pipefail

: "${OUT_ROOT:?Set OUT_ROOT to an existing analysis-id run root.}"

PYTHON_BIN="${PYTHON_BIN:-python}"
EXPRESSION_MANIFEST="${EXPRESSION_MANIFEST:-results/geo_tables/geo_tables_summary.tsv}"
DOWNLOADS_ROOT="${DOWNLOADS_ROOT:-results/retrieval/downloads}"
GENE_SET_REGISTRY="${GENE_SET_REGISTRY:-configs/immune_gene_sets_registry.tsv}"
CRITERIA_REGISTRY="${CRITERIA_REGISTRY:-configs/immunophenotype_criteria_registry.tsv}"
RUN_MANIFEST="${RUN_MANIFEST:-${OUT_ROOT}/logs/run_manifest.yaml}"
EXECUTION_PLAN="${EXECUTION_PLAN:-${OUT_ROOT}/orchestration/analysis_execution_plan.tsv}"
POSTRUN_AUDIT_TSV="${POSTRUN_AUDIT_TSV:-${OUT_ROOT}/orchestration/postrun_audit.tsv}"
POSTRUN_AUDIT_MD="${POSTRUN_AUDIT_MD:-${OUT_ROOT}/orchestration/postrun_audit.md}"

if [[ ! -f "${EXECUTION_PLAN}" ]]; then
  echo "Missing execution plan: ${EXECUTION_PLAN}" >&2
  exit 2
fi

mkdir -p "${OUT_ROOT}/interpretation" "${OUT_ROOT}/reports" "${OUT_ROOT}/logs" "${OUT_ROOT}/orchestration"

mapfile -t analysis_id_list < <(
  awk -F '\t' 'NR>1 && $1 != "" {seen[$1]=1} END{for (id in seen) print id}' "${EXECUTION_PLAN}" | sort
)
if [[ ${#analysis_id_list[@]} -eq 0 ]]; then
  echo "No analysis IDs found in ${EXECUTION_PLAN}" >&2
  exit 2
fi

for analysis_id in "${analysis_id_list[@]}"; do
  echo "[RUN] interpret_enrich ${analysis_id}"
  "${PYTHON_BIN}" -m src.pipeline.cli interpret enrich \
    --results-root "${OUT_ROOT}" \
    --analysis-id "${analysis_id}" \
    --collections "${GENE_SET_REGISTRY}" \
    --out "${OUT_ROOT}/interpretation" \
    --run-manifest "${RUN_MANIFEST}"

  echo "[RUN] interpret_network ${analysis_id}"
  "${PYTHON_BIN}" -m src.pipeline.cli interpret network \
    --results-root "${OUT_ROOT}" \
    --analysis-id "${analysis_id}" \
    --expression-manifest "${EXPRESSION_MANIFEST}" \
    --downloads-root "${DOWNLOADS_ROOT}" \
    --out "${OUT_ROOT}/interpretation" \
    --run-manifest "${RUN_MANIFEST}"
done

echo "[RUN] interpret_hub_meta ALL"
"${PYTHON_BIN}" -m src.pipeline.cli interpret hub-meta \
  --results-root "${OUT_ROOT}" \
  --out "${OUT_ROOT}/interpretation" \
  --run-manifest "${RUN_MANIFEST}"

echo "[RUN] interpret_immunophenotype ALL"
"${PYTHON_BIN}" -m src.pipeline.cli interpret immunophenotype \
  --results-root "${OUT_ROOT}" \
  --criteria-registry "${CRITERIA_REGISTRY}" \
  --out "${OUT_ROOT}/interpretation" \
  --run-manifest "${RUN_MANIFEST}"

echo "[RUN] interpret_epi_infer ALL"
"${PYTHON_BIN}" -m src.pipeline.cli interpret epi-infer \
  --results-root "${OUT_ROOT}" \
  --expression-manifest "${EXPRESSION_MANIFEST}" \
  --out "${OUT_ROOT}/interpretation" \
  --run-manifest "${RUN_MANIFEST}"

echo "[RUN] report ALL"
"${PYTHON_BIN}" -m src.pipeline.cli report build \
  --results-root "${OUT_ROOT}" \
  --out "${OUT_ROOT}/reports" \
  --run-manifest "${RUN_MANIFEST}"

echo "[RUN] postrun_audit ALL"
"${PYTHON_BIN}" scripts/audit_analysis_id_pipeline_run.py \
  --run-root "${OUT_ROOT}" \
  --out "${POSTRUN_AUDIT_TSV}" \
  --summary-out "${POSTRUN_AUDIT_MD}"

printf 'mode\tresume_interpretation\n'
printf 'out_root\t%s\n' "${OUT_ROOT}"
printf 'analysis_ids\t%s\n' "${analysis_id_list[*]}"
printf 'postrun_audit_tsv\t%s\n' "${POSTRUN_AUDIT_TSV}"
printf 'postrun_audit_md\t%s\n' "${POSTRUN_AUDIT_MD}"
