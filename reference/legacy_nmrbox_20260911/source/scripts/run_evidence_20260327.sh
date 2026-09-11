#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/omara.soliman/Desktop/Research/11- Epigenetic's Master Thesis/2-Experimental/Computation Arm/06_analysis_pipeline_repo"
cd "$ROOT"

export MPLCONFIGDIR="/tmp/matplotlib-${USER}"
RUN_TAG="evidence_$(date +%Y%m%d_%H%M%S)"
OUT_ROOT="results/${RUN_TAG}"
RUN_MANIFEST="logs/run_manifest_${RUN_TAG}.yaml"

SAMPLE_MANIFEST="configs/sample_manifest_curated.tsv"
EXPR_MANIFEST="results/geo_tables/geo_tables_summary.tsv"
DOWNLOADS_ROOT="results/retrieval/downloads"
GENE_SET_REGISTRY="configs/immune_gene_sets_registry.tsv"

mkdir -p "$OUT_ROOT"

echo "[1/7] Router run (ALL tracks, include excluded + stubs for evidence coverage)"
python -m pipeline.cli router run \
  --sample-manifest "$SAMPLE_MANIFEST" \
  --track ALL \
  --include-excluded \
  --allow-stub-rows \
  --out "$OUT_ROOT/router" \
  --expression-manifest "$EXPR_MANIFEST" \
  --downloads-root "$DOWNLOADS_ROOT" \
  --count-method deseq2 \
  --run-manifest "$RUN_MANIFEST"

echo "[2/7] Signature derive (strict)"
STRICT_OK=1
if ! python -m pipeline.cli signature derive \
  --contrast PRE_RESPONSE \
  --meta-dir "$OUT_ROOT/router/meta_analysis/pre_response_only/PRE_RESPONSE" \
  --out "$OUT_ROOT/signature_sets" \
  --run-manifest "$RUN_MANIFEST"; then
  STRICT_OK=0
  echo "[WARN] Strict signature derivation failed; retrying with --allow-empty-signature for downstream evidence."
  python -m pipeline.cli signature derive \
    --contrast PRE_RESPONSE \
    --meta-dir "$OUT_ROOT/router/meta_analysis/pre_response_only/PRE_RESPONSE" \
    --allow-empty-signature \
    --out "$OUT_ROOT/signature_sets" \
    --run-manifest "$RUN_MANIFEST"
fi

echo "[3/7] Immune score + effects"
python -m pipeline.cli immune score \
  --sample-manifest "$SAMPLE_MANIFEST" \
  --expression-manifest "$EXPR_MANIFEST" \
  --downloads-root "$DOWNLOADS_ROOT" \
  --gene-set-registry "$GENE_SET_REGISTRY" \
  --out "$OUT_ROOT/immune_state" \
  --run-manifest "$RUN_MANIFEST"

python -m pipeline.cli immune effects \
  --sample-manifest "$SAMPLE_MANIFEST" \
  --immune-dir "$OUT_ROOT/immune_state" \
  --expression-manifest "$EXPR_MANIFEST" \
  --downloads-root "$DOWNLOADS_ROOT" \
  --out "$OUT_ROOT/immune_state" \
  --run-manifest "$RUN_MANIFEST"

echo "[4/7] Mega run"
python -m pipeline.cli mega run \
  --contrast PRE_RESPONSE \
  --sample-manifest "$SAMPLE_MANIFEST" \
  --expression-manifest "$EXPR_MANIFEST" \
  --downloads-root "$DOWNLOADS_ROOT" \
  --meta-dir "$OUT_ROOT/router/meta_analysis/pre_response_only/PRE_RESPONSE/meta_effects.tsv" \
  --out "$OUT_ROOT/mega_analysis" \
  --run-manifest "$RUN_MANIFEST"

echo "[5/7] TCGA map"
python -m pipeline.cli tcga map \
  --projects TCGA-PRAD TCGA-LUAD \
  --out "$OUT_ROOT/tcga_gdc_map" \
  --run-manifest "$RUN_MANIFEST"

echo "[6/7] TCGA project (survival scaffold)"
python -m pipeline.cli tcga project \
  --signature "$OUT_ROOT/signature_sets/pre_response_signature_v1.tsv" \
  --tcga-map "$OUT_ROOT/tcga_gdc_map/tcga_sample_map.tsv" \
  --out "$OUT_ROOT/tcga_projection" \
  --run-manifest "$RUN_MANIFEST"

echo "[7/7] Report build"
python -m pipeline.cli report build \
  --results-root "$OUT_ROOT" \
  --out "$OUT_ROOT/reports" \
  --run-manifest "$RUN_MANIFEST"

echo "STRICT_SIGNATURE_OK=$STRICT_OK" > "$OUT_ROOT/evidence_status.env"
echo "RUN_ROOT=$OUT_ROOT" >> "$OUT_ROOT/evidence_status.env"
echo "RUN_MANIFEST=$RUN_MANIFEST" >> "$OUT_ROOT/evidence_status.env"

echo "DONE evidence run at $OUT_ROOT"
