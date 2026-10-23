# Shared DAV synthetic implementation

Scope: DAV-T01–DAV-T14, plus the Prat two-reader protocol checks. The user confirmed this scope on 23 October 2026. Frozen specifications, previous validation packets and source evidence remain unchanged. This is software verification with invented inputs. No real source object, patient data, biological calculation, model fit, source admission or statistical release is established.

The controlling requirements are the [shared DAV ticket register](../../../specs/A_DATA_ACQUISITION_VALIDATION/TICKETS_AND_TESTS.md), its linked contracts, and the [implementation plan](../../superpowers/plans/2026-10-23-shared-dav-implementation.md). The [independent Prat document review](../A_DAV_PRAT_PROCEDURE_01/INDEPENDENT_PROCEDURE_REVIEW.md) identifies P01–P08. Existing T01–T03 modules are reused without changing their bytes; new stages cover normalized records, governance, materialization and reproduction. Tests call the public APIs with invented records and injected transport. The connected workflow invokes actual stage functions and stops at the first failure or unknown prerequisite.

## Run the invented example

From the repository root, with Python 3.12, `jsonschema` and `pytest` available:

```sh
python -B -m tools.a_dav.demo
python -B -m tools.a_dav.demo --freeze /absolute/existing/parent/invented-release
python -B -m pytest tests/a_dav_implementation -q -p no:cacheprovider
```

The example has no data-file input option. It constructs one invented patient and two invented specimens in memory. Every numeric value, time window and rule is an explicitly labelled example, not a Prat or scientific default. Complete invented object bytes are measured and parsed; a different matrix cannot reuse that object binding. The example validates the per-patient split and exposure ledger before materializing baseline, long and paired views. It calculates no molecular score, effect or prediction. An absent pre/follow-up is retained in the audit denominator; it is never fabricated as a pair row with a null side. The CLI prints a count-free status. The optional freeze directory is a **synthetic reproduction artifact**, containing invented records and protocol input; it is separate from the allowlisted public report.

The frozen source schemas remain authoritative. Canonical assertions and their raw lexical IDs are preserved. Derived views do not replace source records. Dependency receipts bind the current canonical snapshot, owned derived outputs, complete configuration, schemas, declared upstream receipt identities and current runtime code. Reproduction also binds the reused discovery/resolution/object modules and the demo command implementation. Hashes detect changes; they do not authenticate people or prove source truth. A changed object, config, code, schema or relevant upstream output invalidates dependent receipts. Existing freeze destinations are verified and never overwritten.

`SYNTHETIC_READY` means the invented software case is ready for its next simulated stage. The flags `analysis_ready`, `source_admission`, `statistical_release` and `biological_analysis_executed` remain false. Canonical admission and matrix-build drafts retain `BLOCKED_UNKNOWN`; actual review/test fields remain `NOT_RUN`. No parser or caller-supplied reviewer name grants V7, V8 or V9.

## Software coverage and external acceptance

| Tickets | Software behavior exercised | External acceptance still required |
|---|---|---|
| T01–T03 | Existing discovery/resolution APIs, complete invented bytes, injected interrupted retrieval/resume, checksum/overwrite rejection | Current official catalogue tracers, source identity/object/version/terms and independent object review |
| T04 | Lexical IDs, aliases, repeats, lesions and foreign keys | Actual source crosswalk and independent identity review |
| T05 | Raw-preserving endpoint views and prohibited conversions | Source endpoint definitions, individual same-episode binding and clinical review |
| T06 | Explicit time/episode/component assertions and conflicts | Source chronology, regimen and policy evidence |
| T07 | Invented matrix structure/scale/annotation/coverage and missing-versus-zero checks | Source measurement methods, exact object/header links and assay-domain review |
| T08 | Typed overlap closure and lineage-bound prior-use distinctions | Actual overlap and repository-use review |
| T09 | Named branch criteria, rejection of known record/policy contradictions and blocked canonical admission drafts | Real V0–V7 evidence and authenticated source/integrator approval |
| T10–T11 | Explicit outcome-blind eligible-specimen selection, sealed assay/endpoint/split consumption, long/pair views and missing-follow-up audit denominators | Actual admitted source inputs, selection/window policies and matrix review |
| T12 | Protected role/fold boundaries, ancestry/overlap and exposure checks | Reviewed lineage history, role decisions and authenticated split freeze |
| T13 | Allowlisted aggregate statuses/hashes, explicit count suppression and prohibited payload rejection | Authorized privacy review of actual release contents |
| T14 | Connected fresh/resume verification, exact bindings, atomic publication and immutable collision handling | Target-environment validation, whole-branch scientific review and real R9 release |
| Prat P01–P08 | Manifest/common-basis checks, sealed first passes, policy lock order, assertion disagreement retention and count-free summary | Actual complete source set/custody, independent readers, authenticated review and source-backed semantic adjudication |

## Evidence remains open

The [existing evidence register](../../evidence/A_DAV_PRAT_BASELINE_BRIEF_01/EVIDENCE_REQUIREMENTS.tsv) remains the source of truth. E01–E08 are unresolved actual source, identity, treatment, selection, endpoint, assay, overlap and independent-review evidence. E09 named-method use remains deferred. E10 actual admission and releases remain unestablished. Software now checks the shape and consistency of supplied evidence; it supplies none of that missing evidence itself.

No NPD-to-ORR mapping, source-specific threshold, protected role, named scoring method or biological conclusion is selected. The next source step is an authorized review in approved custody, starting with the exact source-object inventory and the fixed two-reader basis. It requires actual evidence and authenticated reviewers. More synthetic code cannot close those items.

Final tests, review findings and dispositions, exact file hashes and preservation results are recorded in the adjacent acceptance artifacts after verification. Historical real-source tracer receipts are not relabelled as new acceptance.
