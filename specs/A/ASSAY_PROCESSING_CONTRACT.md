# Assay-specific processing and measurement contract

## Fail-closed routing

A source receipt declares modality, platform, feature system, unit, transform, normalization, processing history and outcome-aware preprocessing. Unknown or contradictory unit/transform blocks affected analysis; value ranges alone cannot establish provenance. All raw/source values and missingness are preserved. Gene annotation must be versioned; ambiguous mappings are not silently summed. Any deterministic mapping is fixed before outcome analysis.

| Deposited object | Permitted primary route | Prohibited shortcut |
|---|---|---|
| Nonnegative integer gene counts | Count-aware NB model; library offsets/normalization and dispersion documented | Rounding TPM/FPKM to create counts |
| Estimated transcript/gene counts | Documented import with transcript-to-gene map and effective-length/offset handling supported by backend | Pretending fractional estimates are raw observed counts |
| TPM | Source-qualified continuous-expression route; predictor transform frozen; CYT uses unlogged abundance | Feeding TPM to DESeq2 as counts |
| Complete gene FPKM matrix | Continuous route; conversion to TPM only when complete source universe and normalization are documented | Conversion from a preselected/partial gene table |
| Known normalized log expression | Linear model on declared scale; source-normalization limitations recorded | Guessing a logarithm base or reversing unknown transforms |
| Microarray probes/intensities | Platform/annotation-specific linear-model branch with fixed probe resolution | Fabricated TPM or applying RNA-seq abundance scores by name |
| Single-cell/spatial/protein/methylation objects | Separate corroboration branch with modality-appropriate contract | Adding cells or unpaired modalities to clinical patient N |

## CYT and prediction compatibility

The fixed CYT comparator is sqrt(TPM_GZMA × TPM_PRF1), per the approved A-P1 contract and source registry. Both genes must be uniquely measured, finite and nonnegative. A true measured zero produces zero; missing produces unscorable, never zero. No pseudocount is added to CYT. A complete documented FPKM-to-TPM route uses TPM_g = 10^6 FPKM_g / sum_h FPKM_h over the actual complete feature universe; header-only inspection is insufficient to certify completeness. Count-to-TPM is not automatic: consistent effective lengths, quantification and gene aggregation are required. Other representations may support A-BIO without supporting A-P2/CYT.

## Feature and sample handling

Preserve matrix dimensions and exact column strings; duplicate column names, ID coercion or ambiguous joins are fatal until resolved. Distinguish technical replicates from separate lesions/timepoints. Do not fill missing cells/genes with zero. Abundance/range/log checks are diagnostic flags, not automatic reclassification. Record excluded features and mapping loss. For prediction, all filtering, variance selection, scaling, imputation parameters and feature learning are fitted within training folds; final-test expression cannot alter them. No imputation is enabled by default.

## Effect compatibility

NB log-mean ratios, mean log2(TPM+offset) differences, array log-intensity differences and standardized programme effects are different estimands even if all are labelled 'log2'. Store explicit effect_scale_id and transform/config hash. Pool only compatible scales; otherwise separate strata or a prespecified standardized-effect sensitivity. Deconvolution is an interpretation sensitivity with its own input/licence/reference validation, not a universal correction.
