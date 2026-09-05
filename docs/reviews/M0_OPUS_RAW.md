# Independent Opus Review — M0 Evidence Audit

**Reviewer:** Claude Opus 4.6 (Thinking), via Antigravity CLI
**Date:** 5 September 2026
**Scope:** Read-only review of the programme foundation and first evidence reports. No files edited, no commands run, no credentials accessed, no analysis jobs started.
**Status of this document:** Reviewer findings and recommendations. Not an approval of any specification, endpoint or scientific claim.

---

## 1. Files Actually Reviewed

| File | Bytes | Role in review |
|---|---:|---|
| [AGENTS.md](file:///E:/Master_Thesis/master-thesis/AGENTS.md) | 1,133 | Root agent instructions |
| [CONTEXT.md](file:///E:/Master_Thesis/master-thesis/CONTEXT.md) | 3,254 | Glossary and term definitions |
| [README.md](file:///E:/Master_Thesis/master-thesis/README.md) | 1,314 | Project overview |
| [.gitignore](file:///E:/Master_Thesis/master-thesis/.gitignore) | 955 | Repository boundary rules |
| [PROGRESS.md](file:///E:/Master_Thesis/master-thesis/docs/execution/PROGRESS.md) | 2,729 | Milestone tracker |
| [SOURCE_RECONCILIATION.md](file:///E:/Master_Thesis/master-thesis/docs/execution/SOURCE_RECONCILIATION.md) | 6,267 | Reconciliation register |
| [SETUP_PROPOSAL.md](file:///E:/Master_Thesis/master-thesis/docs/execution/SETUP_PROPOSAL.md) | 5,197 | Environment and fleet setup |
| [fleet.approved.json](file:///E:/Master_Thesis/master-thesis/docs/execution/fleet.approved.json) | 297 | Lane configuration |
| [pending_validation.json](file:///E:/Master_Thesis/master-thesis/docs/execution/pending_validation.json) | 676 | Capability gaps |
| [B_paired_prostate.md](file:///E:/Master_Thesis/master-thesis/docs/research/B_paired_prostate.md) | 12,603 | Paper B evidence report |
| [C_immune_context.md](file:///E:/Master_Thesis/master-thesis/docs/research/C_immune_context.md) | 9,944 | Paper C immune-context report |
| [C_pharmacology_contracts.md](file:///E:/Master_Thesis/master-thesis/docs/research/C_pharmacology_contracts.md) | 21,351 | Paper C pharmacology report |
| [domain.md](file:///E:/Master_Thesis/master-thesis/docs/agents/domain.md) | 464 | Domain docs pointer |
| [issue-tracker.md](file:///E:/Master_Thesis/master-thesis/docs/agents/issue-tracker.md) | 864 | Issue workflow |

**Metadata manifests inspected** (not line-by-line but structurally):
- [summary.json](file:///E:/Master_Thesis/master-thesis/docs/research/B_paired_prostate/summary.json) (31,680 B) — TCGA/CPC-GENE intersection counts
- [provenance.json](file:///E:/Master_Thesis/master-thesis/docs/research/B_paired_prostate/provenance.json) (2,009 B) — retrieval URLs and hashes
- [verified_coverage_summary.json](file:///E:/Master_Thesis/master-thesis/docs/research/C_pharmacology_contracts/verified_coverage_summary.json) (14,386 B) — LINCS gene tiers, prostate coverage, PRISM dictionaries
- [phase2_prostate_coverage.json](file:///E:/Master_Thesis/master-thesis/docs/research/C_pharmacology_contracts/phase2_prostate_coverage.json) (2,319 B) — per-drug signature conditions

**Not reviewed** (limitation): git commit history (permission denied), `.delegate/` contents, any historical spec-kit documents referenced as "existing Paper3/Paper4 docs/spec.md" or "preregistration.md", the submitted protocol PDF, wet-lab v1/v2 plans, and any files outside this repository. Claims about those documents are taken from SOURCE_RECONCILIATION.md's citations; I cannot independently verify their content.

---

## 2. Prioritised Findings

### Finding 1 — CRITICAL: Paper A has no evidence report and no data source identified in the repository

**Location:** [README.md L7](file:///E:/Master_Thesis/master-thesis/README.md#L7), [SOURCE_RECONCILIATION.md L26](file:///E:/Master_Thesis/master-thesis/docs/execution/SOURCE_RECONCILIATION.md#L26), [PROGRESS.md L15](file:///E:/Master_Thesis/master-thesis/docs/execution/PROGRESS.md#L15)

**Observation:** Paper A ("immune-signature robustness, clinical endpoints and transferability") is described in the README and SOURCE_RECONCILIATION frontier but has no `docs/research/A_*.md` report, no metadata manifest, and no identified ICI-treated cohort. The reconciliation frontier mentions "retain clinical-score robustness and prostate transferability scope" and that "the narrowed CYT endpoint was a proposal, not approval," but no factual source audit establishes which public ICI cohorts exist, what response definitions they use, or how many independent patients they contain.

**Rationale:** Without even a metadata-level feasibility check, Paper A's primary endpoint cannot be grilled. The programme describes four papers sequentially, but the first paper's data foundation is entirely undocumented. This is the largest gap in M0.

**Recommendation:** Before any A endpoint discussion, produce a bounded A evidence report identifying candidate ICI cohorts, their response definitions, sample sizes, overlap, and data access status — at the same documentation standard as the B and C reports.

---

### Finding 2 — CRITICAL: Paper D has no evidence report and no benchmark dataset identified

**Location:** [README.md L10](file:///E:/Master_Thesis/master-thesis/README.md#L10), [SOURCE_RECONCILIATION.md L29](file:///E:/Master_Thesis/master-thesis/docs/execution/SOURCE_RECONCILIATION.md#L29)

**Observation:** Paper D ("virtual-cell perturbation benchmarking") is described as conditional on an "independent measured perturbation benchmark." The reconciliation frontier says to "pin a checkpoint, assay-compatible independent test conditions and pretraining exclusions; complete the conditional design without pretending the benchmark exists." No `docs/research/D_*.md` report exists. No candidate virtual-cell model, checkpoint, or benchmark dataset is identified.

**Rationale:** The conditional design framing is appropriate, but it means D currently contributes zero factual evidence to M0. The gap is acknowledged but not bounded: what needs to be true for D to become feasible, and what is the decision gate to descope it?

**Recommendation:** Create a minimal D evidence report that identifies the candidate virtual-cell model(s), their pretraining data, and at least one candidate independent perturbation benchmark with access status. Define an explicit go/no-go gate with a calendar deadline.

---

### Finding 3 — HIGH: Metadata counts are clearly distinguished from usable observations, but one remaining conflation risk

**Location:** [B_paired_prostate.md L7](file:///E:/Master_Thesis/master-thesis/docs/research/B_paired_prostate.md#L7), [B_paired_prostate.md L39](file:///E:/Master_Thesis/master-thesis/docs/research/B_paired_prostate.md#L39)

**Observation:** The B report is commendably careful: "497 TCGA-PRAD primary-tumour cases" is qualified as "pre-QC case/patient-code intersections, not a promise of 497+210 final patients." The 210 CPC-GENE pairs are "pre-QC patient-code matches, not verified same tissue aliquots." The table distinguishes "verified records" from "distinct unit and overlap" from "appropriate role."

**Remaining risk:** The report states "501 shared primary-tumour sample IDs belong to 497 shared cases: keep all associations in the manifest and choose a predeclared one-specimen-per-case rule only after portion/aliquot and QC inspection." This is correct methodology. However, the report does not yet surface the magnitude of the replicate problem in CPC-GENE: GSE107298 has 394 records for 286 patient codes, meaning ~108 records are replicates or reanalyses. The report mentions "300 records with explicit Reanalysis relations" but does not reconcile these two numbers (394 total, 300 reanalysis-flagged, 286 unique codes). This arithmetic deserves explicit resolution.

**Recommendation:** In the next B milestone, produce a reconciled replicate table: for each CPCG code, how many methylation records exist, how many are flagged as reanalysis, and which is the proposed representative. The 394/300/286 numbers need a consistent accounting.

---

### Finding 4 — HIGH: Association vs. causality boundaries are well-drawn in text but the design pipeline has no formal causal-claim firewall

**Location:** [CONTEXT.md L29](file:///E:/Master_Thesis/master-thesis/CONTEXT.md#L29), [B_paired_prostate.md L71](file:///E:/Master_Thesis/master-thesis/docs/research/B_paired_prostate.md#L71), [SOURCE_RECONCILIATION.md S08–S09](file:///E:/Master_Thesis/master-thesis/docs/execution/SOURCE_RECONCILIATION.md#L20-L21)

**Observation:** The glossary explicitly defines "methylation-associated regulation" as requiring consideration of alternative explanations and warns that "bulk anticorrelation alone does not prove causal silencing." S08 and S09 in the reconciliation table resolve the boundaries correctly. The B grilling ledger states "Use 'associated'; reserve causal/mechanistic support for relevant independent experiments."

**Gap:** These are textual commitments. No specification or checklist yet exists that would enforce claim-level language review at manuscript stage. The Guo2023 counterexample (domain hypomethylation with repression) is an excellent inclusion, but it is documented as a narrative warning rather than as a formal design constraint with a testable gate (e.g., "if >X% of significant associations are positive-direction, the manuscript must discuss domain-level mechanisms").

**Recommendation:** When B's spec is written, include a claim-boundary checklist that maps each planned figure/table to the maximum permitted inference level (association / prediction / mechanism / causation) with the evidence type required for each.

---

### Finding 5 — HIGH: LINCS prostate coverage is alarmingly narrow for a three-drug programme

**Location:** [C_pharmacology_contracts.md L24–L32](file:///E:/Master_Thesis/master-thesis/docs/research/C_pharmacology_contracts.md#L24-L32), [verified_coverage_summary.json](file:///E:/Master_Thesis/master-thesis/docs/research/C_pharmacology_contracts/verified_coverage_summary.json), [phase2_prostate_coverage.json](file:///E:/Master_Thesis/master-thesis/docs/research/C_pharmacology_contracts/phase2_prostate_coverage.json)

**Observation:** The verified Phase II prostate chemical signatures are:
- Decitabine: **15 signatures, all PC3**, 7 conditions (6 doses × 24h + 1 × 6h)
- Entinostat: **15 signatures, all PC3**, 7 conditions (6 doses × 24h + 1 × 6h)
- Tazemetostat: **0 signatures** in Phase II

No VCAP, LNCaP, DU145, or 22Rv1 chemical signatures were found. The 2020 release signature count for tazemetostat remains unknown. This means the reversal scoring arm of Paper C can only be executed for two of three drugs, in one prostate line, from a single LINCS release. The report correctly flags this, but the specification impact is severe: "drug-class mixed models remain conditional on enough independent compounds and overlapping conditions; neither metadata breadth nor random effects can repair perfect class–drug–dose confounding."

**Furthermore:** Each of the 15 decitabine/entinostat signatures has 1–3 underlying `distil_id` values (the report's `profile_counts` field). Two signatures per condition at 24h means these are MODZ-collapsed from 2–3 profiles each. These are not 15 independent biological experiments.

**Recommendation:** This is a design-level decision gate. Before C's spec is frozen, the user must decide: (a) can C's reversal scoring proceed with only PC3 + two drugs from Phase II, supplemented by checking the 2020 release for tazemetostat and additional lines? (b) What is the minimum number of independent conditions required for a credible reversal claim? (c) Is a single cell line sufficient, or must the design require at least two prostate lines?

---

### Finding 6 — HIGH: Nine of ten immune sentinel genes are inferred, not measured, in L1000

**Location:** [C_pharmacology_contracts.md L9](file:///E:/Master_Thesis/master-thesis/docs/research/C_pharmacology_contracts.md#L9), [verified_coverage_summary.json L8–L48](file:///E:/Master_Thesis/master-thesis/docs/research/C_pharmacology_contracts/verified_coverage_summary.json)

**Observation:** Only PSMB8 is a landmark (directly measured) gene. CXCL9, CXCL10, HLA-A/B/C, B2M, TAP1, TAP2, PSMB9 are all "best inferred." The report correctly flags this: "A landmark-only sensitivity is useful but cannot be presented as a fully measured test of that entire immune panel."

**Rationale:** Best-inferred genes in L1000 are computationally predicted from landmark measurements using a linear model trained on the GEO reference compendium. For immune genes that may have nonlinear, context-dependent regulation in cancer cell lines under epigenetic perturbation, the inference accuracy is not guaranteed. A reversal score built primarily on inferred values has a fundamentally different evidence tier than one built on measured values.

**Recommendation:** The spec must (a) report the measured/inferred tier for every query gene, (b) include a sensitivity analysis using landmark-only genes, and (c) explicitly state that reversal of inferred gene expression is a computational prediction, not a direct observation. Consider whether the Frangieh Perturb-CITE-seq data (which does measure these genes directly, albeit in melanoma) can serve as an orthogonal measured reference.

---

### Finding 7 — MEDIUM: CLUE retirement creates a reproducibility advantage but the local scoring contract is unspecified

**Location:** [C_pharmacology_contracts.md L7](file:///E:/Master_Thesis/master-thesis/docs/research/C_pharmacology_contracts.md#L7), [C_pharmacology_contracts.md L36–L46](file:///E:/Master_Thesis/master-thesis/docs/research/C_pharmacology_contracts.md#L36-L46)

**Observation:** The CLUE retirement (effective January 2026) means hosted tau queries are no longer available. The report recommends "local WTCS as the reproducible core." The scoring contract section correctly distinguishes WTCS, NCS and tau, and warns that "an arbitrary permutation percentile is not interchangeable with official tau."

**Gap:** The report recommends local WTCS but does not specify: what null distribution will be used for significance, how query coverage (measured vs. inferred genes) affects the enrichment statistic, or whether the planned implementation will use the published cmapPy/cmapR packages or a custom implementation. These are design choices that must be made before the spec is frozen.

**Recommendation:** Define the exact scoring procedure: input gene list format, gene-space filtering, enrichment implementation, null model, multiple-testing correction, and reporting format. Pin the implementation to a specific library version or a custom implementation with unit tests against published reference examples.

---

### Finding 8 — MEDIUM: The L1000CDS2 IFNG ligand reference is from breast cell lines, not prostate

**Location:** [C_immune_context.md L12](file:///E:/Master_Thesis/master-thesis/docs/research/C_immune_context.md#L12), [C_immune_context.md L52](file:///E:/Master_Thesis/master-thesis/docs/research/C_immune_context.md#L52)

**Observation:** The report identifies the IFNG ligand entry in the L1000CDS2 22-entry list and correctly warns: "The paper associates the ligand references with LJP4 and describes the experiment context as six breast cell lines." The grilling ledger states the reference cannot be labelled prostate-specific.

**Rationale:** Using a breast-derived IFNG consensus signature as a prostate immune-context reference introduces a tissue-context assumption. The signature payload has not been retrieved, so constituent samples, exposure conditions, and gene-level content are unknown. This is an open factual question, not yet a design decision.

**Recommendation:** Retrieve the IFNG payload, examine its constituent profiles, and decide whether a breast-derived consensus IFNG signature is appropriate as one corroboration arm for prostate immune context, or whether a prostate-specific IFNG reference is required (and from which source).

---

### Finding 9 — MEDIUM: TISMO and Frangieh access status create paper-blocking uncertainties for C

**Location:** [C_immune_context.md L11](file:///E:/Master_Thesis/master-thesis/docs/research/C_immune_context.md#L11), [C_immune_context.md L56](file:///E:/Master_Thesis/master-thesis/docs/research/C_immune_context.md#L56)

**Observation:** TISMO's current release metadata has not been retrieved; only publication-era totals (605 in-vitro, 1,518 in-vivo samples) are cited. The Frangieh/SCP1064 data requires authentication for original download; the scPerturb harmonised release is available on Zenodo but is a ~1.46 GB h5ad file that has not been downloaded or inspected. These are the two principal immune-context corroboration sources for C, and neither has verified current coverage, sample metadata, or eligible independent units.

**Rationale:** The report correctly labels these as "unknown" rather than "available." But the cumulative effect is that Paper C's immune-context arm depends on three resources (Frangieh, TISMO, L1000CDS2 IFNG) for which access, coverage and independence are all unverified. This is not a criticism of the audit's honesty — it is a measurement of remaining risk.

**Recommendation:** Prioritise retrieving Frangieh via the Zenodo route (public, no auth required) and TISMO sample metadata. These are bounded data-access tasks, not analyses, and should be completed before C's spec is frozen.

---

### Finding 10 — MEDIUM: DrugBank unavailability is correctly recorded but its impact on C's annotation layer is unquantified

**Location:** [C_pharmacology_contracts.md L72](file:///E:/Master_Thesis/master-thesis/docs/research/C_pharmacology_contracts.md#L72)

**Observation:** DrugBank academic downloads are paused. The report records `access_status=provider_paused` and recommends ChEMBL as a parallel source. ChEMBL identity checks succeeded (three molecules verified).

**Gap:** The report does not specify which annotations C requires from DrugBank that ChEMBL cannot provide (e.g., pharmacokinetic parameters, clinical dosing, metabolic pathways). If the clinical-feasibility assessment depends on DrugBank-specific fields, ChEMBL may not be a sufficient substitute.

**Recommendation:** Enumerate the specific annotation fields needed from DrugBank for C's clinical-feasibility assessment. For each, determine whether ChEMBL, FDA labels, or published PK studies can substitute. Do not assume DrugBank will resume academic access within the thesis timeline.

---

### Finding 11 — MEDIUM: Internal consistency of entinostat dose discrepancy

**Location:** [C_pharmacology_contracts.md L28–L29](file:///E:/Master_Thesis/master-thesis/docs/research/C_pharmacology_contracts.md#L28-L29), [phase2_prostate_coverage.json L97–L101](file:///E:/Master_Thesis/master-thesis/docs/research/C_pharmacology_contracts/phase2_prostate_coverage.json#L97-L101)

**Observation:** The report prose states entinostat has "6h at 2 µM, three signatures" for the 6h condition. The JSON confirms `"dose": "2.0 um"` for entinostat's 6h condition. For decitabine, the 6h condition is at 10 µM. This is internally consistent between prose and JSON. However, neither the report nor the summary explicitly flags that the two drugs' 6h conditions use different doses (2 µM entinostat vs. 10 µM decitabine), which means dose-matched cross-drug comparisons at the short timepoint are not possible in Phase II.

**Recommendation:** Note this dose mismatch explicitly in the C coverage contract. If dose-matched cross-drug comparison is a planned analysis, it can only use 24h data.

---

### Finding 12 — LOW: RWPE1 tumour classification needs curation

**Location:** [C_pharmacology_contracts.md L24](file:///E:/Master_Thesis/master-thesis/docs/research/C_pharmacology_contracts.md#L24), [verified_coverage_summary.json L117–L138](file:///E:/Master_Thesis/master-thesis/docs/research/C_pharmacology_contracts/verified_coverage_summary.json#L117-L138)

**Observation:** The LINCS 2020 cell dictionary labels RWPE1 as `cell_type: "tumor"`. The report correctly flags: "RWPE1's tumour label in that dictionary needs biological curation before inclusion as a cancer model." RWPE1 is an HPV-18-immortalised but non-tumorigenic prostate epithelial line (Cellosaurus CVCL_3791). Including it as a "prostate cancer" model in sensitivity analyses would be misleading.

**Recommendation:** Flag RWPE1 as a non-malignant control in any prostate panel. This is a factual correction, not a design choice.

---

## 3. Unresolved Facts vs. Design Choices

The following table classifies every major open item I identified. Items marked **Fact** require data retrieval or lookup before they can be settled. Items marked **Design** require a user/advisor decision. Items marked **Both** have a factual prerequisite followed by a design decision.

| ID | Item | Classification | Current status | Blocking paper(s) |
|---|---|---|---|---|
| U01 | Which public ICI cohorts exist for Paper A, with response definitions and sample sizes | **Fact** | No A evidence report exists | A |
| U02 | Paper A primary endpoint: CYT vs. alternative robustness measure | **Design** | Proposal only, not approved (SOURCE_RECONCILIATION L26) | A |
| U03 | CPC-GENE replicate accounting: reconcile 394 records / 300 reanalysis / 286 codes | **Fact** | Partially documented in B report L37 | B |
| U04 | CPC-GENE covariate completeness (Gleason, age, purity, CNV) | **Fact** | Acknowledged as unchecked (B report L49) | B |
| U05 | Paper B primary molecular target and model comparison | **Design** | Unresolved (SOURCE_RECONCILIATION L27) | B |
| U06 | Cross-platform endpoint scale (RNA-seq vs. array) for B validation | **Both** | Design requirement stated, no method selected (B report L47) | B |
| U07 | Paper C primary endpoint: reversal discovery vs. measured corroboration | **Design** | Unresolved (SOURCE_RECONCILIATION L28, S05) | C |
| U08 | Tazemetostat LINCS 2020 signature existence | **Fact** | Unknown; Phase II has 0 signatures (C pharma L30) | C |
| U09 | Minimum prostate lines/drugs for credible reversal claim | **Design** | Not specified | C |
| U10 | IFNG ligand payload content and prostate applicability | **Fact** | Payload not retrieved (C immune L12) | C |
| U11 | Frangieh eligible independent biological units | **Fact** | Cell counts known, replicate/experiment structure unknown (C immune L14) | C |
| U12 | TISMO current release coverage and sample metadata | **Fact** | Only publication totals available (C immune L11) | C |
| U13 | DrugBank-specific annotation requirements vs. ChEMBL substitutability | **Both** | Access paused; field-level needs unspecified (C pharma L72) | C |
| U14 | Local WTCS scoring implementation and null model | **Design** | Recommended but unspecified (C pharma L40) | C |
| U15 | DepMap prostate model/expression/methylation matched coverage | **Fact** | Portal not successfully accessed (C pharma L50) | C |
| U16 | GDSC data file access and license terms | **Fact** | 403 error; unresolved (C pharma L66–68) | C |
| U17 | Virtual-cell model identity and benchmark dataset | **Fact** | No D evidence report exists | D |
| U18 | Paper D go/no-go gate and calendar deadline | **Design** | Not defined | D |
| U19 | Clinical PK evidence source for exposure feasibility | **Fact** | "Outside this bounded audit" (C pharma L95) | C |
| U20 | Eight-gene programme coverage in TCGA/CPC-GENE matrices | **Fact** | "Metadata pairing alone cannot guarantee feature coverage" (B report L51) | B, C |

---

## 4. Assessment: Can M0 Be Committed as Explicit Work-in-Progress?

> [!IMPORTANT]
> **Yes — M0 can and should be committed as explicitly labelled work-in-progress**, subject to the conditions below. This is not an approval of any specification, endpoint, or scientific claim.

### What M0 demonstrably contains

1. **A functioning project structure** with clear root instructions ([AGENTS.md](file:///E:/Master_Thesis/master-thesis/AGENTS.md)), a precise glossary ([CONTEXT.md](file:///E:/Master_Thesis/master-thesis/CONTEXT.md)), and documented agent/workflow conventions.

2. **Unusually disciplined epistemic hygiene.** Across all documents reviewed, I found consistent and correct separation of:
   - Metadata counts vs. usable observations (B report throughout; C pharma coverage tables)
   - Association vs. causation (CONTEXT.md L29; SOURCE_RECONCILIATION S08–S09; B report L71)
   - Database availability vs. measured coverage (C pharma L24, L50, L91)
   - Study overlap vs. independence (B report L37–L41; C immune L55; C pharma L96)
   - Clinical response vs. immune phenotype (CONTEXT.md L19–L23; SOURCE_RECONCILIATION S08)

3. **Two substantive evidence reports** (B paired prostate, C pharmacology contracts) with verifiable provenance (SHA-256 hashes, request URLs, saved metadata files) and one access-status report (C immune context).

4. **A reconciliation register** with 10 resolved/open items and per-paper frontier descriptions.

5. **Appropriate scope control**: the registered protocol's approval status is not assumed; historical work is not treated as validated; agent agreement is not treated as evidence.

### What M0 does not contain (and must not claim to)

- No Paper A or Paper D evidence report
- No frozen primary endpoint for any paper
- No production code, analysis output, or test suite
- No reviewed specification package for any paper
- No independent scientific review (this document is the first)
- No Opus review was previously recorded, despite being listed as pending

### Conditions for commit

The commit message and PROGRESS.md should state:

1. M0 is a **setup and first-evidence milestone**, not a specification or analysis milestone.
2. Papers A and D have **no evidence report** yet; their feasibility is not established.
3. Papers B and C have **metadata-level evidence reports** that document data access feasibility but not matrix-level verification, QC, or scientific results.
4. All four primary endpoints remain **unresolved design choices**.
5. This Opus review was conducted and its findings are recorded; they are **recommendations, not approvals**.

---

## 5. Recommended Next Gates (Sequenced)

The following is a feasibility-informed sequencing recommendation, not an approved plan.

### Gate 1 — Complete the evidence report portfolio (est. 1–2 weeks at 5h/day)

| Task | Paper | Type | Prerequisite |
|---|---|---|---|
| Produce A evidence report: identify candidate ICI cohorts, response definitions, sample sizes, access | A | Fact | None |
| Produce D evidence report: identify candidate virtual-cell model, checkpoint, benchmark dataset, access | D | Fact | None |
| Resolve CPC-GENE replicate accounting (394/300/286) | B | Fact | None |
| Retrieve Frangieh h5ad from Zenodo; inspect sample/replicate metadata | C | Fact | None |
| Retrieve TISMO current sample metadata | C | Fact | None |
| Check LINCS 2020 tazemetostat signature existence | C | Fact | None |
| Retrieve DepMap 26Q1 model/expression metadata | C | Fact | None |

### Gate 2 — Primary endpoint decisions (est. 1 week)

Each paper needs exactly one primary endpoint decision. These are design choices that require user/advisor input, informed by Gate 1 facts:

| Paper | Decision required |
|---|---|
| A | Robustness measure and transferability target: which score, which cohort, what constitutes success? |
| B | Primary molecular target, model form, and what the validation ΔR² is compared against |
| C | Whether the primary endpoint is reversal rank, measured corroboration enrichment, or a combined score |
| D | Go/no-go on virtual-cell benchmarking; if go, the benchmark, metric, and pretraining exclusion rule |

### Gate 3 — Specification drafts (est. 2–3 weeks)

Write one spec per paper with: estimand, data sources (pinned), inclusion/exclusion, analysis plan, claim boundaries, sensitivity analyses, and registered hypotheses. These require review before production coding.

### Gate 4 — Sequential production implementation

Given 4 months remaining and the constraint that "only one paper's production implementation is active at a time," I recommend: **B → C → A → D** ordering.

- **B first** because its data sources are the most concretely verified and its design is most self-contained.
- **C second** because it depends on B's disease signature and has the most complex data integration.
- **A third** because it requires ICI cohort data that may need longer access processes.
- **D last** because it is conditional and may be descoped.

> [!WARNING]
> Four months at five hours daily is approximately **430 hours**. Four full papers from unresolved endpoints through production implementation, manuscript-quality figures, and write-up is ambitious. If Gate 1 reveals that A or D data access is infeasible, early descoping preserves quality for B and C.

---

## 6. Limitations of This Review

1. **No access to historical spec-kit documents.** SOURCE_RECONCILIATION references "existing Paper3/Paper4 docs/spec.md" and "preregistration.md" from prior work. I could not verify those citations independently; I relied on SOURCE_RECONCILIATION's characterisations.

2. **No access to the submitted protocol or wet-lab plans.** Claims about these documents (S01–S03) are taken on trust from SOURCE_RECONCILIATION.

3. **No git history inspected.** The permission-denied error on `git log` means I cannot verify the commit sequence, authorship, or whether any files were modified since their stated creation dates.

4. **No matrix-level data verification.** I inspected metadata manifests (summary.json, provenance.json, verified_coverage_summary.json, phase2_prostate_coverage.json) but did not independently run the retrieval scripts or verify SHA-256 hashes against source servers.

5. **Single-session review.** This review was conducted in one reading pass of the available repository contents. A deeper review would cross-reference specific GDC case IDs, CPC-GENE patient codes, and LINCS signature metadata against the source SOFT/JSON files to verify the computed counts.

6. **No domain expertise claim.** I am an AI reviewer applying logical consistency checks, not a prostate cancer biologist, epigeneticist, or clinical trialist. Domain-specific assessment (e.g., whether PC3 is an appropriate model for immune-gene reversal studies, or whether 210 CPC-GENE patients provides adequate power) requires human expert review.

---

*This document is a deliverable of the independent Opus consultation requested in [PROGRESS.md L20](file:///E:/Master_Thesis/master-thesis/docs/execution/PROGRESS.md#L20). Integration and final assessment are owned by the Astra orchestrator. No files were edited, no commits made, no credentials accessed, and no analysis jobs started.*
