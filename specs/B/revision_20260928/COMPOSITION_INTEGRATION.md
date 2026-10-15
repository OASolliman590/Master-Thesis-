# Cellular composition, multi-omics and mechanistic triangulation

PROPOSED. Each extra analysis must resolve a named ambiguity in B03 or a declared prostate contrast. No method earns a main-figure panel merely by running successfully.

## Three composition roles

**ESTIMATE:** use immune/stromal scores for coarse RNA-based context [R17]. Do not call them detailed cell fractions or orthogonal validation of an RNA programme. ESTIMATE-derived purity cannot silently replace the non-RNA B-P baseline.

**CIBERSORT/CIBERSORTx:** qualify one implementation/version, reference matrix/hash, assay scale, transformation, batch mode and quantile-normalisation setting per source [R18]. LM22, if selected, addresses its supported leukocyte reference space, not a full malignant/stromal prostate census. Relative fractions must state their denominator. RNA-seq and author-normalized arrays need compatible input contracts; missing reference genes and unrepresented malignant states may bias estimates. Exact executable settings remain UNFROZEN rather than guessed. CIBERSORTx-inferred cell-specific expression is inferred, not independently measured scRNA-seq.

**MethylCIBERSORT:** retain the accepted methylation-derived sensitivity [R07]. Verify prostate malignant/reference suitability, cell categories, 450K overlap, processed-beta compatibility and reference provenance. Record the overlap between its deconvolution CpGs and primary/candidate methylation predictors. A predefined disjoint-probe sensitivity may address direct measurement coupling where estimable; it does not eliminate biological dependence. Do not say the method reconstructs each immune cell type's methylome or establishes tumour-intrinsic methylation.

For each estimate retain fit diagnostics, missing/unrepresented categories, reference coverage and denominator. Do not interpret technical fit p-values as biological proof of correct cell fractions. Avoid silently truncating negative estimates or renormalizing incompatible outputs without a documented method rule.

## Adjustment and compositional data

Primary association, non-RNA-purity sensitivity and RNA/methylation-composition sensitivities are distinct estimands. A cell fraction may be a confounder, mediator, consequence, or noisy proxy; conditioning can also introduce selection bias. Consequently neither attenuation nor persistence identifies causality.

Fractions constrained to sum to one cannot all be included with an intercept as independent predictors. Freeze a reduced basis or justified log-ratio representation, reference component and zero-handling rule. Never choose the representation with the most favourable methylation coefficient. Compare nested sensitivity models on the same eligible patients, then show broader availability analyses separately. Report coefficient changes with uncertainty, not a binary “composition corrected” stamp.

## Direct regulatory models before latent factors

Start with explicit gene/region models and competing explanations. Show promoter methylation, locus CNA, measured damaging variants/LOH where available, tumour content and composition side by side. A missing mutation call is not evidence of an intact gene. A diploid gene is not proof of reversibility. miRNA predictions alone do not establish regulation; require a named target mechanism and measured support when making stronger claims.

A promoter beta average can conceal opposite CpG behaviours or alternative promoters. Preserve per-probe coverage and a predeclared diagnostic view. Published domain annotations on sparse arrays are annotation/proxy evidence, not newly measured whole-genome methylation domains. Histone marks and accessibility should retain their actual assay and specimen scope [R01,R05,R06,R12].

Protein evidence requires analyte identity, antibody/peptide specificity, platform normalization and target coverage. RPPA does not necessarily measure every APM component. Phosphosite abundance, protein amount, enzyme activity and surface antigen presentation are different measurements. CPC protein and methylation assays can corroborate within a patient, but do not increase independent patient N.

## MOFA2

Optional question: is there stable shared molecular variation linking defined immune programmes with methylation/genetic/protein views beyond obvious purity, missingness or batch axes? Fit within a coherent prostate context first. Specify transformations, likelihoods, view scaling, feature-selection rules, factor-number rule, seeds and convergence before execution [R19]. Avoid selecting methylation features using the same outcome association then presenting factor–outcome association as independent evidence.

Report variance explained by factor/view, loadings, factor stability under seeds and patient resampling, technical/purity associations and missing-view patterns. Supported missing-view handling does not make unlinked cohorts paired. Factor signs are arbitrary; orientation must be declared. Refitting MOFA in an external cohort is a new fit, not validation of frozen loadings; any projection procedure requires explicit implementation and scale verification.

Retain a factor only if its evidence contributes something the direct models do not. “Epigenetic resistance factor” is not an admissible label merely because methylation contributes variance. No requirement to include MOFA in the final manuscript.

## DIABLO and supervised integration

DIABLO is supervised integration implemented in mixOmics [R20], not an additional independent method beside mixOmics. Remove it from the B core. An RNA-derived pseudo responder label is not a legitimate independent target for RNA-containing multi-omics prediction. A future observed clinical/molecular classification task requires its own target, leakage controls and matched-patient baseline comparison. Actual paired multi-omics ICI-response prediction belongs in a qualified A cohort, not TCGA pseudo validation.

## Single-cell and spatial

Use patient × annotated-cell-type pseudobulk or a justified donor-aware model for inferential comparisons [R22]. Record malignant-cell annotation provenance, cell-state definition, per-donor coverage and dissociation/enrichment methods. Missing cell populations cannot be replaced with gene-expression zeros. Bulk low expression plus localization to sparse immune cells suggests a composition explanation; it does not prove that all observed bulk differences are composition-only.

For spatial data distinguish cell-resolved protein, segmented cells, mixed RNA spots, tumour regions and donors. Exclusion requires measured location relative to tumour boundaries and an appropriate density/area context. Low RNA, fewer sampled cells or a difference in stromal content is not itself exclusion. Region/spot replication is nested within patients; include geometry and donor uncertainty.

Hirz and Kiviaho provide useful sources but reused single-cell datasets must be deduplicated [R09,R10]. A newer HTAN processed spatial release is a conditional lead, not a prerequisite [R16]. Overlap, treatment state, tumour annotations, analyte coverage and donor counts must be established before any of these sources can resolve a B hypothesis.

## Carry-forward scope, not silent cancellation

The existing planned Ayers T-cell-inflamed GEP-18, full official IFNG Hallmark and HOPE_18 secondary programmes remain in scope. Recover actual weights/signs/normalisation for Ayers, a pinned full Hallmark release and a defensible explicitly named HOPE scoring definition. HOPE's prognostic origin does not make it an observed ICI-response signature. Their historical methylation-extended prediction analyses remain conditional; valid uncertainty and multiplicity procedures must be frozen before execution. No percentile-bootstrap CI is converted into an invented p-value.

Retain M0–M6 and the user-requested approved-immunotherapy-target curation as documented exploratory scope. The latter requires drug, authority, dated label, indication, modality, target identity and mechanism/direction; checkpoint candidates alone are not an approval registry. These panels do not automatically join P, the A-derived programme family, or the C query. Any future narrowing of accepted scope requires an explicit decision rather than omission from a figure.
