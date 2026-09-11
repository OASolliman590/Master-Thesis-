# Feature Specification: Stage 00 Retrieval — Audit, Extract, Harden, and Aim-Driven Discovery

**Feature Branch**: `009-stage-00-retrieval-hardening`
**Created**: 2026-05-28
**Status**: Active (since 2026-05-28, M1+M2 complete)
**Input**: User decision (2026-05-28) to audit-and-harden the pipeline stage-by-stage, one spec per stage, starting at Stage 00. Scientific gaps from spec 007 (ssGSEA, Layer 4 epigenetic sets, TCGA validation) are deferred to a later spec.
**Amendment (2026-05-28)**: Aim-driven cohort discovery (`retrieval query` + `retrieval promote-candidates`) added per user request; federated across NCBI GEO, NCBI SRA, EBI ArrayExpress/BioStudies, EBI ENA, recount3, and OmicsDI.

## Context Lock

Stage 00 is the entry point of the pipeline: it consumes a discovery manifest of cohort accessions (GSE, SRP, SRX, SRR, PRJ) and pulls primary data from GEO (SOFT family, series matrix, supplementary) and SRA (runinfo) into local cohort directories, emitting a `retrieval_ledger.tsv` for downstream stages.

**Current state (verified 2026-05-28):**

- `src/pipeline/modules/00_retrieval/__init__.py` is empty (one docstring line).
- All retrieval logic lives in `src/pipeline/cli.py`:
  - `cmd_retrieval_run` (L1306) — basic retrieval driver.
  - `cmd_retrieval_geo_full` (L1392) — full GEO retrieval (soft + matrix + suppl + runinfo).
  - `cmd_retrieval_geo_manifest` (L1538) — downstream summarizer (consumed by Stage 01).
  - `_download_geo_family_soft` (L666), `_download_geo_series_matrix` (L680), `_download_geo_supplementary` (L716), `_download_runinfo` (L754).
  - `_download_url` (L623), `_download_url_if_missing` (L643), `_fetch_html_links` (L649), `_geo_series_prefix` (L619).
- `cli.py` is 10,515 lines total — Stage 00 logic is roughly L583–L1500 (~900 lines).
- Existing tests: `tests/unit/test_retrieval_geo_manifest.py` (65 lines) covers `cmd_retrieval_geo_manifest` only. **No direct tests for `cmd_retrieval_run`, `cmd_retrieval_geo_full`, or the GEO download helpers.**
- Last successful Stage 00 run: part of `results/full_pipeline_20260508_204646`.

**Why this cycle:**

The retrieval stage is correct but fragile: tests cover the summarizer, not the downloader; logic is co-located with 70+ other commands in one CLI file; failure taxonomy is encoded as ad-hoc note strings; and the module directory advertised as Stage 00 is empty. None of this blocks the current full run, but it blocks thesis-defense reproducibility ("show me Stage 00 in isolation") and makes future per-stage hardening of stages 01–15 harder when each of them is also still in `cli.py`.

## User Scenarios & Testing

### User Story 1 — Reproducible single-stage retrieval (Priority: P1)

The thesis defense examiner asks: "Can you re-run only Stage 00 against the existing discovery manifest and show the retrieval ledger is identical to the committed one?" Today this works via the CLI but is not documented as a single-stage entry point and the downloader is untested.

**Why this priority**: Defense reproducibility is the load-bearing requirement of this entire cycle.

**Independent Test**: Run `ici-pipeline retrieval run --discovery-manifest <committed.tsv> --out <tmp>` against the same input used by `results/full_pipeline_20260508_204646`. The resulting `retrieval_ledger.tsv` matches (schema and per-cohort status) the committed ledger, ignoring `retrieval_timestamp`.

**Acceptance Scenarios**:

1. **Given** the committed discovery manifest from the last full run, **When** `retrieval run` executes with `--no-download` against an already-populated downloads dir, **Then** the new ledger matches the committed ledger on every column except `retrieval_timestamp`.
2. **Given** a fresh empty downloads dir and the committed manifest, **When** `retrieval run` is invoked twice, **Then** the second invocation makes zero new HTTP requests for files already present (idempotency).

### User Story 2 — Stage 00 as a real Python module (Priority: P1)

A future contributor (or the thesis advisor) wants to read the retrieval code without scrolling through 10,000 lines of unrelated CLI commands.

**Why this priority**: Required to make subsequent per-stage hardening cycles tractable. If Stage 00 stays in `cli.py`, Stage 01–15 specs inherit the same problem.

**Independent Test**: `python -c "from pipeline.modules._00_retrieval import retrieval_run, download_geo_family_soft, download_geo_series_matrix, download_geo_supplementary, download_runinfo"` succeeds. The CLI dispatches to these functions; behavior is unchanged.

**Acceptance Scenarios**:

1. **Given** the extracted module, **When** the existing `cmd_retrieval_geo_manifest` test runs, **Then** it still passes (no regression in the only existing test).
2. **Given** the extracted module, **When** a developer imports `pipeline.modules._00_retrieval`, **Then** they get the public API; private helpers stay underscore-prefixed.

### User Story 3 — Structured failure taxonomy (Priority: P2)

When retrieval partially fails (HTTP 404 on supplementary files, empty SRA runinfo), the current ledger encodes the reason as a free-text `retrieval_note` like `gse123456:suppl_download_failed:foo.tsv:http_404`. This is human-readable but not machine-queryable.

**Why this priority**: Required for downstream blocked-cohort triage and for the QC stage to programmatically distinguish "soft failure, retry later" from "permanent failure, exclude from analysis."

**Independent Test**: Inspect a ledger from a run with mixed outcomes. Every non-empty `retrieval_note` decomposes into `{accession, file_kind, error_class}` tuples; `error_class` is from a fixed vocabulary.

**Acceptance Scenarios**:

1. **Given** a cohort with a missing supplementary directory, **When** retrieval runs, **Then** the ledger row has `retrieval_status=partial` and `retrieval_note` contains one tuple per attempted file with `error_class ∈ {http_404, http_5xx, network_timeout, empty_response, parse_error}`.
2. **Given** an SRA accession whose runinfo is empty (`!"Run," in text`), **When** retrieval runs, **Then** the row records `error_class=empty_response`, not a generic `runinfo_empty_or_invalid` string.

### User Story 4 — Aim-driven cohort discovery across repositories (Priority: P2)

The discovery manifest is hand-curated today. Cohorts deposited in 2026 that match the study aim (pre-treatment RNA-seq for ICB R-vs-NR) are not discovered until someone manually searches GEO/SRA/ArrayExpress. The user wants Stage 00 to also be able to query the major omics endpoints, encode the study aim as a versioned filter spec, and surface candidate cohorts for triage. The candidates file is never auto-merged into the discovery manifest; a separate explicit `promote-candidates` command moves approved rows in with an audit trail.

**Why this priority**: P2 (not P1) because the existing 22 PRE_RESPONSE cohorts are sufficient for the immediate thesis chapter; this expands future yield and preserves multi-omics datasets (methylation, proteomics) that complement the RNA-seq arm.

**Independent Test**: With `inputs/discovery/study_aim_query.yaml` defining the ICB pre-treatment aim and recorded HTTP fixtures for each endpoint, `ici-pipeline retrieval query --aim-spec ... --out results/discovery/<ts>/` produces `discovery_candidates.tsv` containing rows from at least 2 endpoints, with `match_score`, `matched_rules[]`, and `triage_status` populated for each candidate; `discovery_manifest.tsv` is unchanged.

**Acceptance Scenarios**:

1. **Given** the aim-spec YAML and the recorded NCBI EUtils fixture, **When** `retrieval query` runs against the `geo` endpoint only, **Then** the candidates file lists every fixture record matching ≥3 inclusion rules with the correct `match_score` and `matched_rules[]`.
2. **Given** a candidate cohort already present in the discovery manifest, **When** `retrieval query` runs, **Then** that candidate's `triage_status = already_in_manifest` (not promoted again, not silently dropped).
3. **Given** a reviewed candidates file and an `--approved` list, **When** `retrieval promote-candidates` runs, **Then** approved rows are appended to `discovery_manifest.tsv` with a new `manifest_promotion_log.tsv` row capturing `query_run_id`, `promoted_at`, `cohort_id`, `approving_user`.
4. **Given** an OmicsDI response that includes a methylation array dataset matching the aim, **When** `retrieval query` runs, **Then** the candidate is preserved with `triage_status = multi_omics_for_later` and `omics_type ∈ {methylation, proteomics, ...}` — it is not eligible for promotion to the RNA-seq discovery manifest.

### Edge Cases

- Cohort ID containing both a GSE and an SRP token (e.g. `gse289583_mcrc_regorafenib_ipilimumab_nivolumab` with accession `GSE289583;SRP456789`) — both must be attempted, both recorded.
- GEO accession with non-standard series prefix (very short GSE IDs, GSE9-GSE99). `_geo_series_prefix` currently truncates last 3 chars; for `GSE99` this yields `nnn` not `GSEnnn` — confirm correctness or fix.
- `.part` files left over from interrupted downloads — must be detected and resumed/cleaned (current code uses `.part` rename pattern but does not clean stale parts at startup).
- Empty `discovery_manifest` — must produce an empty ledger with the correct schema, not crash.
- NCBI FTP rate-limit / 503 — must be a typed `error_class=http_5xx`, not a Python exception bubbled up.
- A cohort listed twice in the manifest — must deduplicate or fail explicitly; current code re-downloads.
- **Query**: An endpoint returns a dataset whose `omics_type` is not in the aim's `include.assay` list — must be recorded with `triage_status=out_of_scope`, not silently dropped.
- **Query**: NCBI EUtils rate-limits (≤3 req/s without API key, ≤10 req/s with one) — adapter must respect the limit; treat 429 as `http_5xx`.
- **Query**: An endpoint is unreachable for an entire run — the candidates file still emits with `endpoint_status=unreachable` rows recording which endpoints were skipped, never crashes.
- **Query**: The same study has dataset records in multiple endpoints (GEO + ArrayExpress + OmicsDI) — must dedup by cross-walking accessions before scoring; the canonical accession wins.
- **Promotion**: An approved candidate's accession already appears in `discovery_manifest.tsv` (race: candidate generated before manifest was updated) — promotion must refuse and log, not silently re-add.

## Requirements

### Functional Requirements

- **FR-001**: A Python module `src/pipeline/modules/_00_retrieval/` MUST contain the implementation of `retrieval_run`, `retrieval_geo_full`, and all GEO/SRA download helpers currently in `cli.py` L583–L1500.
- **FR-002**: The CLI commands `retrieval run`, `retrieval geo-full`, and `retrieval geo-manifest` MUST be preserved as user-facing entry points and MUST dispatch to the module functions.
- **FR-003**: `retrieval_ledger.tsv` schema MUST remain byte-identical to the committed one (column names and order frozen in `research.md`); downstream stages depend on it.
- **FR-004**: All downloads MUST be idempotent: a present file with size > 0 is treated as `already_present` without a new HTTP request.
- **FR-005**: Failure modes MUST be classified into a fixed vocabulary: `http_404`, `http_5xx`, `http_other`, `network_timeout`, `empty_response`, `parse_error`, `manifest_error`.
- **FR-006**: A `--dry-run` flag MUST list what would be downloaded without making HTTP calls.
- **FR-007**: A retrieval reproducibility bundle (`commands.sh`, `environment.yml` snapshot, `checksums.sha256` over the ledger and downloaded files) MUST be emitted into the run's `reproducibility/` directory.
- **FR-008**: Unit tests MUST cover: GEO accession parsing, series prefix derivation, idempotency, failure classification, dry-run, empty manifest, duplicate cohort. Integration test MUST exercise `retrieval run` against a mocked NCBI FTP server fixture and produce a ledger identical to a committed golden file.
- **FR-009**: `cli.py` Stage 00 surface MUST shrink by ≥ 800 lines after extraction (verified by `wc -l` before/after).
- **FR-010**: A runbook MUST exist at `docs/runbooks/stage_00_retrieval.md` covering: invocation, expected outputs, failure triage, recovery from partial download.
- **FR-011**: A `retrieval query` subcommand MUST emit `discovery_candidates.tsv` from a YAML aim-spec; it MUST NOT modify `discovery_manifest.tsv`.
- **FR-012**: The aim-spec MUST live at `inputs/discovery/study_aim_query.yaml`, be schema-validated on load, and support: `include` (organism, assay, sample_source, treatment_class, treatment_agents, timing, outcome_signal, cancer_types), `exclude` (assay, sample_source, study_design), `filters` (min_year, min_samples), `endpoints` (list), `scoring` (required_rules, weights).
- **FR-013**: At minimum five endpoints MUST be supported, each behind an `Endpoint` adapter implementing a common protocol: NCBI GEO (`esearch -db gds`), NCBI SRA (`esearch -db sra`), EBI ArrayExpress / BioStudies (REST), EBI ENA (portal API), and OmicsDI (`https://www.omicsdi.org/ws/`). recount3 metadata is supported as a sixth endpoint via its published metadata TSVs.
- **FR-014**: Output `discovery_candidates.tsv` MUST carry per-row: `query_run_id`, `endpoint`, `endpoint_uid`, `canonical_accession`, `title`, `summary`, `pmid`, `omics_type`, `n_samples_estimated`, `cancer_type_inferred`, `treatment_agents_inferred`, `timing_inferred`, `match_score`, `matched_rules[]`, `triage_status ∈ {new, already_in_manifest, already_excluded, out_of_scope, multi_omics_for_later, needs_review}`.
- **FR-015**: Cross-endpoint deduplication MUST happen before scoring: records sharing an accession or referencing the same PMID are collapsed to a single candidate with `endpoint_seen[]` listing every source.
- **FR-016**: A `retrieval promote-candidates` subcommand MUST take a reviewed candidates file and an `--approved <ids.tsv>` list and append only approved rows to `discovery_manifest.tsv`. It MUST write a `manifest_promotion_log.tsv` audit trail (`query_run_id`, `cohort_id`, `accession`, `approving_user`, `promoted_at`, `source_candidates_file`). It MUST refuse to promote candidates whose accession already exists in the manifest.
- **FR-017**: Query runs MUST be reproducible: a query reproducibility bundle (`rendered_queries.json` per endpoint, `commands.sh`, optional cached responses for replay, `checksums.sha256`) is emitted into `<out>/reproducibility/`. Tests MUST use recorded HTTP fixtures, never live API.

### Key Entities

- **Discovery manifest** (input): TSV with `cohort_id`, `accession` columns. Accessions are semicolon- or comma-separated tokens.
- **Retrieval ledger** (output): TSV with frozen schema (see `research.md` § I/O Contracts). One row per cohort.
- **Cohort download directory**: `<out>/downloads/<cohort_id>/` containing `<GSE>_family.soft.gz`, `<GSE>/matrix/*.txt.gz`, `<GSE>/suppl/*`, `<SRA>_runinfo.csv`.
- **Reproducibility bundle**: `<out>/reproducibility/` with `commands.sh`, `environment.yml`, `checksums.sha256`.
- **Aim spec** (query input): `inputs/discovery/study_aim_query.yaml`. Versioned filter spec encoding the study aim; schema in `research.md` § 2.6.
- **Discovery candidates** (query output): TSV with frozen schema (see `research.md` § 2.7). One row per (deduplicated) candidate cohort.
- **Manifest promotion log** (promote output): TSV audit trail at `inputs/discovery/manifest_promotion_log.tsv`. Append-only.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All FR-001 through FR-010 acceptance scenarios pass automated tests.
- **SC-002**: `cli.py` Stage 00 line count drops by ≥ 800 lines (target 900+).
- **SC-003**: Re-running Stage 00 against the discovery manifest from `results/full_pipeline_20260508_204646` produces a ledger that diffs only on `retrieval_timestamp` (`diff <(cut -f1-10,12 old) <(cut -f1-10,12 new)` is empty).
- **SC-004**: Full pipeline run (all 16 stages) executes end-to-end on the 22 PRE_RESPONSE cohorts after the refactor with no behavioral regression in downstream stages.
- **SC-005**: Test count grows by ≥ 8 (one per FR-008 case).
- **SC-006**: Stage 00 runbook (`docs/runbooks/stage_00_retrieval.md`) exists and walks an examiner through a re-run in < 10 minutes.
- **SC-007**: `retrieval query` runs end-to-end against the 5+ configured endpoints using recorded fixtures in CI; mean per-endpoint adapter latency is logged.
- **SC-008**: For a known-good aim-spec, the candidates file contains every committed-as-PRE_RESPONSE cohort with `triage_status=already_in_manifest` — i.e. the query rediscovers what we already have (sanity check).
- **SC-009**: Promotion is reversible: every appended row in `discovery_manifest.tsv` has a corresponding row in `manifest_promotion_log.tsv` enabling exact reverse-out.
- **SC-010**: Multi-omics candidates (e.g. methylation datasets surfaced via OmicsDI) accumulate in the candidates file with `triage_status=multi_omics_for_later` — preserved for spec_008+ methylation work, never promoted to the RNA-seq manifest.

## Out Of Scope

- Refactoring `cmd_intake_*` commands (those are Stage 01, handled by Spec 010).
- Switching the downloader from `urllib` to `httpx`/`requests` (out-of-scope unless needed for FR-005).
- Adding new accession types beyond GSE/GSM/GPL/SRP/SRX/SRR/PRJ.
- Scientific-validity work on what is downloaded vs. what should be (deferred per user decision).
- Controlled-access endpoints (dbGaP, EGA) — query only returns open metadata; downloads handled via separate access agreements out of pipeline scope.
- Auto-curation of candidate metadata. Triage stays manual; the query function generates candidates, it does not decide them.
- Continuous / scheduled querying. The query runs are user-invoked; cron/scheduler integration is a future spec if needed.
- Downloading data for multi-omics candidates (`triage_status=multi_omics_for_later`) — they are listed and preserved, not retrieved.
