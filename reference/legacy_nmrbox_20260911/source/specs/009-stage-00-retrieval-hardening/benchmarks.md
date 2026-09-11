# Benchmarks: Spec 009 — Stage 00 Retrieval

Baseline values and a regression budget for the refactor.

## Baseline (measured T002, 2026-05-28)

**Baseline source correction (2026-05-28):** the spec originally pointed at `results/full_pipeline_20260508_204646/retrieval/retrieval_ledger.tsv`. That subdirectory does not exist — the canonical full-pipeline run does not co-locate Stage 00 outputs. The authoritative cohort manifest is the reconciled T7 file: `/Volumes/T7/1-Epigenetics_MSc_Thesis/retrieval/cohorts_source_reconciled_all_47.tsv`. Downloads live at `/Volumes/T7/1-Epigenetics_MSc_Thesis/retrieval/{downloads_timer_all,downloads_timer_second_roster_delta}/`.

| Metric | Baseline | Source / how measured |
|---|---:|---|
| Cohorts in reconciled manifest | 47 | `wc -l /Volumes/T7/1-Epigenetics_MSc_Thesis/retrieval/cohorts_source_reconciled_all_47.tsv` (48 incl. header) |
| `download_status=downloaded_present` | 39 | `awk -F'\t' '$8=="downloaded_present"' …` |
| `download_status=not_found_local_or_t7` | 8 | as above, complement |
| Cohorts with `retrieval_status=partial` (after FR-005 reclassification) | 0 known | new vocabulary; baseline is "downloaded_present vs not_found" |
| Cohorts with `retrieval_status=failed` | 8 (= not_found) | same as missing count |
| Total bytes, `downloads_timer_all/` (PRE roster) | 811 MB | `du -sh …` |
| Total bytes, `downloads_timer_second_roster_delta/` (DELTA roster) | 728 MB | `du -sh …` |
| Total bytes, `cohorts_source_all/` (consolidated mirror) | 811 MB | `du -sh …` |
| Wall time, full Stage 00 (cold network) | DEFERRED | requires a fresh `retrieval geo-full` invocation; defer to M7 actual re-run |
| Wall time, full Stage 00 (warm cache, all files present) | DEFERRED | as above, second invocation |
| Peak RSS | DEFERRED | `/usr/bin/time -v` on Linux; macOS `gtime` or `/usr/bin/time -l` |
| `cli.py` line count | 10,515 | `wc -l src/pipeline/cli.py` |
| Test count (Stage 00) | 1 | `grep -c "^def test_" tests/unit/test_retrieval_geo_manifest.py` |

**Cohort breakdown by track (from reconciled manifest):**

| Track | Cohorts | Cohorts downloaded |
|---|---:|---:|
| Cat A (PRE_RESPONSE only) | 37 | 29 (8 missing, all SRA-only) |
| Cat B (TREATMENT_DELTA only) | 4 | 4 |
| Cat C (PRE_RESPONSE + TREATMENT_DELTA) | 6 | 6 |

**The 8 missing cohorts** (all pure SRA/ENA, no GEO equivalent — `retrieval geo-full` cannot recover them):

| Accession | Cancer | Track |
|---|---|---|
| ERP105482 | Melanoma | Cat A |
| ERP107734 | Stomach adenocarcinoma | Cat A |
| SRP070710 | Melanoma | Cat A |
| SRP094781 | Melanoma | Cat A |
| SRP150548 | Melanoma | Cat A |
| SRP155030 | Glioblastoma | Cat A |
| SRP230414 | Melanoma | Cat A |
| SRP609012 | Stomach adenocarcinoma | Cat A |

**Wall-time/RSS deferred** because re-running `retrieval geo-full` cold costs ~1.5 GB of redownloads against NCBI/EBI. Defer until M7 (full-pipeline rerun) where the wall time is captured incidentally. Refactor regressions in this dimension surface there.

## Regression budget

After refactor:

| Metric | Budget |
|---|---|
| Wall time (warm cache) | ≤ baseline × 1.10 |
| Wall time (cold network) | ≤ baseline × 1.05 (mostly I/O-bound, refactor should be neutral) |
| Peak RSS | ≤ baseline × 1.10 |
| `cli.py` line count | ≤ baseline − 800 (target ≤ baseline − 900) |
| `retrieval_status` distribution | identical (no cohort regresses from `downloaded` to `partial`/`failed`) |
| Total bytes under `downloads/` | identical (downloads are content-addressable) |
| Test count (Stage 00) | ≥ baseline + 8 |

Any budget violation triggers the rollback procedure in `plan.md`.

## Measurement procedure

```bash
# Baseline (run once, before M2):
cd 06_analysis_pipeline_repo
RUN=results/full_pipeline_20260508_204646
wc -l $RUN/retrieval/retrieval_ledger.tsv
awk -F'\t' 'NR>1{print $10}' $RUN/retrieval/retrieval_ledger.tsv | sort | uniq -c
du -sb $RUN/retrieval/downloads/ 2>/dev/null || du -sk $RUN/retrieval/downloads/

# Refactor measurement (at M7, after extract + tests + bundle):
OUT=results/spec_009/m7_rerun
ici-pipeline retrieval geo-full --discovery-manifest <committed.tsv> --out $OUT
# capture wall time + RSS via /usr/bin/time
diff <(cut -f1-10,12 $RUN/retrieval/retrieval_ledger.tsv) \
     <(cut -f1-10,12 $OUT/retrieval_ledger.tsv)
# expected: empty
```

## Notes

- Cold-network timings depend on NCBI FTP latency on the day of measurement. Re-measure baseline and refactor on the same day if comparing wall times.
- Peak RSS for `urllib`-based streaming download should be < 50 MB regardless of file size; if the refactor introduces buffering (e.g. switching to `requests` without streaming), RSS will balloon.

## Query benchmarks (FR-011..FR-017)

No baseline exists — these are budgets set at design time.

| Metric | Budget | Measurement |
|---|---:|---|
| Per-endpoint adapter latency (live, p50) | ≤ 5 s | `time` on a single `query` invocation per endpoint |
| Per-endpoint adapter latency (live, p95) | ≤ 30 s | as above, repeated × 10 |
| Per-endpoint adapter latency (cached/replay) | ≤ 200 ms | `--no-network` mode |
| End-to-end query (6 endpoints, live) wall time | ≤ 90 s | one invocation |
| Candidates yield on the ICB aim-spec | ≥ 25 candidates | `wc -l discovery_candidates.tsv` after dedup |
| Candidates with `triage_status=already_in_manifest` | ≥ 18 of the 22 PRE_RESPONSE cohorts re-discovered | sanity check, SC-008 |
| Candidates with `triage_status=multi_omics_for_later` | ≥ 5 (methylation/proteomics ICB cohorts) | sourced primarily from OmicsDI |
| NCBI EUtils requests per query run | ≤ 60 with `NCBI_API_KEY`, ≤ 20 without | adapter must paginate, not flood |
| Rate-limit-induced 429 responses | 0 (with backoff) | adapter test |
| Test count (query) | ≥ 12 new tests | `pytest -k query` count |

**Measurement procedure (after M10):**

```bash
# Live full query:
/usr/bin/time -v ici-pipeline retrieval query \
  --aim-spec inputs/discovery/study_aim_query.yaml \
  --out results/discovery/$(date -u +%Y%m%d_%H%M%S)

# Replay-only (cache):
ici-pipeline retrieval query \
  --aim-spec inputs/discovery/study_aim_query.yaml \
  --out /tmp/replay --no-network \
  --responses-cache results/discovery/<last>/reproducibility/responses_cache/

# Yield check:
awk -F'\t' 'NR>1{print $18}' results/discovery/<last>/discovery_candidates.tsv | sort | uniq -c
```
