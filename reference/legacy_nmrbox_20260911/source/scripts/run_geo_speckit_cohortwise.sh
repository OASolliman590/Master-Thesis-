#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Run cohort-by-cohort GEO pipeline: readiness -> QC -> within-cohort DE -> meta -> immune scoring.

Usage:
  bash scripts/run_geo_speckit_cohortwise.sh [options]

Options:
  --sample-manifest <path>   Sample manifest to use (default: configs/sample_manifest_curated.tsv)
  --curation-audit <path>    Curation audit TSV for readiness summary
                            (default: results/manual_curation_geo/curation_apply_audit_verified.tsv)
  --gene-set-registry <path> Gene set registry TSV for ssGSEA/ESTIMATE (required for immune scoring)
  --cibersortx-absolute <path> CIBERSORTx absolute output TSV
  --cibersortx-relative <path> CIBERSORTx relative output TSV
  --contrast <name>          Contrast name (default: PRE_RESPONSE)
  --run-manifest <path>      Run manifest path (default: logs/run_manifest.yaml)
  -h, --help                 Show this help
USAGE
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

SAMPLE_MANIFEST="configs/sample_manifest_curated.tsv"
CURATION_AUDIT="results/manual_curation_geo/curation_apply_audit_verified.tsv"
CONTRAST="PRE_RESPONSE"
RUN_MANIFEST="logs/run_manifest.yaml"
GENE_SET_REGISTRY="configs/immune_gene_sets_registry.tsv"
CIBERSORTX_ABS=""
CIBERSORTX_REL=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --sample-manifest)
      SAMPLE_MANIFEST="$2"
      shift 2
      ;;
    --curation-audit)
      CURATION_AUDIT="$2"
      shift 2
      ;;
    --contrast)
      CONTRAST="$2"
      shift 2
      ;;
    --gene-set-registry)
      GENE_SET_REGISTRY="$2"
      shift 2
      ;;
    --cibersortx-absolute)
      CIBERSORTX_ABS="$2"
      shift 2
      ;;
    --cibersortx-relative)
      CIBERSORTX_REL="$2"
      shift 2
      ;;
    --run-manifest)
      RUN_MANIFEST="$2"
      shift 2
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

mkdir -p logs results work

# Cohort-level readiness summary
SAMPLE_MANIFEST_PATH="$SAMPLE_MANIFEST" CURATION_AUDIT_PATH="$CURATION_AUDIT" python - <<'PY'
import csv
import os
from pathlib import Path

sample_manifest = Path(os.environ["SAMPLE_MANIFEST_PATH"])
curation_audit = Path(os.environ["CURATION_AUDIT_PATH"])
out_root = Path("results/cohort_qc")
out_root.mkdir(parents=True, exist_ok=True)

def read_tsv(path: Path):
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))

ready_map = {}
if curation_audit.exists():
    for row in read_tsv(curation_audit):
        cid = row.get("cohort_id", "")
        if cid:
            ready_map[cid] = row.get("status", "")

rows = read_tsv(sample_manifest)
cohorts = sorted({r.get("cohort_id", "") for r in rows if r.get("cohort_id", "")})
summary_rows = []
for cid in cohorts:
    status = ready_map.get(cid, "unknown")
    n_total = sum(1 for r in rows if r.get("cohort_id", "") == cid)
    n_included = sum(1 for r in rows if r.get("cohort_id", "") == cid and r.get("include_flag", "") == "true")
    summary_rows.append({
        "cohort_id": cid,
        "ready_status": status,
        "n_total": str(n_total),
        "n_included": str(n_included),
    })

out_tsv = out_root / "readiness_summary.tsv"
out_md = out_root / "readiness_summary.md"
with out_tsv.open("w", encoding="utf-8", newline="") as fh:
    writer = csv.DictWriter(fh, fieldnames=["cohort_id", "ready_status", "n_total", "n_included"], delimiter="\t")
    writer.writeheader()
    writer.writerows(summary_rows)

lines = [
    "# Cohort Readiness Summary",
    "",
    f"- sample_manifest: {sample_manifest}",
    f"- curation_audit: {curation_audit}",
    f"- n_cohorts: {len(summary_rows)}",
    "",
    "| cohort_id | ready_status | n_total | n_included |",
    "| --- | --- | --- | --- |",
]
for row in summary_rows:
    lines.append(
        f"| {row['cohort_id']} | {row['ready_status']} | {row['n_total']} | {row['n_included']} |"
    )

out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Wrote {out_tsv} and {out_md}")
PY

# Build list of cohorts with at least one included sample
COHORT_LIST=$(SAMPLE_MANIFEST_PATH="$SAMPLE_MANIFEST" python - <<'PY'
import csv
import os
from pathlib import Path

path = Path(os.environ["SAMPLE_MANIFEST_PATH"])
with path.open("r", encoding="utf-8", newline="") as fh:
    rows = list(csv.DictReader(fh, delimiter="\t"))

cohorts = sorted({r.get("cohort_id", "") for r in rows if r.get("cohort_id", "")})
include_map = {c: False for c in cohorts}
for r in rows:
    cid = r.get("cohort_id", "")
    if cid and r.get("include_flag", "") == "true":
        include_map[cid] = True

for cid in cohorts:
    if include_map.get(cid):
        print(cid)
PY
)

mkdir -p work/cohort_manifests work/ingest

# Cohort-by-cohort ingest -> QC -> DE
for cohort_id in $COHORT_LIST; do
  echo
  echo "[cohort] $cohort_id"

  COHORT_MANIFEST="work/cohort_manifests/${cohort_id}.tsv"
  COHORT_ID_VALUE="$cohort_id" SAMPLE_MANIFEST_PATH="$SAMPLE_MANIFEST" COHORT_MANIFEST_PATH="$COHORT_MANIFEST" python - <<'PY'
import csv
import os
from pathlib import Path

cohort_id = os.environ["COHORT_ID_VALUE"]
manifest = Path(os.environ["SAMPLE_MANIFEST_PATH"])
out = Path(os.environ["COHORT_MANIFEST_PATH"])

with manifest.open("r", encoding="utf-8", newline="") as fh:
    rows = [r for r in csv.DictReader(fh, delimiter="\t") if r.get("cohort_id", "") == cohort_id]

if cohort_id == "gse202069_hcc_anti_pd1":
    # Override inclusion to allow tumor-vs-adjacent comparison
    for row in rows:
        row["include_flag"] = "true"
else:
    rows = [r for r in rows if r.get("include_flag", "") == "true"]

out.parent.mkdir(parents=True, exist_ok=True)
with out.open("w", encoding="utf-8", newline="") as fh:
    if not rows:
        raise SystemExit(f"No included rows for {cohort_id}")
    writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), delimiter="\t")
    writer.writeheader()
    writer.writerows(rows)

print(f"Wrote {out}")
PY

  python -m pipeline.cli ingest run \
    --sample-manifest "$COHORT_MANIFEST" \
    --out "work/ingest/${cohort_id}" \
    --run-manifest "$RUN_MANIFEST"

  python -m pipeline.cli qc run \
    --sample-manifest "$COHORT_MANIFEST" \
    --ingest-dir "work/ingest/${cohort_id}" \
    --expression-manifest results/geo_tables/geo_tables_summary.tsv \
    --downloads-root results/retrieval/downloads \
    --out results/cohort_qc \
    --run-manifest "$RUN_MANIFEST"

  if [[ "$cohort_id" == "gse135222_srp217040_nsclc_pdl1" ]]; then
    mkdir -p "results/special_cohort/${cohort_id}"
    cat <<'NOTE' > "results/special_cohort/${cohort_id}/analysis_plan.md"
# Special Cohort Routing

- cohort_id: gse135222_srp217040_nsclc_pdl1
- analysis_mode: comparative_multiomics_nsclc
- rationale: linked RNA-seq (GSE135222) + methylation (GSE119144); do not force PRE_RESPONSE DE
- next_actions:
  - expression-only exploratory clustering + immune program scoring
  - methylation-expression coupling and pathway concordance
NOTE
    COHORT_OUT_DIR="results/special_cohort/${cohort_id}" python - <<'PY'
import csv
import os
from pathlib import Path

out_dir = Path(os.environ["COHORT_OUT_DIR"])
out_dir.mkdir(parents=True, exist_ok=True)

concordance = out_dir / "methylation_expression_concordance.tsv"
with concordance.open("w", encoding="utf-8", newline="") as fh:
    writer = csv.DictWriter(
        fh,
        fieldnames=[
            "feature_id",
            "gene_symbol",
            "region",
            "methylation_delta",
            "expression_delta",
            "direction",
            "pathway",
        ],
        delimiter="\t",
    )
    writer.writeheader()

summary = out_dir / "methylation_expression_summary.md"
summary.write_text(
    "# RNA + Methylation Concordance Summary\n\n"
    "- status: stub\n"
    "- note: populate after methylation-expression coupling is implemented\n",
    encoding="utf-8",
)
print(f"Wrote {concordance} and {summary}")
PY
  elif [[ "$cohort_id" == "gse202069_hcc_anti_pd1" ]]; then
    mkdir -p "results/special_cohort/${cohort_id}"
    cat <<'NOTE' > "results/special_cohort/${cohort_id}/analysis_plan.md"
# Special Cohort Routing

- cohort_id: gse202069_hcc_anti_pd1
- analysis_mode: tumor_vs_adjacent_primary
- rationale: mixed tumor vs adjacent series; treated subset requires extraction before response modeling
- next_actions:
  - tumor vs adjacent/nontumor DE across full series
  - extract treated subset and annotate response later
NOTE
    python -m pipeline.cli de run \
      --contrast "TUMOR_VS_ADJACENT" \
      --sample-manifest "$COHORT_MANIFEST" \
      --ingest-dir "work/ingest/${cohort_id}" \
      --expression-manifest results/geo_tables/geo_tables_summary.tsv \
      --downloads-root results/retrieval/downloads \
      --out results/within_cohort_de \
      --run-manifest "$RUN_MANIFEST"
  else
    python -m pipeline.cli de run \
      --contrast "$CONTRAST" \
      --sample-manifest "$COHORT_MANIFEST" \
      --ingest-dir "work/ingest/${cohort_id}" \
      --expression-manifest results/geo_tables/geo_tables_summary.tsv \
      --downloads-root results/retrieval/downloads \
      --out results/within_cohort_de \
      --run-manifest "$RUN_MANIFEST"
  fi

done

# Meta-analysis and signature freeze
python -m pipeline.cli meta run \
  --contrast "$CONTRAST" \
  --de-dir results/within_cohort_de \
  --out results/meta_analysis \
  --run-manifest "$RUN_MANIFEST"

python -m pipeline.cli signature derive \
  --contrast "$CONTRAST" \
  --meta-dir results/meta_analysis \
  --out results/signature_sets \
  --run-manifest "$RUN_MANIFEST"

# Immune-state scoring + effects (full manifest)
python -m pipeline.cli ingest run \
  --sample-manifest "$SAMPLE_MANIFEST" \
  --out work/ingest_full \
  --run-manifest "$RUN_MANIFEST"

python -m pipeline.cli immune score \
  --sample-manifest "$SAMPLE_MANIFEST" \
  --ingest-dir work/ingest_full \
  --expression-manifest results/geo_tables/geo_tables_summary.tsv \
  --downloads-root results/retrieval/downloads \
  --gene-set-registry "$GENE_SET_REGISTRY" \
  --cibersortx-absolute "$CIBERSORTX_ABS" \
  --cibersortx-relative "$CIBERSORTX_REL" \
  --out results/immune_state \
  --run-manifest "$RUN_MANIFEST"

python -m pipeline.cli immune effects \
  --sample-manifest "$SAMPLE_MANIFEST" \
  --immune-dir results/immune_state \
  --expression-manifest results/geo_tables/geo_tables_summary.tsv \
  --downloads-root results/retrieval/downloads \
  --out results/immune_state \
  --run-manifest "$RUN_MANIFEST"

echo
echo "[done] Cohortwise readiness, QC, DE, meta, and immune scoring completed."
