# Implementation tickets and tests

## Release discipline

Tickets are bounded implementation units. None authorizes biological analysis. TDD is required: write an adversarial test, observe the expected failure, implement the minimum behavior, run focused and repository regression tests, then issue a completion receipt.

## Ticket register

| ID | Ticket | Objective | Owned files | Input/output schemas | Dependencies | Acceptance criteria | Failure states | Tests | Real-source tracer | Review requirements |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DAV-T01 | Search and candidate registry | Build append-only search logging and candidate-packet validation. | tools/a_dav/search_log.py; schemas/source_record.schema.json; templates/search_log.tsv | query config + source families -> search log TSV + candidate packet JSON | none | Exact query/filter/page logging; idempotent packet IDs; agents cannot write canonical registries. | duplicate query IDs; incomplete pagination; malformed packet; secret in query | Unit: ID/idempotency/pagination/secret scan. Integration: no-result and multi-page candidate runs. | One official catalogue/API pagination tracer and one no-result tracer. | Integrator review plus independent audit of a sample of included/excluded records. |
| DAV-T02 | Study and publication-family resolution | Resolve accessions/publications to originating studies and typed aliases. | tools/a_dav/study_resolution.py; study/publication schemas; alias template | candidate packets -> study registry, publication-family registry and alias crosswalk | DAV-T01 | GEO/SRA aliases and multiple publications resolve without duplicate cohort creation. | ambiguous origin; superseries conflict; publication subset unknown | Unit: alias/case/punctuation/superseries. Contract: schema-valid records and no duplicate canonical study IDs. | Riaz GSE91061/SRP094781 and Cho GSE126045 subseries metadata. | Independent source reviewer checks original-study and publication-family claims. |
| DAV-T03 | Source-object verification | Discover exact processed objects, retrieve safely and record complete provenance. | tools/a_dav/object_verification.py; source registry | study/source candidates -> source_object records + retrieval/validation receipts | DAV-T02 | Atomic retrieval, complete SHA-256, version/replacement handling and null hash before retrieval. | landing page only; partial object; hash mismatch; access blocked | Unit: partial/stale/hash/version cases. Integration: interrupted retrieval and resume. | One small GEO metadata/object tracer without patient data. | Code reviewer plus object/source reviewer; terms and redistribution field required. |
| DAV-T04 | Patient and specimen registry | Build private patient, alias and specimen registries without overwriting repeats or lesions. | tools/a_dav/registries.py; patient/specimen schemas | validated metadata/crosswalks -> private patient/alias/specimen registries | DAV-T02,DAV-T03 | Leading-zero IDs, duplicate raw IDs across studies, multiple lesions and repeated sequencing pass adversarial tests. | ambiguous alias; duplicate UID; raw ID in public output | Unit: ID preservation/collisions/repeats/lesions. Privacy: public-output rejection. | Header/sample crosswalk tracer from a public cohort. | Private-data reviewer and independent source-identity reviewer. |
| DAV-T05 | Endpoint ontology | Preserve raw outcomes and derive branch-specific ORR/DCR/DCB mappings. | tools/a_dav/endpoints.py; clinical_outcome schema | private patient outcomes + mapping config -> endpoint registry and mapping receipt | DAV-T04 | CR/PR/SD/PD/NE, source binary, PSA, pathological and censored outcomes map or fail correctly. | undefined binary response; conflict; invalid conversion | Unit: every endpoint class and discrepancy priority. Metamorphic: raw labels unchanged. | Riaz original BOR metadata tracer. | Clinical endpoint reviewer verifies criteria, source hierarchy and branch mapping. |
| DAV-T06 | Treatment and timepoint ontology | Create treatment episodes and evidence-bearing canonical time assertions. | tools/a_dav/timing.py; treatment schema | patient/specimen metadata + treatment config -> treatment/time assertions | DAV-T04 | Prior ICI, regimen change, progression and exact-day conflicts are preserved and reason-coded. | index treatment unresolved; chronology conflict; inferred row order | Unit: sequence/prior-ICI/day conflicts. Metamorphic: row-order invariance. | Riaz baseline/on-treatment schedule tracer. | Clinical/pharmacology reviewer verifies index treatment and chronology. |
| DAV-T07 | Assay validator | Validate matrix/object structure, unit, transform, annotation and branch suitability. | tools/a_dav/assays.py; assay schema | source object + source docs + assay config -> assay registry and validation receipt | DAV-T03,DAV-T04 | Counts/TPM/FPKM/log/array/methylation/missing-zero adversarial cases fail or pass correctly. | unknown scale; duplicate columns; incomplete universe; unsupported assay | Unit: format/scale/ID/coverage cases. Property: no missing-to-zero. | Bounded public headers from Riaz/Rose plus source documentation. | Assay-domain reviewer and code reviewer approve fail-closed behavior. |
| DAV-T08 | Overlap and exposure ledgers | Build typed overlap graph and prior-exposure ledger. | tools/a_dav/overlap.py; tools/a_dav/exposure.py; overlap schema | study/publication/patient/object identities + repository history -> overlap/exposure ledgers | DAV-T02,DAV-T04 | Aliases, mirrors, publication reuse and prior model exposure block false independence. | unknown material overlap; exposure conflict; cross-namespace false join | Unit: every edge/exposure class. Adversarial: same trial under multiple labels. | Riaz/Hugo deposited-ID comparison and atlas alias tracer. | Independent overlap reviewer; unresolved material edges remain blocking. |
| DAV-T09 | Cohort-admission engine | Evaluate V0–V7 for each named branch and emit immutable receipts. | tools/a_dav/admission.py; admission receipt schema | validated normalized records + branch config -> admission receipts/registry | DAV-T03–DAV-T08 | Branch-specific pass/fail; no global usable flag; parser success cannot admit. | missing gate; unsupported branch; reviewer absent | Unit: each branch and gate state. Contract: receipt completeness and immutability. | One source-specific dry run producing BLOCKED_UNKNOWN, not admission. | Source reviewer and integrator approve V7; no self-admission by parser. |
| DAV-T10 | Baseline matrix builder | Select one outcome-independent baseline specimen/assay and build matrix/receipt. | tools/a_dav/matrices.py; BASELINE contract | admitted normalized records + baseline rule + split -> baseline matrix + receipt | DAV-T09 | Multiple baseline specimens, repeats and row permutations produce deterministic output. | ambiguous tie; unadmitted source; endpoint/assay failure | Unit: tie hierarchy, duplicate grain and exclusions. Metamorphic: endpoint/performance changes do not alter specimen choice. | Small public header/metadata tracer after a source receipt exists. | Independent matrix reviewer checks counts, selection and receipt against registry. |
| DAV-T11 | Longitudinal long and pair builders | Preserve all timepoints and build window-specific pairs without last-row selection. | tools/a_dav/matrices.py; longitudinal contracts | admitted longitudinal records + window config -> long/pair matrices + receipts | DAV-T06,DAV-T07,DAV-T09 | Multiple follow-ups and row permutations are invariant; regimen/progression states remain separate. | no pair in window; chronology conflict; multiple follow-ups no rule | Unit: windows/pair quality/missing follow-up. Metamorphic: row permutation. | Riaz pre/on subset after full source validation. | Longitudinal clinical reviewer verifies windows, missingness and pair selection. |
| DAV-T12 | Split and independence validator | Freeze development/outer/final roles after overlap and exposure checks. | tools/a_dav/release.py; split template | admission/membership + overlap/exposure + split config -> split registry/freeze receipt | DAV-T08,DAV-T09 | Patient/study/trial/publication/exposure leakage tests fail closed. | post-performance selection; unknown exposure; required source missing | Unit: all leakage classes. Mutation: new exposure invalidates untouched status. | Metadata-only simulated split followed by prohibited exposure mutation. | Independent leakage reviewer signs the split freeze before outcome analysis. |
| DAV-T13 | Validation and privacy report builder | Create public aggregate receipts and scan releases for identifiers/secrets/restricted paths. | tools/a_dav/reporting.py | private receipts + public-report config -> public aggregate report/privacy receipt | DAV-T09–DAV-T12 | Public bundle contains no patient records and includes gate/count/limitation tables. | raw ID; token; signed URL; controlled path; small-cell disclosure | Unit: privacy patterns and aggregate tables. Integration: private/public fixture pair. | Synthetic private/public fixture pair. | Privacy reviewer signs; any detected sensitive field blocks release. |
| DAV-T14 | Reproduction and freeze bundle | Pin inputs, code, config, schemas, outputs and commands for R9 release. | tools/a_dav/release.py | validated matrices/receipts/splits -> immutable release bundle and readiness report | DAV-T13 | Fresh build and no-op resume match hashes; stale inputs invalidate completion. | hash mismatch; stale receipt; overwrite attempt | Integration: fresh/resume/invalidation/atomic publish. Contract: all hashes resolve. | One patient-free synthetic end-to-end release. | Whole-branch code/scientific review plus environment validation before R9. |

## Ticket completion receipt

Each ticket records:

```text
ticket ID and objective
owned files and commit range
input/output schema versions
tests written and RED/GREEN evidence
focused and full-suite commands/results
real-source tracer and limits
code/config hashes
known limitations
review findings and fixes
completion status
```

## Required adversarial test families

### Source identity

Same study under GEO/SRA; multiple publications; superseries/subseries; reanalysis mirror; suspected patient overlap; punctuation/case collisions.

### Patient/specimen identity

Numeric-looking IDs, leading zeros, duplicate IDs across studies, technical repeats, repeated sequencing, multiple lesions and multiple baseline specimens.

### Endpoints

CR/PR/SD/PD/NE/unknown; undefined binary response; conflicting sources; DCB threshold; short censoring; PSA versus ORR; pathological response; PFS/OS.

### Timing

Baseline, early/late on-treatment, progression, post-discontinuation, regimen change, multiple follow-ups, exact-day conflict and row-order invariance.

### Assays

Counts mislabeled TPM, TPM mislabeled counts, FPKM truncation, log scale, missing versus zero, negatives, duplicate genes/columns, feature collisions, incompatible platform, unknown scale and incomplete universe.

### Pairing

Same patient/different specimen, lesion or time; unpaired modalities; ambiguous links; multiple follow-ups.

### Splits

Patient in development/final test; same trial under multiple studies; outcome-informed feature selection; atlas-derived exposure; missing required test source; prior model exposure.

### Privacy

Raw IDs in public output; restricted paths; signed URLs/tokens; patient matrices in Git; credentials in manifests.

Tests fail closed. Synthetic fixtures validate software only. Public real-source tracers validate format/provenance assumptions only.
