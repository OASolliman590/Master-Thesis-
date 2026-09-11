#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${ROOT:-$(cd "${SCRIPT_DIR}/../.." && pwd)}"
RUN_ROOT_REL="${RUN_ROOT_REL:-results/analysis_id_runs_t7_20260607_stage07_scale_provenance}"
REPORT_ROOT_REL="${REPORT_ROOT_REL:-reports/analysis_id_runs_t7_20260607_stage07_scale_provenance}"
FIGURE_ROOT_REL="${FIGURE_ROOT_REL:-figures/analysis_id_runs_t7_20260607_stage07_scale_provenance}"
STAMP="$(date -u +%Y%m%d_%H%M%S)"
OUT_DIR="${OUT_DIR:-${ROOT}/results/nmrbox_ici_canary_bundle_${STAMP}}"
BUNDLE_ROOT="${OUT_DIR}/ici_thesis_pipeline_canary"

mkdir -p "${BUNDLE_ROOT}"
cd "${ROOT}"

copy_path() {
  local src="$1"
  local dst_parent="$2"
  if [[ -e "${src}" ]]; then
    mkdir -p "${dst_parent}"
    rsync -a \
      --exclude ".git" \
      --exclude ".pytest_cache" \
      --exclude "__pycache__" \
      --exclude ".DS_Store" \
      --exclude "._*" \
      --exclude "*.pyc" \
      --exclude "*.fastq" \
      --exclude "*.fastq.gz" \
      --exclude "*.fq" \
      --exclude "*.fq.gz" \
      --exclude "*.bam" \
      --exclude "*.sam" \
      --exclude "*.cram" \
      --exclude "*.bai" \
      --exclude "*.crai" \
      --exclude "*.xtc" \
      --exclude "*.trr" \
      --exclude "*.dcd" \
      --exclude "*.tpr" \
      "${src}" "${dst_parent}/"
  fi
}

copy_path "src" "${BUNDLE_ROOT}"
copy_path "pipeline" "${BUNDLE_ROOT}"
copy_path "tests" "${BUNDLE_ROOT}"
copy_path "scripts" "${BUNDLE_ROOT}"
copy_path "configs" "${BUNDLE_ROOT}"
copy_path "pyproject.toml" "${BUNDLE_ROOT}"
copy_path "README.md" "${BUNDLE_ROOT}"
copy_path "SOURCE_OF_TRUTH.md" "${BUNDLE_ROOT}"

copy_path "${RUN_ROOT_REL}/README.md" "${BUNDLE_ROOT}/$(dirname "${RUN_ROOT_REL}")"
copy_path "${RUN_ROOT_REL}/comparison_registry.tsv" "${BUNDLE_ROOT}/$(dirname "${RUN_ROOT_REL}")"
copy_path "${RUN_ROOT_REL}/immune_state" "${BUNDLE_ROOT}/${RUN_ROOT_REL}"
copy_path "${RUN_ROOT_REL}/meta" "${BUNDLE_ROOT}/${RUN_ROOT_REL}"
copy_path "${RUN_ROOT_REL}/patient_manifest" "${BUNDLE_ROOT}/${RUN_ROOT_REL}"
copy_path "${RUN_ROOT_REL}/sample_allocation" "${BUNDLE_ROOT}/${RUN_ROOT_REL}"
copy_path "${RUN_ROOT_REL}/signature" "${BUNDLE_ROOT}/${RUN_ROOT_REL}"
copy_path "${RUN_ROOT_REL}/validation" "${BUNDLE_ROOT}/${RUN_ROOT_REL}"
copy_path "${RUN_ROOT_REL}/tcga_projection" "${BUNDLE_ROOT}/${RUN_ROOT_REL}"
copy_path "${RUN_ROOT_REL}/logs" "${BUNDLE_ROOT}/${RUN_ROOT_REL}"
copy_path "${REPORT_ROOT_REL}" "${BUNDLE_ROOT}/$(dirname "${REPORT_ROOT_REL}")"
copy_path "${FIGURE_ROOT_REL}" "${BUNDLE_ROOT}/$(dirname "${FIGURE_ROOT_REL}")"

{
  echo "# NMRbox ICI Canary Bundle"
  echo
  echo "- created_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "- source_root: ${ROOT}"
  echo "- run_root: ${RUN_ROOT_REL}"
  echo "- report_root: ${REPORT_ROOT_REL}"
  echo "- figure_root: ${FIGURE_ROOT_REL}"
  echo
  echo "This bundle is for a canary reproducibility audit only. It is not a full pipeline rerun bundle."
} > "${BUNDLE_ROOT}/NMRBOX_CANARY_BUNDLE.md"

(
  cd "${BUNDLE_ROOT}"
  find . -type f -print0 | sort -z | xargs -0 shasum -a 256
) > "${OUT_DIR}/MANIFEST.sha256"

cp "${OUT_DIR}/MANIFEST.sha256" "${BUNDLE_ROOT}/MANIFEST.sha256"
COPYFILE_DISABLE=1 tar -czf "${OUT_DIR}/ici_thesis_pipeline_canary.tar.gz" -C "${OUT_DIR}" ici_thesis_pipeline_canary

printf 'bundle_root\t%s\n' "${BUNDLE_ROOT}"
printf 'manifest\t%s\n' "${OUT_DIR}/MANIFEST.sha256"
printf 'tarball\t%s\n' "${OUT_DIR}/ici_thesis_pipeline_canary.tar.gz"
