#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${ROOT:-$(cd "${SCRIPT_DIR}/../.." && pwd)}"
RUN_ROOT_REL="${RUN_ROOT_REL:-results/analysis_id_runs_t7_20260607_stage07_scale_provenance}"
REPORT_ROOT_REL="${REPORT_ROOT_REL:-reports/analysis_id_runs_t7_20260607_stage07_scale_provenance}"
FIGURE_ROOT_REL="${FIGURE_ROOT_REL:-figures/analysis_id_runs_t7_20260607_stage07_scale_provenance}"
STAMP="$(date -u +%Y%m%d_%H%M%S)"
OUT_DIR="${OUT_DIR:-${ROOT}/results/nmrbox_ici_canary_${STAMP}}"
LOG_DIR="${OUT_DIR}/logs"
STATUS_TSV="${OUT_DIR}/nmrbox_pipeline_canary.tsv"
RUNTIME_TSV="${OUT_DIR}/nmrbox_runtime_audit.tsv"
FINGERPRINT_TSV="${OUT_DIR}/nmrbox_reproducibility_fingerprint.tsv"
AUDIT_MD="${OUT_DIR}/nmrbox_scientific_audit.md"

mkdir -p "${OUT_DIR}" "${LOG_DIR}"
cd "${ROOT}"

is_supported_python() {
  local candidate="$1"
  "${candidate}" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY
}

PY=""
PY_STATUS="missing"
if [[ -n "${PYTHON_BIN:-}" ]]; then
  if command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    PY="${PYTHON_BIN}"
    if is_supported_python "${PY}"; then
      PY_STATUS="supported"
    else
      PY_STATUS="unsupported_version"
    fi
  fi
else
  for candidate in python3.13 python3.12 python3.11 python3 python; do
    if command -v "${candidate}" >/dev/null 2>&1 && is_supported_python "${candidate}"; then
      PY="${candidate}"
      PY_STATUS="supported"
      break
    fi
  done
  if [[ -z "${PY}" ]]; then
    for candidate in python3 python; do
      if command -v "${candidate}" >/dev/null 2>&1; then
        PY="${candidate}"
        PY_STATUS="unsupported_version"
        break
      fi
    done
  fi
fi

export PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-/tmp/ici_pycache_${USER:-unknown}_$$}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-${OUT_DIR}/.matplotlib}"
mkdir -p "${MPLCONFIGDIR}"

if [[ "${CANARY_CLEAN_APPLEDOUBLE:-1}" == "1" ]]; then
  for maybe_tree in "${RUN_ROOT_REL}" "${REPORT_ROOT_REL}" "${FIGURE_ROOT_REL}"; do
    if [[ -d "${maybe_tree}" ]]; then
      find "${maybe_tree}" -name '._*' -type f -delete 2>/dev/null || true
    fi
  done
fi

write_status() {
  local step="$1"
  local status="$2"
  local reason="$3"
  local detail="$4"
  printf '%s\t%s\t%s\t%s\n' "${step}" "${status}" "${reason}" "${detail}" >> "${STATUS_TSV}"
}

printf 'step\tstatus\treason\tdetail\n' > "${STATUS_TSV}"

{
  printf 'key\tvalue\n'
  printf 'host\t%s\n' "$(hostname 2>/dev/null || true)"
  printf 'user\t%s\n' "${USER:-unknown}"
  printf 'workdir\t%s\n' "${ROOT}"
  printf 'date_utc\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'condor_job_id\t%s\n' "${_CONDOR_JOB_AD:-not_in_condor_or_unset}"
  printf 'run_root\t%s\n' "${RUN_ROOT_REL}"
  printf 'report_root\t%s\n' "${REPORT_ROOT_REL}"
  printf 'figure_root\t%s\n' "${FIGURE_ROOT_REL}"
  printf 'python_executable\t%s\n' "${PY:-missing}"
  printf 'python_status\t%s\n' "${PY_STATUS}"
} > "${RUNTIME_TSV}"

if [[ -n "${PY}" ]]; then
  "${PY}" - <<'PY' >> "${RUNTIME_TSV}" || true
import importlib
import platform
import sys

print(f"python_version\t{sys.version.replace(chr(9), ' ').replace(chr(10), ' ')}")
print(f"python_platform\t{platform.platform()}")
for module in ["pytest", "pandas", "numpy", "scipy", "statsmodels", "matplotlib"]:
    try:
        importlib.import_module(module)
    except ModuleNotFoundError:
        status = "missing"
    except Exception as exc:
        status = f"import_failed:{exc.__class__.__name__}:{str(exc).splitlines()[0]}"
    else:
        status = "import_ok"
    print(f"python_module_{module}\t{status}")
PY
else
  write_status "python_runtime" "failed" "python_missing" "No python executable found on PATH."
fi

if [[ "${PY_STATUS}" == "unsupported_version" ]]; then
  write_status "python_runtime" "failed" "unsupported_python_version" "Set PYTHON_BIN to Python >=3.11 with pipeline dependencies."
fi

if command -v Rscript >/dev/null 2>&1; then
  printf 'rscript_path\t%s\n' "$(command -v Rscript)" >> "${RUNTIME_TSV}"
  printf 'rscript_version\t%s\n' "$(Rscript --version 2>&1 | head -1)" >> "${RUNTIME_TSV}"
else
  printf 'rscript_path\tmissing\n' >> "${RUNTIME_TSV}"
  printf 'rscript_version\tmissing\n' >> "${RUNTIME_TSV}"
fi

if [[ -z "${PY}" ]]; then
  write_status "selected_pytest" "skipped" "python_missing" "Cannot run tests without Python."
else
  TEST_LOG="${LOG_DIR}/selected_pytest.log"
  if "${PY}" -m pytest \
    tests/integration/test_immune_effects_smoke.py \
    tests/unit/test_tcga_naive_contracts.py \
    tests/unit/test_spec025_viz_build.py \
    -q > "${TEST_LOG}" 2>&1; then
    write_status "selected_pytest" "passed" "ok" "${TEST_LOG}"
  else
    write_status "selected_pytest" "failed" "pytest_failed" "${TEST_LOG}"
  fi
fi

REPORT_OUT="${OUT_DIR}/report_rebuild"
if [[ -z "${PY}" ]]; then
  write_status "report_build" "skipped" "python_missing" "Cannot rebuild report without Python."
elif [[ ! -d "${RUN_ROOT_REL}" ]]; then
  write_status "report_build" "skipped" "run_root_missing" "${RUN_ROOT_REL}"
else
  REPORT_LOG="${LOG_DIR}/report_build.log"
  FIGURE_ARG=()
  if [[ -d "${FIGURE_ROOT_REL}" ]]; then
    FIGURE_ARG=(--figure-root "${FIGURE_ROOT_REL}")
  fi
  if "${PY}" -m pipeline.cli report build \
    --results-root "${RUN_ROOT_REL}" \
    --out "${REPORT_OUT}" \
    "${FIGURE_ARG[@]}" \
    --run-manifest "${LOG_DIR}/report_build.yaml" > "${REPORT_LOG}" 2>&1; then
    write_status "report_build" "passed" "ok" "${REPORT_OUT}"
  else
    write_status "report_build" "failed" "report_build_failed" "${REPORT_LOG}"
  fi
fi

printf 'artifact\texists\tn_data_rows\tsha256\tstatus\tnotes\n' > "${FINGERPRINT_TSV}"

fingerprint_file() {
  local artifact="$1"
  local notes="$2"
  if [[ -f "${artifact}" ]]; then
    local rows
    local checksum
    rows="$(awk 'END { if (NR == 0) print 0; else print NR - 1 }' "${artifact}")"
    checksum="$(shasum -a 256 "${artifact}" | awk '{print $1}')"
    printf '%s\ttrue\t%s\t%s\tpresent\t%s\n' "${artifact}" "${rows}" "${checksum}" "${notes}" >> "${FINGERPRINT_TSV}"
  else
    printf '%s\tfalse\t0\t\tmissing\t%s\n' "${artifact}" "${notes}" >> "${FINGERPRINT_TSV}"
  fi
}

fingerprint_file "${RUN_ROOT_REL}/immune_state/cohort_level_effects.tsv" "immune score-response association table"
fingerprint_file "${RUN_ROOT_REL}/immune_state/ssgsea_scores_long.tsv" "real GSVA/ssGSEA long table"
fingerprint_file "${RUN_ROOT_REL}/immune_state/immune_effects_input_audit.tsv" "expression availability audit for immune effects"
fingerprint_file "${RUN_ROOT_REL}/immune_state/marker_correlations.tsv" "expression-backed marker correlations"
fingerprint_file "${RUN_ROOT_REL}/signature/PRE_RESPONSE/responder_signature_tiered.tsv" "PRE_RESPONSE signature table"
fingerprint_file "${RUN_ROOT_REL}/signature/PAN_ICB_RESPONSE__PRE_TREATMENT/responder_signature_tiered.tsv" "PAN_ICB pre-treatment signature table"
fingerprint_file "${RUN_ROOT_REL}/signature/ICI_COMBINATION_RESPONSE__PRE_TREATMENT/responder_signature_tiered.tsv" "ICI combination pre-treatment signature table"
fingerprint_file "${REPORT_OUT}/evidence_readiness_status.tsv" "rebuilt report evidence readiness table"
fingerprint_file "${REPORT_OUT}/report_claim_boundaries.tsv" "rebuilt report claim boundary table"
fingerprint_file "${REPORT_OUT}/figure_manifest_summary.tsv" "rebuilt report figure manifest summary"

{
  echo "# NMRbox ICI Pipeline Canary Scientific Audit"
  echo
  echo "- generated_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "- workdir: ${ROOT}"
  echo "- run_root: ${RUN_ROOT_REL}"
  echo "- output_dir: ${OUT_DIR}"
  echo
  echo "## Canary Status"
  echo
  echo "| step | status | reason | detail |"
  echo "| --- | --- | --- | --- |"
  awk -F '\t' 'NR > 1 { printf("| %s | %s | %s | %s |\n", $1, $2, $3, $4) }' "${STATUS_TSV}"
  echo
  echo "## Fingerprinted Artifacts"
  echo
  echo "| artifact | exists | n_data_rows | status | notes |"
  echo "| --- | --- | ---: | --- | --- |"
  awk -F '\t' 'NR > 1 { printf("| %s | %s | %s | %s | %s |\n", $1, $2, $3, $5, $6) }' "${FINGERPRINT_TSV}"
  echo
  echo "## Scientific Boundaries"
  echo
  echo "- TCGA projection is prognostic context only, not ICB responder validation."
  echo "- Internal concordance and robustness are not external validation."
  echo "- Discovery signatures are not validated predictors until held-out ICI-treated validation is completed."
  echo "- Expression-backed marker correlations require expression matrices; if missing, the absence must remain explicit in the audit table."
  echo
  echo "## What Was Not Done"
  echo
  echo "- No full pipeline rerun."
  echo "- No raw expression matrix transfer."
  echo "- No raw sequencing alignment."
  echo "- No external ICI-treated validation."
  echo
  echo "## Recommended Next Action"
  echo
  echo "Review failed or skipped rows in nmrbox_pipeline_canary.tsv. If the canary is clean, plan a targeted remote Stage 09/15 rerun with explicit expression-matrix input paths before considering a full remote rerun."
} > "${AUDIT_MD}"

printf 'audit_dir\t%s\n' "${OUT_DIR}"
printf 'runtime\t%s\n' "${RUNTIME_TSV}"
printf 'status\t%s\n' "${STATUS_TSV}"
printf 'fingerprint\t%s\n' "${FINGERPRINT_TSV}"
printf 'scientific_audit\t%s\n' "${AUDIT_MD}"
