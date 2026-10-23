# Independent review: Prat two-reader procedure and source-object checklist

Review date: 2026-10-23. Reviewer: the independently dispatched documentation-review agent for this packet. This identifies the review performed; it is not an authenticated clinical source-review signature.

**Verdict: the historical procedure is not sufficient, as written, for current canonical DAV source review or admission.** Its independent reading, source-locator, unresolved-state and narrow-export principles are useful. The procedural gaps below need an explicit current review contract before reader work. This review neither rejects the actual Prat source nor establishes a defect in existing software. Source readiness remains `BLOCKED_UNKNOWN`; no E01–E10 evidence item is closed.

## Scope and authority

This is an independent document comparison only. I read the historical proposed procedure, the current Prat baseline brief and evidence requirements, the six frozen DAV documents listed below, the compatibility decisions, and the root context/instructions and relevant accepted A/A1 decisions. I did not open source objects, patient tables, matrix headers, private control outputs or historical execution outputs. No network, remote execution, test, installation, commit or biological analysis was performed. No implementation or frozen specification was edited.

Line references below are to the documents as read on this date. Abbreviations resolve to these exact files:

| Reference | Document |
|---|---|
| PROC | [Historical proposed procedure](../../../../paper-a-batch-pipeline/specs/source-evidence/2026-10-12-patient-semantics/CONTRACT_AUTHORING_PROCEDURE.md) |
| BRIEF | [Current Prat baseline evidence brief](../../evidence/A_DAV_PRAT_BASELINE_BRIEF_01/BRIEF.md) |
| E | [Evidence requirements](../../evidence/A_DAV_PRAT_BASELINE_BRIEF_01/EVIDENCE_REQUIREMENTS.tsv) |
| COMPAT | [Compatibility decisions](../A_DAV_LEGACY_COMPAT_01/COMPATIBILITY_DECISIONS.md) |
| MODEL | [Normalized patient model](../../../specs/A_DATA_ACQUISITION_VALIDATION/PATIENT_DATA_MODEL.md) |
| REL | [Relational invariants](../../../specs/A_DATA_ACQUISITION_VALIDATION/RELATIONAL_INVARIANTS.md) |
| END | [Endpoint ontology](../../../specs/A_DATA_ACQUISITION_VALIDATION/ENDPOINT_ONTOLOGY.md) |
| ASSAY | [Assay and measurement contract](../../../specs/A_DATA_ACQUISITION_VALIDATION/ASSAY_AND_MEASUREMENT_CONTRACT.md) |
| ADMIT | [Cohort admission and release](../../../specs/A_DATA_ACQUISITION_VALIDATION/COHORT_ADMISSION_AND_RELEASE.md) |
| AMEND | [Integration amendment](../../../specs/A_DATA_ACQUISITION_VALIDATION/INTEGRATION_AMENDMENT_20261015.md) |

The review target is `Prat-GSE93157 × A_BASELINE_BIO`, for evidence preparation. Canonical IDs remain unresolved and no endpoint variant or development/test role is established (BRIEF lines 7–11). The shared normalized DAV store, episode bindings and release sequence control integration, rather than the legacy tables or their gate vocabulary (COMPAT lines 5–9, 33–37; AMEND lines 5–13). The accepted [A/A1 decision](../../decisions/A_A1_INTEGRATED_SPEC_20261015.md), lines 15–24, preserves that authority and leaves source-specific numerical policies unreleased.

## Findings: procedural defects with software-enforceable parts

These are defects in the written procedure relative to current contracts. The suggested checks are a bounded design for later invented-data verification, not claims about the behavior of uninspected implementations. A passing synthetic check would establish only its software behavior (REL lines 25–27).

### P01 — The source-object set is described but not sealed or shown complete

PROC lines 25–28 require native/format states, and lines 80–84 name retained objects and historical observations. They do not define an authoritative current object inventory, complete-byte verification, object versions, correction/publication-family coverage, access terms, custody or a change protocol. Format verification and a shortened historical hash cannot establish those facts. Current requirements explicitly demand exact objects, complete-byte hashes, version/retrieval/terms and authorized custody (REL line 7; ADMIT lines 29–31; E line 3; BRIEF lines 28, 54).

**Suggested testable contract:** both readers and each build/audit receipt reference the same sealed private object-manifest digest and its version. The manifest distinguishes required, available, missing, superseded and uninspected objects with scoped completeness claims. Missing required objects or a byte/version mismatch withholds dependent acceptance. A changed object set creates a new review version and invalidates affected comparisons and receipts; it must not silently replace the first-pass basis (ADMIT line 69; REL line 23). Invented fixtures can test absent-object, stale-version and changed-byte rejection. Actual completeness, custody and access authority require source review, not a manifest-shaped assertion.

### P02 — Blind first passes lack a verifiable common basis and independence record

PROC lines 18–19, 29–40 correctly require independent contracts, fixed relation questions and no sharing until both contracts are hashed. They do not specify preserved first-pass artifacts, order of sealing, authenticated reader identities/dates, access to the peer's work, shared hints or pre-existing outcome exposure. Nor do they bind the two first passes to the same branch questions, source inventory, schema, rule-language definition and executor/auditor versions. A local reviewer sees hashes (lines 21, 53), which cannot authenticate the process. REL line 23 specifically rejects a reviewer string as proof of a real signature; BRIEF lines 34, 55–56 and E line 9 require blind first passes and authenticated version-bound review.

**Suggested testable contract:** fix the question set and branch before reading; retain two distinct authorized reader records and immutable first-pass digests; permit comparison only after both are sealed. Bind each pass to the common object-manifest, question-set, schema and execution/rule-language versions. Reader-specific authored rules remain separate, with their own versions and hashes: independent interpretation must not be replaced by copying a common answer. A workflow can reject a missing second seal, unequal common basis, mutable prior pass or absent authentication reference. It cannot prove that a human or agent never saw a peer's work; that needs the authorized review system and an honest independence/exposure record. No particular authentication technology is selected here.

### P03 — Equal legacy table hashes are treated as semantic agreement

PROC lines 41–45 state “Equal per-table hashes → agreement.” Equal derived tables show reproducible legacy reconstruction under the executed rules; they do not establish that either reader's asserted identities, episode relations, endpoint interpretation or source locators are correct or equivalent under DAV. Identical omissions or different source interpretations can produce the same output. Conversely, different rule text or order can support the same evidenced relation. COMPAT lines 7, 15, 21, 35–37 expressly reserve canonical source-evidenced reconstruction and retained conflicts; BRIEF lines 19, 55 excludes hash equality as canonical equivalence.

**Suggested testable contract:** report legacy reconstruction equality separately from assertion-level canonical review. Compare each required identity, patient–specimen–assay relation, exposure/specimen/outcome episode binding, timing/selection rule, endpoint and assay assertion against its source authority and locator. Semantic equivalence requires a documented source-backed reviewer disposition; neither equal hashes nor normalized text alone can grant it. Keep unresolved and conflicting assertions blocking their dependent records. Invented cases should include equal legacy tables with incompatible episode assertions, equal tables with unsupported endpoint meaning, and harmless ordering changes. No equivalence tolerance or biological default is invented here.

### P04 — Disagreement retention and adjudication are underspecified

PROC lines 20, 44–45 retain an AIU adjudication record and export a category plus final contract hash. They do not require the record to retain both first passes, source/rule locators, the exact disputed assertion, the chosen or unresolved disposition, rationale, adjudicator identity/date and references to superseded versions. The procedure does not explicitly prohibit deleting conflicts after selecting a final contract. MODEL lines 65–78 requires versioned provenance and supersession; END lines 78–88 retains separate assertions and the frozen discrepancy priority; REL lines 19, 23 requires adjudication and real review authentication.

**Suggested testable contract:** adjudication references both sealed passes and the disputed assertions; preserves every original assertion; records whether the issue is resolved, remains unresolved, or needs additional objects; and binds the final reviewed contract to its evidence and reviewer. No majority vote, automatic reader preference or silent lower-priority overwrite resolves clinical meaning. New objects reopen the affected review under a new basis. Invented fixtures can reject missing originals, altered seals, unreferenced resolutions and unresolved-conflict promotion. They cannot establish that a chosen clinical resolution is correct.

### P05 — Repeat/selection policy is locked too late and has an insufficient blind safeguard

PROC step 6 (lines 46–48) fixes the repeat rule after both source contracts are authored and build/audit comparison has occurred (steps 3–5). Its stated “before anyone tabulates outcomes” safeguard does not establish outcome-blind policy selection: readers may already have viewed endpoint values in the same objects. Restricting `repeat_select` to QC/timing columns also cannot rule out indirect outcome proxies or a result-driven ranking. BRIEF lines 30, 54–55 and E line 5 require a source-supported policy fixed before outcome-based selection, with all candidates/reasons retained. REL line 15 requires deterministic selections; COMPAT lines 25–27 forbids inheriting a legacy timing category as current policy.

**Suggested testable contract:** establish and version the authorized baseline/archival/repeat/lesion/assay selection policy before outcome-based selection and before readers use outcome results to choose that policy. Keep a truthful exposure record when perfect masking is impossible; do not claim untouched blinding retrospectively. Retain every candidate and selection/exclusion reason. A workflow can enforce lock order, explicit policy/version dependency, prohibited direct outcome inputs and deterministic selection under input permutation. Independent scientific review must assess indirect dependence and source justification. The old three-month category is not a default.

### P06 — Historical role and gate prerequisites can be mistaken for current admission

PROC lines 26–27 uses historical G0–G2/format prerequisites; lines 54, 56–72 uses legacy G3–G7, primary/supporting relations and targeted-panel feature checks. In that table timing is only “if available” for supporting use, native secondary endpoints are optional, and overlap is recommended. Those relaxed historical requirements cannot qualify the current `A_BASELINE_BIO` branch, whose pre-index expression, evaluable exact ORR or separately declared source-binary endpoint, and V1–V6 are mandatory (ADMIT line 11; END lines 90–95). Native G0–G2/G7 do not prove DAV or assay-method gates (COMPAT lines 7, 23). The current brief assigns no development/test role (BRIEF lines 9–11).

**Suggested testable contract:** use a named current branch requirement set as the review checklist; record legacy statuses only in their original namespace and evidence class. No predicate maps a historical pass, matching audit, parser success or synthetic receipt to V7 admission or V8/V9 release. Tests can supply all historical passes while withholding a current required endpoint/timing/assay/overlap assertion and verify that current acceptance remains blocked. Admission remains a separate reviewed versioned step (ADMIT lines 5, 57–65; REL lines 23–27).

### P07 — The legacy relation list does not cover canonical grains and episode bindings

PROC lines 60–67 requests person, assay, episode and endpoint relations but does not specify canonical record grains, lexical alias collision handling, per-component bindings or same-patient/same-episode assertions. A “one-to-one after a declared specimen rule” statement (line 61) must not erase multiple specimens/assays, collapse aliases into persons, or propagate one outcome over sequential episodes. Required normalized grains and provenance are defined by MODEL lines 9–26, 47–63, 80–88; AMEND line 9 and REL lines 7–11 require source-backed bindings for each selected component/specimen/outcome. COMPAT line 15 documents the legacy/canonical gap.

**Suggested testable contract:** preserve raw lexical aliases and reader assertions; require evidence for every canonical alias link and every selected subject-to-episode relation; retain unknown bindings as blocked. Verify foreign-key uniqueness, same-patient/same-index-episode constraints, distinct components and correct binding roles. Invented tests can exercise leading-zero aliases, duplicate assay labels, conflicting person merges, sequential regimens and response transfer across episodes. None can establish Prat's actual crosswalk.

### P08 — Export restrictions are strong but need binding to the current review artifact

PROC lines 87–96 provides a useful narrow boundary: enum states/reasons, relation statuses, hashes and fixed flags only; no identifiers, headers, values, dates, counts or free text, with class presence disabled. Lines 51–53 rely on the legacy export validator, whose actual code/schema and output were not inspected in this review. A current checklist or adjudication summary could otherwise accidentally add private paths, counts or descriptive free text. BRIEF lines 55–57 explicitly retains private assertions and permits only aggregate-free statuses/hashes locally. REL line 7 treats pseudonyms as private patient-level records; MODEL lines 47, 88 does not make them exportable.

**Suggested testable contract:** freeze the exact narrow export schema/version and code hash; allow only its approved enum/hash/flag fields, with rejection of unknown fields and free-text channels, nested payloads and alternate sidecars. Keep reader identities, dates, source locators, counts and authentication evidence in approved custody; local status/hash references must not embed private paths or patient information. Hashes must identify approved whole artifacts rather than form a patient-level linkage export. No class-presence or count export is newly authorized. Invented prohibited-field and extra-artifact cases can test the boundary, but cannot certify an unexamined real export. DAV's general aggregate receipt provisions do not widen this source-specific export permission (ADMIT lines 32–46; BRIEF line 56).

## Proposed private source-object checklist

This is a reviewable checklist proposal. It adds no new canonical registry or schema and grants no source access. Its evidence and detailed locators belong in approved custody; the current local packet may receive only the already permitted states/hashes. The distinction between “not in inspected objects” and global absence must be preserved (PROC lines 36–37; BRIEF line 17).

| Check | Required private evidence and review condition | Documentary basis |
|---|---|---|
| Source/family scope | Exact candidate and originating-study/publication-family aliases; publication, deposit, supplements, corrections and reanalyses considered; each required supporting object's purpose and status; any completeness/search limitation stated. An accession/listing alone is not complete evidence. | BRIEF lines 7, 28; E lines 2–3, 8; MODEL lines 11–14 |
| Exact object identity | Registry reference for each exact object; authoritative origin, version/retrieval record, complete-byte SHA-256, retained-byte verification, relation to any superseded object; no truncated hash, format check or historical filename used as proof. | REL lines 7, 23; ADMIT lines 29–31, 69 |
| Custody and permission | Authorized access/terms, approved retained location and custody/retrieval history, allowed readers and export boundary; current review establishes authority rather than copying a historical custody statement. Detailed paths and identities remain private. | E line 3; PROC lines 3–4, 18–21, 87–96; BRIEF lines 28, 54–56 |
| Completeness and inspectability | Required objects actually available and complete; formats/versions and worksheet/section scope recorded privately; missing/truncated/unreadable/superseded objects distinguished from absent evidence; no uninspected object claimed reviewed. | PROC lines 27, 35–37; E line 3; ASSAY lines 28–38 |
| Stable review basis | Object-manifest digest/version plus fixed branch/questions; same basis supplied to both readers; common rule-language/schema/code/auditor versions recorded, reader-specific authored contracts kept separate; changed basis reopens dependent review. | BRIEF lines 34, 54–55; E line 9; REL line 23 |
| Identity and joins | Each lexical person/specimen/assay/header alias tied to exact source location; ambiguity/collision retained; canonical IDs supplied through shared DAV; every selected exposure, specimen and outcome bound to the evidenced index episode. | E lines 2, 4; MODEL lines 47–63, 80–88; REL lines 7–11 |
| Baseline and assay suitability | Source-backed pre-index timing, precision, archival/intervening-treatment and repeat/lesion/assay policy; all candidates/reasons; platform/panel/annotation/unit/transform/normalization/QC/coverage and header linkage. Structure/gene presence does not qualify scale or method. | E lines 5, 7; BRIEF lines 30, 32; ASSAY lines 7–40, 97–101 |
| Endpoint evidence | Original native label and binary definition; assessment system/version, duration premise where needed, evaluability, same-episode individual binding; discrepancies retained under frozen source priority; no group-total assignment or source-binary conversion shortcut. | E line 6; END lines 26–39, 64–88, 97–99 |
| Overlap and prior use | Originating-family aliases, overlap/possible overlap and actual curation/molecular–outcome use; reservation across related papers/specimens; unknown exposure stays unknown. This checklist does not assign a role. | E line 8; BRIEF lines 9, 33; REL line 19; AMEND line 17 |
| Reader and adjudication custody | Two authorized independent first passes, source/rule locators and seals; real identities/dates/authentication references; preserved disagreements, rationale and version-linked adjudication. Local summaries cannot substitute for private review evidence. | E line 9; BRIEF lines 34, 55–56; MODEL lines 65–78; REL line 23 |

## Missing actual evidence and authenticated review

Nothing in this document establishes actual source-object completeness/custody/version (E02), the patient/specimen/assay crosswalk (E01), episode and component bindings (E03), baseline policy evidence (E04), deposited individual endpoint meaning (E05), assay suitability (E06), or overlap/prior use (E07). The exact requirements and current unresolved states remain E lines 2–8. Historical source-level claims at PROC lines 73–84 remain future review questions, consistent with BRIEF lines 17–19 and 27–34; I did not independently verify their contents.

There are no actual two-reader first passes, blindness attestations, authenticated review records or adjudicated canonical equivalence examined in this review. Therefore E08 is not closed merely because the proposed procedure has now received an independent documentation review. E line 9 requires both procedural and real review evidence. Software can require authentication references and immutable seals; only the authorized review system can verify the reviewers, actual dates, source access and evidence referenced (REL line 23). The present agent-authored review is not that verification.

No source admission or statistical/matrix release is requested or established (E line 11; BRIEF lines 36, 44, 57). E09 named-method use remains deferred (E line 10). Private admission counts required later by ADMIT lines 32–33 and REL line 23 must be computed against actual branch records in their authorized environment; no count belongs in this narrow local review export.

## Frozen scientific policy: preserve unknowns and do not invent defaults

The following matters need source evidence and the existing authorized scientific decision process. Procedural tooling must not choose values to make a workflow pass:

- **Endpoint and branch:** retain the exact source-binary meaning if supported; no NPD-to-ORR/DCR/DCB conversion and no endpoint branch silently registered. `A_BASELINE_BIO` eligibility still needs its explicit endpoint declaration (BRIEF line 11; END lines 64–95). The frozen discrepancy priority at END lines 80–88 is not replaced by reader preference.
- **Timing and selection:** no inherited three-month threshold, date precision assumption, archival eligibility, lesion priority or repeat tie-breaker. Establish the applicable source-backed policy before outcome-based selection; unestablished fields remain unresolved (BRIEF line 30; COMPAT lines 25–27). A1 windows and pair estimands are outside this review.
- **Identity and episode:** do not mint canonical IDs from legacy hash prefixes or duplicated labels; do not assign response across episodes. Shared DAV evidence-backed aliases and binding grains remain controlling (E lines 2, 4; COMPAT line 15; REL lines 7–11).
- **Measurement and methods:** targeted-panel description, feature presence, legacy G7 or a declared `UNKNOWN` unit does not qualify a score, continuous/count model, comparator or missing-feature policy. Unknown scale remains blocked; no new numerical or named-method default is selected (ASSAY lines 40, 97–101; COMPAT line 23; E lines 7, 10).
- **Protection, admission and release:** metadata curation is recorded separately from molecular–outcome exposure; no retrospective untouched-test status, protected-role assignment, overlap resolution, V7 admission or V8/V9 release follows from a procedural pass (REL lines 19, 23; ADMIT lines 57–69; BRIEF lines 9, 33, 36).

## Review disposition and remaining scope

The useful historical constraints should be retained: author rules where authorized source bytes reside, freeze evidence questions before reading, preserve unresolved assertions, keep readers blind until first-pass sealing, retain disagreements, and export only the approved narrow document (PROC lines 12–21, 29–40, 87–96). P01–P08 specify what must be made explicit around those constraints for the current review.

This independently authored document completes **documentation review only**. It offers concrete proposed contracts for a later bounded synthetic implementation brief, without authorizing that implementation or asserting a current executable defect. Any later software work must first agree its exact contract and remain invented-data-only; any actual source review needs separately authorized custody and authenticated evidence. Historical receipts remain historical, frozen scientific specifications remain unchanged, and all source-admission, matrix-release, statistical-release and biological-validation claims remain unestablished by this review.
