# Research: Spec 015 — Stage 06 Within-Cohort DE Method

Companion to `spec.md`. Grounded in the Round-2 data inspection + source audit (2026-05-30).

## 1. Current-State Audit

- `cmd_de_run` (cli.py L4273). Routing (L4561): count DE (`scripts/rna_deseq2.R` / `rna_edger.R`) fires only when `input_class=="raw_counts" AND _looks_like_count_matrix`. Else → **Welch t-test on log2(x+1)** (`welch_t_test_log2`, L4641–4664).
- `is_log` magnitude heuristic at L4429–4445 decides whether to log-transform — the X1 guess.
- `rna_deseq2.R`: DESeq2 `~ group` (or `~ paired + group`), **no `lfcShrink`** → unshrunken MLE `log2FoldChange` + Wald `lfcSE` written as `log2fc` / `se_or_stat`. So the count path is already meta-compatible.
- The Welch path computes `se = sqrt(var_case/n_case + var_ctrl/n_ctrl)` — a naive SE of a difference of log means, with no moderation; unstable at small n.

## 2. The real problem (from data inspection)

Of 21 primary PRE cohorts: a minority are verified raw counts (gse91061, gse195832, gse126044, gse115821, gse235910, gse136961, gse289583), the rest are log-CPM / log-TPM / TPM / FPKM / normalized (gse159067 log2cpm, gse207422 log2TPM, gse100797, gse67501, gse135222 TPM, gse145996 FPKM, gse218989 normalized, …). Under the current code the non-count majority all run the **unmoderated Welch t-test**, and their effect sizes are pooled with DESeq2 LFCs in Stage 07.

## 3. Design contract (study_design_decisions_2026-05-30 D2 + D5)

**Harmonize first, then one uniform effect:**

| assay_type (spec 010) | harmonization | model |
|---|---|---|
| raw_counts | VST/rlog or `log2(CPM+1)` | DESeq2/edgeR/limma-voom → log2FC + SE |
| tpm, fpkm | `log2(x+1)` | limma + `eBayes(trend=TRUE)` → log2FC + SE |
| log_normalized, rlog_vst | as-is | limma + `eBayes(trend=TRUE)` |
| microarray_intensity | as-is (log intensities) | classic limma |
| methylation_beta, unreadable | — | **hard-excluded** |

Pooled quantity (Stage 07) = **inverse-variance log2FC + honest SE** (existing estimator). All paths emit `{log2fc, se, model_class, n_case, n_control}` on the common log2 scale.

**X3 / D5 (mediator):** the **primary** DE has **no composition covariate** (infiltration is a mediator; adjusting removes the effect). A composition-adjusted variant is a labeled secondary ("survives infiltration adjustment"); tumor-intrinsic separation uses an explicit mediation analysis (composition from spec 018), not adjustment.

## 4. Scientific Validity
- limma-trend/limma is the standard for log-normalized & microarray expression; voom is valid only on counts (needs library sizes). Empirical-Bayes moderation is the accepted remedy for unstable per-gene variance at small n (Smyth 2004; Law 2014; Ritchie 2015).
- Keeping inverse-variance log2FC pooling preserves the verified Stage-07 estimator and avoids the low-variance-gene inflation of SMD.

## 5. References
Smyth 2004 (limma eBayes); Law et al. 2014 (voom — counts only); Ritchie et al. 2015 (limma); Love et al. 2014 (DESeq2); VanderWeele 2015 (mediation, for D5).

## 6. R-script SE semantics (implementation notes)
- `scripts/rna_deseq2.R`: outputs DESeq2 unshrunken MLE `log2FoldChange` and Wald `lfcSE`; this is the count-model SE consumed by Stage-07 inverse-variance pooling.
- `scripts/rna_edger.R`: outputs `log2fc` plus an SE-compatible proxy in `se_or_stat` for meta weighting on the common log2 scale.
- `scripts/rna_limma.R`: outputs moderated limma `logFC`; `se_or_stat` is derived from `abs(logFC / t)` after empirical-Bayes moderation (`eBayes(trend=TRUE)`), with non-finite values handled as NA.
- All Stage-06 branches therefore emit a harmonized `{log2fc, se_or_stat}` contract and record `model_class` + `normalization_method` for downstream guard checks.
