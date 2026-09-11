#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export MPLCONFIGDIR="/tmp/matplotlib-${USER}"

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: $0 <run_root> [run_manifest]"
  echo "Example: $0 results/evidence_20260327_104332"
  exit 1
fi

RUN_ROOT="$1"
if [[ ! -d "$RUN_ROOT" ]]; then
  echo "[ERROR] run_root does not exist: $RUN_ROOT"
  exit 1
fi
RUN_TAG="$(basename "$RUN_ROOT")"
RUN_MANIFEST="${2:-logs/run_manifest_${RUN_TAG}.yaml}"

SAMPLE_MANIFEST="configs/sample_manifest_curated.tsv"
EXPR_MANIFEST="results/geo_tables/geo_tables_summary.tsv"
DOWNLOADS_ROOT="results/retrieval/downloads"
GENE_SET_REGISTRY="configs/immune_gene_sets_registry.tsv"
META_DIR="$RUN_ROOT/router/meta_analysis/pre_response_only/PRE_RESPONSE"
SIGNATURE_DIR="$RUN_ROOT/signature_sets"
IMMUNE_DIR="$RUN_ROOT/immune_state"
TCGA_MAP="$RUN_ROOT/tcga_gdc_map/tcga_sample_map.tsv"
TCGA_OUT="$RUN_ROOT/tcga_projection"
REPORT_OUT="$RUN_ROOT/reports"

if [[ ! -f "$SAMPLE_MANIFEST" ]]; then
  echo "[ERROR] Missing sample manifest: $SAMPLE_MANIFEST"
  exit 1
fi
if [[ ! -f "$EXPR_MANIFEST" ]]; then
  echo "[ERROR] Missing expression manifest: $EXPR_MANIFEST"
  exit 1
fi
if [[ ! -f "$GENE_SET_REGISTRY" ]]; then
  echo "[ERROR] Missing gene set registry: $GENE_SET_REGISTRY"
  exit 1
fi
if [[ ! -f "$TCGA_MAP" ]]; then
  echo "[ERROR] Missing TCGA map file in run root: $TCGA_MAP"
  exit 1
fi

command_seen() {
  local cmd_name="$1"
  [[ -f "$RUN_MANIFEST" ]] && rg -q "\"command\": \"${cmd_name}\"" "$RUN_MANIFEST"
}

check_gene_set_paths() {
  python - "$GENE_SET_REGISTRY" <<'PY'
import csv
import sys
from pathlib import Path

registry = Path(sys.argv[1])
missing = []
with registry.open("r", encoding="utf-8") as fh:
    reader = csv.DictReader(fh, delimiter="\t")
    for row in reader:
        cohort = row.get("cohort_id", "") or "UNKNOWN"
        for key in ("hallmark_gene_set_path", "gene_set_path", "kegg_gene_set_path"):
            value = (row.get(key, "") or "").strip()
            if not value:
                continue
            path = Path(value).expanduser()
            if not path.exists():
                missing.append((cohort, key, str(path)))

if missing:
    print("[ERROR] Missing gene-set files required by registry:")
    for cohort, key, path in missing:
        print(f"  - cohort={cohort} field={key} path={path}")
    sys.exit(2)
print("[OK] Gene-set registry paths are resolvable.")
PY
}

check_tcga_local_files() {
  python - "$TCGA_MAP" <<'PY'
import csv
import sys
from pathlib import Path

map_path = Path(sys.argv[1])
missing = []
with map_path.open("r", encoding="utf-8") as fh:
    reader = csv.DictReader(fh, delimiter="\t")
    for row in reader:
        project = row.get("project", "UNKNOWN")
        expr = Path((row.get("local_expression_path", "") or "").strip())
        surv = Path((row.get("local_survival_path", "") or "").strip())
        if not expr.exists():
            missing.append((project, "local_expression_path", str(expr)))
        if not surv.exists():
            missing.append((project, "local_survival_path", str(surv)))

if missing:
    print("[ERROR] Missing TCGA local files required for tcga project:")
    for project, field, path in missing:
        print(f"  - project={project} field={field} path={path}")
    sys.exit(2)
print("[OK] TCGA local expression/survival files are present.")
PY
}

signature_has_genes() {
  local sig_file="$SIGNATURE_DIR/pre_response_signature_v1.tsv"
  [[ -f "$sig_file" ]] || return 1
  local n_lines
  n_lines=$(wc -l < "$sig_file" | tr -d ' ')
  [[ "$n_lines" -gt 1 ]]
}

DID_RUN=0

echo "[INFO] Resuming evidence run"
echo "       run_root    = $RUN_ROOT"
echo "       run_manifest= $RUN_MANIFEST"

check_gene_set_paths
check_tcga_local_files

if command_seen "immune score" && [[ -s "$IMMUNE_DIR/estimate_scores.tsv" ]]; then
  echo "[SKIP] immune score already succeeded (manifest + output present)."
else
  echo "[RUN] immune score"
  python -m pipeline.cli immune score \
    --sample-manifest "$SAMPLE_MANIFEST" \
    --expression-manifest "$EXPR_MANIFEST" \
    --downloads-root "$DOWNLOADS_ROOT" \
    --gene-set-registry "$GENE_SET_REGISTRY" \
    --out "$IMMUNE_DIR" \
    --run-manifest "$RUN_MANIFEST"
  DID_RUN=1
fi

if command_seen "immune effects" && [[ -s "$IMMUNE_DIR/marker_correlations.tsv" ]] && [[ -s "$IMMUNE_DIR/cohort_level_effects.tsv" ]]; then
  echo "[SKIP] immune effects already succeeded (manifest + outputs present)."
else
  echo "[RUN] immune effects"
  python -m pipeline.cli immune effects \
    --sample-manifest "$SAMPLE_MANIFEST" \
    --immune-dir "$IMMUNE_DIR" \
    --expression-manifest "$EXPR_MANIFEST" \
    --downloads-root "$DOWNLOADS_ROOT" \
    --out "$IMMUNE_DIR" \
    --run-manifest "$RUN_MANIFEST"
  DID_RUN=1
fi

if command_seen "signature derive" && signature_has_genes; then
  echo "[SKIP] signature derive already produced non-empty signature."
else
  echo "[RUN] signature derive (strict, no empty override)"
  python -m pipeline.cli signature derive \
    --contrast PRE_RESPONSE \
    --meta-dir "$META_DIR" \
    --out "$SIGNATURE_DIR" \
    --run-manifest "$RUN_MANIFEST"
  DID_RUN=1
fi

if command_seen "tcga project" && ls "$TCGA_OUT"/*_survival_stats.tsv >/dev/null 2>&1; then
  echo "[SKIP] tcga project already has survival outputs."
else
  echo "[RUN] tcga project"
  python -m pipeline.cli tcga project \
    --signature "$SIGNATURE_DIR/pre_response_signature_v1.tsv" \
    --tcga-map "$TCGA_MAP" \
    --out "$TCGA_OUT" \
    --run-manifest "$RUN_MANIFEST"
  DID_RUN=1
fi

if [[ "$DID_RUN" -eq 1 ]] || ! command_seen "report build" || [[ ! -f "$REPORT_OUT/pipeline_summary.md" ]]; then
  echo "[RUN] report build"
  python -m pipeline.cli report build \
    --results-root "$RUN_ROOT" \
    --out "$REPORT_OUT" \
    --run-manifest "$RUN_MANIFEST"
else
  echo "[SKIP] report build already succeeded and no new stage was executed."
fi

echo "[DONE] Resume workflow complete for $RUN_ROOT"
