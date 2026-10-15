# Cellular, composition and orthogonal evidence

RNA is the clinical discovery backbone. Additional modalities support interpretation under their own release; their absence does not block the RNA core. Report modality totals, linked patients, same-timepoint pairs, same-specimen pairs, endpoint-eligible pairs and longitudinal pairs separately. A study label shared by RNA/methylation files is not a patient crosswalk. No unpaired data are combined into synthetic patients and no missing modality is imputed.

## Method qualification

For ESTIMATE, CIBERSORT/CIBERSORTx, EPIC or another chosen method, archive the original publication and actual code/service version, reference matrix, gene identifiers, input unit/platform support, licence/access, transformations, quality thresholds and output definition. No implementation is automatically admitted by being named in this kit. Do not pass arbitrary log values to a method requiring unlogged abundance, or call a custom immune average ESTIMATE/TIDE. Quantile normalization and batch correction are method/platform-specific choices, not universal defaults.

ESTIMATE is an aggregate stromal/immune signal, not detailed cell fractions. Reference-based fractions are model-dependent estimates, not cell counts. Composition-adjusted response associations are sensitivity analyses on matched patients. Attenuation can reflect mediation, collinearity, measurement error or loss of precision, not necessarily confounding; persistence does not establish tumour-cell causality. Report unadjusted, adjusted and matched-subset results with uncertainty and rank/covariate checks.

## Orthogonal evidence roles

Verified RNA/methylation pairs can support regulatory associations, not automatic causal silencing. Protein measurements may corroborate pathway abundance; chromatin accessibility provides context; single-cell or sorted-cell sources may localize expression; spatial evidence can characterize compartments/proximity. The patient remains the independent clinical unit. Cells/spots/fields are nested observations; use patient-aware or pseudobulk designs for clinical associations and report both patient and measurement counts.

Data from different cancers, regimens or timepoints remain transport evidence, not replication of the exact clinical estimand. Small paired subsets used to develop features cannot also confirm them. Reserved final-test patients remain protected even when encountered through another modality.

## Outputs

biological_context.tsv separates immune function, proposed cellular localization, composition sensitivity, same-specimen versus orthogonal support, source population, direction, conflicting evidence and uncertainty. Programme labels are hypotheses unless directly supported. Each figure panel must state what the modality establishes and what it cannot. No branch creates a tumour-intrinsic restoration target solely from a bulk immune marker.
