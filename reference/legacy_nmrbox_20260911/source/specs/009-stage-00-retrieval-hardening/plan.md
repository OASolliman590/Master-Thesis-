# Plan: Spec 009 — Stage 00 Retrieval Hardening

## Architecture

**Target module layout** (extract from `cli.py` L583–L1500):

```
src/pipeline/modules/00_retrieval/
├── __init__.py                 # public API: retrieval_run, retrieval_geo_full, retrieval_geo_manifest, query_run, promote_candidates
├── ledger.py                   # retrieval_ledger schema, write_ledger(), read_ledger()
├── geo.py                      # _download_geo_family_soft, _series_matrix, _supplementary, prefix helpers
├── sra.py                      # _download_runinfo + helpers
├── http.py                     # _download_url, _download_url_if_missing, _fetch_html_links, failure_class()
├── soft_parser.py              # _parse_geo_soft_sample_records, _parse_geo_soft_samples
├── errors.py                   # ErrorClass enum, RetrievalError, classify_http_exception()
└── query/                      # aim-driven discovery subsystem (FR-011..FR-017)
    ├── __init__.py             # public: query_run(), promote_candidates()
    ├── aim_spec.py             # YAML schema, validation, synonym expansion
    ├── candidates.py           # CandidateRecord, scoring, cross-endpoint dedup, manifest cross-check
    ├── promotion.py            # promote_candidates(); manifest_promotion_log.tsv writer
    ├── reproducibility.py      # query-specific bundle (rendered_queries.json + commands + checksums)
    └── endpoints/
        ├── __init__.py         # Endpoint protocol: render_query(aim) -> str, execute() -> list[RawRecord], parse() -> list[CandidateRecord]
        ├── ncbi_geo.py         # EUtils esearch -db gds + esummary
        ├── ncbi_sra.py         # EUtils esearch -db sra + esummary
        ├── arrayexpress.py     # EBI BioStudies REST search
        ├── ena.py              # EBI ENA portal API
        ├── recount3.py         # recount3 metadata TSV filter (no live API; reads published index)
        └── omicsdi.py          # OmicsDI REST (https://www.omicsdi.org/ws/) — federates many repositories
```

Note: directory keeps the digit-prefix `00_retrieval` matching the existing convention (e.g. `01_dataset_intake/sample_allocation.py`). Imports use `importlib.import_module(".modules.00_retrieval.<sub>", package=__package__)`, the same pattern `cmd_intake_build_sample_allocation` uses today (cli.py L2960). `__init__.py` re-exports the public surface.

`cli.py` becomes a thin dispatcher for retrieval commands:

```python
def cmd_retrieval_run(args):
    from pipeline.modules.00_retrieval import retrieval_run
    return retrieval_run(
        discovery_manifest=Path(args.discovery_manifest),
        out_dir=Path(args.out),
        no_download=args.no_download,
        dry_run=args.dry_run,
        run_manifest=Path(args.run_manifest),
    )
```

## Milestones

| # | Milestone | Deliverable | Exit criterion |
|---|---|---|---|
| M1 | Audit complete | `research.md` finalized with code citations, contracts, scientific-validity section | Reviewed by user |
| M2 | Tests-first | Failing tests for FR-001…FR-008 committed | `pytest tests/unit/test_stage_00_*.py` shows expected failures |
| M3 | Extract module | Code moved to `src/pipeline/modules/00_retrieval/`, CLI dispatches | All existing tests pass; `wc -l cli.py` drops ≥ 800 |
| M4 | Failure taxonomy | `ErrorClass` enum, structured `retrieval_note` parser | FR-005 tests green |
| M5 | Reproducibility bundle | `commands.sh`, `environment.yml`, `checksums.sha256` emitter | FR-007 test green |
| M6 | Runbook & docs | `docs/runbooks/stage00_retrieval.md` + `docs/USAGE.md` update | Examiner walkthrough < 10 min |
| M7 | Full-pipeline rerun | New `results/full_pipeline_<ts>/` with Stage 00 from refactored code | Diff vs. committed ledger is timestamps-only |
| M8 | Aim-spec + query scaffold | `inputs/discovery/study_aim_query.yaml` committed; `query/aim_spec.py` validator; `Endpoint` protocol + first adapter (`ncbi_geo`) | Schema load + 1 endpoint passes recorded-fixture test |
| M9 | Remaining endpoints | `ncbi_sra`, `arrayexpress`, `ena`, `recount3`, `omicsdi` adapters | Each adapter has ≥1 recorded-fixture test; rate-limit handling verified |
| M10 | Dedup + scoring + triage | Cross-endpoint dedup, scoring engine, manifest cross-check, `triage_status` assignment | Candidates file passes SC-007, SC-008, SC-010 |
| M11 | Promotion + audit | `retrieval promote-candidates` + `manifest_promotion_log.tsv` | SC-009 passes; reverse-out works in tests |
| M12 | Sign-off | CHANGELOG entry, spec status → Active → Complete | All SC-001…SC-010 met |

## Dependencies

- **Upstream**: none (Stage 00 is the entry point).
- **Downstream stages that consume Stage 00 outputs** (must not break):
  - Stage 01 dataset intake — reads `retrieval_ledger.tsv` and the `downloads/` tree.
  - Stage 02 cohort audit — uses `_parse_geo_soft_sample_records` directly (today, via cli.py import). Audit during M3 whether to expose this in `00_retrieval` public API or move it.
  - Stages 03+ are downstream of Stage 01 outputs, not direct consumers of Stage 00.

## Rollback

If any milestone breaks downstream stages or the full-pipeline rerun (M7) diverges beyond `retrieval_timestamp`:

1. **Identify the bad change** — `git bisect` between the M3 extract commit and the failing milestone.
2. **Code rollback** — `git revert <bad-commit>`; do NOT `git reset --hard` (preserves working tree from concurrent work).
3. **Data rollback**:
   - Retrieval ledger from last good run is at `results/full_pipeline_20260508_204646/retrieval/retrieval_ledger.tsv` — never overwrite this path.
   - All new Stage 00 outputs go under `results/spec_009/` until M7, never `results/full_pipeline_*/`.
   - Downloaded files in `downloads/` are content-addressable and safe to keep; corrupt files are caught by FR-007 checksums.
4. **CLI contract rollback** — if the dispatcher in `cli.py` breaks the argparse surface, the rollback restores the inline command definition. Keep a copy of the pre-M3 `cmd_retrieval_*` functions in `specs/009-stage-00-retrieval-hardening/archive/cli_pre_extract.py` for one cycle.
5. **Communicate** — update the spec Status line to "Rolled back at M<n>" with reason; do not close the spec until either re-attempted or formally abandoned.

**Trip-wires for triggering rollback:**

- Stage 01 integration test fails after M3.
- Full-pipeline rerun (M7) diverges on any column other than `retrieval_timestamp`.
- `cli.py` argparse surface changes (subcommand names, flag names, default values).
- Any cohort that was `downloaded` in the 2026-05-08 ledger becomes `failed` or `partial` after refactor.
- **Query-specific**: `retrieval query` modifies `discovery_manifest.tsv` directly (must be append-only via `promote-candidates`).
- **Query-specific**: An endpoint adapter sends >100 requests in 10 seconds without backoff (NCBI rate-limit risk).
- **Query-specific**: A candidate with `triage_status=multi_omics_for_later` ends up in the RNA-seq manifest after promotion.

**Query rollback procedure** (if M8–M11 deliverables break things):

1. The aim-spec YAML and candidates file are inputs/outputs only — rolling back code does not affect them.
2. If `promote-candidates` polluted `discovery_manifest.tsv`: use `manifest_promotion_log.tsv` to compute the row diff and revert manifest rows by `cohort_id`. The log is append-only and authoritative.
3. If an endpoint adapter is broken, disable it in `study_aim_query.yaml` (remove from `endpoints:` list) and re-run; do not block other endpoints.
4. Query runs are sandboxed under `results/discovery/<ts>/` — never written into `results/full_pipeline_*` paths.

## Constitutional Checks

(Following `.specify/templates/constitution-template.md` if present; otherwise these are project-specific.)

- **Reproducibility first**: every output has a checksum, every command is logged.
- **No silent downgrades**: a stage that was `downloaded` does not regress to `partial` without an explicit code or upstream-NCBI reason.
- **Tests cover behavior, not implementation**: the failure-taxonomy tests assert on `error_class`, not on note string contents.
- **Schema freeze**: `retrieval_ledger.tsv` columns frozen in `research.md` § I/O Contracts; any change is a breaking change requiring a new spec.
- **Discovery does not curate**: the query function MUST NOT promote candidates automatically. Manual review is the gate (FR-011, FR-016).
- **Endpoint adapters respect upstream policy**: NCBI rate limits, ArrayExpress/EBI terms of use, OmicsDI fair-use — adapters back off on 429/5xx with exponential delays, never retry tighter than 200ms.
- **No PHI / no controlled access**: dbGaP / EGA / TCGA-controlled tiers are out of scope; query only returns open-access metadata.
