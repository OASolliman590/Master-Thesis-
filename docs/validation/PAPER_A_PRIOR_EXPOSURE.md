# Paper A prior-exposure audit

**Status: PROPOSED_INCOMPLETE; user acceptance is still required.** This audit preserves the 20 signed `DEVELOPMENT` cohorts and the `UNTOUCHED_FINAL_TEST` role for `imvigor210`. It makes no admission, role, comparator, or independence decision.

**Evidence cutoff: 7 November 2026.**

## Scope and method

The audit covers exactly the 21 cohorts in the 2 Nov 2026 acquisition-close decision. It records dated project exposure declarations separately from published comparator use, source-family overlap, exact-patient overlap, training/tuning evidence, and final-test protection. `PRIOR_SOURCE_FAMILY_USE_CONFIRMED` means the publication or author code documents use of that source family; it does not establish that the comparator was trained or tuned on those patients. `UNVERIFIED` is retained wherever the evidence does not settle the question. Absence from an inspected publication is not evidence of independence.

Sources were limited to patient-free project decisions/specifications and coordinator publication-provenance notes. No cohort data, patient/source tables, runtime objects, checkpoints, expression values, outcomes, or scores were accessed; no downloads or new publication browsing occurred for this audit. The existing Braun/CheckMate025 project-history entry is recorded in the TSV and cited in `specs/amendments/2026-11-05-prostate-state-and-causal-evidence/DEVIATIONS.md`. It records the allowed aggregate class-count review and accidental `Tumor_Shrinkage` load without a feature association. This report adds no counts or incident.

## Evidence findings

- **Lin 2026:** the final paper reports a 59-gene signature validated on 1,383 baseline tumours across 19 cohorts ([primary PubMed record](https://pubmed.ncbi.nlm.nih.gov/42679812/)). The exact 19-cohort bulk roster remains **UNVERIFIED**. The 1,988-tumour preprint is a different reported population and is not substituted ([bioRxiv revision 3](https://www.biorxiv.org/content/10.1101/2024.06.30.601413v3)). Zenodo record 19586163 describes single-cell/spatial resources, not the final bulk roster ([author Zenodo record](https://zenodo.org/records/19586163)). No exact bulk-roster locator has been identified. If one is identified, its locator must be reported before any data are accessed; no cohort membership is inferred from common ICI datasets.
- **Subramanian 2023:** primary indexed Methods confirm source-family use for Gide, Hugo, Liu, Van Allen, Nathanson/GSE165278, Mariathasan/IMvigor210, Kim, and Braun; Motzer is outside this roster ([primary article](https://pmc.ncbi.nlm.nih.gov/articles/PMC9873950/)). This establishes published source-family use only, not exact patient overlap or training/tuning.
- **COMPASS 2026:** Figure 2 confirms Riaz, Hugo, Liu, Van Allen, Kim, Gide, Rose/GSE176307, and IMvigor source-family use ([primary article](https://www.nature.com/articles/s41591-026-04502-7)). The signed batch decision documents the Rose lineage. Exact patient intersections and method-specific checkpoint training remain unverified.
- **TIDE/Jiang:** primary indexed evidence confirms Riaz, Hugo, Van Allen, and GSE93157 source-family use ([primary article](https://pmc.ncbi.nlm.nih.gov/articles/PMC6487502/); [reference list](https://www.nature.com/articles/s41591-018-0136-1); [GSE93157 series citation metadata](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE93157)). This is not evidence of exact patient overlap or training membership.
- **quanTIseq:** Finotello 2019 explicitly analyses GSE91061/Riaz ([primary article](https://pmc.ncbi.nlm.nih.gov/articles/PMC6534875/)); the signed Paper A specification also records this reuse. Riaz has confirmed source-family reuse in that report; exact patient intersection and training/tuning status remain unverified. Other cohort-level quanTIseq exposure remains unverified.
- **PredictIO:** author validation code contains Kim/Gide labels in `code/PredictIO_Validation/PredictIO.R` and `code/PredictIO_Validation/run_PredictIO.R`. The cited-source-to-local-family mapping and exact patient membership remain unverified ([primary publication](https://pubmed.ncbi.nlm.nih.gov/36055464/); [author repository](https://github.com/bhklab/PredictIO)). No comparator is admitted by this audit.
- **Ayers GEP, TIS, and CYT source overlap:** exact source-family intersections remain unverified for every row. The final weighted Ayers GEP is distinct from the expanded 18-gene score ([primary JCI article](https://www.jci.org/articles/view/91190)). The exact TIS implementation remains unresolved under `specs/A/COMPARATOR_REGISTRY.md`. CYT remains the formal fixed comparator, but its overlap with the current roster is unverified ([Rooney et al.](https://doi.org/10.1016/j.cell.2014.12.033)).

Dated project declarations are `METADATA_ONLY` for Riaz (29 Oct 2026), Hugo and GSE168204 (29 Oct 2026), and Liu, Gide, and IMvigor210 (30 Oct 2026). These are declarations, not exhaustive independent historical audits. All other undocumented project histories remain `UNVERIFIED`.

## Unresolved overlap and protection

Melanoma overlap among Riaz, Hugo, Liu, Gide, and GSE168204 remains explicitly flagged in `docs/decisions/BATCH2_CBIOPORTAL_20261030.md`; exact patient intersections and independence are unresolved. The Snyder/Nathanson relationship attached to GSE165278 is a source-family relationship, not proof of independent patients. Absence of shared local identifiers cannot establish independence. The TSV marks exact-patient overlap and training/tuning evidence `UNVERIFIED` throughout. The exact Lin roster locator, PredictIO source-to-local mapping, and exact intersections for the confirmed comparator source families are still missing.

`imvigor210` remains `UNTOUCHED_FINAL_TEST` with the existing information barrier: no expression-response relationship, DEG table, or prediction inspection before authorized final evaluation. Published comparator use of IMvigor does not alter its project role or prove the exact patient intersection. All 20 development roles are also preserved.

## Proposed conclusion

**Gate 3 evidence is incomplete.** The exact Lin final 19-cohort bulk roster is missing, and exact patient overlaps and method-specific training/tuning remain unresolved across comparator families. Cohort-level exposure declarations are not exhaustive historical audits. No claim of full exposure independence is supported. User acceptance of the eventual audit conclusion remains needed.

CIBERSORTx is **not run**. The real A-P2 rebuild remains deferred; this provenance audit did not score any cohort or inspect restricted runtime/source data.

## Evidence references

The row-level dated evidence references and repository-relative paths are in [PAPER_A_PRIOR_EXPOSURE.tsv](PAPER_A_PRIOR_EXPOSURE.tsv). Scope and role authority: `specs/A/SPEC_v2.md` sections 7, 8, 11; `specs/A/VALIDATION_AND_SPLITS.md`; `specs/A/COMPARATOR_REGISTRY.md`; `specs/A/NOVELTY_AND_CLOSEST_STUDIES.md`; `docs/cohorts/REGISTRY.tsv`; `docs/decisions/A_ACQUISITION_CLOSED_20261102.md`; the dated batch/signature decisions; and `docs/research/A_DAV_RIAZ_DECISIONS_20261026.md`.
