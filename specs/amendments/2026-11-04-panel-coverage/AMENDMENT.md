# Panel coverage: two corrections and a labelled sensitivity (4 Nov 2026)

**Status: APPROVED by the user on 4 Nov 2026 (chat answer "Yes").** Amends `specs/amendments/2026-11-03-analysis-modules/SPEC.md`, effect contract. All of this was decided from gene availability only. No responder or non-responder result had been computed on real data.

## Problem

The signed rule scores a panel only with complete gene coverage. Two studies failed that rule through gene identifiers or the choice of source matrix, not because the genes were unmeasured. Other studies lack a small number of members, which removes them from the main panel synthesis entirely.

## Decisions

1. **GSE135222 identifier.** Its matrix carries CCL5 under the older Ensembl ID `ENSG00000161570`. This is recorded in `gene_aliases_addendum.tsv` in this folder. The frozen table in `2026-11-02-paper-a-validation/` stays unchanged, so A-P2 inputs and hashes stay unchanged.
2. **GSE176307 source.** A-META features for this study use the Salmon TPM matrix, as A-P2 already does, on log2(TPM+1). Patients with no TPM assay are missing, never imputed. Standard bulk QC and PCA keep the cohort-view matrix.
3. **Main rule unchanged.** Panels need complete coverage after aliases. The main results, A-P2 and the frozen predictor use only this rule.
4. **Sensitivity.** A separate unit family, `panel_coverage90`, scores a panel as the unweighted mean of its available members when at least 90% of them are available after aliases, otherwise NA. It includes complete studies too.
   - Reported as sensitivity only, labelled as such, with n_found and n_total per study.
   - Pooled and FDR-corrected only within its own family. It never replaces, or adds tests to, the main panel family.
   - It never selects or changes features.
   - An 8-gene panel needs all 8 members, because 7 of 8 is 87.5%.

## Not changed

Liu 2019 and Braun 2020 still lack CCL5 in their signed sources. The iAtlas copy of Liu remains a cross-check only, and is not used to fill the gap. Outcome steps stay locked until the numerical register is frozen.
