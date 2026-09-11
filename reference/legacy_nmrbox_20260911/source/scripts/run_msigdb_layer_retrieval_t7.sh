#!/usr/bin/env bash
set -euo pipefail

# Retrieve layered MSigDB gene sets for pipeline:
# HALLMARK -> KEGG -> C7 (ImmuneSigDB) -> REACTOME
#
# Usage:
#   bash scripts/run_msigdb_layer_retrieval_t7.sh
#   bash scripts/run_msigdb_layer_retrieval_t7.sh /Volumes/T7/1-Epigenetics_MSc_Thesis

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
T7_ROOT="${1:-/Volumes/T7/1-Epigenetics_MSc_Thesis}"
STAMP="$(date +%F)"
OUT_DIR="${T7_ROOT}/gene_sets/msigdb_layers_${STAMP}"

mkdir -p "${OUT_DIR}"

cd "${REPO_ROOT}"

echo "Repository root: ${REPO_ROOT}"
echo "Output dir:      ${OUT_DIR}"

if ! command -v Rscript >/dev/null 2>&1; then
  echo "Rscript not found. Please activate your R environment first." >&2
  exit 2
fi

echo "== Step 1/3: Ensure msigdbr package =="
Rscript -e "if (!requireNamespace('msigdbr', quietly=TRUE)) install.packages('msigdbr', repos='https://cloud.r-project.org')"

echo "== Step 2/3: Export layered GMT files =="
Rscript scripts/export_msigdb_layers.R --out-dir "${OUT_DIR}" --species "Homo sapiens"

echo "== Step 3/3: File summary =="
ls -lh "${OUT_DIR}"
du -sh "${OUT_DIR}"

echo
echo "Completed."
echo "Use these files in registry:"
echo "- ${OUT_DIR}/MSIGDB_HALLMARK_Hs.gmt"
echo "- ${OUT_DIR}/MSIGDB_KEGG_Hs.gmt"
echo "- ${OUT_DIR}/MSIGDB_C7_IMMUNESIGDB_Hs.gmt"
echo "- ${OUT_DIR}/MSIGDB_REACTOME_Hs.gmt"
