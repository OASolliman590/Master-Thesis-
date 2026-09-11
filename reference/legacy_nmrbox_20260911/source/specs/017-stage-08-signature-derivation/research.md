# Research: Spec 017 — Stage 08 Signature Derivation

Companion to `spec.md`. This captures the current-state audit and decisions for continuing the RNA-seq downstream path.

## 1. Current-State Audit

- The Stage 08 spec was still a stub: `spec.md` existed, while `plan.md`, `research.md`, `benchmarks.md`, and `quickstart.md` were missing.
- The current context lock points to `cmd_signature_derive` in `pipeline/cli.py` and tiered FDR/effect thresholds.
- The known scientific risks are:
  - signature selection on the same data later described as validation;
  - an effect-size floor that is not interpretable if Stage 06/07 effects are still mixed-scale;
  - insufficient explanation for what Tier 1, Tier 2, and Tier 3 are meant to support.

## 2. Decision

Stage 08 must be treated as the next active RNA-seq maturation cycle after corrected Stage 06/07 outputs and Stage 09 verification. The work should not jump directly to TCGA, visualization, reports, Tahoe, AlphaGenome, or wet-lab handoff until the signature registry is frozen.

## 3. Contracts

### Signature threshold config

`signature_thresholds.yaml` should define:

```text
tier_id
max_fdr
min_abs_effect
min_meta_cohorts
max_heterogeneity
allowed_analysis_families
intended_use
```

### Signature registry

`signature_registry.tsv` should include:

```text
signature_id
signature_version
analysis_id
analysis_family
timing_label
contrast_direction
gene_id
gene_symbol
effect
effect_scale
standard_error
fdr
meta_cohort_count
contributing_cohorts
heterogeneity_metric
evidence_tier
module_id
module_assignment_method
derivation_mode
validation_allowed_label
run_root
```

### LOCO/nested manifest

`signature_loco_derivation_manifest.tsv` should include:

```text
fold_id
heldout_cohort_id
training_cohorts
analysis_id
signature_id
threshold_config
output_path
blocked_reason
```

## 4. Scientific Validity

- A signature derived from all available samples can support discovery and wet-lab prioritization, but not independent validation.
- LOCO or nested derivation is the minimum defensible path for independent-style evaluation when fully external cohorts are unavailable.
- TCGA can receive and project the signature, but it remains prognostic/projection evidence because TCGA-PRAD is not an ICI-treated response cohort.
- Tier 1 should be conservative enough for wet-lab handoff. Tier 2 can support broader biological interpretation. Tier 3 should be marked exploratory/sensitivity only.

## 5. Open Choices For Implementation

- Whether default Tier 1 should require `min_meta_cohorts >= 2` or allow a single high-quality cohort when the corrected slice is underpowered.
- Whether heterogeneity should be a hard gate or an annotation in early runs.
- Whether module assignment should prefer curated gene sets only or allow GO/MSigDB-assisted assignment as a secondary label.
- Whether LOCO evaluation should be mandatory for all analysis families or only for families with at least two eligible cohorts.
