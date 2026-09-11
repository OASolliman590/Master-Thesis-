# Tasks: Spec 009 — Stage 00 Retrieval Hardening

Tasks are grouped by milestone (`plan.md` § Milestones). Each task is independently testable and traceable to one or more FRs in `spec.md`.

## Phase 0: Spec Kit Setup (M1)

- [x] T001 Create `specs/009-stage-00-retrieval-hardening/` directory with the six standard files (spec, plan, research, benchmarks, tasks, quickstart). _(this task)_
- [x] T002 Measure and fill baseline values in `benchmarks.md`. Cohort counts/status/bytes filled (47 reconciled, 39 downloaded, 8 missing all-SRA, 811 MB + 728 MB on T7, cli.py 10,515 lines, 1 existing test). Wall time / RSS DEFERRED to M7 actual re-run to avoid ~1.5 GB redownload cost. **Baseline source corrected**: T7 reconciled manifest, not `full_pipeline_*/retrieval/` (that path does not exist).
- [x] T003 Commit spec-kit files. Status line in `spec.md` moves Draft → Active. _Committed 4e98cf6 (2026-05-28)._

## Phase 1: Tests-First (M2) — FR-008 driver

- [x] T004 Add `tests/unit/test_stage_00_accession_parsing.py` — covers `_extract_geo_accession_from_cohort_id`, `_geo_series_prefix`, including GSE < 1000 edge case. _FR-008, edge case 2._
- [x] T005 Add `tests/unit/test_stage_00_idempotency.py` — second invocation against fully populated downloads makes zero HTTP calls (mock `urllib.request.urlopen` and assert call count). _FR-004._
- [x] T006 Add `tests/unit/test_stage_00_failure_taxonomy.py` — parametrized over each `ErrorClass`; each scenario constructs a mocked NCBI response and asserts the resulting `retrieval_note` parses into the expected `(accession, file_kind, error_class)` tuple. _FR-005._
- [x] T007 Add `tests/unit/test_stage_00_dry_run.py` — `--dry-run` lists planned URLs and does not call `urlopen`. _FR-006._
- [x] T008 Add `tests/unit/test_stage_00_empty_manifest.py` — empty manifest produces empty ledger with correct schema, no crash. _FR-008, edge case 4._
- [x] T009 Add `tests/unit/test_stage_00_duplicate_cohort.py` — duplicate cohort_id in manifest is rejected with `manifest_error`, not silently re-downloaded. _FR-005, edge case 6._
- [x] T010 Add `tests/unit/test_stage_00_stale_partfiles.py` — pre-existing `.part` files are cleaned at startup. _FR-004, edge case 3._
- [x] T011 Add `tests/integration/test_stage_00_golden_ledger.py` — uses a small committed mock-NCBI fixture; asserts produced ledger == golden ledger (modulo timestamp). _FR-001, FR-003._
- [x] T012 Commit T004–T011 as failing tests. CI must show 8 expected failures, 1 pass (existing). _Committed 3f082ae (2026-05-28). Actual: 23 failures (parametrization), 1 pass (test_retrieval_geo_manifest)._

## Phase 2: Extract Module (M3) — FR-001, FR-002, FR-009

- [ ] T013 Create `src/pipeline/modules/00_retrieval/` package skeleton (`__init__.py`, `ledger.py`, `geo.py`, `sra.py`, `http.py`, `soft_parser.py`, `errors.py`).
- [ ] T014 Move `_download_url`, `_download_url_if_missing`, `_fetch_html_links`, `_safe_remote_filename` from `cli.py` (L623–L663) into `00_retrieval/http.py`. Update `cli.py` to import.
- [ ] T015 Move `_geo_series_prefix`, `_download_geo_family_soft`, `_download_geo_series_matrix`, `_download_geo_supplementary`, `_extract_geo_accession_from_cohort_id`, `_find_geo_soft_file` (L583–L752) into `00_retrieval/geo.py`.
- [ ] T016 Move `_download_runinfo` (L754–L766) into `00_retrieval/sra.py`.
- [ ] T017 Move `_parse_geo_soft_sample_records`, `_parse_geo_soft_samples`, `_sample_record_metadata_text` (L769–L868) into `00_retrieval/soft_parser.py`. Verify Stage 01/02 imports still resolve.
- [ ] T018 Move the body of `cmd_retrieval_run` (L1306–L1389) into `00_retrieval.__init__.retrieval_run(...)`. CLI handler becomes a thin dispatcher.
- [ ] T019 Move the body of `cmd_retrieval_geo_full` (L1392–L1499) into `00_retrieval.__init__.retrieval_geo_full(...)`. CLI handler becomes a thin dispatcher.
- [ ] T020 Move the body of `cmd_retrieval_geo_manifest` (L1538–end) into `00_retrieval.__init__.retrieval_geo_manifest(...)`. CLI handler becomes a thin dispatcher.
- [ ] T021 Save pre-extract copy of `cli.py` retrieval section to `specs/009-stage-00-retrieval-hardening/archive/cli_pre_extract.py` (rollback aid per `plan.md` § Rollback).
- [ ] T022 Run full test suite. All pre-existing tests must pass. `wc -l src/pipeline/cli.py` must drop by ≥ 800.

## Phase 3: Failure Taxonomy (M4) — FR-005

- [ ] T023 Define `ErrorClass` enum in `00_retrieval/errors.py` per `research.md` § 2.5.
- [ ] T024 Add `classify_http_exception(exc) -> ErrorClass` and `classify_response(body, expect) -> ErrorClass | None`.
- [ ] T025 Update `_download_url` and all helpers to return `(ok: bool, err: ErrorClass | "", detail: str)` instead of string `err`.
- [ ] T026 Update `retrieval_run` / `retrieval_geo_full` to format `retrieval_note` as `<accession>:<file_kind>:<error_class>[:<detail>]; ...`.
- [ ] T027 Verify T006 failure-taxonomy tests now pass.
- [ ] T028 Verify the M7 ledger diff against the 2026-05-08 ledger: status column unchanged, note column structured-but-equivalent (manual review of any divergence).

## Phase 4: Dry-Run + Idempotency Hardening (M4 cont.) — FR-004, FR-006

- [ ] T029 Add `--dry-run` flag to `retrieval run` and `retrieval geo-full`. In dry-run, emit a `planned_downloads.tsv` with `cohort_id, accession, file_kind, url, dest_path` columns; do not call `urlopen`.
- [ ] T030 At startup, scan `downloads/` for `*.part` files older than 1 hour; delete with a logged warning.
- [ ] T031 Verify T005, T007, T010 tests pass.

## Phase 5: Reproducibility Bundle (M5) — FR-007

- [ ] T032 Add `00_retrieval/reproducibility.py` with `emit_bundle(out_dir, commands, env_snapshot)`.
- [ ] T033 `commands.sh` captures the exact `sys.argv` used to invoke the stage, plus environment variables relevant to NCBI access (e.g. `NCBI_API_KEY` redacted).
- [ ] T034 `environment.yml` is generated from `pip freeze` (fallback) or `conda env export --no-builds` (preferred if conda is detected).
- [ ] T035 `checksums.sha256` covers `retrieval_ledger.tsv` and every file under `downloads/<cohort>/`. Use `hashlib.sha256` with 1 MB chunks.
- [ ] T036 Add `tests/unit/test_stage_00_reproducibility_bundle.py` — round-trip: emit bundle, re-run with `--no-download`, verify checksums match.

## Phase 6: Runbook & Docs (M6) — FR-010

- [ ] T037 Write `docs/runbooks/stage00_retrieval.md` covering: when to run, expected wall time, output layout, failure triage (mapping `ErrorClass` → action), recovery from partial download, how to verify the reproducibility bundle.
- [ ] T038 Update `docs/USAGE.md` Stage 00 section to reference the new module and the runbook.
- [ ] T039 Update `CHANGELOG.md` with the Spec 009 entry: extracted module, failure taxonomy, dry-run, reproducibility bundle, +8 tests.

## Phase 7: Full-Pipeline Rerun (M7) — SC-003, SC-004

- [ ] T040 Run `bash run_full_pipeline.sh` (or the equivalent invocation) end-to-end. Output goes to `results/full_pipeline_<ts>/`.
- [ ] T041 Diff the new Stage 00 ledger against `results/full_pipeline_20260508_204646/retrieval/retrieval_ledger.tsv`. Acceptance: empty diff on all columns except `retrieval_timestamp` and (allowed) structured-equivalent `retrieval_note`.
- [ ] T042 Verify downstream stages (01–15) produce outputs equivalent to the 2026-05-08 baseline (Stage 01 manifest row count, Stage 06 DE result hashes, Stage 07 meta-analysis top genes).

## Phase 8: Aim-Spec + Query Scaffold (M8) — FR-011, FR-012, FR-013 (first endpoint)

- [ ] T043 Author `inputs/discovery/study_aim_query.yaml` from `research.md` § 2.6; commit alongside the spec.
- [ ] T044 Add JSON schema at `inputs/discovery/study_aim_query.schema.json`; validate the YAML in CI.
- [ ] T045 Create `00_retrieval/query/aim_spec.py` with `AimSpec` dataclass + `load(path) -> AimSpec`; raise on schema violation.
- [ ] T046 Create `00_retrieval/query/endpoints/__init__.py` defining the `Endpoint` protocol per `research.md` § 2.9.
- [ ] T047 Implement `00_retrieval/query/endpoints/ncbi_geo.py` (first adapter): `render_query`, `execute` (with rate limiting), `parse`, `cache_key`. Use `NCBI_API_KEY` env var when present.
- [ ] T048 Add `tests/unit/test_query_aim_spec.py` — schema validation, synonym expansion.
- [ ] T049 Add `tests/integration/test_query_ncbi_geo_fixture.py` — recorded EUtils fixture round-trip; assert candidates output matches a golden file.

## Phase 9: Remaining Endpoint Adapters (M9) — FR-013

- [ ] T050 Implement `00_retrieval/query/endpoints/ncbi_sra.py`. Fixture test.
- [ ] T051 Implement `00_retrieval/query/endpoints/arrayexpress.py` (BioStudies REST). Fixture test.
- [ ] T052 Implement `00_retrieval/query/endpoints/ena.py` (ENA portal API). Fixture test.
- [ ] T053 Implement `00_retrieval/query/endpoints/recount3.py` (static metadata filter; no live API). Fixture is a small copy of the recount3 metadata CSV.
- [ ] T054 Implement `00_retrieval/query/endpoints/omicsdi.py` (`https://www.omicsdi.org/ws/`). Fixture covering at least one multi-omics record (`omics_type=methylation`).
- [ ] T055 Add `tests/unit/test_query_rate_limit_handling.py` — every adapter backs off on 429/5xx with exponential delay; no retry tighter than 200ms.

## Phase 10: Dedup, Scoring, Triage (M10) — FR-014, FR-015

- [ ] T056 Implement `00_retrieval/query/candidates.py`: `CandidateRecord` dataclass, scoring engine (per `aim_spec.scoring.weights`), `required_rules` enforcement.
- [ ] T057 Implement cross-endpoint dedup: collapse records sharing accession or PMID; populate `endpoint_seen[]`.
- [ ] T058 Implement manifest cross-check: load `inputs/discovery/discovery_manifest.tsv`, set `triage_status=already_in_manifest` for candidates whose accession matches.
- [ ] T059 Implement out-of-scope and multi-omics classification: assay not in `aim.include.assay` and not in `aim.exclude.assay` → `out_of_scope`; multi-omics non-RNA-seq records → `multi_omics_for_later`.
- [ ] T060 Wire `query_run(aim_path, out_dir)` in `00_retrieval/query/__init__.py`. Emit `discovery_candidates.tsv` with frozen schema (`research.md` § 2.7).
- [ ] T061 Emit query reproducibility bundle into `<out>/reproducibility/`: `rendered_queries.json`, `commands.sh`, `checksums.sha256`, optional `responses_cache/`.
- [ ] T062 Wire `retrieval query` CLI subcommand: `--aim-spec`, `--out`, `--endpoints` (override aim-spec list), `--no-network` (replay cache only).
- [ ] T063 Add `tests/integration/test_query_end_to_end.py` — all 6 endpoints with fixtures; assert SC-007, SC-008, SC-010.

## Phase 11: Promotion + Audit (M11) — FR-016, SC-009

- [ ] T064 Implement `00_retrieval/query/promotion.py`: `promote_candidates(candidates_path, approved_ids_path, manifest_path, log_path, user)`; refuses if accession already in manifest.
- [ ] T065 Wire `retrieval promote-candidates` CLI subcommand: `--candidates`, `--approved`, `--manifest`, `--log`.
- [ ] T066 Emit `manifest_promotion_log.tsv` rows per `research.md` § 2.8.
- [ ] T067 Add `tests/unit/test_promotion_idempotency.py` — promoting the same approved row twice raises; log has one entry only.
- [ ] T068 Add `tests/integration/test_promotion_reverse_out.py` — given a log, derive the exact rows to remove from manifest to revert a promotion.
- [ ] T069 Document promotion workflow in `docs/runbooks/stage_00_query.md` (separate runbook for the query/promotion path).

## Phase 12: Sign-Off (M12) — SC-001..SC-010

- [ ] T070 Update `spec.md` Status → "Complete". Record measured values in `benchmarks.md` against the budget (including query metrics).
- [ ] T071 Tag the commit `spec_009_complete`.
- [ ] T072 Open Spec 010 (Stage 01 dataset intake hardening). Carry forward any Stage 00 lessons (e.g. failure-taxonomy pattern, reproducibility bundle pattern, endpoint-adapter pattern).

---

## Task → FR traceability

| FR | Tasks |
|---|---|
| FR-001 | T013–T020 |
| FR-002 | T018–T020 |
| FR-003 | T011, T041 |
| FR-004 | T005, T010, T030 |
| FR-005 | T006, T023–T028 |
| FR-006 | T007, T029 |
| FR-007 | T032–T036 |
| FR-008 | T004–T012 |
| FR-009 | T022, T041 |
| FR-010 | T037, T038 |
| FR-011 | T060, T062 |
| FR-012 | T043–T045, T048 |
| FR-013 | T046–T047, T050–T055 |
| FR-014 | T056, T060, T063 |
| FR-015 | T057–T059, T063 |
| FR-016 | T064–T068 |
| FR-017 | T049, T055, T061, T063 |
