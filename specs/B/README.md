# Paper B — prostate immune deficits and epigenetic correlates

**Scientific aim amended, 11 September 2026:** [approved A/B reconciliation](../../docs/decisions/AB_IMMUNE_BARRIERS_20260911.md). The controlling broader question and figure plan are in [IMMUNE_BARRIER_FRAMEWORK.md](IMMUNE_BARRIER_FRAMEWORK.md): clinically anchored prostate immune deficits, epigenetic correlates, composition alternatives and candidates for restoration testing. Existing B-P is the specified confirmatory estimand within the fixed APM validation module, not proof of the whole barrier claim. W1-W7 are implemented/reviewed locally for the synthetic APM component; W8 and broader scientific modules remain pending. Historical engineering statuses below are superseded by current PROGRESS. No new score or real analysis is authorized here.

**Engineering entry point, 11 September 2026:** [WORKFLOW_IMPLEMENTATION.md](WORKFLOW_IMPLEMENTATION.md) defines the connected acquisition-to-figures coding sequence, actual interfaces, stage-specific gates and end-to-end acceptance. A connected synthetic W1-W7 APM-component workflow now exists; W8 and the broader immune-barrier analyses remain pending. Use [requirements-windows.txt](requirements-windows.txt) for the isolated Windows component environment.

**Primary decision, 6 September 2026:** the user selected **B-P, external prediction improvement**, as Paper B's single primary. The primary estimand is the independent CPC-GENE `Delta_R2=(SSE_baseline-SSE_extended)/SST` from two TCGA-fitted frozen ridge predictors. B-R is retained only as a historical alternative. Selection does not freeze the proposed program, U/Q, specimen/covariate policy, final eligible N or precision target and does not authorize a biological run. [Decision record](../../docs/decisions/B_PRIMARY_BP_20260906.md).

**Measurement evidence, 6 September 2026:** [verified source facts refining proposed platform, promoter and cellularity contracts](../../docs/research/B_MEASUREMENT_CHECKPOINT.md) refine shared gates. Annotation and measurement choices remain unselected.

**Updated closest-study boundary:** the2026 published atlas already covers prostate methylation prediction, RNA/CNA associations and purity analyses. [The current comparison](../../docs/research/B_NOVELTY_2026.md) identifies APM-specific incremental transport or adjusted replication as conditional distinctions; it does not clear novelty or select either primary. Final-study methods/cohort inventory remain to be verified.

**SELECTED PRIMARY / BIOLOGICAL INPUTS NOT FROZEN.** The B-P engine is implemented for validated feature tables and synthetic testing. No real-cohort external validation or biological conclusion is claimed. Measurement and population gates block their dependent real-cohort stages, not all software construction or permitted public-source preparation.

**Exploratory-module amendment, integrated 10 September 2026:** corrected B-KIT v0.2 admits planned secondary programs, M0-M6 and proposed extra data types to an outcome-blind registry. It does not freeze `P`, add primary predictors, authorize scores or release cohort work. See [the decision](../../docs/decisions/B_KIT_MODULES_20260907.md), [human-readable module contract](EXPLORATORY_MODULES.md), [registry](gene_set_registry.proposed.json), [schema](gene_set_registry.schema.json) and [B-G1 ticket](tickets/BG1_gene_set_registry.md).

**B-G2 implemented, 11 September 2026:** `tools.b_annotation_normalize` converts identifier sources under its plan and freeze receipts. Official real-source normalized exports and AIU validation remain pending. It does not freeze `P`/`U`/`Q` or authorize scores. See [ANNOTATION_NORMALIZATION.md](ANNOTATION_NORMALIZATION.md), [plan](annotation_normalization.proposed.json), [schema](annotation_normalization.schema.json) and [B-G2 ticket](tickets/BG2_annotation_normalization.md).

**6 September decision checkpoint:** [PRIMARY_ALTERNATIVES_PROPOSED.md](PRIMARY_ALTERNATIVES_PROPOSED.md) preserves the preselection comparison. B-P is now selected; B-R and its rank-aware inference proposal remain historical, unexecuted alternatives and cannot become co-primary or replace a null B-P result without a new explicit amendment.

## Question and thesis role

Which clinically relevant immune functions are deficient in defined prostate tumour contexts, which deficits have reproducible epigenetic correlates, and which candidates warrant restoration testing? The fixed APM validation module asks whether promoter methylation adds externally reproducible information beyond clinical and purity covariates, developing in TCGA-PRAD and evaluating frozen models in CPC-GENE. Its Delta_R2 is a molecular validation endpoint, not the entire barrier claim, an ICI-response prediction or proof of causal silencing.

B is the central patient molecular chapter. It retains the registered PRAD/LUAD contrast as a secondary tissue comparison and a frozen, discovery-only signed handoff to C. Neither the contrast nor expression–methylation anticorrelation proves that a tumour cell is epigenetically silenced. Wet-lab requirements remain separate; this kit contains no experimental procedures.

## Novelty and counterexamples

| Closest source | What already exists | Proposed contribution |
|---|---|---|
| [MethylCIBERSORT](https://www.nature.com/articles/s41467-018-05570-1), DOI 10.1038/s41467-018-05570-1 | Methylation-derived tumour composition/immune patterns | Independent prediction of a defined prostate molecular program with explicit composition limits; not a generic methylation immune score. |
| [Arbet et al., Cancer Discovery2026](https://doi.org/10.1158/2159-8290.CD-25-0761) | Broad prostate methylation heterogeneity and regulatory relationships | A narrowly specified external immune-program estimand and transparent incremental information beyond shared covariates. Exact overlap with the final selected data must be audited. |
| [Guo et al., Cell 2023](https://doi.org/10.1016/j.cell.2023.05.028) | Immune-gene repression associated with hypomethylated domains in prostate cancer | Explicitly distinguish promoter association from domain-level mechanisms and preserve both directions. Rediscovering methylation-associated immune repression alone is insufficient novelty. |

Selected directional hypothesis: external delta-R-squared is positive. A null/negative result is scientifically valid. The study may establish predictive transport on the declared molecular scale; it cannot establish independence from every unmeasured covariate, cellular causality or ICI sensitisation. A conditional standalone manuscript decision follows the actual evidence and closest-study comparison, not the presence of a spec.

## Current evidence changing feasibility

The verified metadata route is **497 TCGA cases** and **210 CPC-GENE patient-code pairs**, before specimen reconciliation/QC. Actual headers support the code coverage. The original clinical table now supplies **114 candidate code matches**:73 with original-study assay/protocol support and41 code-only bridges;96 lack this original-table bridge. Individual focus/aliquot linkage and an acceptable specimen policy remain unresolved. Qpure is present for72 of the73 stronger candidates, not a final eligible N; the portal field formerly called WGS purity is quarantined as SNP-call agreement. Gene-level external copy number is not established. A complete AIU expression audit verified all eight proposed genes as unique gene-ID rows, each finite in213 samples (24,598 feature rows;32,357,821 compressed bytes). No expression matrix or Y score was retained. The common TCGA/CPC annotation universe, promoter coverage and cross-platform scale remain unresolved. The adjusted primary is conditional;210 is not its final validation N. See DATA_AND_SOURCES and the source-resolution reports.

## Requirements and kit map

Research users must be able to inspect source-specific patient/sample counts, trace reanalyses, reproduce ranks and promoter mappings, distinguish prediction from mechanism, see negative associations, audit held-out outcome access, and reconstruct the C handoff without using CPC-GENE outcomes.

| GOAL deliverable | Document |
|---|---|
| 1 Scope, thesis mapping, novelty, claims | README |
| 2 Coverage/manifest/mapping/real evidence | DATA_AND_SOURCES.md; SOURCE_MANIFEST.json |
| 3 Exact proposed primary analysis | ANALYSIS.md |
| 4 Validation/leakage boundaries | VALIDATION_AND_FIGURES.md |
| 5 Four figures | VALIDATION_AND_FIGURES.md |
| 6 Preregistration, ledger, glossary, citations | PREREGISTRATION_AND_LEDGER.md |
| 7 Architecture, environment, schemas | SOFTWARE_CONTRACT.md |
| 8 Tickets | TICKETS_AND_TESTS.md |
| 9 Tests | TICKETS_AND_TESTS.md |
| 10 Reproduction/readiness | REPRODUCE_AND_READINESS.md |
| Exploratory-module amendment | EXPLORATORY_MODULES.md; gene_set_registry.proposed.json; gene_set_registry.schema.json |

| Annotation-normalization plan | ANNOTATION_NORMALIZATION.md; annotation_normalization.proposed.json; annotation_normalization.schema.json; tickets/BG2_annotation_normalization.md |

**Proceed criteria:** all source/scale/covariate/precision/review gates pass. **Narrow proposal:** explicitly restrict external inference to a verified covariate-complete subset if sufficiently precise and scientifically representative; do not pretend that decision is already accepted. **Combine proposal:** if B supplies credible associations but C lacks independent standalone differentiation, consider an integrated chapter/manuscript. **Defer an analysis:** when its mandatory covariates or independent data remain missing; continue unaffected design work. None of these recommendations cancels B without user acceptance.
