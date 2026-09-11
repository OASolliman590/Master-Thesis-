#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

REMOTE_DATA_ROOT="${BIBALEX_DATA_ROOT:?Set BIBALEX_DATA_ROOT to the remote retrieval root.}"
JOB_ID="${JOB_ID:?Set JOB_ID to the Slurm retrieval job ID.}"
JOB_NAME="${JOB_NAME:-geo_retrieval_full_all}"
DEST="${DEST:-${BIBALEX_LOCAL_ROOT}/runtime_audits/bibalex_geo_full_${JOB_ID}}"

mkdir -p "${DEST}"

REMOTE_RETRIEVAL="${REMOTE_DATA_ROOT%/}/retrieval"

for file in \
  "geo_full_retrieval_ledger.tsv" \
  "geo_data_type_manifest_timer_all.tsv" \
  "geo_data_type_manifest_timer_all.md" \
  "download_summary_timer_all.md"
do
  rsync -av "${BIBALEX_SSH_HOST}:${REMOTE_RETRIEVAL}/${file}" "${DEST}/"
done

for file in \
  "${JOB_NAME}_${JOB_ID}.out" \
  "${JOB_NAME}_${JOB_ID}.err"
do
  rsync -av "${BIBALEX_SSH_HOST}:${BIBALEX_REMOTE_SLURM_ROOT}/${file}" "${DEST}/"
done

printf 'dest\t%s\n' "${DEST}"
find "${DEST}" -maxdepth 1 -type f -print | sort
