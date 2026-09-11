# Feature Specification: Downstream Biological Interpretation of the ICI Response Signature

**Feature Branch**: `027-downstream-biological-interpretation`
**Created**: 2026-07-03
**Status**: Implemented locally (2026-07-03; scoped interpretation tests pass)
**Input**: 2026-07-03 analysis vision. Consumes outputs of specs 006 (DE), 007 (immune/epigenetic layer), 015/016 (DE/meta), 017/018 (signature/immune), 026 (analysis-id design). Does **not** modify the core pipeline or the frozen signature.

## Summary

Turn the existing responder-vs-non-responder statistics (Stage 06 DE → Stage 07 meta → Stage 08 signature → Stage 09 immune) into **mechanism-level, thesis-facing interpretation**: functional enrichment, gene network / hub genes, cross-cancer hub meta-analysis, immunophenotype criteria scoring, and RNA-inferred epigenetic state. All modules are **read-only consumers of a reviewed run root** and emit into a new `interpretation/` subtree. The ML prediction layer is **out of scope** (deferred — see below).

## Fixed design constraints (carry from committed decisions)

- **Comparator = responders vs non-responders, within-cohort, per timepoint** (PRE / ON / POST / DELTA as separate `analysis_id`s). No external/normal control recall. Within-cohort DE → inverse-variance random-effects meta (already built).
- **Cancer is a low-dimension moderator (meta-regression), not a per-cancer subgroup claim** (design D4). Per-cancer volcanoes are descriptive only.
- **Operate on the RANKED meta statistic**, not only the FDR-significant sliver — the signal is thin (6 genes at FDR<0.05 in the current run), so enrichment/network must be robust to that.
- **Never mutate the frozen signature or a committed `results/` run root.** Outputs go to `<root>/interpretation/`.
- **Preserve claim boundaries**: outputs are *discovery / mechanism-hypothesis*, not validated predictors.

## User Scenarios

### US1 — Pathway enrichment of the response signal (P1)
As the analyst, I turn the ranked R-vs-NR meta statistic (per `analysis_id`) into pathway-level interpretation, so I can describe *what biology* separates responders from non-responders.

### US2 — Hub-gene network (P1)
As the analyst, I build a gene network from the response statistics and identify hub genes, with a robustness guard so a thin DEG set cannot manufacture spurious hubs.

### US3 — Immunophenotype scoring (P1)
As the analyst, I score immune-phenotype criteria (hot/cold, IFN-γ, TIS-like, and the **HOPE criteria [NEEDS DEFINITION]**) across all cohorts and correlate them to response — the immuno-phenotype ↔ genotype description.

### US4 — RNA-inferred epigenetic state (P2)
As the analyst (epigenetics thesis), I infer epigenetic-regulator activity / methylation-proxy state from bulk RNA-seq and relate it to response and to the epigenetic signature.

### US5 — Cross-cancer hub meta (P2)
As the analyst, I meta-analyze hub-gene effects with cancer as a moderator to separate pan-cancer from cancer-specific response hubs.

## Requirements

### Functional Requirements

**M1 — Functional enrichment**
- **FR-001**: Run GSEA on the full **ranked** `meta_effect_random` statistic per active `analysis_id`.
- **FR-002**: Run ORA on the tiered signature gene set as a secondary view.
- **FR-003**: Use curated collections (Hallmark, Reactome, GO-BP, KEGG, immune-specific) sourced from the existing gene-set registry / atlas.
- **FR-004**: Emit per-`analysis_id` enrichment tables + dotplot inputs + provenance (collection version, statistic used).

**M2 — Network & hub genes**
- **FR-005**: Build a network from response genes (co-expression from mounted expression matrices AND/OR a PPI backbone) seeded by ranked meta stats.
- **FR-006**: Detect hub genes with a **permutation-based robustness guard** (report permutation FDR); refuse to emit hubs when input signal is below a configured floor.
- **FR-007**: Contrast R-vs-NR network topology where expression is available.
- **FR-008**: Emit hub table (gene, centrality, permutation FDR, direction, module) + a hub-difference report.

**M3 — Cross-cancer hub meta**
- **FR-009**: Meta-analyze hub-gene effects with cancer as a low-dimension moderator (≥ configured studies/moderator).
- **FR-010**: Classify each hub as pan-cancer vs cancer-specific; emit table + forest inputs.

**M4 — Immunophenotype criteria**
- **FR-011**: Extend Stage 09 scoring with additional immune criteria and a phenotype class (hot/cold/IFN-γ/TIS-like) per sample/cohort.
- **FR-012**: Integrate the **HOPE criteria** as an RNA-proxy panel driven by `configs/immunophenotype_criteria_registry.tsv`. HOPE (defined 2026-07-03) is a *bundle* of ICB predictive biomarkers + response-tracking metrics; only the RNA-derivable subset is scored here, the rest is explicitly routed elsewhere:
  - **RNA-derivable (score in M4)**: checkpoint-axis expression (CD274/PDCD1/PDCD1LG2/…), MSI/dMMR expression proxy (MMR genes), T-cell-inflamed GEP + cytolytic + IFN-γ (hot/cold), and a `hope_composite_rna` favorability score.
  - **NOT RNA-derivable (flagged, not scored)**: TMB (needs matched WES → spec 020), PD-L1 IHC TPS/CPS (IHC; CD274 expr is only a coarse proxy), ECOG (clinical covariate).
  - **Response-definition, not a feature**: iRECIST / pseudoprogression / durable remission map to the responder-*label* definition (durable clinical benefit) → spec 010 FR-006 response-definition heterogeneity, not a scored column.
  Emit `hope_composite_rna` as `mechanism_hypothesis`/`discovery`, never as a validated predictor.
- **FR-013**: Emit immunophenotype-to-response association across cohorts.

**M5 — RNA-inferred epigenetic state**
- **FR-014**: Infer epigenetic-regulator activity and/or methylation-proxy state from bulk RNA-seq (candidate methods in `research.md`).
- **FR-015**: Relate inferred epigenetic state to response and to the epigenetic signature genes.

**Cross-cutting**
- **FR-016**: Every module reads a reviewed run root **read-only**; no writes outside `<root>/interpretation/`.
- **FR-017**: Never mutate the frozen signature or a committed run root.
- **FR-018**: Enrichment/network operate on ranked stats and degrade gracefully on thin signal (no fabricated results).
- **FR-019**: Every output row/table carries a claim class (`mechanism_hypothesis` / `discovery`), never `validated`.
- **FR-020**: Each module emits a reproducibility bundle (`commands.sh` + `environment.yml` + `checksums.sha256`).

### Out of scope (explicitly deferred)
- **ML prediction layer** (RNA-seq → response classifier / AUC). Deferred by user decision 2026-07-03; it does **not** gate pipeline progress and will be its own spec after this layer emits stable interpretation outputs.
- **MOFA multi-omics on TCGA vs ICI** → strategic spec 020.
- **TCGA genotype/phenotype/survival with clinical** → strategic spec 020 continuation.

### Key Entities
- **Enrichment row**: analysis_id, collection, pathway, NES, p, FDR, leading-edge genes, statistic, claim_class.
- **Hub gene**: analysis_id, gene, centrality, permutation_fdr, direction, module, pan_cancer_flag.
- **Immunophenotype call**: sample/cohort, criteria_id, score, phenotype_class, response_association.
- **Inferred epigenetic score**: sample/cohort, regulator/proxy, score, response_association.
- **Interpretation run root**: `<reviewed_run_root>/interpretation/`.

## Success Criteria
- **SC-001**: Non-empty enrichment tables for each active `analysis_id`, computed on the ranked statistic.
- **SC-002**: Hub table with permutation FDR; on the current thin run it may legitimately report "insufficient signal" for some analysis_ids — that is a pass, not a failure.
- **SC-003**: Immunophenotype-to-response association table across cohorts.
- **SC-004**: Inferred-epigenetic-state table with response association.
- **SC-005**: Every output carries a claim class; none labeled validated.
- **SC-006**: Frozen signature + committed run roots unchanged (checksum verified).
- **SC-007**: ≥1 unit test per public function + ≥1 integration test per module; full suite passes.

## Edge Cases
- Thin signal (few FDR genes) → GSEA on ranked stat still valid; hub detection must gate on the signal floor.
- Cancer types with 1–3 cohorts → moderator, not subgroup.
- HOPE criteria undefined → M4 ships without it; criteria-registry slot reserved.
- Expression matrices not mounted (T7 offline) → co-expression/immuno/epi modules degrade to score-based only and record the gap (mirror Stage 09 `immune_effects_input_audit.tsv`).
