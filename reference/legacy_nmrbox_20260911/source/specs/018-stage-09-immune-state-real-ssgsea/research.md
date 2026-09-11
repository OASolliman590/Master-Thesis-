# Research: Spec 018 — Stage 09 Real ssGSEA / Deconvolution / Layer-4

Companion to `spec.md`. Grounded in the Round-2 source audit (2026-05-30).

## 1. Current-State Audit
- `cmd_immune_score` (cli.py L6147); `_score_gene_sets` (L6247) = **mean percentile rank** (`rank(pct=True).loc[genes].mean()`), label `ssgsea_rank_mean_python`. gseapy imported (L6174) then ignored.
- ESTIMATE/EPIC placeholders: `estimate_score=immune_score`, stromal/purity `nan`, `epic_fractions` empty, `score_scale="IMMUNE_SCORE_proxy_deprecated"`.
- **Real backends already exist and are correct but unused:**
  - `scripts/ssgsea_gsva.R` — GSVA `ssgseaParam(normalize=TRUE)` / `method="ssgsea"`, robust GMT parse + duplicate collapse + version compat. (Quirk: older-API branch uses `abs.ranking=TRUE` — non-standard for directional sets.)
  - `scripts/estimate_scores.R`, `scripts/epic_scores.R` — present.
- Layer-4 registry `L4_EPIGENETIC` → `inputs/gene_sets/epigenetic_layer/EPIGENETIC_IMMUNE_PRIMING.gmt`, which contains **2 sets** (EPIGENETIC_IMMUNE_PRIMING, EPIGENETIC_CHECKPOINT_REGULATION). **6 of 8** spec-007 named sets are missing.

## 2. The fix is mostly wiring
Because the real R implementations exist, the bulk of this spec is: make `cmd_immune_score` dispatch to `ssgsea_gsva.R` (pattern: `cmd_de_run`→`rna_deseq2.R`), wire ESTIMATE/EPIC or delete the placeholders, and author the 6 missing GMTs. This is far cheaper than the round-1 "implement real ssGSEA" framing implied.

## 3. Contracts (frozen)
- ssGSEA output: `{cohort_id, sample_id, patient_uid, gene_set_id, gene_set_layer, ssgsea_score, method="gsva_ssgsea"}`. Score is the GSVA ssGSEA enrichment statistic on the assay-correct (log2-normalized) expression.
- Deconvolution output (if kept): real ESTIMATE (immune/stromal/purity) + EPIC fractions with named methods; **exposed as the mediator** for spec-015 D5 mediation, not as a DE covariate.
- Layer-4 GMTs: 8 sets total, each with cited gene membership, in `inputs/gene_sets/epigenetic_layer/`.

## 4. Scientific Validity
- ssGSEA (Barbie 2009; Hänzelmann 2013) is a rank-weighted KS-style enrichment statistic — fundamentally different from a mean percentile rank; the proxy can invert relative set rankings. Using GSVA's implementation makes the "ssGSEA layer scores" claim true.
- D5: deconvolution quantifies infiltration as a **mediator**; the analysis is mediation/decomposition, not adjustment.

## 5. References
Barbie et al. 2009; Hänzelmann et al. 2013 (GSVA/ssGSEA); Yoshihara et al. 2013 (ESTIMATE); Racle et al. 2017 (EPIC); spec 007 (Layer-4 battery names).
