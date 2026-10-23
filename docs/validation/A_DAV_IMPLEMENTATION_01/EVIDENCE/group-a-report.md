# Group A implementation receipt — DAV-T04–T07

Scope: invented data and synthetic software validation only. All actual analysis/admission/statistical-release/biological-execution flags stay false. No real source object, source receipt/control output, network, installation, remote, biological analysis, commit, full suite, or subagent was used by this worker. Canonical entity records and frozen specifications remain unchanged. Parent owns connected integration, complete suite, independent reviews, and commit.

## Owned changes and result

| Ticket | Public API / stage | Implemented behavior | Status |
| --- | --- | --- | --- |
| DAV-T04 | `build_registries` / `registries` | Frozen schema validation; lexical IDs and leading zeros; study-scoped aliases; duplicate canonical IDs/ambiguous aliases; study/family/patient/specimen/assay/source/episode ownership; repeated sequencing and multiple lesions retained; full source hash config attestations. | Synthetic software implemented and focused-tested; real-source/reviewer acceptance NOT_RUN. |
| DAV-T05 | `map_endpoints` / `endpoints` | Immutable raw/canonical outcomes; explicit versioned category mapping; frozen endpoint views for ORR/DCR/DCB and separate PSA/pathology/survival/source-binary lanes; NE/unknown unevaluable; prohibited conversions fail; DCB duration/censoring evidence; explicit discrepancy priority/resolution with all assertions retained. | Synthetic software implemented and focused-tested; clinical/source review and real tracer NOT_RUN. |
| DAV-T06 | `validate_timing` / `timing` | Supplied episode/binding ownership, component closure and regimen/prior-ICI assertions; exact-day and bounded-interval distinctions; source-declared episode sequence and windows; progression/regimen-change/post-discontinuation separation; no row-order inference; full specimen timing audit retained. | Synthetic software implemented and focused-tested; clinical timing source/reviewer acceptance NOT_RUN. |
| DAV-T07 | `validate_assays` / `assays` | Invented matrix/header/feature/value structure, source-object/hash/specimen ties, explicit measurement lanes and transforms, finite/missing/zero/negative/integer checks, annotation/universe collisions, library/quantifier requirements, array/methylation documentation, QC/replicates, frozen coverage views. No score or molecular calculation. | Synthetic software implemented and focused-tested; assay-domain/source review and real tracer NOT_RUN. |

Owned new files: `tools/a_dav/registries.py`, `endpoints.py`, `timing.py`, `assays.py`, and `tests/a_dav_implementation/test_group_a.py`. No commit range: these changes remain uncommitted for parent review. Source schemas keep their existing versions (canonical legacy schemas use 1.0.0 where present; treatment episode/binding and endpoint/coverage materialized rows use frozen 1.1.0). SchemaStore binds the actual frozen file hashes.

Every stage consumes the public packet and preserves all incoming canonical records, adding only stage views/audit. All four declare a fixed `REASON_CODES` frozenset and use `@stage_boundary`. Endpoints, timing and assays require `dependency(packet, "registries", schemas)`; registries has no upstream stage dependency. Every config key must already be present before sealing registries because the core binds the complete config digest.

## Integration fixtures and exact configurations

Use the invented fixture helpers in `tests/a_dav_implementation/test_group_a.py`:

```python
p = assay_config(timing_config(endpoint_config(packet())))
p["dependencies"]["registries"] = build_registries(p, schemas=SCHEMAS)
# Run downstream APIs with this same complete config and canonical records.
```

`packet()` invents one study/family/full-hash source/patient/specimen/assay/outcome/episode/exposure and three explicit bindings. The raw patient ID is the string `001`; all values are invented. The fixture source's SHA-256 is an invented attestation, not a claim about bytes retrieved by this worker. Root's actual source-object seam supplies measured hashes in connected tests.

Registries config:

```python
{"study_ids": ["s1"], "source_hashes": {"obj1": "a" * 64}}
```

Exact study and source key sets must match supplied registries. Each source must be `RETRIEVED`, `FULL_OBJECT`, nonnull SHA-256, with matching config hash; supplied source validation status may be `PASS` or `STRUCTURAL_ONLY`. The latter supports only synthetic processing after structural retrieval and never mutates the source into `PASS`. Known failures/contradictions fail; missing context blocks. Canonical identities must be supplied and verified; no IDs are generated from prefixes.

Endpoint config:

```python
{
  "version": "invented-v1",
  "category_map": {"invented-partial": "PR"},
  "classes": ["ORR", "DCR"],
  "source_priority": ["o1"]
}
```

The explicit exact raw label mapping must agree with each immutable `canonical_category`; version must agree with `mapping_rule_version`. `source_priority` lists all outcome IDs once. Per-outcome classes apply only to compatible source endpoint classes; unsupported conversions fail rather than disappearing. Every outcome needs one verified outcome episode binding. Optional `assessment_days` maps outcome ID to a numeric day.

Optional DCB config is `dcb_rule = {"unit": "days", "threshold": number >= 0, "source_locator": nonempty string, "outcomes": {outcome_id: {"source_supported_rule": True, "benefit": bool, "duration": nonnegative number, "censored": bool}}}`. Short censored observations remain unevaluable. These are explicit invented rules, with no scientific default threshold.

Discrepancies require `discrepancy_resolutions[patient_uid + ":" + episode_id] = {"preferred_outcome_id": highest_priority_id, "source_locator": nonempty string}`. Both source assertions and their views remain; the preferred assertion is explicit in audit, and downstream consumers must respect that resolution rather than selecting a row arbitrarily.

Timing config:

```python
{
  "version": "invented-time-v1", "episode_order": ["e1"],
  "windows": {"invented-pre": {"category": "PRE_INDEX_BASELINE", "min_day": -5, "max_day": -1}},
  "specimens": {"sp1": {
    "treatment_episode_id": "e1", "precision": "EXACT", "relative_day": -2,
    "canonical_category": "PRE_INDEX_BASELINE", "window_id": "invented-pre",
    "source_locator": "invented-row", "inferred_from_order": False
  }}
}
```

No window is invented by the implementation. `BOUNDED_INTERVAL` uses `interval: [lower, upper]` and retains a null point estimate. Source-category evidence can use `category_only_allowed: True`; unknown precision/category still blocks. Optional `progression_days` and `regimen_change_days` map episode IDs to explicit relative days. Complete source-provided episode components and exactly one binding for every subject are checked. Numeric component dates must lie within episode bounds; delayed components are legitimate. All treatment exposures require verified certainty, known prior-ICI, sequence and line assertions. These assertions do not authenticate a real source/reviewer.

Assay config:

```python
{
  "required_features": ["F1", "F2"],
  "matrices": [{
    "source_object_id": "obj1", "source_sha256": "a" * 64,
    "headers": ["sample-001"], "features": ["F1", "F2"], "values": [[0], [2]],
    "unit": "counts", "transform": "NONE", "lane": "COUNTS",
    "platform": "INVENTED", "modality": "RNA", "annotation": "invented-v1",
    "feature_universe": ["F1", "F2"], "feature_map": {"F1": "F1", "F2": "F2"},
    "feature_scope": "COMPLETE", "normalization": "NONE",
    "source_locator": "invented-row", "delimiter": "TAB", "encoding": "UTF-8",
    "replicate_policy": "PRESERVE", "missingness_policy": "PRESERVE",
    "library_properties": {"sample-001": {"library_size": 2, "source_locator": "invented-library"}}
  }]
}
```

Accepted lanes/units: `COUNTS` (`counts`, `estimated_counts`), `CONTINUOUS` (`TPM`, `FPKM`, `log_expression`), `ARRAY` (`array_intensity`, `log_array_intensity`), `METHYLATION_BETA` (`beta`), `METHYLATION_M` (`M`). Declared transforms are `NONE`, `LOG2`, `LN`, `LOG10`; counts must be untransformed and unnormalized. Estimated counts additionally need nonempty `quantifier` and `estimated_count_structure`. Array declarations need platform/annotation/preprocessing/probe_to_gene_policy/batch_structure. Methylation declarations need platform/genome_build/detection_p_provenance/probe_filter_policy/snp_policy/cross_reactive_policy/sex_chromosome_policy and methylation modality. No documented scale is overridden by magnitude heuristics, and no FPKM/TPM/count conversion occurs.

`feature_scope` is explicitly `COMPLETE` or `TARGETED`; listed feature universe must exactly match the supplied matrix. Targeted panels never acquire full-universe DE suitability. Missing matrix values remain `None`, generate missing feature coverage and block rather than becoming zero. Required absent features remain explicit. Identical repeated profiles are retained and audited. Measurement and scoring QC statuses remain separate; final-test suitability stays `UNKNOWN` because this stage does not certify independence or release.

## Output and audit contracts

- `registries`: all input records; audit `LEXICAL_IDENTITIES_PRESERVED` with `patient_alias_count`, `specimen_alias_count`.
- `endpoints`: adds frozen `records["endpoint"]`; each row carries patient/episode/outcome/endpoint IDs, raw label, category, class, mapping version, binary/evaluability, explicit assessment/duration/event/censoring/source fields and synthetic build ID. Audit `RAW_OUTCOMES_PRESERVED` (`mapping_version`, `endpoint_count`) and `DISCREPANCY_RETAINED` (`patient_uid`, `treatment_episode_id`, `preferred_outcome_id`, `all_outcome_ids`).
- `timing`: no canonical time row rewritten. Audit `TIMING_ASSERTION` (`specimen_uid`, `treatment_episode_id`, `canonical_category`, `precision`, `relative_day`, `interval`, `window_id`, `mapping_version`).
- `assays`: adds frozen `records["coverage"]` with required/present/missing/ambiguous features, study/assay/branch/source IDs, annotation/unit, measurement/scoring/DE/final-test suitability. Audit `MATRIX_COLUMN_VALIDATED` (`assay_uid`, `source_object_id`, `feature_count`, `missing_value_count`, `zero_value_count`, `feature_scope`, `replicate_status`) and optional `IDENTICAL_PROFILE_RETAINED` (`assay_uids`).

Audits and canonical records are private synthetic detail; the public summary emits only fixed enums, hashes, false flags and aggregate counts. Raw IDs/labels/locators are not exported by that summary.

## TDD and verification evidence

All pytest commands used `PYTHONDONTWRITEBYTECODE=1 /private/tmp/thesis-adav05-20261020/bin/python -B -m pytest -p no:cacheprovider -q tests/a_dav_implementation/test_group_a.py` with the selector listed below. Logs are preserved in sibling `group-a-logs/`. A log filename containing `green` is only a filename; unsuccessful intermediate runs are explicitly reported.

| Log | Selector / command | Exit | Actual result |
| --- | --- | --- | --- |
| 01-registry-red.txt | no selector | 2 | Expected missing module collection RED: 1 error. |
| 02-registry-green.txt | no selector | 1 | 1 passed, 1 failed: fixture expected original row order although core canonicalizes order. |
| 03-registry-green.txt | no selector | 0 | 2 passed after expectation compares all intact rows independent of order. |
| 04-endpoint-red.txt | `-k endpoint` | 1 | 2 expected missing-module failures, 2 deselected. |
| 05-endpoint-green.txt | `-k endpoint` | 0 | 2 passed, 2 deselected. |
| 06-timing-red.txt | `-k timing` | 1 | 2 expected missing-module failures, 4 deselected. |
| 07-timing-green.txt | `-k timing` | 0 | 2 passed, 4 deselected. |
| 08-assay-red.txt | `-k assay` | 1 | 2 expected missing-module failures, 6 deselected. |
| 09-assay-green.txt | `-k assay` | 0 | 2 passed, 6 deselected. |
| 10-mypy.txt | strict mypy, four owned modules | 0 | No issues in 4 files. |
| 11-expanded-green.txt | no selector | 0 | 32 passed. |
| 12-adversarial.txt | no selector | 1 | 71 passed, 1 fixture failure: rebuilding registry with its prior result recursively changed input receipt. |
| 13-cached-schemas.txt | no selector | 1 | Same fixture failure, 71 passed; explicit cached frozen SchemaStore removes repeated schema loading only. |
| 14-mypy.txt | strict mypy, four modules | 0 | No issues in 4 files. |
| 15-adversarial-green.txt | no selector | 0 | 72 passed after fixture removes prior registry dependency before rebuilding. |
| 16-mypy-green.txt | strict mypy with explicit package bases | 0 | No issues in 4 files. |
| 17-review-red.txt | `-k 'component_start or unknown_precision or missing_modality or library_properties'` | 1 | 4 expected behavior failures, 72 deselected. |
| 18-review-green.txt | no selector | 0 | 76 passed. |
| 19-final-green.txt | no selector | 0 | 85 passed. |
| 20-final-mypy.txt | strict mypy with explicit package bases | 0 | No issues in 4 files. |
| 21-source-assertion-red.txt | `-k 'ne_cannot or estimated_counts_require'` | 1 | 2 expected behavior failures, 85 deselected. |
| 22-final-green.txt | no selector | 0 | **87 passed in 4.26s**. |
| 23-final-mypy.txt | strict mypy with explicit package bases | 0 | **No issues found in 4 source files**. |

Exact final typecheck command:

```sh
UV_CACHE_DIR=/private/tmp/dav-uv-cache UV_TOOL_DIR=/private/tmp/dav-uv-tools uv tool run --offline --from mypy==1.18.2 mypy --strict --ignore-missing-imports --follow-imports=silent --explicit-package-bases tools/a_dav/registries.py tools/a_dav/endpoints.py tools/a_dav/timing.py tools/a_dav/assays.py
```

Earlier mypy logs 10 and 14 used the same command without `--explicit-package-bases`; both passed at that point. No compile check is mislabeled typechecking. Only this worker's owned tests ran; complete suite/integration/review remain parent-owned. Cached schemas in tests preserve exact actual frozen hash verification.

Coverage includes lexical collisions/cross-study aliases/legitimate repeats/lesions; all CR/PR/SD/PD/NE/unknown response categories; forbidden source-binary/PSA/pathology/survival-to-ORR mappings; separated survival and censoring; DCB duration and short censoring; discrepancy retention; exact/bounded/unknown and row-order timing; regimen/prior-ICI/sequence/component/episode conflicts; multiple follow-ups; all declared measurement lanes, source-doc unit conflicts, transformed counts, unknown scale, duplicate features/headers/collisions, negatives/fractions, truncated universes, missing versus zero, targeted panel suitability, QC, repeated profiles, dependency tampering and stale config. Independent literal expectations exercise public APIs rather than implementation-private helpers.

## Exact hashes and remaining limits

Complete composed invented config SHA-256: `dec7678d03b8c1e2236d156feac343de78da2b588c459adb5a5997a938531180`.

| File | SHA-256 at worker handoff |
| --- | --- |
| tools/a_dav/registries.py | `8fce15fa880d7a92876e283fea5cf7988778f398415e13d729b3204bfe60414a` |
| tools/a_dav/endpoints.py | `3943344cee914cc10512a2f567a4974013bb810f75bdc4bb2e04d5af2583f3f1` |
| tools/a_dav/timing.py | `86b0df92ce43c6a1d117095918e163d6fa6211d01ded6029285e1f943ff425fb` |
| tools/a_dav/assays.py | `c8e0376d9de869ca69ae349eb35489348db91b63cde5a6ab66fd285ec7a2682f` |
| tests/a_dav_implementation/test_group_a.py | `8fcb81d6cd416f070e0f4af56738b7c55c95ad694cfdc6a0f5742d8e4dd73163` |

These are software/synthetic assertion checks. They do not authenticate source documents, object bytes not supplied to these APIs, source mappings, clinician or assay reviewers, treatment windows, DCB scientific rules, completeness of a real matrix, or a production environment. Actual source/reviewer gates, bounded public metadata/header tracers and biological/statistical acceptance are **NOT_RUN**. Parent must review and connect all stages before any whole-workflow claim. No placeholders or real-source acceptance claims were added.

## Independent review fix wave 1 — supersedes initial timing/endpoint hashes above

Addressed Standards finding 1 in `docs/validation/A_DAV_IMPLEMENTATION_01/REVIEW_STANDARDS.md` and parent-confirmed Spec findings on legitimate specimen episode contexts and defined source-binary endpoint branches. Read frozen `RELATIONAL_INVARIANTS.md` episode-integrity rule, `ENDPOINT_ONTOLOGY.md` source-binary prohibition/branch permission, and `COHORT_ADMISSION_AND_RELEASE.md` baseline endpoint permission. No frozen specification changed.

Component chronology now parses each supplied numeric component endpoint, checks **both** endpoints against **both** known episode bounds, and enforces start <= stop. Cases 50..10, 61..60, 0..-1, -1..10 and 0..61 against episode 0..60 fail with `COLLECTION_CHRONOLOGY_CONFLICT`. Valid delayed components (1..59) still pass. Missing or unparseable component dates are retained and return `BLOCKED_UNKNOWN` / `INDEX_TREATMENT_UNRESOLVED`; unknown dates never create an included exact assertion. Known chronology contradictions are checked before that deferred missing-evidence disposition. The pre-review timing snapshot is `group-a-logs/round1-timing-before.py`, SHA-256 `86b0df92ce43c6a1d117095918e163d6fa6211d01ded6029285e1f943ff425fb`; `round1-timing.diff` records the exact change against that snapshot (`diff -u` exit 1 means differences exist).

The frozen invariant permits one physical specimen to serve end-of-prior/start-of-next contexts through separate evidenced bindings. Timing retains the old flat singleton config and additionally accepts:

```python
"specimens": {
  "sp1": {
    "canonical_context_episode_id": "e1",
    "contexts": {
      "e1": {
        "treatment_episode_id": "e1", "canonical_category": "POST_TREATMENT",
        "precision": "EXACT", "relative_day": 60, "window_id": "invented-end",
        "source_locator": "invented-end-binding", "inferred_from_order": False
      },
      "e2": {
        "treatment_episode_id": "e2", "canonical_category": "PRE_INDEX_BASELINE",
        "precision": "EXACT", "relative_day": 0, "window_id": "invented-start",
        "source_locator": "invented-start-binding", "inferred_from_order": False
      }
    }
  }
}
```

The two corresponding source bindings are required. Config context keys must identify exactly the bound episode contexts; unknown/missing evidence blocks, extraneous/contradictory contexts fail. Duplicate specimen binding in the same episode is ambiguous and fails; distinct explicitly evidenced episode contexts are retained. Cross-patient ownership remains prohibited. Immutable specimen category/day assertions are checked against the explicitly declared canonical context; the physical collection day must agree with every exact relative-day context. All original canonical rows remain untouched. Each `TIMING_ASSERTION` now also carries `binding_id` and `role`, with the existing specimen/episode/category/precision/day/interval/window/version fields. Consumers select `(specimen_uid, treatment_episode_id)` explicitly. `timing_shared_specimen_context_packet()` is the complete invented test helper. Record reversal produces the identical complete result.

Defined source-binary outcomes now have an explicit separate frozen `OTHER` endpoint lane:

```python
"endpoints": {
  "version": "invented-v1", "classes": ["OTHER"], "source_priority": ["o1"],
  "category_map": {"invented-positive": "SOURCE_POSITIVE"},
  "binary_definitions": {
    "o1": {
      "name": "invented-binary-endpoint", "version": "invented-binary-v1",
      "source_locator": "invented-binary-rule",
      "raw_value_map": {"invented-positive": 1, "invented-negative": 0}
    }
  }
}
```

Source class must be `SOURCE_BINARY`; immutable source canonical category must be `SOURCE_POSITIVE` or `SOURCE_NEGATIVE`, agree with the explicit exact-raw mapping, and be evaluable. Definition name/version/locator and raw mapping are required. Values must be actual integer 0/1, not booleans. Missing definitions/evidence block with `SOURCE_BINARY_DEFINITION_UNKNOWN`; known contradictory mappings fail with `SOURCE_BINARY_DEFINITION_CONFLICT`. Source-binary ORR/DCR conversion remains prohibited. Output is frozen `endpoint_class=OTHER`, `canonical_category=SOURCE_BINARY`, `binary_value=0|1`, `evaluability=EVALUABLE`; no ORR/DCR source fields are synthesized. Audit `SOURCE_BINARY_DEFINED` includes `patient_uid`, `treatment_episode_id`, `outcome_id`, `definition_name`, `definition_version`, and `source_locator`. Undefined source-binary behavior remains frozen `SOURCE_BINARY_UNKNOWN` with null binary/unknown evaluability. `defined_source_binary_packet(binary_value=1)` is the complete invented helper.

Communicated both exact interfaces to parent and Group C. Group C owns explicit `endpoint_policy` selection and consumption of per-episode timing audits; no matrix code was edited by this worker.

All review-wave pytest commands retain the exact previously documented interpreter/flags, file `tests/a_dav_implementation/test_group_a.py`, and selectors below. These are only focused owned-test checks, never the complete shared suite.

| Log | Selector / command | Exit | Actual result |
| --- | --- | --- | --- |
| round1-chronology-red.txt | `-k 'component_interval or missing_component_date'` | 1 | 5 expected failures, 2 existing boundary checks passed, 87 deselected. |
| round1-context-red.txt | `-k 'shared_specimen or duplicate_same_episode'` | 1 | 2 expected failures, 1 existing duplicate-context rejection passed, 94 deselected. |
| round1-timing-green.txt | `-k 'timing or component'` | 0 | 34 passed, 63 deselected. |
| round1-binary-red.txt | `-k 'defined_source_binary'` | 1 | 6 expected missing-path failures, 3 existing rejections passed, 97 deselected. |
| round1-focused-green.txt | `-k 'endpoint or binary or timing or component'` | 0 | 65 passed, 41 deselected. |
| round1-mypy.txt | Exact strict offline four-module command above | 1 | One typing error: bounded interval needed explicit narrowing after validation. |
| round1-mypy-green.txt | Exact strict offline four-module command above | 0 | No issues found in 4 source files; narrow cast follows the existing runtime guard. |
| round1-final-green.txt | `-k 'endpoint or binary or timing or component'` | 0 | **65 passed, 41 deselected in 3.80s**. |

Current review-wave SHA-256 values:

| File | SHA-256 |
| --- | --- |
| tools/a_dav/timing.py | `ab8d588e0610371cebd647c3e92fc5f305dda8a21cf673124adba355bb5678a7` |
| tools/a_dav/endpoints.py | `3bfe5786674bcb5e4a5692fa31af96a55d1d3fbaf9297512b061abb4a5f4dad2` |
| tests/a_dav_implementation/test_group_a.py | `cf064145a9a928cc4d4f752a292e59f8bb406f52695fa6d097199b1742d97d64` |

Registries/assays code and original complete example config are unchanged from initial handoff hashes. All synthetic-only and four false actual flags remain; real-source/reviewer/clinical/statistical/environment acceptance is still NOT_RUN. No network, installs, commits, new agents or full suite were used for these fixes.
