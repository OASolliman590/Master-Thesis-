# Assay observations, compartment separation and model adaptation

## qPCR/omics

Retain raw Cq/Ct, reference-gene qualification, efficiency where established, detection limits and preprocessing. Model ΔCq or a justified log-expression scale with normalization uncertainty/covariance. Fold-change is not absolute RNA concentration. Cross-sectional differential expression constrains a phenotype, not all turnover rates or a causal epigenetic mechanism.

## Flow cytometry

Retain permitted FCS files, gating/compensation/QC, settings and tumour/immune labels. Absolute counts, proportions and fluorescence are different outcomes. MFI is not receptor copies/cell without calibration. Positive log-ratios require valid background/reference handling; shared controls introduce dependence. Surface-HLA is a candidate kinetic marker, not an automatically frozen primary.

## Proximal engagement and protein

Choose drug-appropriate activity/mark/target measurements. Histone acetylation, DNA methylation and target-protein loss are not interchangeable. Western densitometry needs original images, dynamic-range and loading normalization; it is not absolute concentration. Proximal change plus gene induction supports a stronger mechanistic argument than gene induction alone, but alternate stress/selection explanations remain.

## Exposure and secretion

Nominal medium additions and documented withdrawals support nominal-exposure PD. Analytical total/free medium or intracellular measurements can identify additional terms only with assay identity/limits/recovery. Do not presume a zero drug pool after washing. Secreted concentrations need medium volume, collection interval and viable-cell context before they can become secretion rates.

## Functional readout

Target-specific counts/death and immune viability/function enable separate tumour and immune contributions. Endpoint LDH or a mixed metabolic assay is not automatically a tumour-killing rate. Use the assay's spontaneous/max-release controls and denominator model. Preserve cytostasis versus death unless data only support net growth.

## Adaptation contract

For each measured y define `y=h(x,theta,assay_version)+error`; record states, units, baseline conditioning, noise model and which parameters become identifiable. Start from the released canonical simulator. Add only necessary states/observations; refit only allowed parameters. A new observation scale does not justify changing biological values until mapping uncertainty is assessed. Treat cross-drug, cell-line and recognition changes as distinct contexts with explicit transfer uncertainty.
