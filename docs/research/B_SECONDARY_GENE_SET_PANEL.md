# Paper B secondary gene-set panel: source and freeze recommendation

Date: 6 September 2026 (Africa/Cairo). Status: bounded scientific recommendation, **not a membership or analysis freeze**. No CPC outcome value, gene-set score, model fit, or cohort comparison was inspected or computed.

## Recommendation

Keep the accepted one-primary design unchanged. For the small prespecified secondary family, carry forward **two conditional programs only**:

1. **Ayers T-cell–inflamed GEP-18.** The recovered 18 symbols exactly match the published membership. This asks whether the frozen B methylation program adds prediction of a bulk T-cell-inflamed/adaptive-resistance state beyond its matched baseline. It is biologically distinct from the eight-gene antigen-presentation primary outcome because exact gene overlap is 0/8, although it is still a mixed-cell-origin tumor-microenvironment readout.
2. **Official MSigDB `HALLMARK_INTERFERON_GAMMA_RESPONSE`, not the recovered mini.** Retrieve and freeze one exact official release of the full 200-gene reference set. This asks whether the same frozen B methylation program adds prediction of a broad IFN-gamma-induced transcriptional response beyond its matched baseline. The current membership overlaps the proposed primary expression program at 6/8 genes (`HLA-A`, `HLA-B`, `B2M`, `TAP1`, `PSMB8`, `PSMB9`), so the interpretation must be “broader IFNG response,” not an independent antigen-presentation construct; a sensitivity score excluding those six members should be specified before outcomes and remain secondary to the intact reference score. The current MSigDB card defines the set as genes upregulated in response to IFNG and identifies 200 members; the Hallmark paper describes these sets as refined, coherently expressed representations of biological states. [Official IFN-gamma Hallmark](https://www.gsea-msigdb.org/gsea/msigdb/cards/HALLMARK_INTERFERON_GAMMA_RESPONSE.html), [Liberzon et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC4707969/)

This is deliberately a two-program panel. None of the nine recovered epigenetic composites has an exact source-backed membership plus a coherent direction. Promoting one now would turn an attractive label into an unregistered measurement choice. They remain exploratory until resourced and canonicalized.

## Why the recovered names cannot be taken at face value

The Ayers paper did not define an unweighted GMT average. It used elastic-net penalized regression across pembrolizumab-treated tumors, retained 18 genes, used the final nonzero regression coefficients as weights, and computed a weighted sum of housekeeping-normalized expression. Seventeen genes were favorable and **CD276 was negative**. Thus the recovered membership is reusable, but its unoriented rank-mean implementation is not the published GEP. The coefficient vector and platform-transport normalization still have to be recovered and frozen. [Ayers et al., JCI 2017](https://www.jci.org/articles/view/91190)

The local `HALLMARK_INTERFERON_GAMMA_RESPONSE_MINI` is 10 genes, while the official reference is 200. Only 7/10 local symbols occur in the current official membership; `IFNG`, `HLA-DRA`, and `GBP1` do not. The local `HALLMARK_TNFA_SIGNALING_VIA_NFKB_MINI` is a 10-member subset of the official 200-member TNF/NF-kappa-B set, but no source-based rule explaining that subset was recovered. Both must be called **custom mini-panels**, not Hallmark gene sets. [Official IFN-gamma set](https://www.gsea-msigdb.org/gsea/msigdb/cards/HALLMARK_INTERFERON_GAMMA_RESPONSE.html), [official TNF/NF-kappa-B set](https://www.gsea-msigdb.org/gsea/msigdb/cards/HALLMARK_TNFA_SIGNALING_VIA_NFKB.html)

The label `C7_T_CELL_EXHAUSTION_CORE` is also custom. MSigDB C7 is a collection of thousands of immune cell-state and perturbation signatures, usually tied to a named experimental comparison; it is not a single generic exhaustion panel. No matching source comparison or exact membership was recovered for this local 15-gene composite. [MSigDB collections](https://www.gsea-msigdb.org/gsea/msigdb/human/collections.jsp), [C7/ImmuneSigDB methods](https://www.gsea-msigdb.org/gsea/msigdb/collection_details.jsp)

`HOPE_18` is the other exact published membership, but it answers the wrong confirmatory question. Kondou et al. first selected 62 genes upregulated in PD-L1+/CD8B+ immune-type-A tumors, then retained 18 individual genes associated with overall survival after median splits and log-rank tests. It is a pan-cancer **prognostic selection**, not a validated ICI-response score. Moreover, HAVCR2 was adverse while the other 17 univariate directions were favorable, so an all-positive, unweighted GMT score misstates the paper. [Kondou et al., Table III and methods](https://www.spandidos-publications.com/10.3892/mco.2021.2395)

## Source-and-coverage table

“Audited” below means only already-verified, outcome-blind measurement evidence. The CPC matrix audit tested all 213 columns for the eight primary genes only; the historical Brainarray audit mapped those same eight genes only; the promoter audit was likewise restricted to those eight. It would be false precision to infer coverage for the other members from a 24,598-row matrix or a 24,937-ID annotation intersection.

| Recovered set | Source/direction status | Existing coverage evidence | Disposition |
|---|---|---|---|
| `T_CELL_INFLAMED_GEP_18` (18) | Exact Ayers membership; published signed weighted score, recovered GMT unoriented | 0/18 members previously audited for full CPC/platform coverage; promoter coverage not relevant unless predictor scope expands | Secondary 1, conditional |
| `C7_T_CELL_EXHAUSTION_CORE` (15) | Custom; no exact C7 source; mixed receptors/regulators/effectors; no sign | 0/15 audited | Exploratory/defer |
| `HALLMARK_INTERFERON_GAMMA_RESPONSE_MINI` (10) | Custom; not official 200; only 7/10 are current official members | 0/10 audited | Do not use as named; replace with versioned official set for secondary 2 |
| `HALLMARK_TNFA_SIGNALING_VIA_NFKB_MINI` (10) | Custom subset; all 10 occur in official 200, but subset rule/sign absent | 0/10 audited | Exploratory/defer |
| `EPIGENETIC_IMMUNE_PRIMING` (18) | Custom chromatin-regulator/immune-effector mixture; no common sign | Only B2M/TAP1: CPC finite and one-to-one on both v18 platforms; inspection-only promoter candidates 14/83 respectively; remaining 16 unknown | Exploratory/defer |
| `EPIGENETIC_CHECKPOINT_REGULATION` (15) | Custom regulators/signaling/checkpoint mixture; no common sign | 0/15 audited | Exploratory/defer |
| `PRC2_IMMUNE_TARGETS` (12) | Custom PRC2-plus-target mixture; direction absent; 6/8 primary overlap | HLA-A/B/C, B2M, TAP1/2 verified in CPC and both v18 platforms; inspection-only promoter candidate counts 3/8/12/14/83/75; other 6 unknown | Exploratory mechanism crosswalk only |
| `SWI_SNF_ICB` (10) | Custom complex-member plus CIITA/IRF1 mixture; no sign | 0/10 audited | Exploratory/defer |
| `DNMT_IMMUNE_LOCI` (11) | Custom DNMT/TET plus immune-target mixture; regulator abundance and target activation have no defensible shared sign | 0/11 audited | Exploratory/defer |
| `HISTONE_WRITERS_ICB` (10) | Custom writers/erasers/coactivators/IFNG-effectors mixture; title and membership do not define one process | 0/10 audited | Exploratory/defer |
| `RETROELEMENT_SENSING` (12 raw tokens; 11 loci) | Custom mixed RNA/DNA sensing and effector set; `CGAS`=`MB21D1`; `TMEM173` is alias of `STING1`; no sign | 0/12 raw tokens audited; alias-sensitive coverage unknown | Exploratory until canonicalized and resourced |
| `T_CELL_EXHAUSTION_EPIGENETIC` (12) | Custom regulators/receptors/differentiation mixture; no exact source/sign | 0/12 audited | Exploratory/defer |
| `T_CELL_MEMORY_EPIGENETIC` (10) | Custom immune-cell-state panel; no exact source/sign | 0/10 audited | Exploratory/defer |
| `HOPE_18` (18) | Exact prognosis-selected membership; mixed survival direction; not ICI response | 0/18 audited | Exploratory prognostic context only |

The machine-readable version is [source_and_coverage.tsv](B_secondary_gene_set_panel/source_and_coverage.tsv). Existing promoter counts are inspection-only unmasked +/-1500-bp candidates, not a frozen `Q`.

## Identifier, origin, and construct cautions

Raw symbols must be retained alongside a versioned canonical identifier. The clearest defect is `RETROELEMENT_SENSING`: current NCBI records make `CGAS` the approved symbol with `MB21D1` as an alias, so the GMT counts one locus twice; `STING1` is current and `TMEM173` is an alias. [NCBI CGAS](https://www.ncbi.nlm.nih.gov/gene/115004/), [NCBI STING1](https://www.ncbi.nlm.nih.gov/gene/340061)

The biological idea is real but the exact composite is not validated. DNA-demethylating-agent studies support an MDA5/IFIH1-MAVS-IRF7 viral-mimicry axis and interferon outputs; one study found STING knockdown did not blunt the Aza response in its models. That evidence does not validate combining RNA sensing, cGAS-STING DNA sensing, transcription factors, and downstream effectors into one equal-positive 12-token score. [Roulois et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC4843502/), [Chiappinelli et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC4556003/)

Bulk-tumor scores also do not identify cell of origin. Ayers GEP and the exhaustion/memory/HOPE sets contain lymphocyte, myeloid/APC, tumor-inducible, and adaptive-resistance signals. A high score can therefore reflect abundance, activation, or both. The custom epigenetic panels add a second interpretive problem: chromatin regulator expression is not equivalent to chromatin activity, and mixing regulators with their putative immune outputs can hide opposing biology.

## Scoring contract and multiplicity

Do not reuse the historical “ssGSEA” label for a mean within-sample rank. The maintained GSVA documentation defines ssGSEA through enrichment of expression-rank distributions inside versus outside the set and filters nonmatching genes before applying size limits. Exact gene identifiers, algorithm/package version, parameters, normalization, minimum retained size, and missing-feature behavior therefore belong in the freeze. [GSVA vignette](https://bioconductor.posit.co/packages/release/bioc/vignettes/GSVA/inst/doc/GSVA.html)

The proposed secondary confirmatory family is exactly the two `Delta_R2` comparisons above. Use **Holm family-wise error control at two-sided alpha 0.05** across those two tests. The primary B-P test remains outside and prior to this family. Every secondary program gets its own matched baseline and extended model; all feature engineering, fitting, tuning, and thresholds remain TCGA-only. The Hallmark score with the six P-overlap genes removed is a descriptive robustness check, not a third confirmatory hypothesis. Exploratory sets are clearly labeled and excluded from this confirmatory family; their results cannot be used to swap a program into the family.

## Remains to freeze before any CPC outcome analysis

- Exact source bytes, release/version, identifier namespace, license/redistribution status, and SHA-256 for the Ayers and official Hallmark memberships.
- The Ayers coefficient vector and sign, housekeeping normalization, cross-platform transport rule, and deterministic missing-gene behavior. If these cannot be reproduced, use a newly named membership-only score and keep it exploratory; do not call it the published GEP.
- The official Hallmark release and exact membership, plus true ssGSEA/GSVA version and parameters. Do not substitute the local mini after seeing coverage or outcomes.
- Outcome-blind full-member finite-value coverage in CPC and mapping coverage on both historical v18 platforms. Modern aliases must not be projected onto the 2013 Entrez annotation without a recorded rule.
- Minimum retained fraction/set size and what happens when a member is absent, duplicated, retired, or ambiguous.
- The secondary outcome definitions and each matched baseline/extended model, including covariates, split/fitting rules, performance metric, uncertainty interval, and failure rule.
- A written lock that CPC outcomes cannot choose membership, signs, weights, promoter features, covariates, scoring method, or which exploratory program is reported as confirmatory.

The structured recommendation and evidence hashes are in [recommendation.json](B_secondary_gene_set_panel/recommendation.json). This deliverable does not change the primary membership, `specs/B/ANALYSIS.md`, any code, or any fleet configuration.
