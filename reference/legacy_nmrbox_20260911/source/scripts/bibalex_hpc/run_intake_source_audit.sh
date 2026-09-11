#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

TRACK="${TRACK:-all}"
STAMP="${BIBALEX_AUDIT_STAMP:-$(bibalex_stamp)}"
DATA_ROOT="${BIBALEX_DATA_ROOT:-${BIBALEX_REMOTE_DATA_ROOT}/geo_retrieval_20260628_195749}"
JOB_NAME="${JOB_NAME:-intake_source_audit_${TRACK}}"
REQUEST_CPUS="${REQUEST_CPUS:-4}"
REQUEST_MEM="${REQUEST_MEM:-24G}"
REQUEST_TIME="${REQUEST_TIME:-02:00:00}"

case "${TRACK}" in
  all|pre|delta)
    ;;
  *)
    echo "Unsupported TRACK=${TRACK}; use all, pre, or delta." >&2
    exit 2
    ;;
esac

case "${TRACK}" in
  all)
    TAG="timer_all"
    DISCOVERY_MANIFEST="configs/timer_discovery_manifest_geo_sra.tsv"
    ;;
  pre)
    TAG="timer_pre"
    DISCOVERY_MANIFEST="configs/timer_discovery_manifest_pre_response_geo_sra.tsv"
    ;;
  delta)
    TAG="timer_delta"
    DISCOVERY_MANIFEST="configs/timer_discovery_manifest_treatment_delta_geo_sra.tsv"
    ;;
esac

DOWNLOADS_ROOT="${DOWNLOADS_ROOT:-${DATA_ROOT}/retrieval/downloads_${TAG}}"
DATA_TYPE_MANIFEST="${DATA_TYPE_MANIFEST:-${DATA_ROOT}/retrieval/geo_data_type_manifest_${TAG}.tsv}"
OUT_ROOT="${OUT_ROOT:-${DATA_ROOT}/intake_source_audit_${STAMP}}"

bibalex_require_remote_root

REMOTE_SCRIPT="${BIBALEX_REMOTE_SCRIPTS_ROOT}/run_${JOB_NAME}_${STAMP}.sh"

bibalex_ssh "mkdir -p '${BIBALEX_REMOTE_SCRIPTS_ROOT}' '${BIBALEX_REMOTE_SLURM_ROOT}' '${OUT_ROOT}' && chmod 700 '${BIBALEX_REMOTE_ROOT}'"

cat > /tmp/ici_bibalex_intake_source_audit.sh <<EOF_REMOTE
#!/usr/bin/env bash
#SBATCH --job-name=${JOB_NAME}
#SBATCH --partition=${BIBALEX_SLURM_PARTITION}
#SBATCH --cpus-per-task=${REQUEST_CPUS}
#SBATCH --mem=${REQUEST_MEM}
#SBATCH --time=${REQUEST_TIME}
#SBATCH --output=${BIBALEX_REMOTE_SLURM_ROOT}/${JOB_NAME}_%j.out
#SBATCH --error=${BIBALEX_REMOTE_SLURM_ROOT}/${JOB_NAME}_%j.err

set -euo pipefail
export PYTHONNOUSERSITE=1
cd '${BIBALEX_REMOTE_REPO}'

DATA_ROOT='${DATA_ROOT}'
DOWNLOADS_ROOT='${DOWNLOADS_ROOT}'
DATA_TYPE_MANIFEST='${DATA_TYPE_MANIFEST}'
OUT_ROOT='${OUT_ROOT}'
DISCOVERY_MANIFEST='${DISCOVERY_MANIFEST}'
RUN_MANIFEST="\${OUT_ROOT}/run_manifest.yaml"
ROUTING_MANIFEST="\${OUT_ROOT}/geo_input_routing_from_retrieval.tsv"
RECOVERY_MANIFEST="\${OUT_ROOT}/prj_raw_sra_recovery_candidates.tsv"
ENRICHED_DISCOVERY_MANIFEST="\${OUT_ROOT}/discovery_manifest_enriched.tsv"
AUDIT_INPUTS_PY="\${OUT_ROOT}/build_intake_audit_inputs.py"
SUMMARY_PY="\${OUT_ROOT}/summarize_intake_source_audit.py"
GEO_TABLES_DIR="\${OUT_ROOT}/geo_tables"
SAMPLE_MANIFEST="\${OUT_ROOT}/sample_manifest_geo_all.tsv"
READY_MANIFEST="\${OUT_ROOT}/sample_manifest_geo_ready.tsv"
STAGE01_DIR="\${OUT_ROOT}/stage01"
DESIGN_DIR="\${OUT_ROOT}/analysis_design"
SUMMARY_MD="\${OUT_ROOT}/intake_source_audit_summary.md"

mkdir -p "\${OUT_ROOT}" "\${GEO_TABLES_DIR}" "\${STAGE01_DIR}" "\${DESIGN_DIR}"

echo "conda_bin	${BIBALEX_CONDA_BIN}"
echo "conda_env	${BIBALEX_CONDA_ENV}"
echo "data_root	\${DATA_ROOT}"
echo "downloads_root	\${DOWNLOADS_ROOT}"
echo "data_type_manifest	\${DATA_TYPE_MANIFEST}"
echo "out_root	\${OUT_ROOT}"
echo "discovery_manifest	\${DISCOVERY_MANIFEST}"

if [[ ! -d "\${DOWNLOADS_ROOT}" ]]; then
  echo "Missing downloads root: \${DOWNLOADS_ROOT}" >&2
  exit 2
fi
if [[ ! -f "\${DATA_TYPE_MANIFEST}" ]]; then
  echo "Missing data-type manifest: \${DATA_TYPE_MANIFEST}" >&2
  exit 2
fi

cat > "\${AUDIT_INPUTS_PY}" <<'PY'
import csv
import sys
from pathlib import Path

discovery_manifest = Path(sys.argv[1])
timer_roster = Path(sys.argv[2])
data_type_manifest = Path(sys.argv[3])
enriched_discovery_manifest = Path(sys.argv[4])
routing_manifest = Path(sys.argv[5])
recovery_manifest = Path(sys.argv[6])

def read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))

discovery_rows = read_tsv(discovery_manifest)
timer_rows = read_tsv(timer_roster)
data_rows = read_tsv(data_type_manifest)

roster_by_accession = {
    (row.get("dataset", "") or "").strip().upper(): row
    for row in timer_rows
    if (row.get("dataset", "") or "").strip()
}

enriched_fields = [
    "cohort_id",
    "accession",
    "cancer_type",
    "therapy_agent",
    "tracks_present",
]
with enriched_discovery_manifest.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=enriched_fields, delimiter="\t")
    writer.writeheader()
    for row in discovery_rows:
        accession = (row.get("accession", "") or "").strip().upper()
        roster = roster_by_accession.get(accession, {})
        writer.writerow(
            {
                "cohort_id": row.get("cohort_id", ""),
                "accession": row.get("accession", ""),
                "cancer_type": roster.get("cancer_type", row.get("cancer_type", "")),
                "therapy_agent": roster.get("therapy_combination", row.get("therapy_agent", "")),
                "tracks_present": roster.get("tracks_present", ""),
            }
        )

routing_fields = [
    "cohort_id",
    "downloads_folder",
    "recommended_input_route",
    "inferred_data_mode",
    "geo_core_complete",
    "n_soft_files",
    "n_matrix_files",
    "n_suppl_files",
    "n_runinfo_files",
    "n_raw_archive_files",
    "cohort_download_size_gb",
]
recovery_fields = [
    "cohort_id",
    "recommended_action",
    "reason",
    "n_runinfo_files",
    "inferred_data_mode",
    "recommended_input_route",
]

routing_manifest.parent.mkdir(parents=True, exist_ok=True)
with routing_manifest.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=routing_fields, delimiter="\t")
    writer.writeheader()
    for row in data_rows:
        cohort_id = row.get("cohort_id", "")
        route = row.get("recommended_input_route", "")
        mode = row.get("inferred_data_mode", "")
        out = {field: row.get(field, "") for field in routing_fields}
        out["downloads_folder"] = cohort_id
        if route == "manual_fetch_additional_files" and cohort_id.lower().startswith("prj"):
            out["recommended_input_route"] = "raw_sra_recovery_candidate"
            out["inferred_data_mode"] = mode or "metadata_only"
        writer.writerow(out)

with recovery_manifest.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=recovery_fields, delimiter="\t")
    writer.writeheader()
    for row in data_rows:
        cohort_id = row.get("cohort_id", "")
        route = row.get("recommended_input_route", "")
        if cohort_id.lower().startswith("prj") or route == "manual_fetch_additional_files":
            writer.writerow(
                {
                    "cohort_id": cohort_id,
                    "recommended_action": "defer_to_raw_sra_expression_recovery",
                    "reason": "runinfo_present_but_no_expression_matrix",
                    "n_runinfo_files": row.get("n_runinfo_files", ""),
                    "inferred_data_mode": row.get("inferred_data_mode", ""),
                    "recommended_input_route": route,
                }
            )
print(f"Wrote {enriched_discovery_manifest}")
print(f"Wrote {routing_manifest}")
print(f"Wrote {recovery_manifest}")
PY

'${BIBALEX_CONDA_BIN}' run -n '${BIBALEX_CONDA_ENV}' python "\${AUDIT_INPUTS_PY}" \
  "\${DISCOVERY_MANIFEST}" \
  "configs/timer_active_cohort_roster_with_stratification.tsv" \
  "\${DATA_TYPE_MANIFEST}" \
  "\${ENRICHED_DISCOVERY_MANIFEST}" \
  "\${ROUTING_MANIFEST}" \
  "\${RECOVERY_MANIFEST}"

'${BIBALEX_CONDA_BIN}' run -n '${BIBALEX_CONDA_ENV}' python -m pipeline.cli intake build-geo-tables \
  --discovery-manifest "\${ENRICHED_DISCOVERY_MANIFEST}" \
  --downloads-root "\${DOWNLOADS_ROOT}" \
  --out "\${GEO_TABLES_DIR}" \
  --routing-manifest "\${ROUTING_MANIFEST}" \
  --run-manifest "\${RUN_MANIFEST}"

'${BIBALEX_CONDA_BIN}' run -n '${BIBALEX_CONDA_ENV}' python -m pipeline.cli intake build-geo-sample-manifest \
  --cohort-input-table "\${GEO_TABLES_DIR}/cohort_input_table_all.tsv" \
  --curated-manifest "configs/sample_manifest_curated.tsv" \
  --out "\${SAMPLE_MANIFEST}" \
  --ready-out "\${READY_MANIFEST}" \
  --summary-out "\${OUT_ROOT}/sample_manifest_build_summary.md" \
  --expected-pre-treatment-cohorts 18 \
  --run-manifest "\${RUN_MANIFEST}"

'${BIBALEX_CONDA_BIN}' run -n '${BIBALEX_CONDA_ENV}' python -m pipeline.cli intake detect-assay-type \
  --sample-manifest "\${SAMPLE_MANIFEST}" \
  --expression-manifest "\${GEO_TABLES_DIR}/geo_tables_summary.tsv" \
  --downloads-root "\${DOWNLOADS_ROOT}" \
  --out "\${STAGE01_DIR}" \
  --run-manifest "\${RUN_MANIFEST}"

'${BIBALEX_CONDA_BIN}' run -n '${BIBALEX_CONDA_ENV}' python -m pipeline.cli intake build-response-record \
  --sample-manifest "\${SAMPLE_MANIFEST}" \
  --out "\${STAGE01_DIR}" \
  --run-manifest "\${RUN_MANIFEST}"

'${BIBALEX_CONDA_BIN}' run -n '${BIBALEX_CONDA_ENV}' python -m pipeline.cli intake curation-report \
  --assay-detection "\${STAGE01_DIR}/assay_detection.tsv" \
  --response-definition "\${STAGE01_DIR}/response_definition.tsv" \
  --timing-provenance "\${STAGE01_DIR}/timing_provenance.tsv" \
  --sample-manifest "\${SAMPLE_MANIFEST}" \
  --out "\${STAGE01_DIR}" \
  --run-manifest "\${RUN_MANIFEST}"

'${BIBALEX_CONDA_BIN}' run -n '${BIBALEX_CONDA_ENV}' python -m pipeline.cli design build \
  --sample-manifest "\${SAMPLE_MANIFEST}" \
  --expression-manifest "\${GEO_TABLES_DIR}/geo_tables_summary.tsv" \
  --downloads-root "\${DOWNLOADS_ROOT}" \
  --check-expression-readiness \
  --out "\${DESIGN_DIR}" \
  --run-manifest "\${RUN_MANIFEST}"

cat > "\${SUMMARY_PY}" <<'PY'
import csv
import sys
from collections import Counter
from pathlib import Path

out_root = Path(sys.argv[1])

def read_tsv(path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))

sample_rows = read_tsv(out_root / "sample_manifest_geo_all.tsv")
ready_rows = read_tsv(out_root / "sample_manifest_geo_ready.tsv")
assay_rows = read_tsv(out_root / "stage01" / "assay_detection.tsv")
curation_rows = read_tsv(out_root / "stage01" / "intake_curation_report.tsv")
registry_rows = read_tsv(out_root / "analysis_design" / "analysis_contrast_registry.tsv")
recovery_rows = read_tsv(out_root / "prj_raw_sra_recovery_candidates.tsv")

ready_cohorts = sorted({r.get("cohort_id", "") for r in ready_rows if r.get("cohort_id", "")})
all_cohorts = sorted({r.get("cohort_id", "") for r in sample_rows if r.get("cohort_id", "")})
assays = Counter(r.get("assay_type", "unknown") for r in assay_rows)
curation = Counter(r.get("status", "unknown") for r in curation_rows)
feasibility = Counter(r.get("feasibility_status", "unknown") for r in registry_rows)

lines = [
    "# BibaLex Intake Source Audit",
    "",
    f"- out_root: {out_root}",
    f"- n_manifest_rows: {len(sample_rows)}",
    f"- n_ready_rows: {len(ready_rows)}",
    f"- n_manifest_cohorts: {len(all_cohorts)}",
    f"- n_ready_cohorts: {len(ready_cohorts)}",
    f"- ready_cohorts: {', '.join(ready_cohorts)}",
    f"- raw_sra_recovery_candidates: {', '.join(r.get('cohort_id', '') for r in recovery_rows if r.get('cohort_id', ''))}",
    "",
    "## Assay Detection Counts",
    "",
]
for key, value in sorted(assays.items()):
    lines.append(f"- {key}: {value}")
lines.extend(["", "## Stage 01 Curation Status Counts", ""])
for key, value in sorted(curation.items()):
    lines.append(f"- {key}: {value}")
lines.extend(["", "## Analysis Design Feasibility Counts", ""])
for key, value in sorted(feasibility.items()):
    lines.append(f"- {key}: {value}")

(out_root / "intake_source_audit_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

'${BIBALEX_CONDA_BIN}' run -n '${BIBALEX_CONDA_ENV}' python "\${SUMMARY_PY}" "\${OUT_ROOT}"

echo "DONE: \${OUT_ROOT}"
echo "summary: \${SUMMARY_MD}"
EOF_REMOTE

scp /tmp/ici_bibalex_intake_source_audit.sh "${BIBALEX_SSH_HOST}:${REMOTE_SCRIPT}"
JOB_ID="$(bibalex_ssh "chmod +x '${REMOTE_SCRIPT}' && sbatch --parsable '${REMOTE_SCRIPT}'")"

printf 'job_id\t%s\n' "${JOB_ID}"
printf 'remote_script\t%s\n' "${REMOTE_SCRIPT}"
printf 'data_root\t%s\n' "${DATA_ROOT}"
printf 'downloads_root\t%s\n' "${DOWNLOADS_ROOT}"
printf 'out_root\t%s\n' "${OUT_ROOT}"
printf 'track\t%s\n' "${TRACK}"
printf 'mode\t%s\n' "intake-source-audit"
printf 'stdout\t%s/%s_%s.out\n' "${BIBALEX_REMOTE_SLURM_ROOT}" "${JOB_NAME}" "${JOB_ID}"
printf 'stderr\t%s/%s_%s.err\n' "${BIBALEX_REMOTE_SLURM_ROOT}" "${JOB_NAME}" "${JOB_ID}"
