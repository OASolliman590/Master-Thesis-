#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Run spec-kit GEO-focused pipeline stages 1-13 with cohort-oriented R/NR timing logic.

Default behavior:
- uses merged analysis authority: ../02_data_inventory/analysis_cohorts_merged_v1.tsv
- filters to GEO/GEO+SRA rows for discovery execution
- excludes FASTQ cohorts for home-safe GEO-first analysis (override with --include-fastq)
- runs cohort-level method inspection before modeling

Usage:
  bash scripts/run_geo_speckit_1_13.sh [options]

Options:
  --discovery-manifest <path>        Source cohort authority TSV
  --geo-manifest-out <path>          GEO-filtered manifest output path
  --candidate-roster <path>          Candidate roster for cohort audit
  --inventory <path>                 Existing inventory TSV for audit overlap checks
  --validation-manifest <path>       Validation manifest TSV
  --contrast <name>                  Contrast name (default: PRE_RESPONSE)
  --no-download                      Run retrieval stage in ledger-only mode (no remote fetch)
  --include-fastq                    Keep FASTQ cohorts in active sample manifest
  --apply-curation                   Apply manual curation sheet to sample manifest before downstream stages
  --with-tcga                        Also run TCGA/TCIA/methylation stages
  --run-manifest <path>              Run manifest path (default: logs/run_manifest.yaml)
  -h, --help                         Show this help
EOF
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DISCOVERY_MANIFEST="../02_data_inventory/analysis_cohorts_merged_v1.tsv"
GEO_MANIFEST_OUT="configs/discovery_geo_focus.tsv"
CANDIDATE_ROSTER="configs/candidate_cohort_roster.tsv"
INVENTORY_MANIFEST="../02_data_inventory/ici_cross_cancer_cohorts.tsv"
VALIDATION_MANIFEST="configs/validation_manifest.tsv"
RUN_MANIFEST="logs/run_manifest.yaml"
CONTRAST="PRE_RESPONSE"
NO_DOWNLOAD=0
INCLUDE_FASTQ=0
WITH_TCGA=0
APPLY_CURATION=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --discovery-manifest)
      DISCOVERY_MANIFEST="$2"
      shift 2
      ;;
    --geo-manifest-out)
      GEO_MANIFEST_OUT="$2"
      shift 2
      ;;
    --candidate-roster)
      CANDIDATE_ROSTER="$2"
      shift 2
      ;;
    --inventory)
      INVENTORY_MANIFEST="$2"
      shift 2
      ;;
    --validation-manifest)
      VALIDATION_MANIFEST="$2"
      shift 2
      ;;
    --contrast)
      CONTRAST="$2"
      shift 2
      ;;
    --no-download)
      NO_DOWNLOAD=1
      shift
      ;;
    --run-manifest)
      RUN_MANIFEST="$2"
      shift 2
      ;;
    --include-fastq)
      INCLUDE_FASTQ=1
      shift
      ;;
    --with-tcga)
      WITH_TCGA=1
      shift
      ;;
    --apply-curation)
      APPLY_CURATION=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[error] Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

echo "[info] repo_root=$ROOT_DIR"
echo "[info] discovery_manifest=$DISCOVERY_MANIFEST"
echo "[info] geo_manifest_out=$GEO_MANIFEST_OUT"
echo "[info] contrast=$CONTRAST"
echo "[info] no_download=$NO_DOWNLOAD"
echo "[info] include_fastq=$INCLUDE_FASTQ"
echo "[info] apply_curation=$APPLY_CURATION"
echo "[info] with_tcga=$WITH_TCGA"

STEP=1
run_step() {
  local title="$1"
  shift
  echo
  echo "[$STEP/13] $title"
  "$@"
  STEP=$((STEP + 1))
}

mkdir -p configs logs results reports work

run_step "Build GEO-focused discovery manifest" \
  bash -lc "awk -F '\t' 'NR==1 || \$3 ~ /GEO/' '$DISCOVERY_MANIFEST' > '$GEO_MANIFEST_OUT'"

retrieval_cmd=(
  python -m pipeline.cli retrieval run
  --discovery-manifest "$GEO_MANIFEST_OUT"
  --out results/retrieval
  --run-manifest "$RUN_MANIFEST"
)
if [[ "$NO_DOWNLOAD" -eq 1 ]]; then
  retrieval_cmd+=(--no-download)
fi
run_step "Retrieval: accession resolution ledger" "${retrieval_cmd[@]}"

run_step "Dataset intake: sample/input-class inspection" \
  python -m pipeline.cli intake inspect \
    --retrieval-ledger results/retrieval/retrieval_ledger.tsv \
    --out results/dataset_intake \
    --run-manifest "$RUN_MANIFEST"

run_step "Primary-source cohort audit" \
  python -m pipeline.cli cohort audit \
    --candidate-roster "$CANDIDATE_ROSTER" \
    --inventory "$INVENTORY_MANIFEST" \
    --out results/cohort_audit \
    --run-manifest "$RUN_MANIFEST"

run_step "Build canonical sample manifest" \
  python -m pipeline.cli manifest build \
    --discovery-manifest "$GEO_MANIFEST_OUT" \
    --retrieval-ledger results/retrieval/retrieval_ledger.tsv \
    --intake-record results/dataset_intake/dataset_inspection.tsv \
    --out configs/sample_manifest.tsv \
    --run-manifest "$RUN_MANIFEST"

run_step "Method inspection + study-by-study curation sheet" \
  bash -lc "python -m pipeline.cli method inspect \
    --sample-manifest configs/sample_manifest.tsv \
    --out results/method_inspection \
    --run-manifest '$RUN_MANIFEST' && \
  python -m pipeline.cli method curation-sheet \
    --discovery-manifest '$GEO_MANIFEST_OUT' \
    --method-inspection results/method_inspection/cohort_method_inspection.tsv \
    --out results/manual_curation \
    --run-manifest '$RUN_MANIFEST' && \
  if [[ '$APPLY_CURATION' -eq 1 ]]; then \
    python -m pipeline.cli method apply-curation \
      --sample-manifest configs/sample_manifest.tsv \
      --curation-sheet results/manual_curation/study_manual_curation.tsv \
      --out configs/sample_manifest_curated.tsv \
      --projection-out results/manual_curation/sample_manifest_projection.tsv \
      --audit-out results/manual_curation/curation_apply_audit.tsv \
      --run-manifest '$RUN_MANIFEST'; \
  fi"

ACTIVE_SAMPLE_MANIFEST="configs/sample_manifest.tsv"
if [[ "$APPLY_CURATION" -eq 1 ]]; then
  ACTIVE_SAMPLE_MANIFEST="configs/sample_manifest_curated.tsv"
fi
if [[ "$INCLUDE_FASTQ" -eq 0 ]]; then
  run_step "Build GEO-first active manifest (exclude FASTQ cohorts)" \
    bash -lc "awk -F '\t' 'BEGIN{OFS=\"\t\"} NR==1 || \$11 != \"FASTQ\"' \
      '$ACTIVE_SAMPLE_MANIFEST' > configs/sample_manifest_geo_only.tsv"
  ACTIVE_SAMPLE_MANIFEST="configs/sample_manifest_geo_only.tsv"
else
  run_step "Use full manifest as active analysis manifest" \
    cp "$ACTIVE_SAMPLE_MANIFEST" configs/sample_manifest_geo_only.tsv
  ACTIVE_SAMPLE_MANIFEST="configs/sample_manifest_geo_only.tsv"
fi

run_step "Ingest expression inputs" \
  python -m pipeline.cli ingest run \
    --sample-manifest "$ACTIVE_SAMPLE_MANIFEST" \
    --out work/ingest \
    --run-manifest "$RUN_MANIFEST"

run_step "Cohort-level QC" \
  python -m pipeline.cli qc run \
    --sample-manifest "$ACTIVE_SAMPLE_MANIFEST" \
    --ingest-dir work/ingest \
    --out results/cohort_qc \
    --run-manifest "$RUN_MANIFEST"

run_step "Within-cohort DE ($CONTRAST)" \
  python -m pipeline.cli de run \
    --contrast "$CONTRAST" \
    --sample-manifest "$ACTIVE_SAMPLE_MANIFEST" \
    --ingest-dir work/ingest \
    --out results/within_cohort_de \
    --run-manifest "$RUN_MANIFEST"

run_step "Meta-analysis + signature freeze" \
  bash -lc "python -m pipeline.cli meta run \
    --contrast '$CONTRAST' \
    --de-dir results/within_cohort_de \
    --out results/meta_analysis \
    --run-manifest '$RUN_MANIFEST' && \
  python -m pipeline.cli signature derive \
    --contrast '$CONTRAST' \
    --meta-dir results/meta_analysis \
    --out results/signature_sets \
    --run-manifest '$RUN_MANIFEST'"

run_step "Immune-state scoring + effects + held-out validation" \
  bash -lc "python -m pipeline.cli immune score \
    --sample-manifest '$ACTIVE_SAMPLE_MANIFEST' \
    --ingest-dir work/ingest \
    --out results/immune_state \
    --run-manifest '$RUN_MANIFEST' && \
  python -m pipeline.cli immune effects \
    --sample-manifest '$ACTIVE_SAMPLE_MANIFEST' \
    --immune-dir results/immune_state \
    --out results/immune_state \
    --run-manifest '$RUN_MANIFEST' && \
  python -m pipeline.cli validate run \
    --signature results/signature_sets/pre_response_signature_v1.tsv \
    --validation-manifest '$VALIDATION_MANIFEST' \
    --out results/validation \
    --run-manifest '$RUN_MANIFEST'"

run_step "Optional TCGA stack + report packaging" \
  bash -lc "if [[ '$WITH_TCGA' -eq 1 ]]; then \
    python -m pipeline.cli tcga map \
      --projects TCGA-PRAD TCGA-LUAD \
      --out results/tcga_gdc_map \
      --run-manifest '$RUN_MANIFEST' && \
    python -m pipeline.cli tcga project \
      --signature results/signature_sets/pre_response_signature_v1.tsv \
      --tcga-map results/tcga_gdc_map/tcga_sample_map.tsv \
      --out results/tcga_projection \
      --run-manifest '$RUN_MANIFEST' && \
    python -m pipeline.cli tcia overlay \
      --projects TCGA-PRAD TCGA-LUAD \
      --out results/tcia_overlay \
      --run-manifest '$RUN_MANIFEST' && \
    python -m pipeline.cli methylation integrate \
      --tcga-projection results/tcga_projection \
      --tcga-map results/tcga_gdc_map/tcga_sample_map.tsv \
      --immune-dir results/immune_state \
      --tcia-annotations results/tcia_overlay/tcia_ips_annotations.tsv \
      --out results/methylation_integration \
      --run-manifest '$RUN_MANIFEST'; \
  fi; \
  python -m pipeline.cli report build \
    --results-root results \
    --out reports \
    --run-manifest '$RUN_MANIFEST'"

echo
echo "[done] GEO spec-kit stages 1-13 completed."
echo "[done] active_sample_manifest=$ACTIVE_SAMPLE_MANIFEST"
