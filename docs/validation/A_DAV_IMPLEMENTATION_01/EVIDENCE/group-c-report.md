# Group C — DAV-T10–T14 synthetic software implementation

Implemented only `tools/a_dav/matrices.py`, `release.py`, `reporting.py` and `tests/a_dav_implementation/test_group_c.py`. No commits, network, installs, remote execution, source-object reads, frozen-file edits, subagents or full-suite runs. Every value in the fixtures is invented. Actual source/reviewer/environment/statistical gates and biological analysis remain NOT_RUN. All four actual readiness/admission/release/analysis flags stay false.

## Public behavior

- Baseline verifies synthetic admission, registries, endpoints, timing and assays; checks study eligibility and source membership in schema-valid BLOCKED_UNKNOWN admission drafts with no approved branches. Outcome-blind explicit specimen/assay ranks select one candidate. Ties block and retain candidate audit. Source/canonical exclusions, missing assays and repeats remain audited. Canonical rows remain untouched. ORR and optional DCR come from same-patient/same-episode frozen endpoint views.
- Longitudinal preserves every specimen/assay timepoint, including no-assay rows, and one pair denominator row for every patient/window. Window candidates and exclusions remain audited. Missing follow-up is explicit. Unknown/bounded timing is retained in long rows but conservatively excluded from exact-day pairing; numeric raw source days never manufacture EXACT precision. Different lesions/platforms/measurement scales, progression and regimen-change categories never gain silent qualification. No measurement bridge or different-lesion qualification is invented.
- Split requires immutable prespecified assignments, source completeness and sealed admission/overlap/exposure. Typed transitive possible/unknown overlap and patient/specimen/assay/study/family/trial ancestry protect permanent and nested roles. Older lineage exposure cannot be reset by changing lineage names. Synthetic final-test simulation additionally requires explicit metadata-only review evidence; actual untouched certification remains false.
- Public reporting exports only its `audit` entry's `public_report` object: fixed synthetic status, fixed stage statuses, receipt/config hashes, NOT_RUN limitations, false flags, and optionally a suppressed patient count. The full stage result retains canonical records as required and is not the public artifact. Caller payloads, sidecars and unknown export config fail. Minimum small-cell denominator is explicit, at least 2. Prat summaries are count-free.
- Freeze binds canonical exact packet/config/inputs, every required upstream and descendant code/core/schema receipt, exact output bytes, commands and declared environment. Fixed four-file publication uses native atomic no-replace directory rename (`renamex_np(RENAME_EXCL)` on macOS, `renameat2(RENAME_NOREPLACE)` on Linux). Fresh/resume, changed inputs, extra sidecars, hash tampering, collision, missing upstream closure, symlink and traversal paths are checked. Bundle paths are local synthetic test directories only. Release draft remains SYNTHETIC/READY_FOR_REVIEW with data/statistical/protected gates NOT_RUN and no actual admissions. `verify_bundle` raises fixed `DavError` on invalid artifacts.

## Integration configuration

All stage configs must exist before any dependency is built, because core seals the entire config dictionary. APIs accept `schemas=SchemaStore`; freeze additionally takes destination `Path`.

`baseline`: `{selection_basis:'PRESPECIFIED_METADATA', specimen_rank:{specimen_uid: nonnegative_integer}, assay_rank:{assay_uid: nonnegative_integer}, assay_suitability:'BASELINE_DE', build_utc:fixed_string, split_role:'DEVELOPMENT', prior_exposure_status:'METADATA_ONLY', index_episode_by_patient?:{patient_uid:episode_id}}`. Ranks must cover every eligible candidate; IDs never break tied ranks. If multiple episodes exist, explicitly name the index episode. Patient `cancer` must be supplied.

`longitudinal`: same rank/basis/build/index config, `assay_suitability:'LONGITUDINAL'`, plus nonempty `windows:[{window_id,contrast_id,category,lower_day,upper_day}]` with exactly those keys. Categories: EARLY_ON_TREATMENT, LATE_ON_TREATMENT, RESPONSE_ASSESSMENT, MAXIMAL_RESPONSE, PROGRESSION, POST_TREATMENT, POST_DISCONTINUATION. Windows do not silently equate these states.

`split`: `{selection_basis:'PRESPECIFIED_METADATA', performance_observed:false, version:nonempty_string, analysis_lineage_id:nonempty_string, required_source_ids:[source_object_id], assignments:[exact frozen SPLIT rows with SYNTHETIC_ONLY classification]}`. Every patient has one assignment/version. Only DEVELOPMENT may have nested assignments; each evaluation/fold has one role per patient and related component. For FINAL_TEST simulation also provide `final_test_review:{decision_id,analysis_lineage_id,review_complete:true,metadata_only_permitted:true,covered_patient_uids:[...],source_locators:[...]}` matching the frozen row exposure decision. Exposure must have metadata-only same-lineage audit support and no related unknown/associated or older lineage use.

`public_report`: `{minimum_cell_count:integer>=2, include_counts:boolean}`. No additional config except a `payload` key, which always rejects. Report dependencies: admission, baseline, longitudinal, split. Safe export: `next(a['public_report'] for a in result['audit'] if 'public_report' in a)`; do not export full result records.

`freeze`: `{commands:[nonempty_string], environment:{declared_json_values}, required_source_ids:[source_object_id], source_universe_version:nonempty_string}`. Required dependencies: public_report, admission, baseline, longitudinal, split, registries, endpoints, timing, assays, overlap, exposure. Every supplied additional dependency is verified too. Unsupported frozen release-contract branches fail schema validation. A_BASELINE_BIO and A1_PAIRED_CHANGE fit the frozen release schema. Files are exactly manifest.json, packet.json, release_draft.json, result.json. No caller file names or arbitrary output sidecars.

## Upstream and output audit contracts

Admission must include `{kind:'admission_eligibility',study_id,branch_id,eligibility:'SYNTHETIC_READY',...}` per patient study and canonical `cohort_admission_receipt` synthetic drafts containing supported source object IDs.

Timing must include one assertion per specimen: `{check:'TIMING_ASSERTION',specimen_uid,treatment_episode_id,canonical_category,precision,relative_day,interval,...}`. Actual Group A API produces this shape. Exact-day positive pair fixtures need EXACT assertions for pre and follow-up.

Overlap uses `{kind:'overlap_component',nodes:[{node_type,node_id}],protection:'RELATED'|'POTENTIAL_OR_UNKNOWN',...}`. Exposure uses `{kind:'exposure_decision',subject_type,subject_id,analysis_lineage_id,state:'METADATA_ONLY'|'RESPONSE_ASSOCIATED'|'UNKNOWN',...}`.

Matrix audit kinds: CANDIDATE, BASELINE_SELECTION, WINDOW_CANDIDATE, PAIR_SELECTION. Split audit: SPLIT_COMPONENT with patient_count, membership_sha256, actual_untouched_certified:false. Reporting audit: public_report and optional prat_summary. Freeze audit: SYNTHETIC_FREEZE with release-draft/commands/environment hashes.

## Verification and RED/GREEN evidence

Common pytest command prefix: `PYTHONDONTWRITEBYTECODE=1 /private/tmp/thesis-adav05-20261020/bin/python -B -m pytest -q -p no:cacheprovider`.

| Log | Test suffix | Exit | Observed result |
|---|---|---:|---|
| group-c-red-01.log | tests/a_dav_implementation/test_group_c.py | 1 | 5 failed: absent public modules |
| group-c-green-01.log | same | 0 | 5 passed |
| group-c-red-02-path.log | tests/a_dav_implementation/test_group_c.py::test_freeze_refuses_symlink_and_traversal_destination | 1 | 1 failed: unsafe path incorrectly blocked only on dependency |
| group-c-green-02-path.log | same | 0 | 1 passed |
| group-c-red-02-prerequisite.log | tests/a_dav_implementation/test_group_c.py | 1 | 16 failed / 5 passed; upstream files not yet available; prerequisite evidence only |
| group-c-red-03-features.log | tests/a_dav_implementation/test_group_c.py -k 'baseline or longitudinal or split or reporting or fresh' | 1 | 15 failed / 4 passed / 2 deselected |
| group-c-green-03-attempt.log | tests/a_dav_implementation/test_group_c.py | 1 | 5 failed / 16 passed; fixture wrongly filtered stage/module aliases during reseal |
| group-c-green-03.log | same | 0 | 21 passed |
| group-c-red-04.log | tests/a_dav_implementation/test_group_c.py -k 'unknown_timing or invariant or stale_dependency or extra_bundle or transitive' | 1 | 2 failed / 3 passed / 21 deselected: uncertain timing wrongly paired; reseal fixture included old dependency chain |
| group-c-green-04.log | tests/a_dav_implementation/test_group_c.py | 0 | 26 passed |
| group-c-red-05.log | tests/a_dav_implementation/test_group_c.py -k 'final_split_simulation or uncovered_prior or tied_candidates' | 1 | 2 failed / 1 passed / 26 deselected: uncovered older exposure and lost tie audit |
| group-c-green-05.log | tests/a_dav_implementation/test_group_c.py | 0 | 29 passed |
| group-c-red-06.log | tests/a_dav_implementation/test_group_c.py -k 'unadmitted_assay or canonically_excluded' | 1 | 2 failed / 29 deselected |
| group-c-green-06.log | tests/a_dav_implementation/test_group_c.py | 0 | 31 passed |
| group-c-red-07.log | tests/a_dav_implementation/test_group_c.py::test_freeze_requires_upstream_code_closure | 1 | 1 failed: omitted assays still published |
| group-c-green-final.log | tests/a_dav_implementation/test_group_c.py | 0 | 32 passed |

Strict typecheck command: `UV_CACHE_DIR=/private/tmp/dav-uv-cache UV_TOOL_DIR=/private/tmp/dav-uv-tools uv tool run --offline --from mypy==1.18.2 mypy --strict --explicit-package-bases --ignore-missing-imports --follow-imports=silent tools/a_dav/matrices.py tools/a_dav/release.py tools/a_dav/reporting.py`. Exit 0, `Success: no issues found in 3 source files`; logs group-c-mypy-01.log, group-c-mypy-02.log and group-c-mypy-final.log. An initial exploratory mypy run without explicit-package-bases found 8 annotation/name errors; fixed before these passing logged runs.

Tests are focused public API synthetic tests. Their upstream unit fixtures use `core.finish` only after actual upstream module files existed; they are invented sealed evidence, not connected acceptance. Parent owns actual connected stage API tests, independent review, full suite and local commit. Parent must rerun affected checks after any integrated code/core edits.

## File SHA-256 at handoff

- matrices.py: `6088325e6779e34d594daa205c0054ed4e0aed9458721c873e7bea90cc8f3875`
- release.py: `b003325edff179577f40613a487b12b5b94f1f5550ff081cdd86d912e44c6dc6`
- reporting.py: `fbc3040578ae0bb784a0d75be6a2f2701a3376992f64c8c7709f9d3e90f064f8`
- test_group_c.py: `4f428c29634d62ac876a3e8494a628d7e210033e2ebd976166a3e3c393adf613`

## Independent Spec review fix round 1 (S1–S4, S6–S7)

This section supersedes the original baseline/longitudinal denominator, coverage, endpoint and public-report behavior above. `release.py` is unchanged in this review fix wave.

- **S1:** Every matrix candidate now consumes the matching assay's sealed frozen coverage row from the assays dependency. Study, branch, source object, unit and annotation must agree with the assay. The explicitly configured coverage suitability property must PASS; FAIL excludes and UNKNOWN/missing blocks acceptance. Supplied `branch_suitability` is a necessary label, not sufficient evidence. Required new own-stage `coverage_suitability` selects `de_suitability`, `scoring_suitability`, `final_test_suitability` or `measurement_suitability`. Named BASELINE_DE, BASELINE_SCORING and FINAL_TEST lanes must use their corresponding property. The broader LONGITUDINAL lane requires explicit selection, with no implicit scientific default.
- **S2:** Required new own-stage `endpoint_policy` is `{required:boolean,endpoint_class:explicit_frozen_class_or_null,discrepancy_policy:'SEALED_PREFERRED_OUTCOME'}`. Baseline requires a declared endpoint; longitudinal supports explicitly endpoint-optional branches (`required:false,endpoint_class:null`) and emits response_group NOT_APPLICABLE. Defined source binary uses the sealed OTHER/SOURCE_BINARY endpoint view produced by Group A's explicit definition mapping, while baseline ORR and DCR remain null. Undefined SOURCE_BINARY_UNKNOWN remains unevaluable. No source binary becomes ORR.
- **S3:** Multiple retained endpoint assertions are selected only through same-patient/same-episode sealed `DISCREPANCY_RETAINED` audit with preferred_outcome_id and all_outcome_ids support. All input assertions remain unchanged. DCR, where applicable, uses the same adjudicated outcome process.
- **S4:** Missing pre or follow-up never creates a null-sided pair. Every patient/window emits private `PAIR_DENOMINATOR` audit with patient_uid, treatment_episode_id, window_id, contrast_id, reason, inclusion_status and selected side IDs. This is the denominator authority. All actual timepoint rows remain preserved; pair rows contain two actual sides. Parent updated workflow checks/connected missing-follow-up expectations to consume this audit.
- **S6:** Safe public export now includes fixed allowlisted gate_table and limitation_table, plus count_table under the explicit existing small-cell policy. Gate table distinguishes synthetic software readiness from NOT_RUN source review, authenticated independent review, target environment and statistical release. Fixed limitations retain these four actual evidence gaps. Public fields still contain no IDs, paths, locators or arbitrary caller text.
- **S7:** Timing is keyed by (specimen_uid,treatment_episode_id), not specimen alone. Every timing assertion must match the exact binding_id and role. Candidates select the requested episode's evidence and category. Long views preserve every explicit specimen/episode/assay context; an alternate episode's category is not overwritten with the specimen's global canonical category. Duplicate same-context assertions and binding/ownership contradictions fail.
- **Prat narrow privacy follow-up:** A Prat-linked general report verifies `dependency(packet,'prat_review',store)`, including full config/canonical lineage. It emits neither patient_count nor count_table even when include_counts is requested; its fixed `PRAT_COUNT_FREE_EXPORT/ENFORCED` limitation documents the narrower rule. The Prat summary is also count-free. Stale Prat config fails.

### Review-round tests and typechecking

Pytest prefix remains `PYTHONDONTWRITEBYTECODE=1 /private/tmp/thesis-adav05-20261020/bin/python -B -m pytest -q -p no:cacheprovider`.

| Log | Suffix | Exit | Actual result |
|---|---|---:|---|
| group-c-review-red-01.log | tests/a_dav_implementation/test_group_c.py -k 'computed_coverage or source_defined or endpoint_optional or adjudicated_endpoint or missing_pre_or_followup or gate_and_limitation or multiple_evidenced' | 1 | 7 failed / 32 deselected, corresponding to S1–S4/S6/S7 |
| group-c-review-green-01-attempt.log | tests/a_dav_implementation/test_group_c.py | 0 | 39 passed in 17.12s |
| group-c-review-red-02.log | tests/a_dav_implementation/test_group_c.py -k prat_bound | 1 | 2 failed / 39 deselected: leaked general counts and stale Prat config accepted |
| group-c-review-green-final.log | tests/a_dav_implementation/test_group_c.py | 1 | 2 failed / 39 passed; both failures were test privacy substring heuristics matching `001` inside permitted SHA-256 values, not source-value export. Corrected checks compare exact JSON string values. No production output was changed for these false positives. |
| group-c-review-green-final-corrected.log | tests/a_dav_implementation/test_group_c.py | 0 | 41 passed |

Strict command unchanged: `UV_CACHE_DIR=/private/tmp/dav-uv-cache UV_TOOL_DIR=/private/tmp/dav-uv-tools uv tool run --offline --from mypy==1.18.2 mypy --strict --explicit-package-bases --ignore-missing-imports --follow-imports=silent tools/a_dav/matrices.py tools/a_dav/release.py tools/a_dav/reporting.py`. Both review-round logs `group-c-review-mypy-01.log` and `group-c-review-mypy-final.log` exit 0: `Success: no issues found in 3 source files`.

Review-round SHA-256:

- matrices.py: `2cb3a2e90a6d9fca6e9f8047fb26659d07b07106d89a08b8e9c474534e711717`
- release.py: `b003325edff179577f40613a487b12b5b94f1f5550ff081cdd86d912e44c6dc6`
- reporting.py: `d5f390ef192339f83db2c5c04d339736b28efff94e55be65b343685f79079c41`
- test_group_c.py: `f52df78dcbb7aa5f450be673fed6da4fcdf1464d7fd242b6e4683b51ed3b1fa9`

No full-suite run, real-source/object read, network, install, subagent or commit occurred in this round. Actual source admission, authenticated reviewer, target-environment and scientific/statistical acceptance remain NOT_RUN with false actual flags. Parent owns connected re-verification and independent review acceptance.
