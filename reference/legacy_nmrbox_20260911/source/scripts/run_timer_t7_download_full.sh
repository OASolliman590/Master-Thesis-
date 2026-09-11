#!/usr/bin/env bash
set -euo pipefail

# Full TIMER GEO/SRA retrieval workflow to external T7 storage.
# Usage:
#   bash scripts/run_timer_t7_download_full.sh
#   bash scripts/run_timer_t7_download_full.sh /Volumes/T7/1-Epigenetics_MSc_Thesis
#   bash scripts/run_timer_t7_download_full.sh /Volumes/T7/1-Epigenetics_MSc_Thesis --health-only
#   bash scripts/run_timer_t7_download_full.sh /Volumes/T7/1-Epigenetics_MSc_Thesis --track pre

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python}"

T7_ROOT="${1:-/Volumes/T7/1-Epigenetics_MSc_Thesis}"
TRACK="all"
HEALTH_ONLY="false"

for arg in "$@"; do
  case "${arg}" in
    --health-only)
      HEALTH_ONLY="true"
      ;;
    --track=pre)
      TRACK="pre"
      ;;
    --track=delta)
      TRACK="delta"
      ;;
    --track=all)
      TRACK="all"
      ;;
  esac
done

case "${TRACK}" in
  all)
    MANIFEST="${REPO_ROOT}/configs/timer_discovery_manifest_geo_sra.tsv"
    TAG="timer_all"
    ;;
  pre)
    MANIFEST="${REPO_ROOT}/configs/timer_discovery_manifest_pre_response_geo_sra.tsv"
    TAG="timer_pre"
    ;;
  delta)
    MANIFEST="${REPO_ROOT}/configs/timer_discovery_manifest_treatment_delta_geo_sra.tsv"
    TAG="timer_delta"
    ;;
  *)
    echo "Unsupported --track value: ${TRACK}" >&2
    exit 2
    ;;
esac

if [[ ! -f "${MANIFEST}" ]]; then
  echo "Manifest not found: ${MANIFEST}" >&2
  exit 2
fi

OUT_ROOT="${T7_ROOT}/retrieval/downloads_${TAG}"
MANIFEST_OUT="${T7_ROOT}/retrieval/geo_data_type_manifest_${TAG}.tsv"
SUMMARY_MD="${T7_ROOT}/retrieval/download_summary_${TAG}.md"

mkdir -p "${T7_ROOT}/retrieval"

echo "Repository root: ${REPO_ROOT}"
echo "T7 root:         ${T7_ROOT}"
echo "Track:           ${TRACK}"
echo "Manifest:        ${MANIFEST}"
echo "Downloads root:  ${OUT_ROOT}"

cd "${REPO_ROOT}"

echo
echo "== Step 1/4: Health check (no download) =="
"${PYTHON_BIN}" -m pipeline.cli retrieval geo-full \
  --discovery-manifest "${MANIFEST}" \
  --out "${OUT_ROOT}" \
  --no-download

if [[ "${HEALTH_ONLY}" == "true" ]]; then
  echo
  echo "Health check completed successfully (--health-only)."
  exit 0
fi

echo
echo "== Step 2/4: Full GEO/SRA retrieval =="
"${PYTHON_BIN}" -m pipeline.cli retrieval geo-full \
  --discovery-manifest "${MANIFEST}" \
  --out "${OUT_ROOT}"

echo
echo "== Step 3/4: Build GEO data-type manifest =="
"${PYTHON_BIN}" -m pipeline.cli retrieval geo-manifest \
  --discovery-manifest "${MANIFEST}" \
  --downloads-root "${OUT_ROOT}" \
  --out "${MANIFEST_OUT}"

echo
echo "== Step 4/4: Write retrieval summary =="
"${PYTHON_BIN}" - <<PY
from pathlib import Path
import pandas as pd

manifest_path = Path("${MANIFEST_OUT}")
summary_path = Path("${SUMMARY_MD}")

if not manifest_path.exists():
    raise SystemExit(f"Missing manifest output: {manifest_path}")

df = pd.read_csv(manifest_path, sep="\\t")

lines = [
    f"# TIMER Retrieval Summary ({manifest_path.stem})",
    "",
    f"- total cohorts: {len(df)}",
]

if "core_gse_soft_complete" in df.columns:
    complete = int((df["core_gse_soft_complete"].astype(str).str.lower() == "true").sum())
    lines.append(f"- GEO core complete: {complete}/{len(df)}")

if "inferred_data_mode" in df.columns:
    lines.extend(["", "## Inferred Data Modes"])
    vc = df["inferred_data_mode"].fillna("unknown").value_counts()
    for mode, n in vc.items():
        lines.append(f"- {mode}: {int(n)}")

if "recommended_input_route" in df.columns:
    lines.extend(["", "## Recommended Input Routes"])
    vc = df["recommended_input_route"].fillna("unknown").value_counts()
    for route, n in vc.items():
        lines.append(f"- {route}: {int(n)}")

summary_path.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
print(f"Wrote summary: {summary_path}")
PY

echo
echo "Completed successfully."
echo "Key outputs:"
echo "- ${OUT_ROOT}"
echo "- ${MANIFEST_OUT}"
echo "- ${SUMMARY_MD}"
