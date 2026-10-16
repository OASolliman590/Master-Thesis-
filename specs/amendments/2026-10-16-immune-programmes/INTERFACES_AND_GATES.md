# Shared A/A.1/B measurement and release contract

## A: baseline clinical reference

A-BIO estimates baseline response-associated programme effects with uncertainty, cohort/tumour/regimen context and contradiction. A-PRED remains a separately frozen learned product; expanding the explanatory catalogue does not silently expand its candidate feature space. A-P2 retains paired independent-test learned-minus-fixed-CYT AUROC, equal cancer weights and equal originating-study weights within cancer. A-P1 remains the fixed-score endpoint-definition sensitivity. Catalogue admission cannot unlock either analysis.

Scores require source-specific units, gene/probe mappings, duplicate resolution, full expected membership, coverage denominator and an explicit missing-feature policy. Published scores require the original coefficient vector, signs, intercept if applicable, normalization and implementation; an unweighted mean or ssGSEA is a differently named method. No silent removal of missing genes, zeros for absent genes, direction reversal after labels, or test-set normalization fitting. Official sets require release/license/source bytes; public access alone is not method admission.

## A.1: paired response-associated change

Use the same programme version, genes, score parameters and compatible measurement scale at both visits. Keep patient, specimen, treatment episode, baseline/follow-up dates, exposure, tissue site, assay and biopsy-selection records from shared DAV. Classify scheduled on-treatment, genuinely after treatment cessation and progression-triggered samples separately. Freeze allowable windows and pairing policy before analysis. Do not independently standardize each timepoint and call the difference a biological change; baseline-trained/reference-fixed transformations need justified transport.

The existing contrast registry controls: baseline R–NR; on-treatment R–NR; genuinely post-treatment R–NR; within-responder change; within-nonresponder change; and responder-minus-nonresponder change. Repeated measures require a patient-aware estimand. Cross-sectional differences are not paired changes. Response-stratified change is associative and may reflect treatment/biopsy selection; it is not a causal ICI effect. Comparative arms and dynamic prediction require their existing separate releases. Sparse/absent paired evidence remains nonestimable rather than pooled into a false longitudinal result.

## B: measured prostate molecular context

Use linked TCGA prostate RNA and measured methylation as the core, with source-matched genetic/CNA and purity/composition covariates or sensitivity analyses where genuinely available. Missing genetic data are unknown, not wild type; RNA downregulation is not a mutation, deletion or HLA-LOH call. Maintain specimen/aliquot alignment and explain subset changes. No cross-cancer pooled comparison without a declared lineage model; localized TCGA tissue cannot establish metastatic ICI response.

For each programme/locus distinguish low bulk expression, composition, measured genetic disruption, promoter methylation association, other chromatin mechanisms, and evidence of perturbational restoration. Adjusted associations do not prove cell-intrinsic silencing or reversibility. RNA-derived cell estimates may induce circular adjustment; report unadjusted and predeclared sensitivity estimands with limitations. Methylation-based fractions need their own reference and platform gates.

Keep the B-P estimand and existing proposed P/X construction and external validation policy intact; P/U/Q, assay and measurement freezes remain pending. Broader promoter mappings, probe filters, CNA/genetic inclusion and covariate models require pre-outcome freeze. No CPC outcome, A final-test label or C ranking may select these candidates. B exports a separately frozen TCGA-discovery-only, signed, uncertainty-bearing evidence table to C; programme direction, disease direction and desired perturbation direction must be separate fields.

## Common interchange fields

Each later score/effect row must carry `amendment_id`, `programme_id`, `membership_sha256`, `source_release`, `score_contract_id`, `implementation_hash`, `input_object_hash`, `assay_id`, `patient_id`, `specimen_id`, `episode_id`, `timepoint_class`, `measurement_scale`, `normalization_reference_hash`, `coverage_numerator`, `coverage_denominator`, `missing_reason`, `composition_method_id`, `claim_class`, `release_id` and `exposure_status`. Effect exports additionally carry contrast ID, eligible N by independent unit, effect scale, uncertainty, cohort/context and nonestimable reasons. Unsupported fields remain explicit null with a reason. This is an additive future interface, not a claim that existing pipeline outputs already implement it.

## Typed pending gates

| Gate | Owner | Required evidence / closure artifact | Blocked stage |
|---|---|---|---|
| G01 Source identity | Scientific curator | Primary member list or candidate-specific rationale; immutable source/version/license; coefficient/housekeeping/normalization bundle where required | Named score admission |
| G02 Measurement | Assay curator | Verified gene/probe mapping, actual coverage, scale and missingness rule per input; duplicate/alias audit; no absent-as-zero | Programme computation |
| G03 Method freeze | Scientific owner + method reviewer | Named scoring algorithm, direction, weights, normalization, reference, missing threshold, software version; no numerical default invented here | Score release |
| G04 Identity/timing | DAV curator | Patient/episode/specimen linkage, baseline or pairing windows, actual admitted roster, protected-family/test overlap audit | Branch admission |
| G05 Composition/mechanism | Domain reviewer | Reference/platform compatibility, cell-type support, uncertainty, measured genetic/purity alternatives and noncircular interpretation | Composition/mechanism claim |
| G06 Statistics/release | Scientific owner + integrator | Prespecified contrast, multiplicity family/overlap policy, precision and feasibility, fitted-only-on-development transforms, independent review and release ID | Biological analysis |

All gates are pending for new programmes. For inherited components, existing evidence remains valid at its original scope; this packet closes none of their outstanding gates. No source-specific cutoff, gene-coverage fraction, minimum N, effect threshold or multiplicity numeric setting is invented. A later freeze must declare all tested programmes, handle overlap, report null/contradictory results and prevent result-based membership changes. Test-protected families remain protected across A, A.1, B and C.
