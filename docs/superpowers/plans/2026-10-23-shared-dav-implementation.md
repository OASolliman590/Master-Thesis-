# Shared DAV implementation — synthetic software scope

User confirmed all DAV-T01–14 on 23 October 2026. Use implement, TDD at the public packet/result APIs, independent code-review and a local current-branch commit. Frozen specifications are the authority; this plan changes none. No real source data, downloads, remote work, biological analysis, model fitting or source admission. Real-source tracers and actual reviewer/environment/statistical gates remain explicitly NOT_RUN.

## Public contract

New stage functions consume one JSON-compatible packet:

```python
{
    "classification": "SYNTHETIC_ONLY",
    "branch_id": "A_BASELINE_BIO",  # or another frozen named branch
    "records": {"patient_registry": [...], ...},
    "config": {"registries": {...}, "endpoints": {...}, ...},
    "schema_hashes": SchemaStore().hashes,
    "dependencies": {"stage_name": prior_result},
}
```

Every new stage API is `function(packet: dict[str, Any], *, schemas: SchemaStore | None = None) -> dict[str, Any]`. It reads only its named config key and explicit normalized records. It returns `classification`, `stage`, `status` (`SYNTHETIC_READY`, `BLOCKED_UNKNOWN`, `FAIL`), `records`, `audit`, fixed `reasons`, `bindings`, `receipt_id` and four permanently false readiness/admission/release/analysis flags. `SYNTHETIC_READY` is software simulation, never a V0–V9 clinical pass or canonical admission.

The core owns schema validation, safe failures, deterministic canonical JSON/hash, dependency verification and result sealing. A dependency must name the expected stage, bind actual records/runtime-code/schema/config and declared upstream receipt identities, and have `SYNTHETIC_READY`; missing/stale/tampered/wrong-branch inputs cannot support a downstream included row. Frozen canonical schemas remain the only normalized record model. View table aliases (`baseline`, `timepoint`, `pair`, `endpoint`, `coverage`, `split`, `membership`) use the existing materialized-matrix schema. Some inherited record shapes require PRIVATE_PATIENT_LEVEL labels; top-level SYNTHETIC_ONLY means every value is invented. No real file reader or registry writer is added.

`core.py` public helpers: `SchemaStore(root=SCHEMA_ROOT, expected_hashes=None)` with `.hashes` and `.validate(table, record)`; `canonical_bytes(value)`, `digest(value)`, `require(condition, code)`, `check_packet(packet, schemas)`, `verify_result(result, stage=None, branch_id=None, schemas=None)`, `finish(stage, packet, records=None, *, status="SYNTHETIC_READY", reasons=(), audit=(), schemas=None)` and `public_summary(result, *, include_counts=True)`. Fixed failures use `DavError(code, *, blocked=False)` and `@stage_boundary(stage)`; boundary catches invalid input and returns fixed codes without caller text. Modules may add fixed reason codes. Never emit raw IDs/paths/locators in public summaries.

## Tasks and ownership

| Task | Owner/files | APIs and required behavior |
|---|---|---|
| Core + T01–03 reuse | Parent: core.py; tests/a_dav_implementation/test_core.py and test_existing_seams.py | Test hash/schema/dependency/privacy boundaries. Exercise existing search_log, study_resolution and object_verification with invented packets and injected in-memory transport. Preserve existing modules and all prior receipts. No live/cached real-source tracer is a new acceptance claim. |
| T04 registries | Group A: registries.py | `build_registries`; unique lexical canonical IDs, study-scoped raw aliases, legitimate repeats/lesions, exact patient/specimen/assay/source FKs, ambiguous merges rejected; no prefix-generated IDs. |
| T05 endpoints | Group A: endpoints.py | `map_endpoints`; source raw immutable, explicit mapping/version/locators, ORR/DCR source categories, NE/unknown remain unevaluable, undefined binaries cannot become ORR, DCB needs explicit duration rule, survival/PSA/pathology separate, discrepancy/source-priority rules explicit. Produce frozen endpoint views as applicable. |
| T06 timing | Group A: timing.py | `validate_timing`; source-supplied episodes/bindings and same-patient ownership, regimen/prior-ICI/chronology conflicts, exact versus bounded/unknown dates, no order inference or default window. Missing evidence blocks; known contradictions fail; bindings and component closure checked. |
| T07 assays | Group A: assays.py | `validate_assays`; explicit source object/header/specimen ties, small invented matrix config only, unit/transform/annotation/feature coverage/QC and replicate/missingness validation. Counts/TPM/FPKM/log/array/methylation lanes must be declared, never coerced; missing is not zero. Produce schema-valid coverage records. No score or biology. |
| T08 overlap | Group B: overlap.py; exposure.py | `validate_overlap`, `validate_exposure`; typed frozen edges and exposure records, same trial/publication/mirror aliases, transitive potential overlap, namespace-safe joins; unknown use cannot certify untouched; metadata-only versus molecular-outcome use distinguished, prior exposure lineage bound. |
| T09 admission | Group B: admission.py | `evaluate_admission`; verify registry/endpoint/timing/assay/overlap/exposure dependency seals and same branch/config; evaluate each frozen branch's explicit requirements, unknown/failure distinctions, required-source completeness, no parser self-admission. Output synthetic eligibility plus schema-valid canonical admission draft with BLOCKED_UNKNOWN, no approved branches/real V7 pass. Downstream can simulate using SYNTHETIC_READY only, with false real flags. |
| Prat procedure/checklist | Group B: prat_review.py | `review_prat_packet`; implement independent review findings P01–P08 with sealed same object/code/schema/questions/repeat-policy basis, distinct blind committed reader first passes, assertion/locator support beyond legacy hash equality, full disagreement/adjudication retention and stale-version invalidation. Validate exact invented object bytes from content_hex and actual complete hash, null authored version allowed with immutable capture basis; no listing/prefix/caller pass as custody. Missing actual evidence/authentication stays separate from synthetic protocol checks. Public Prat summary has only fixed enums/hashes/false flags, no counts/IDs/dates/free text. |
| T10–11 matrices | Group C: matrices.py | `build_baseline`, `build_longitudinal`; require sealed synthetic admission plus relevant stages. Select explicit outcome-blind baseline/assay rank config, no silent ID tie breaker; preserve all timepoints, repeated windows and missing-follow-up denominator/audit; same patient/episode/assay/lesion/platform guards, progression/regimen changes distinct. Schema-valid views + build draft; no biological calculation. Endpoint mutation cannot change specimen selection; row permutations invariant. |
| T12 split | Group C: release.py | `validate_split`; frozen permanent roles and nested fold roles; verify sealed overlap/exposure/admission, required-source completeness, patient/family/trial/related-specimen protection and lineage; no post-performance selection, unknown prior use blocks final-test simulation. Validate frozen split views. |
| T13 reporting | Group C: reporting.py | `build_public_report`; verify dependency seals then export only allowlisted aggregate software statuses/counts/hashes under explicit small-cell policy; private row pairs, raw IDs/paths, signed URLs/tokens/free text or extra sidecars fail closed. Prat narrow export policy is stricter and has no counts. |
| T14 freeze | Group C: release.py | `freeze_bundle(packet, destination: Path, *, schemas=None)` plus `verify_bundle(destination)`; bind exact inputs/code/config/schema/outputs/commands/environment and all required sources. Atomic directory publication, immutable collision protection, fresh/no-op resume, changed input/config/schema/descendant invalidation, reject symlinks/path traversal/overwrites. Only SYNTHETIC evidence with READY_FOR_REVIEW/BLOCKED frozen release draft and false real release flags. |
| Connected workflow | Parent: workflow.py; tests and synthetic fixture/demo | `run_workflow(packet)` invokes real stage functions, propagates current records and dependency receipts in topological order (split/exposure validation before matrix materialization), exposes result for each ticket, produces connected synthetic baseline and longitudinal paths plus blocked Prat/evidence cases. No bypass with hand-made PASS dictionaries. |

Groups own only their named NEW module files and `tests/a_dav_implementation/test_<group>*.py` plus their report/logs in this plan's workspace. Parent owns core/workflow/shared fixtures, public contract, cross-group integration and receipts. No worker commits, installs, network, remote, reads real objects, changes old/frozen files, spawns agents or reruns the full suite. Agent reports contain actual RED/GREEN and file/hash details. Parent alone commits exact named new files after review. No push.

## TDD and verification

For each public API, write one observable adversarial tracer, observe RED, implement the minimal behavior, then add the next vertical slice. Tests use independent expected literals/worked examples and public results; no private helpers or self-fulfilling hash assertions. Keep focused RED/GREEN logs per group. Typecheck new modules regularly with pinned mypy when available; compile checks are not mislabeled typechecking. Parent runs the complete newly implemented synthetic DAV suite once after integration, plus appropriate existing synthetic regressions; real-source/cached-source tracers remain NOT_RUN. No unrelated biological workflow is invoked as a test.

Independent code-review runs Standards and Spec axes in separate agents on the exact new-file diff from the fixed base plus untracked additions. Review actual frozen schemas, the canonical ticket table and this plan. Fix confirmed findings with narrow retests. Final receipt lists all14 tickets individually, reused versus new software, actual tests, deferred real tracers/reviewer/environment gates and source evidence gaps. Do not label real production or scientific acceptance complete.

## Review focus

1. Explicit malformed/hash/schema/relationship conflicts must not disappear behind missing assertions.
2. A stale/tampered upstream result must invalidate every dependent matrix/split/freeze.
3. Selection is outcome-blind and permutation-invariant; all repeat/window candidates and missing reasons survive in audit. Missing pre/follow-up has an audit denominator entry, never a fabricated pair row with a null side (frozen relational invariant).
4. Real admission/release/protected status cannot be fabricated from a synthetic pass or reviewer name.
5. Privacy rejection must cover malicious payloads, nested data, counts under Prat's narrow policy, and extra output artifacts.
