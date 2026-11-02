# Paper B secondary B-ICIM: immune-gene methylation in ICI-treated tumours, v2, signed 2 Nov 2026

**Status: SIGNED by the user on 2 Nov 2026 ("I sign it"), as v2.** It follows the user's requests of 2 Nov 2026 ("Draft it with Astra"; centre it on immunity and the 11 panels; then "investigate all the genes related to the anti-cancer effect of immunity or the success of immunotherapy, including the targets of immunotherapy"), and Astra's high review (`REVIEW_ASTRA_HIGH.md`, verdict "add minimal version"), whose defaults are adopted here. It adds one secondary to Paper B. **B-P is unchanged and isolated.** No B-ICIM gene, probe, sign, QC choice or result may modify B-P, use CPC-GENE, or rewrite the TCGA-only hand-off. B-MX and B-V are unchanged.

## Question (outcome-free)
**Is promoter DNA methylation associated with the expression of immune-related genes, after tumour-purity adjustment, in pretreatment tumours from patients who then received ICI, and does the pattern resemble TCGA?**

This is association consistency across cohorts. It is not transport of a frozen predictor, not an ICI-induced effect, and not a benefit analysis. **No clinical-benefit analysis, classifier or cutpoint search** is part of B-ICIM.

## Gene universe (frozen before any TCGA or ICI association is examined)
Scope: "a frozen, curated universe of immune-function, immunotherapy-response and immunotherapy-target genes", including suppressive and resistance genes as well as favourable immune activity.

| Tier | Definition | Approximate size |
| --- | --- | ---: |
| 0 | B-P antigen-presentation primary: isolated, unchanged | 8 |
| 1 | The 11 locked panels, memberships as registered, with the official Hallmark IFN-gamma membership frozen first; M5 and M6 genes reported individually; CYT stays a comparator | 250-300 |
| 2 | **Immunotherapy targets:** human molecular targets from a pinned CRI immuno-oncology landscape export, reconciled with IUPHAR/BPS; approved status from dated FDA/EMA labels, investigational status from named trials. Checkpoint blockade, co-stimulation, cytokine pathways, innate-immune targets, cell-therapy and bispecific targets. Always includes PDCD1, CD274, CTLA4, LAG3, HAVCR2 and TIGIT; ICOS, CD40, TNFRSF4 and TNFRSF9 are audited. Drug-binding targets are tagged apart from ligands, mediators and biomarkers; therapy-targeted tumour antigens form their own tag | 100-300 |
| 3 | **Wider immune biology:** the union of the ImmPort immune-related gene list, TISIDB immunomodulator/chemokine/receptor lists, and a fixed signature whitelist (Ayers GEP, Rooney CYT, Charoentong immunophenoscore components, HOPE, and the official IFN-gamma, IFN-alpha and inflammatory-response Hallmarks) | 2,000-3,000 |

- **Combination:** union, canonical human gene IDs, deduplicated loci, every source tag kept, reporting precedence Tier 1 → 2 → 3. Literal lists, releases, hashes, inclusion reasons and an evidence cutoff of 2 Nov 2026 are frozen. Later evidence cannot silently expand this version.
- **Excluded:** wholesale ImmuneSigDB (C7) unions, all GO "immune" descendants, unrestricted network neighbours, genome-wide TIDE weights, any gene reported significant in an ICI study, and generic anticancer drug targets without an immunotherapy mechanism. Patient-specific neoantigens and non-gene targets stay outside the gene-level universe. Published signatures derived from these same cohorts are never presented as independent validation.
- **Multiplicity:** one BH FDR 5% family across all eligible unique gene × study tests in Tiers 1-3, with the same adjusted value reported wherever a gene appears. There are no per-pathway or per-source resets. Panel summaries are descriptive.

## Data and admission
- **Start with Jung 2019 only** (NSCLC; methylation GSE119144, EPIC; RNA GSE135222, signed), chosen because it has the most candidate pairs and admitted RNA, not because of its results.
  - Use only the 27 candidate pretreatment pairs; the 33 methylation-only patients cannot enter.
  - Response labels are not needed, so missing labels never remove an eligible patient.
- **Cho 2020** (GSE126043 / GSE126044) and **Krakow** (GSE264158 / GSE213145) are deferred and are not extended automatically.
- **Admission needs** a source-supported patient–specimen–timepoint crosswalk, one baseline specimen per patient, duplicate handling and RNA–DNA specimen compatibility. Sex concordance is an exclusion check only, not identity proof. Genotype concordance is used only if existing measurements make it straightforward. Unresolved pairs are excluded.
- **Protected families:** nothing from an A final-test family (IMvigor210) is inspected, in any modality.

## Measurement (frozen with the gene universe)
- IDAT to beta with one pinned pipeline (SeSAMe: noob, pOOBAH masking, dye-bias correction), version recorded.
- **Promoter definition:** one annotation-defined promoter aggregate per eligible gene, using the **common 450K–EPIC probe set**, so that the same definition applies in TCGA and in the ICI cohort. Platform-appropriate masks are pinned.
  - Coverage is measured against the fixed eligible probe set; probe counts are reported and single-probe genes are flagged.
  - The most negatively correlated promoter is never chosen; positive associations and unresolved mappings are kept.
- **RNA:** normalised gene-level abundance under a frozen procedure, which is not B-P's within-sample rank.
- **Purity:** a qualified non-RNA estimate, with any probe overlap with the methylation data disclosed. If no defensible purity estimate exists, the adjusted analysis is unavailable and unadjusted results are descriptive only.
- **TCGA benchmark:** LUAD and LUSC kept separate, on the same probe definition.

## Estimation
- Within the study: rank association of gene expression with promoter methylation, adjusted for purity (and for histology or preservation only if frozen and estimable). The unadjusted association is a sensitivity. Uncertainty comes from a patient-level bootstrap that keeps each patient's whole gene vector, with TCGA uncertainty included in comparisons.
- Panel summaries (median association, share of genes in the TCGA-expected direction) are descriptive, on exactly matched gene sets. No independent-gene binomial tests, no combined estimates across studies, and no new composite "methylation scores".

## Reporting and wording
- One association and coverage figure, descriptive panel comparisons against TCGA, and the full tested family with adjusted and unadjusted values. Intervals are always shown; nulls are "inconclusive".
- The thesis may say: **"B-ICIM assesses whether promoter DNA methylation is associated with immune-related gene expression, after tumour-purity adjustment, in pretreatment tumours from patients receiving ICI, providing cross-cancer molecular context rather than evidence of causal regulation or benefit attributable to immunotherapy."**
- Signed rule 7 wording applies. There are no claims of silencing, prostate ICI response or reversibility.

## Budget (stop-loss)
20 hours for Jung: about 4 for feasibility, 4 for the universe and measurement freeze, 6 for processing and QC, 3 for estimation and 3 for review and reporting. Work stops if the prerequisites do not fit.
