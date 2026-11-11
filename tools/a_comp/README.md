# Paper A composition path

This module implements the A-COMP software path with invented data. It calls the locked R `immunedeconv` wrapper and `quantiseqr` TIL10 method, checks the installed reference hashes, validates each sample's eleven returned fractions, and reuses A-META for Hedges g, synthesis, BH correction, and the eleven locked custom panel scores.

The synthetic demonstration also exercises within-study Spearman correlations and paired incremental AUROC calculations. Its synthetic-only bootstrap uses fixed full-data logistic-model predictions, outcome-stratified resampling in R, and the registered `second_check` stream for a report-only check. This is a machinery contract only. Real incremental AUROC remains blocked because the signed specification does not set its stream or refit/evaluation rule. The weighted published eighteen-gene GEP and its housekeeping normalization also remain unpinned. The synthetic score is explicitly named `SYNTHETIC_WEIGHTED_GEP18_DEMO` and is not presented as the published GEP.

The N15 contract is unsigned in [the proposal](../../../docs/decisions/A_COMP_N15_PROPOSED_20261106.md). Its 90% post-exclusion coverage floor and `1e-6` fraction tolerances are proposed project QC choices, not quanTIseq defaults. No real cohort run has been performed. A-COMP summaries never pool raw fractions across studies, and CIBERSORTx is reported as **not run**.

## Commands

Run the invented-data software demonstration with the locked Python environment:

```sh
python -m tools.a_comp synthetic-demo --out .scratch/a_comp/synthetic-demo-w4-review-20261107-next
```

Use a fresh output directory for each run; existing products are never overwritten.

The following are exact refusal examples with the current proposed pin. They stop before opening cohort inputs. Signing N15 alone will not make deconvolution runnable: the real A-COMP source loader and source-manifest admission are still unimplemented. Analysis also needs the user to resolve the bootstrap/refit/evaluation and published weighted-GEP rules, and the existing A-META real-outcome gate must remain closed until separately authorized. No real-release command is claimed to work after signatures alone.

```sh
python -m tools.a_comp deconvolve --cohort riaz_gse91061 --pin docs/decisions/A_COMP_N15_PROPOSED_20261106.md --expression .scratch/runtime/a_comp/TPM_AFTER_USER_RELEASE.tsv --manifest .scratch/runtime/a_comp/TPM_AFTER_USER_RELEASE.json --out .scratch/A/a_comp/riaz_gse91061
python -m tools.a_comp analyze --cohort riaz_gse91061 --pin docs/decisions/A_COMP_N15_PROPOSED_20261106.md --expression .scratch/runtime/a_comp/TPM_AFTER_USER_RELEASE.tsv --clinical .scratch/runtime/a_comp/CLINICAL_AFTER_USER_OUTCOME_RELEASE.tsv --out .scratch/A/a_comp/analysis/riaz_gse91061
```

## Implemented behavior and limits

| Requirement | Code path | Evidence or gate |
|---|---|---|
| N15 signed pin and provenance | Python pin parser; `r/R/a_comp.R` direct deconvolution boundary | Proposed/missing pin refuses before cohort input access. The direct R route independently checks the pin, cohort identity, the hash of the existing A-P2 decision, and declared source-manifest identity, then refuses because the real source loader remains unimplemented. Preflight checks locked R/package/reference identities. |
| Allowed RNA-seq cohorts and representation | `classify_input`, `read_tpm_matrix` | Exactly the 12 signed A-COMP cohort IDs; non-TPM, logged, non-symbol, non-RNA-seq, incomplete source, Braun, arrays, targeted panels, and the locked final test refuse |
| quanTIseq options and removal behavior | `r/R/a_comp.R` | `TIL10`, `lsei`, tumour mode, RNA mode, mRNA scaling, packaged RNA default and tumour-aberrant removals; synthetic R call uses the locked packages |
| Fractions, coverage, weak types, no silent renormalization | `validate_fraction_rows`, R coverage writer | Ten immune types plus Other; explicit range and sum tolerances; per-type pre/post exclusion coverage; 90% floor is marked proposed; Tregs, B cells, and M2 are flagged |
| Per-study response effects and synthesis | `analyze_synthetic_inputs` → existing `study_effects` and `synthesize` | ORR, clinical-benefit, source-label definitions, endpoint definition IDs, and the fraction family stay separate. All four existing A-META strata are invoked over varied invented cancers and drugs. The existing A-META `synthesize()` R-retention forwarding is still a W2 dependency; its current interface does not yet accept `retention_dir`. |
| Panel correlations and alignment | `build_feature_table`, `_study_correlations` | Eleven locked custom panel scores plus qualified CYT; strict sample order and coverage checks; within-study Spearman followed by descriptive median/range only |
| Incremental AUROC | R `synthetic_incremental_auc`; tests reconstruct predictions and resamples | Each fraction is added separately to CYT and a distinctly named invented weighted score. R emits shared row assignments and a receipt; the synthetic-only interval uses fixed full-data predictions. The test independently recomputes deltas, paired type-7 intervals, receipt hash, and the report-only `second_check` flag. No A-P2/P1 stream is reused. |
| Synthetic input admission | `analyze_synthetic_inputs`; R snapshot/provenance boundaries | Hash-bound invented manifests, known-real-alias refusal, checked paths/symlink ancestry, exact named clinical fields, and verified private snapshots before analysis/R reads. A direct analyzer test supplies a separate hash-bound fixture and exercises alignment refusal. |
| Enclosing provenance | `artifact_manifest.json` | Binds input declaration and representation, unsigned N15 proposal hash, source/scoring/config/lock identities, R run receipts/runtime/reference hashes, and hashes for every public product. Private verified snapshots and bridge stages are excluded. |
| Real outcome analysis | Python `analyze_real_request`; direct R deconvolution gate | Refuses open scientific gates. The real TPM/source loader is not complete, so the example commands above are refusal-only and no real cohort is admitted or executed. |
| Secondary CIBERSORTx | Summary and R provenance | Always `not run` |

Synthetic fixtures demonstrate software behavior only. They do not validate biological accuracy, response associations, real-cohort coverage, published GEP equivalence, or a real release. A-COMP's real loader remains incomplete; the N15 contract is proposed and unsigned, and the real bootstrap and published weighted-GEP rules remain open.

## References

- Finotello et al. “Molecular and pharmacological modulators of the tumor immune contexture revealed by deconvolution of RNA-seq data.” *Genome Medicine* 11, 34 (2019). [doi:10.1186/s13073-019-0638-6](https://doi.org/10.1186/s13073-019-0638-6).
- Official [`quantiseqr::run_quantiseq` documentation](https://federicomarini.github.io/quantiseqr/reference/run_quantiseq.html) and [Bioconductor package page](https://bioconductor.org/packages/release/bioc/html/quantiseqr.html).
- The [pinned `immunedeconv` wrapper](https://github.com/omnideconv/immunedeconv/blob/e625e6c28ed14a30f9f40f159925cc9f0df4fa49/R/immune_deconvolution_methods.R) and [pinned `quantiseqr` source](https://github.com/bioc/quantiseqr/blob/a948291c8d6b2a3262655ad2e4c52e1573ae55e4/R/quantiseqr.R).
