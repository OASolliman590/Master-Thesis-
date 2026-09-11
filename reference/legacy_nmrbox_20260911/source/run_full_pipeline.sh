#!/usr/bin/env bash
set -euo pipefail

export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/matplotlib-${USER:-unknown}}"
RUN_TAG="${RUN_TAG:-$(date +%Y%m%d_%H%M%S)}"
OUT_ROOT="${OUT_ROOT:-results/full_pipeline_${RUN_TAG}}"
RUN_MANIFEST="${RUN_MANIFEST:-logs/run_manifest_${RUN_TAG}.yaml}"
PYTHON_BIN="${PYTHON_BIN:-python}"
CIB_ABS="${CIB_ABS:-inputs/cibersortx/absolute.tsv}"
CIB_REL="${CIB_REL:-inputs/cibersortx/relative.tsv}"
SAMPLE_MANIFEST="${SAMPLE_MANIFEST:-configs/sample_manifest_curated.tsv}"
EXPRESSION_MANIFEST="${EXPRESSION_MANIFEST:-results/geo_tables/geo_tables_summary.tsv}"
DOWNLOADS_ROOT="${DOWNLOADS_ROOT:-results/retrieval/downloads}"
GENE_SET_REGISTRY="${GENE_SET_REGISTRY:-configs/immune_gene_sets_registry.tsv}"
ROUTER_ALLOW_WELCH_FALLBACK="${ROUTER_ALLOW_WELCH_FALLBACK:-0}"

ROUTER_WELCH_ARG=()
if [[ "${ROUTER_ALLOW_WELCH_FALLBACK}" == "1" ]]; then
  ROUTER_WELCH_ARG+=(--allow-welch-fallback)
fi

"${PYTHON_BIN}" -m pipeline.cli intake build-patient-manifest \
  --sample-manifest "${SAMPLE_MANIFEST}" \
  --cohort-input-table results/geo_tables/cohort_input_table_all.tsv \
  --out "${OUT_ROOT}/patient_manifest" \
  --run-manifest "${RUN_MANIFEST}"

"${PYTHON_BIN}" -m pipeline.cli router run \
  --sample-manifest "${SAMPLE_MANIFEST}" \
  --track ALL \
  --out "${OUT_ROOT}/router" \
  --expression-manifest "${EXPRESSION_MANIFEST}" \
  --downloads-root "${DOWNLOADS_ROOT}" \
  --count-method deseq2 \
  "${ROUTER_WELCH_ARG[@]}" \
  --run-manifest "${RUN_MANIFEST}"

"${PYTHON_BIN}" -m pipeline.cli signature derive \
  --contrast PRE_RESPONSE \
  --meta-dir "${OUT_ROOT}/router/meta_analysis/pre_response_only/PRE_RESPONSE" \
  --out "${OUT_ROOT}/signature_sets" \
  --run-manifest "${RUN_MANIFEST}"

if [[ ! -f "$CIB_ABS" || ! -f "$CIB_REL" ]]; then
  echo "[WARN] CIBERSORTx files missing; continuing with Spec 007 gene-set immune scoring only."
fi

"${PYTHON_BIN}" -m pipeline.cli immune score \
  --sample-manifest "${SAMPLE_MANIFEST}" \
  --expression-manifest "${EXPRESSION_MANIFEST}" \
  --downloads-root "${DOWNLOADS_ROOT}" \
  --gene-set-registry "${GENE_SET_REGISTRY}" \
  --out "${OUT_ROOT}/immune_state" \
  --run-manifest "${RUN_MANIFEST}"

"${PYTHON_BIN}" -m pipeline.cli immune effects \
  --sample-manifest "${SAMPLE_MANIFEST}" \
  --immune-dir "${OUT_ROOT}/immune_state" \
  --expression-manifest "${EXPRESSION_MANIFEST}" \
  --downloads-root "${DOWNLOADS_ROOT}" \
  --allow-weak-gene-mapping \
  --out "${OUT_ROOT}/immune_state" \
  --run-manifest "${RUN_MANIFEST}"

"${PYTHON_BIN}" -m pipeline.cli report build \
  --results-root "${OUT_ROOT}" \
  --out "${OUT_ROOT}/reports" \
  --run-manifest "${RUN_MANIFEST}"

echo "DONE: ${OUT_ROOT}"
