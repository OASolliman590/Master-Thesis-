#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ $# -lt 3 || $# -gt 4 ]]; then
  echo "Usage: $0 <run_root> <signature_tsv> <concordance_tsv> [run_manifest]"
  echo "Example: $0 results/tcga_naive_projection results/full_pipeline_20260327/signature_sets/pre_response_signature_v1.tsv results/full_pipeline_20260327/validation/validation_concordance.tsv"
  exit 1
fi

export MPLCONFIGDIR="/tmp/matplotlib-${USER}"

RUN_ROOT="$1"
SIGNATURE="$2"
CONCORDANCE="$3"
RUN_TAG="$(basename "$RUN_ROOT")"
RUN_MANIFEST="${4:-logs/run_manifest_${RUN_TAG}.yaml}"

SAMPLE_MANIFEST="${SAMPLE_MANIFEST:-configs/sample_manifest_curated.tsv}"
PROJECT_REGISTRY="${PROJECT_REGISTRY:-configs/tcga_naive_project_registry.tsv}"
EPI_MIN_SAMPLES="${TCGA_EPI_MIN_SAMPLES:-30}"

MAPPING_DIR="$RUN_ROOT/mapping"
MANIFEST_DIR="$RUN_ROOT/manifests"
TIER_DIR="$RUN_ROOT/concordance_tiers"
PROJECTION_DIR="$RUN_ROOT/projection"
EPI_DIR="$RUN_ROOT/epidemiology"
REPORT_DIR="$RUN_ROOT/reports"

TCGA_MAP="$MAPPING_DIR/tcga_sample_map.tsv"
NAIVE_MAP="$MAPPING_DIR/geo_tcga_cancer_mapping.tsv"
NAIVE_MANIFEST="$MANIFEST_DIR/tcga_naive_patient_manifest.tsv"
CLINICAL_FLAT="$MANIFEST_DIR/tcga_clinical_flat.tsv"
PROJECTION_STATUS="$PROJECTION_DIR/tcga_projection_status.tsv"
PAN_STATUS="$REPORT_DIR/tcga_pan_cancer_status.tsv"
TIER_SUMMARY="$TIER_DIR/tier_performance_summary.tsv"
REPORT_FILE="$REPORT_DIR/pipeline_summary.md"

mkdir -p "$MAPPING_DIR" "$MANIFEST_DIR" "$TIER_DIR" "$PROJECTION_DIR" "$EPI_DIR" "$REPORT_DIR"

if [[ ! -f "$SAMPLE_MANIFEST" ]]; then
  echo "[ERROR] Missing sample manifest: $SAMPLE_MANIFEST"
  exit 1
fi
if [[ ! -f "$PROJECT_REGISTRY" ]]; then
  echo "[ERROR] Missing project registry: $PROJECT_REGISTRY"
  exit 1
fi
if [[ ! -f "$SIGNATURE" ]]; then
  echo "[ERROR] Missing signature file: $SIGNATURE"
  exit 1
fi
if [[ ! -f "$CONCORDANCE" ]]; then
  echo "[ERROR] Missing concordance file: $CONCORDANCE"
  exit 1
fi

command_seen() {
  local cmd_name="$1"
  [[ -f "$RUN_MANIFEST" ]] && rg -Fq "\"command\": \"$cmd_name\"" "$RUN_MANIFEST"
}

registry_projects() {
  python - "$PROJECT_REGISTRY" <<'PY'
import csv
import sys
from pathlib import Path

reg = Path(sys.argv[1])
projects = []
with reg.open("r", encoding="utf-8") as fh:
    reader = csv.DictReader(fh, delimiter="\t")
    for row in reader:
        inc = (row.get("analysis_include_flag", "") or "").strip().lower()
        if inc in {"", "1", "true", "yes", "y"}:
            project = (row.get("tcga_project", "") or "").strip()
            if project:
                projects.append(project)
print(" ".join(projects))
PY
}

check_tcga_local_files() {
  python - "$TCGA_MAP" <<'PY'
import csv
import sys
from pathlib import Path

map_path = Path(sys.argv[1])
if not map_path.exists():
    print(f"[ERROR] Missing TCGA map: {map_path}")
    sys.exit(2)

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
    print("[ERROR] Missing TCGA local expression/survival files:")
    for project, field, path in missing:
        print(f"  - project={project} field={field} path={path}")
    sys.exit(2)
print("[OK] TCGA local files are present for all projects in map.")
PY
}

has_completed_projection() {
  python - "$PROJECTION_STATUS" <<'PY'
import csv
import sys
from pathlib import Path

status = Path(sys.argv[1])
if not status.exists():
    sys.exit(1)
with status.open("r", encoding="utf-8") as fh:
    for row in csv.DictReader(fh, delimiter="\t"):
        if (row.get("status", "") or "").strip() == "completed":
            sys.exit(0)
sys.exit(1)
PY
}

echo "[INFO] Resume TCGA naive pipeline"
echo "       run_root    = $RUN_ROOT"
echo "       run_manifest= $RUN_MANIFEST"

DID_RUN=0

if command_seen "tcga naive-map" && [[ -s "$NAIVE_MAP" ]]; then
  echo "[SKIP] tcga naive-map already completed."
else
  echo "[RUN] tcga naive-map"
  python -m pipeline.cli tcga naive-map \
    --sample-manifest "$SAMPLE_MANIFEST" \
    --project-registry "$PROJECT_REGISTRY" \
    --out "$MAPPING_DIR" \
    --run-manifest "$RUN_MANIFEST"
  DID_RUN=1
fi

if command_seen "tcga map" && [[ -s "$TCGA_MAP" ]]; then
  echo "[SKIP] tcga map already completed."
else
  PROJECTS="$(registry_projects)"
  if [[ -z "$PROJECTS" ]]; then
    echo "[ERROR] No projects resolved from $PROJECT_REGISTRY"
    exit 1
  fi
  read -r -a PROJECT_ARRAY <<<"$PROJECTS"
  echo "[RUN] tcga map (${#PROJECT_ARRAY[@]} projects)"
  python -m pipeline.cli tcga map \
    --projects "${PROJECT_ARRAY[@]}" \
    --out "$MAPPING_DIR" \
    --run-manifest "$RUN_MANIFEST"
  DID_RUN=1
fi

check_tcga_local_files

if command_seen "tcga naive-manifest" && [[ -s "$NAIVE_MANIFEST" ]] && [[ -s "$CLINICAL_FLAT" ]]; then
  echo "[SKIP] tcga naive-manifest already completed."
else
  echo "[RUN] tcga naive-manifest"
  python -m pipeline.cli tcga naive-manifest \
    --tcga-map "$TCGA_MAP" \
    --out "$MANIFEST_DIR" \
    --run-manifest "$RUN_MANIFEST"
  DID_RUN=1
fi

if command_seen "tcga tier-validate" && [[ -s "$TIER_SUMMARY" ]]; then
  echo "[SKIP] tcga tier-validate already completed."
else
  echo "[RUN] tcga tier-validate"
  python -m pipeline.cli tcga tier-validate \
    --concordance "$CONCORDANCE" \
    --survival-dir "$PROJECTION_DIR" \
    --signature "$SIGNATURE" \
    --out "$TIER_DIR" \
    --run-manifest "$RUN_MANIFEST"
  DID_RUN=1
fi

if command_seen "tcga project" && has_completed_projection; then
  echo "[SKIP] tcga project already has completed rows."
else
  echo "[RUN] tcga project"
  python -m pipeline.cli tcga project \
    --signature "$SIGNATURE" \
    --tcga-map "$TCGA_MAP" \
    --naive-manifest "$NAIVE_MANIFEST" \
    --tier-signatures-dir "$TIER_DIR" \
    --out "$PROJECTION_DIR" \
    --run-manifest "$RUN_MANIFEST"
  DID_RUN=1
fi

if command_seen "tcga epi-model" && [[ -s "$EPI_DIR/tcga_epidemiology_interactions.tsv" ]]; then
  echo "[SKIP] tcga epi-model already completed."
else
  echo "[RUN] tcga epi-model"
  python -m pipeline.cli tcga epi-model \
    --score-dir "$PROJECTION_DIR" \
    --naive-manifest "$NAIVE_MANIFEST" \
    --clinical-flat "$CLINICAL_FLAT" \
    --min-samples "$EPI_MIN_SAMPLES" \
    --out "$EPI_DIR" \
    --run-manifest "$RUN_MANIFEST"
  DID_RUN=1
fi

if command_seen "tcga pan-cancer" && [[ -s "$PAN_STATUS" ]]; then
  echo "[SKIP] tcga pan-cancer already completed."
else
  echo "[RUN] tcga pan-cancer"
  python -m pipeline.cli tcga pan-cancer \
    --survival-dir "$PROJECTION_DIR" \
    --epi-dir "$EPI_DIR" \
    --project-registry "$PROJECT_REGISTRY" \
    --out "$REPORT_DIR" \
    --run-manifest "$RUN_MANIFEST"
  DID_RUN=1
fi

if [[ "$DID_RUN" -eq 1 ]] || ! command_seen "report build" || [[ ! -f "$REPORT_FILE" ]]; then
  echo "[RUN] report build"
  python -m pipeline.cli report build \
    --results-root "$RUN_ROOT" \
    --out "$REPORT_DIR" \
    --run-manifest "$RUN_MANIFEST"
else
  echo "[SKIP] report build already completed and no stage changed."
fi

echo "[DONE] TCGA naive resume pipeline completed for $RUN_ROOT"
