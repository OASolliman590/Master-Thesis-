#!/usr/bin/env bash
set -euo pipefail

# Non-GEO controlled/publication dataset retrieval probe.
# Targets: IMvigor210, Braun_2020, phs000452, NCT02032277, MEDI4736, E-MTAB-6270
#
# Usage:
#   bash scripts/run_timer_t7_download_non_geo_controlled.sh
#   bash scripts/run_timer_t7_download_non_geo_controlled.sh /Volumes/T7/1-Epigenetics_MSc_Thesis
#   bash scripts/run_timer_t7_download_non_geo_controlled.sh /Volumes/T7/1-Epigenetics_MSc_Thesis --probe-only

T7_ROOT="${1:-/Volumes/T7/1-Epigenetics_MSc_Thesis}"
PROBE_ONLY="false"
for arg in "$@"; do
  case "$arg" in
    --probe-only) PROBE_ONLY="true" ;;
  esac
done

STAMP="$(date +%F)"
OUT_DIR="${T7_ROOT}/retrieval/non_geo_controlled_${STAMP}"
LOG_TSV="${OUT_DIR}/non_geo_download_log.tsv"
README_MD="${OUT_DIR}/README_non_geo_acquisition.md"

mkdir -p "${OUT_DIR}/imvigor210" "${OUT_DIR}/e_mtab_6270" "${OUT_DIR}/manual_queue"

printf "dataset\tstatus\tartifact\tnote\n" > "$LOG_TSV"

log_row () {
  printf "%s\t%s\t%s\t%s\n" "$1" "$2" "$3" "$4" >> "$LOG_TSV"
}

# 1) E-MTAB-6270: direct BioStudies metadata files (often publicly accessible)
E_JSON_URL="https://www.ebi.ac.uk/biostudies/files/E-MTAB-6270/E-MTAB-6270.json"
E_TSV_URL="https://www.ebi.ac.uk/biostudies/files/E-MTAB-6270/E-MTAB-6270.tsv"

if curl -fsSL --max-time 60 "$E_JSON_URL" -o "${OUT_DIR}/e_mtab_6270/E-MTAB-6270.json"; then
  log_row "E-MTAB-6270" "downloaded" "e_mtab_6270/E-MTAB-6270.json" "BioStudies metadata JSON"
else
  log_row "E-MTAB-6270" "failed" "e_mtab_6270/E-MTAB-6270.json" "JSON metadata download failed"
fi

if curl -fsSL --max-time 60 "$E_TSV_URL" -o "${OUT_DIR}/e_mtab_6270/E-MTAB-6270.tsv"; then
  log_row "E-MTAB-6270" "downloaded" "e_mtab_6270/E-MTAB-6270.tsv" "BioStudies metadata TSV"
else
  log_row "E-MTAB-6270" "failed" "e_mtab_6270/E-MTAB-6270.tsv" "TSV metadata download failed"
fi

# 2) IMvigor210: try Bioconductor Experiment package route via R
if command -v Rscript >/dev/null 2>&1; then
  if [[ "$PROBE_ONLY" == "true" ]]; then
    log_row "IMvigor210" "probe_only" "imvigor210/IMvigor210CoreBiologies.rds" "R available; skipped package install/download"
  else
    if Rscript - <<RS
options(repos = c(CRAN = "https://cloud.r-project.org"))
if (!requireNamespace("BiocManager", quietly = TRUE)) install.packages("BiocManager", quiet=TRUE)
if (!requireNamespace("IMvigor210CoreBiologies", quietly = TRUE)) {
  BiocManager::install("IMvigor210CoreBiologies", ask = FALSE, update = FALSE, quiet = TRUE)
}
library(IMvigor210CoreBiologies)
data("IMvigor210CoreBiologies")
saveRDS(IMvigor210CoreBiologies, file = "${OUT_DIR}/imvigor210/IMvigor210CoreBiologies.rds")
RS
    then
      log_row "IMvigor210" "downloaded" "imvigor210/IMvigor210CoreBiologies.rds" "Downloaded via Bioconductor package"
    else
      log_row "IMvigor210" "failed" "imvigor210/IMvigor210CoreBiologies.rds" "Bioconductor package route failed"
    fi
  fi
else
  log_row "IMvigor210" "failed" "imvigor210/IMvigor210CoreBiologies.rds" "Rscript not found"
fi

# 3) Controlled/publication-only queues (manual)
cat > "${OUT_DIR}/manual_queue/controlled_access_queue.tsv" <<MAN
dataset\taccess_type\tprimary_route\tnote
Braun_2020\tpublication_or_author_request\tPMID:32472114 supplement/author\tNo standard public accession in current roster
phs000452\tdbGaP_controlled\tdbGaP study request\tControlled-access human dataset
NCT02032277\ttrial_publication_only\tClinicalTrials + publication supplement\tNo direct omics bulk accession in current roster
MEDI4736\tpublication_or_author_request\tPMID:35377948 supplement/author\tNo standard public accession in current roster
MAN

log_row "Braun_2020" "manual_required" "manual_queue/controlled_access_queue.tsv" "No auto-download route"
log_row "phs000452" "manual_required" "manual_queue/controlled_access_queue.tsv" "dbGaP controlled-access"
log_row "NCT02032277" "manual_required" "manual_queue/controlled_access_queue.tsv" "Publication/trial route"
log_row "MEDI4736" "manual_required" "manual_queue/controlled_access_queue.tsv" "Publication route"

cat > "$README_MD" <<'MD'
# Non-GEO Controlled/Public Retrieval (${STAMP})

This folder contains attempted retrievals for:
- IMvigor210
- Braun_2020
- phs000452
- NCT02032277
- MEDI4736
- E-MTAB-6270

## Files
- non_geo_download_log.tsv : status log for each dataset.
- manual_queue/controlled_access_queue.tsv : datasets requiring manual/controlled acquisition.
- e_mtab_6270/ : E-MTAB metadata files when reachable.
- imvigor210/ : IMvigor210 RDS if Bioconductor route succeeds.

## Notes
- This script does not use GEO/SRA retrieval mode.
- Any `manual_required` entries should be considered outside automated pipeline download.
MD

echo "Completed non-GEO controlled retrieval probe."
echo "Output dir: $OUT_DIR"
echo "Log file:   $LOG_TSV"
