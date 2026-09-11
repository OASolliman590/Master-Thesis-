# Quickstart: Spec 009 — Stage 00 Retrieval

How to run, verify, and reproduce Stage 00 after this spec is complete.

## TL;DR

```bash
cd 06_analysis_pipeline_repo

# Run Stage 00 against the committed discovery manifest:
ici-pipeline retrieval geo-full \
  --discovery-manifest inputs/discovery/discovery_manifest.tsv \
  --out results/stage_00/$(date -u +%Y%m%d_%H%M%S) \
  --run-manifest logs/run_manifest.yaml

# Dry-run (lists URLs, no HTTP):
ici-pipeline retrieval geo-full \
  --discovery-manifest inputs/discovery/discovery_manifest.tsv \
  --out /tmp/stage_00_dryrun \
  --dry-run

# Verify reproducibility bundle:
cd <out>/reproducibility/
sha256sum -c checksums.sha256
```

## What you get

```
<out>/
├── retrieval_ledger.tsv            # one row per cohort, schema in research.md § 2.2
├── downloads/<cohort_id>/...       # SOFT + matrix + suppl + runinfo
└── reproducibility/
    ├── commands.sh
    ├── environment.yml
    └── checksums.sha256
```

## How to verify it reproduces the baseline

```bash
BASELINE=results/full_pipeline_20260508_204646/retrieval/retrieval_ledger.tsv
NEW=<your-out>/retrieval_ledger.tsv

# Compare all columns except retrieval_timestamp (column 11 in the basic ledger):
diff <(cut -f1-10,12 "$BASELINE") <(cut -f1-10,12 "$NEW")
# Expected: empty
```

If the diff is non-empty, see `docs/runbooks/stage_00_retrieval.md` § Failure triage.

## How to run only the tests for Stage 00

```bash
pytest tests/unit/test_stage_00_*.py tests/integration/test_stage_00_golden_ledger.py -v
```

Expected: 9+ tests, all green (after M5).

## How to read the failure taxonomy

A non-`downloaded` ledger row has `retrieval_note` formatted as semicolon-separated tuples:

```
GSE123456:suppl:http_404; SRP100001:runinfo:empty_response
```

Each tuple is `<accession>:<file_kind>:<error_class>[:<detail>]`. See `research.md` § 2.5 for the full enum.

## Common operations

### Re-download a single cohort

```bash
echo -e "cohort_id\taccession\nmycohort\tGSE123456" > /tmp/one.tsv
ici-pipeline retrieval geo-full \
  --discovery-manifest /tmp/one.tsv \
  --out results/stage_00/single_$(date -u +%Y%m%d_%H%M%S)
```

### Resume after a partial failure

Just re-run the same command — `_download_url_if_missing` skips files already present. Stale `.part` files are cleaned at startup (FR-004 + T030).

### Audit what was downloaded

```bash
find <out>/downloads -type f | wc -l
du -sh <out>/downloads/
awk -F'\t' '$10!="downloaded"' <out>/retrieval_ledger.tsv
```

## Aim-driven discovery (FR-011..FR-017)

The retrieval stage now also queries the data endpoints to surface candidate cohorts matching the study aim. Candidates are listed for manual review; nothing is auto-merged.

### Run a discovery query

```bash
# Edit the aim if needed:
vi inputs/discovery/study_aim_query.yaml

# Run the query across all configured endpoints:
ici-pipeline retrieval query \
  --aim-spec inputs/discovery/study_aim_query.yaml \
  --out results/discovery/$(date -u +%Y%m%d_%H%M%S)

# Look at what came back:
column -t -s$'\t' results/discovery/<ts>/discovery_candidates.tsv | less -S
```

### Output

```
results/discovery/<ts>/
├── discovery_candidates.tsv        # the candidates (schema in research.md § 2.7)
└── reproducibility/
    ├── rendered_queries.json       # exact URL+params per endpoint
    ├── commands.sh                 # the invocation
    ├── checksums.sha256
    └── responses_cache/            # optional, for replay
```

### Triage flow

1. Review `discovery_candidates.tsv`. Focus on rows with `triage_status=new` and high `match_score`.
2. Save the cohort_ids you want to promote into `inputs/discovery/approved_<ts>.tsv` (one column: `canonical_accession`).
3. Promote:
   ```bash
   ici-pipeline retrieval promote-candidates \
     --candidates results/discovery/<ts>/discovery_candidates.tsv \
     --approved   inputs/discovery/approved_<ts>.tsv \
     --manifest   inputs/discovery/discovery_manifest.tsv \
     --log        inputs/discovery/manifest_promotion_log.tsv
   ```
4. Inspect the promotion log: `tail inputs/discovery/manifest_promotion_log.tsv`.
5. Rows with `triage_status=multi_omics_for_later` (e.g. methylation, proteomics ICB cohorts surfaced via OmicsDI) accumulate for spec_008+ work; the promotion command refuses to merge them into the RNA-seq manifest.

### Replay a previous query (no live HTTP)

```bash
ici-pipeline retrieval query \
  --aim-spec inputs/discovery/study_aim_query.yaml \
  --out /tmp/replay \
  --no-network \
  --responses-cache results/discovery/<previous>/reproducibility/responses_cache/
```

### Reverse a promotion

The promotion log is authoritative. To reverse out, look up the rows with `query_run_id=<run>` in the log and delete the matching `cohort_id` rows from `discovery_manifest.tsv`. See `docs/runbooks/stage_00_query.md` for the exact procedure.

## Where to look next

- Per-stage runbook with failure triage: `docs/runbooks/stage_00_retrieval.md` (created in T037).
- Per-stage runbook for the query/promotion path: `docs/runbooks/stage_00_query.md` (created in T069).
- Schema reference: `specs/009-stage-00-retrieval-hardening/research.md` § 2.
- Rollback if something breaks: `specs/009-stage-00-retrieval-hardening/plan.md` § Rollback.
- Next stage (intake): `specs/010-stage-01-dataset-intake-hardening/` (to be created in T072).
