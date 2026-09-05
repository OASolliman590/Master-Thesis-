# Independent Bounded Review — M1 Four-Paper Specification Kits

**Reviewer:** Claude Opus 4.6 (Thinking), via Antigravity  
**Date:** 6 September 2026  
**Scope:** Read-only file inspection; no commands, writes, network verification, or production tests  
**Disposition:** Advisory to the orchestrator; the orchestrator owns final judgment

---

## 1  Files Reviewed and Coverage Limits

**Directly inspected (38 files):** AGENTS.md · CONTEXT.md · docs/execution/GOAL.md · docs/execution/PROGRESS.md · specs/README.md · specs/A/{README, ANALYSIS, DISCOVERY, TRANSPORT, FIGURES, DATA(dir listing only)}.md · specs/A/tickets/ (6 ticket filenames) · specs/B/{README, ANALYSIS, TICKETS_AND_TESTS, REPRODUCE_AND_READINESS, DATA_AND_SOURCES(via subagent), VALIDATION_AND_FIGURES(via subagent), SOFTWARE_CONTRACT(via subagent), PREREGISTRATION_AND_LEDGER(via subagent), SOURCE_MANIFEST.json(via subagent)}.md · specs/C/{README, ANALYSIS, VALIDATION_AND_FIGURES, DATA(via subagent), ENGINEERING(via subagent), PREREGISTRATION(via subagent), SOURCE_MANIFEST.json(via subagent), environment.contract.json(via subagent)}.md · specs/C/tickets/ (13 ticket filenames; individual tickets via subagent) · specs/D/{README, ANALYSIS, REPRODUCE_AND_READINESS, DATA_AND_SOURCES(via subagent), VALIDATION_AND_FIGURES(via subagent), SOFTWARE_CONTRACT(via subagent), PREREGISTRATION_AND_LEDGER(via subagent), REVIEW_RESPONSE(via subagent), TICKETS_AND_TESTS(via subagent), SOURCE_MANIFEST.json(via subagent), environment.contract.json(via subagent)}.md · All 7 evidence documents in docs/research/ (via subagent).

**Not inspected in this pass:** A/DATA.md body text, A/ENGINEERING.md body text, A/PREREGISTRATION.md body text, A/REVIEW_RESPONSE.md body text, individual A ticket bodies, B SOURCE_MANIFEST.json directly (subagent-reported), C/references.bib, planning documents under docs/planning/, any pharmacology contracts doc body. The integrated draft snapshot has ~63 documents; this review covered ~38 directly plus subagent-mediated summaries of the remainder, yielding substantive coverage of all four kits but not line-level verification of every file.

**Limitation:** No external source verification was performed. Claims about LINCS2020 byte counts, CPC-GENE gene coverage, State vocabulary, etc. are assessed only against internal consistency of the documents; the reviewer did not access GEO, GDC, S3, Hugging Face, or any other external resource.

---

## 2  Prioritized Findings

### F1 — A-P1 vs A-P2 primary choice remains the critical strategic decision [A/ANALYSIS.md §5–7; A/DISCOVERY.md §7–17]
**Classification: BLOCKER (design)**

A-P1 (CYT endpoint sensitivity) is feasible on ≥2 non-prostate cohorts but its novelty ceiling is low given Kang 2023 and Luo 2022. A-P2 (discovered signature incremental discrimination) aligns with the original thesis objective but requires ≥3 independent development cohorts and separately reserved test data — neither verified today. The spec correctly leaves this open; however, no ticket can be dispatched until the choice is frozen.

**Fix:** Schedule a user decision session presenting: (a) A-P1 precision scenario at actual admitted category counts (49 GSE91061 / 89 GSE176307, with only 16/4 SD patients); (b) A-P2 feasibility audit of available cohort splits; (c) explicit novelty gap analysis versus Kang/Luo. If A-P2 splits cannot be verified within a bounded research ticket, recommend A-P1 as primary with A-P2 as declared secondary.

---

### F2 — B external Delta_R² may be estimable on ≤73 patients, not 210 [B/DATA_AND_SOURCES.md §15; B/REPRODUCE_AND_READINESS.md E4]
**Classification: BLOCKER (data)**

Only 73/210 CPC-GENE paired codes have candidate clinical covariates via the cBioPortal `-F1` route; 70 have joint grade and purity. The primary estimand requires age, Gleason, and purity. At n≤73 (before QC/focus exclusions), a bootstrap 95% CI on Delta_R² will be wide. The spec honestly flags this but has not yet assessed whether precision at this N is adequate for a meaningful scientific claim.

**Fix:** (i) Complete the research ticket B-R2 to establish the true covariate-complete N after focus/identity/QC reconciliation. (ii) Before B-R3 freeze, compute a paired-error precision scenario using TCGA development residuals to estimate anticipated CI width at realistic N values (50–73). (iii) If precision is inadequate, the spec's own narrow/combine options apply — either restrict to a reduced-baseline unadjusted analysis (secondary only) or combine B with C.

---

### F3 — B eight-gene program membership lacks formal biological citation [B/ANALYSIS.md §7]
**Classification: REFINEMENT**

The eight genes {HLA-A/B/C, B2M, TAP1, TAP2, PSMB8, PSMB9} are described as "literature-informed" but no specific citation justifies this exact membership. The spec acknowledges this. The program is biologically coherent (classical MHC-I antigen presentation pathway), but a reviewer would expect a published gene-set source or a transparent biological rationale frozen before any scoring.

**Fix:** Cite the primary biological source for this exact eight-gene set (e.g., Şenbabaoğlu et al. 2016 or a pathway database entry) or document the selection rationale as a declared design choice with the eight genes justified individually by pathway role. Freeze before B-R3.

---

### F4 — C primary anchor dose produces non-HIQ tazemetostat and only 1 collapsed signature [C/ANALYSIS.md §15; C_lincs2020_readiness.md §69]
**Classification: BLOCKER (design/data)**

At 1.11111 µM PC3/24h, tazemetostat has exactly one collapsed signature (MOAR005 project, non-HIQ) with 3 underlying wells. Entinostat has one signature with 2 wells. The spec correctly prohibits bootstrapping these as independent biological units but the resulting "descriptive estimate" for two of three drugs is a single number with no replication-based uncertainty. Furthermore, tazemetostat is confined to MOAR005 while the other drugs are in REP.A022/PBIOA022, creating irremediable project confounding.

**Fix:** (i) Accept that the primary is descriptive at the compound level with no between-drug inferential comparison — the spec already does this. (ii) Consider whether the 10 µM anchor (where all three drugs have HIQ and more signatures) should be a co-reported primary sensitivity or whether the lowest-dose rationale is worth the precision cost. (iii) Explicitly declare that tazemetostat's project isolation means any tazemetostat-specific claim is confounded. These are design choices for review, not evidence gates.

---

### F5 — C novelty depends entirely on the methylation-vs-expression query comparison [C/README.md §11; C_novelty_comparison.md]
**Classification: BLOCKER (scientific)**

Six direct precedents already combine prostate transcriptomics, CMap/LINCS, and immune annotations. The spec correctly identifies that the defensible novelty is: "does integrating patient methylation evidence change drug prioritisation relative to expression-only?" This is a testable empirical question — but if the answer is "no" or "minimally," the paper lacks standalone contribution.

**Fix:** The spec already contains the right escape hatch: combine with B if C's independent contribution is only a familiar ranked list. No action needed beyond ensuring the combine criterion is evaluated honestly after scoring rather than post-hoc rationalized away.

---

### F6 — D has zero verified qualifying prostate ground truth [D/DATA_AND_SOURCES.md §11–16; D/REPRODUCE_AND_READINESS.md G1]
**Classification: BLOCKER (data, fundamental)**

No accessible single-cell chemical-perturbation prostate response dataset has been identified. The State vocabulary lacks entinostat and tazemetostat entirely. The released Tahoe zero-shot test split contains no prostate contexts. GSE199800/GSE216053 are bulk perturbation profiles incompatible with the single-cell model input. Gate G1 is fully open and there is no identified path to closing it.

**Fix:** Maintain the complete conditional specification (the spec does this correctly). Recommend explicit deferral of D execution until an independent prostate single-cell perturbation dataset is identified or the user accepts an alternative disposition. D-I02 (non-prostate software reproduction) can proceed within a 15-hour feasibility cap to establish G7 only.

---

### F7 — D silent control fallback in State `_infer.py` creates a false-positive hazard [D_virtual_benchmark.md §31; D/SOFTWARE_CONTRACT.md]
**Classification: BLOCKER (software)**

The inspected inference code returns control-like predictions for unknown perturbation labels rather than rejecting them. A successful command exit does not demonstrate that a drug was actually supported. The spec identifies this and requires hard assertion wrappers, but no implementation exists.

**Fix:** Any D-I02 reproduction ticket must include a mandatory test: submit a known-absent drug label and verify that the adapter rejects it rather than returning a silent control prediction. This is a software invariant test, not a biological validation.

---

### F8 — B cross-platform rank-score transport is asserted but not validated [B/ANALYSIS.md §11; B/REPRODUCE_AND_READINESS.md E1]
**Classification: BLOCKER (methodological)**

The mean-percentile-rank score Y_i is invariant to monotone transforms within a sample, but TCGA uses RNA-seq TPM while CPC-GENE uses RMA microarray. Different platforms have different dynamic ranges, probe specificities, and gene-specific biases that ranks do not eliminate. The spec acknowledges this honestly but has not proposed a validation strategy for cross-platform rank comparability.

**Fix:** Before B-R3 freeze, design a bounded empirical check: compute rank distributions of the eight program genes relative to the common universe U in matched tissue from both platforms (if any TCGA/CPC overlap or a third-party matched platform dataset exists). If no empirical check is feasible, the limitation must be explicitly stated in the preregistration as a primary threat to external validity.

---

### F9 — A prostate clinical transport remains exploratory only [A/TRANSPORT.md §35; A_clinical_transfer.md]
**Classification: REFINEMENT**

COMBAT's sequential BAT/nivolumab design cannot isolate ICI efficacy. Guan 2022 has no downloadable matrix/label package. No public prostate ICI monotherapy cohort with RECIST response and matched transcriptomes has been identified. The spec correctly bounds this as exploratory, but the thesis title implies prostate transferability.

**Fix:** Ensure the manuscript framing distinguishes "molecular transport characterization" (achievable with TCGA-PRAD distributions) from "clinical transfer validation" (not achievable with current data). The prostate transport module is a legitimate thesis contribution as a boundary analysis — it becomes problematic only if overclaimed.

---

### F10 — C scorer runtime and numerical parity are completely unresolved [C/ENGINEERING.md §47; C/environment.contract.json]
**Classification: BLOCKER (implementation)**

The pinned MATLAB cmapM scorer has not been executed. AIU lacks MATLAB/Octave. Docker permissions are unverified. No Python WTCS port has been validated against reference fixtures. The environment lock is `pending`. Without a working scorer, C cannot produce its primary endpoint.

**Fix:** C-02 ticket (scorer runtime resolution) is correctly identified as an early implementation gate. It can proceed in parallel with scientific review. Options: (a) Docker container with pinned cmapM on AIU; (b) Python reimplementation validated against synthetic oracle fixtures at tolerance ≤1e-7; (c) Octave if MATLAB is unavailable. The choice is an engineering decision, not a scientific one.

---

### F11 — B CpG annotation and probe masking are not yet acquired [B/REPRODUCE_AND_READINESS.md E2; B/DATA_AND_SOURCES.md §33]
**Classification: BLOCKER (data)**

The Chen et al. cross-reactive/polymorphic probe mask has not been acquired or versioned. The per-gene common promoter CpG lists (Q_g) have not been constructed. Without these, the eight promoter methylation aggregates cannot be computed.

**Fix:** B-R1 ticket correctly identifies this as its primary deliverable. This is a straightforward research/data-acquisition task that can proceed immediately after spec review.

---

### F12 — A secondary panel risks unbounded multiplicity [A/ANALYSIS.md §41]
**Classification: REFINEMENT**

The spec requires a frozen family of M secondary tests with BH adjustment, and correctly mandates computational p=1 for non-estimable entries. However, the "fixed signature panel" membership (IFN-γ/TIS and "other documented scores") is not yet enumerated. An open-ended secondary family creates multiplicity inflation risk.

**Fix:** Enumerate and freeze the exact secondary score identities, their source implementations, and the BH family size M before any primary scoring. The spec framework is correct; it just needs the list filled in.

---

## 3  One Primary Recommendation per Paper

### Paper A — Recommend A-P1 (endpoint sensitivity) as primary unless A-P2 splits are verified within a bounded research ticket

**Tradeoff:** A-P1 is transparent, assayable, and executable on currently identified cohorts. Its novelty ceiling is modest but defensible if the concordance decomposition and prostate boundary analysis are well-executed. A-P2 has higher thesis alignment but currently unverifiable feasibility requirements (≥3 development cohorts with reserved independent test data). Choosing A-P2 today risks specifying a non-estimable primary. Retaining A-P2 as a declared secondary preserves the full scope.

### Paper B — The external Delta_R² is a defensible central endpoint; the eight-gene program is the larger concern

**Tradeoff:** Delta_R² is a well-specified incremental prediction estimand with clear interpretation. The risk is not the endpoint formula but the combination of (a) potentially small covariate-complete N (≤73), (b) unmeasured CNA confounding at HLA/B2M loci, and (c) uncertain cross-platform rank comparability. These are limitations to disclose and assess, not reasons to abandon the design. The alternative — making methylation biology the primary instead of prediction — would require causal evidence the study cannot provide. Recommend proceeding with the predictive estimand while honestly bounding mechanistic claims.

### Paper C — The descriptive WTCS anchor plus contextual validation can sustain a paper only if the methylation-vs-expression comparison produces a substantive difference

**Tradeoff:** The descriptive reversal estimate itself is achievable but trivially reproducible by anyone with LINCS access. The paper's independent contribution depends on demonstrating that patient methylation evidence materially changes drug prioritisation — a genuinely novel and testable question. If the methylation layer adds nothing, the spec's combine-with-B recommendation is correct. No design change is needed; the critical test is built into the existing spec.

### Paper D — Recommend explicit deferral of execution with preserved conditional specification

**Tradeoff:** The spec is the most rigorous conditional design in the kit, with correctly identified gates. But G1 (prostate ground truth) has no identified resolution path. Investing execution time in a paper whose fundamental input does not exist would consume the 600-hour budget without scientific output. D-I02 (non-prostate software reproduction) is the only executable D work and should be capped at 15 hours. If a compatible prostate dataset is identified during the programme, the conditional spec is ready to activate.

---

## 4  Proceed / Narrow / Combine / Defer Recommendations

> [!IMPORTANT]
> These are reviewer recommendations for the orchestrator and user to evaluate, not decisions.

| Paper | Recommendation | Condition |
|---|---|---|
| **A** | **Proceed (narrowed)** with A-P1 as primary, A-P2 as secondary, prostate as bounded exploratory | After primary choice is frozen, precision scenario computed, and ≥2 eligible cohorts verified |
| **B** | **Proceed (conditional)** | After E1–E4/E6 gates pass; explicitly narrow to covariate-complete N if ≤73 is adequate; honestly bound CNA/platform limitations |
| **C** | **Proceed (conditional), with combine trigger** | After B handoff, scorer runtime, and Level 5 matrix are resolved; combine with B if methylation contribution is not substantive |
| **D** | **Defer execution; preserve spec** | Release only D-I02 (≤15h software reproduction); reopen if qualifying prostate ground truth is identified |

---

## 5  M1 WIP Publication and B-F1 Release Conditions

### M1 as reviewed WIP

**May publish as WIP** under these exact conditions:

1. Every document is labeled `PROPOSED / NOT IMPLEMENTATION-READY` or equivalent — **currently satisfied** across all four kits.
2. No gate is claimed passed that has not actually been verified — **currently satisfied**; the progress ledger and readiness files are honest about open gates.
3. The WIP label is propagated to GitHub commit message, Notion entry, and any issue mirrors — the orchestrator must verify this at push time.
4. No production test, score, model, or biological result is reported as completed — **currently satisfied**.
5. This independent review receipt is included in the M1 record.

The draft set is an honest, well-structured work-in-progress. It does not claim false readiness and is suitable for milestone publication with the WIP designation.

### B-F1 format-only ticket release

**May be released** under these exact conditions:

1. All four specification kits have received independent review — **this review satisfies that gate** for the reviewer's bounded scope.
2. The ticket uses only Python 3.11 standard library — **specified and bounded**.
3. It accepts only the four listed uncompressed TSV fixtures — **specified; no gzip adapter, download, or preprocessing**.
4. No biological score, model, association, or scientific figure is produced — **explicitly prohibited in the ticket contract**.
5. The B-F1 acceptance criteria include adversarial negative tests (wrong SHA, unexpected row width, false missing-header repair, duplicate ID, invalid beta token, intentional prefix vs undeclared truncation, conflating detection-P with beta) — **specified**.
6. The ticket's completion cannot be counted as implementing Paper B or bypassing any biological gate (E1–E8) — **explicitly stated**.
7. The orchestrator confirms path reservations (`tools/b_formats/`, `tests/b_formats/`, `docs/validation/B_formats/`) before dispatch.
8. Real fixture redistribution terms are checked before any real data rows enter the repository.
9. The implementer returns a diff and test logs; the orchestrator owns review/commit/publication.

Under these conditions, B-F1 is a well-bounded, endpoint-independent, low-risk coding ticket suitable for first implementation after spec review.

---

> [!NOTE]
> This review assessed specification quality, internal consistency, and scientific design. It did not verify external data sources, run any computation, or approve biological science. A successful review does not mean the papers will produce positive results or merit publication — it means the designs are honest, internally consistent, and ready for the next stage of evidence resolution.
