# Research: Downstream Biological Interpretation

**Branch**: `027-downstream-biological-interpretation` | **Date**: 2026-07-03

## Current-state audit

| Capability | Exists? | Where |
|---|---|---|
| Within-cohort DE (DESeq2/limma, common log2) | yes | Stage 06 (`modules/06_within_cohort_de/`) |
| Inverse-variance RE meta + LOCO + moderator hooks | yes | Stage 07 (`cmd_meta_run`) |
| Tiered signature | yes | Stage 08 (`signature/<analysis_id>/`) |
| Real ssGSEA/GSVA immune scoring | yes | Stage 09 (`immune_state/`, `scripts/ssgsea_gsva.R`) |
| Volcano / forest viz | yes | `modules/_viz/` |
| Analysis-id families (PRE/ON/POST/DELTA, drug/cancer-stratified) | yes | spec 026 |
| **Ranked-GSEA enrichment** | yes | `src/pipeline/modules/10_interpretation/enrich.py` + `interpret enrich` |
| **Gene network / hub genes** | yes, guarded | `network.py`; current reviewed root emits `insufficient_signal` instead of hubs |
| **Cross-cancer hub meta** | yes, guarded | `hub_meta.py`; propagates hub-gate status |
| **Immunophenotype class + criteria registry (HOPE)** | yes | `immunophenotype.py`; RNA-derivable subset scored from Stage 09 scores |
| **RNA-inferred epigenetic state** | yes | `epi_infer.py`; Layer-4 ssGSEA proxies |

## I/O contracts

**Inputs (read-only, from reviewed run root):**
- `meta/<analysis_id>/meta_effects.tsv` — rank key = `meta_effect_random` (fallback `meta_effect_fixed`); id = `gene_symbol` (+ `gene_id`); support = `n_cohorts_contributed`, `direction_consistency`, `heterogeneity_i2`, `meta_fdr`.
- `signature/<analysis_id>/responder_signature_tiered.tsv` — tiered gene set for ORA.
- `immune_state/` — existing ssGSEA scores for M4 baseline.
- Expression: existing `--expression-manifest` + `--downloads-root` (T7) for M2/M4/M5.
- Gene sets: `configs/immune_gene_sets_registry*.tsv`, `configs/expanded_gene_set_atlas_rules.tsv`.

**Outputs (write only under `<root>/interpretation/`):**
- `interpretation/enrichment/<analysis_id>/{gsea.tsv,ora.tsv,dotplot_data.tsv}`
- `interpretation/network/<analysis_id>/{edges.tsv,hub_genes.tsv,hub_difference.tsv}`
- `interpretation/hub_meta/{cross_cancer_hub_meta.tsv,forest_data.tsv}`
- `interpretation/immunophenotype/{sample_phenotype.tsv,phenotype_response_assoc.tsv}`
- `interpretation/epigenetic/{inferred_scores.tsv,epi_response_assoc.tsv,epi_input_audit.tsv}`
- each dir: `reproducibility/{commands.sh,environment.yml,checksums.sha256}`

Every table carries `claim_class` ∈ {`mechanism_hypothesis`,`discovery`}.

## Scientific-validity notes

- **Ranked GSEA over ORA-on-FDR.** With ~6 FDR<0.05 genes, ORA on the significant set is underpowered/unstable; fgsea on the full ranked `meta_effect_random` uses the whole distribution and is the primary enrichment. ORA on the tiered signature is a secondary, clearly-labeled view.
- **Hub robustness.** Hubs from a thin DEG set are prone to artefact. Require: (a) build on ranked stats, (b) node-degree permutation FDR, (c) a `min_signal_floor` (e.g. ≥N genes past a set threshold) below which the module emits `insufficient_signal` rather than hubs.
- **Cancer = moderator.** Cross-cancer hub meta uses cancer as a low-dim moderator with a ≥studies/moderator gate (reuse D4 rule); no per-cancer subgroup significance claims.
- **RNA→epigenetics is inference, not measurement.** Candidate methods to pilot (finalize in M0/M5):
  - regulator/TF activity: dorothea + VIPER-style (R) on the expression matrices;
  - chromatin-regulator expression modules (epigenetic-regulator gene panels already in Layer-4 gene sets);
  - published RNA→promoter-methylation predictors (evaluate feasibility/licence).
  Output is an epigenetic *state proxy* correlated to response — never reported as measured methylation.
- **Claim boundaries.** All outputs are discovery/mechanism-hypothesis. TCGA, MOFA, survival, and the ML predictor are out of scope here.

## Implementation decisions recorded 2026-07-03

- **M1 enrichment** uses a local ranked-meta z-score GSEA fallback over `meta_effect_random` for portability and an optional `scripts/interpret/fgsea_enrich.R` backend for environments with Bioconductor `fgsea`.
- **M2 network/hubs** uses a signal-floor gate before hub emission. In the reviewed root, PRE has 23 signal genes at `meta_fdr <= 0.5` and `abs(effect) >= 0.3`, below the default `min_signal_floor=25`, so `hub_genes.tsv` correctly reports `insufficient_signal`.
- **M3 hub meta** does not fabricate cancer-moderator results when M2 gates hubs. It emits `not_evaluable` / `insufficient_signal`.
- **M4 immunophenotype/HOPE** scores the RNA subset only when matching Stage 09 scores exist. Direct gene-expression-only pieces without a mounted reviewed expression matrix are recorded in `immunophenotype_input_audit.tsv`; TMB, PD-L1 IHC, ECOG, and iRECIST are explicitly skipped/routed.
- **M5 epigenetic inference** pilots the conservative method: existing Layer-4 ssGSEA epigenetic immune proxies (`EPIGENETIC_IMMUNE_PRIMING`, `PRC2_IMMUNE_TARGETS`, `SWI_SNF_ICB`, `DNMT_IMMUNE_LOCI`, etc.) as RNA-inferred state, not measured methylation/chromatin.

## HOPE criteria decomposition (defined 2026-07-03)

HOPE = the ICB predictive-biomarker + response-tracking bundle oncologists use to
judge durable response. Most components are **not** bulk-RNA-seq quantities — the
registry `configs/immunophenotype_criteria_registry.tsv` encodes the split:

| HOPE component | Clinical assay | RNA-derivable? | Handling in 027 |
|---|---|---|---|
| PD-L1 (TPS/CPS) | IHC | proxy only | `hope_checkpoint_expression` (CD274/PDCD1/PDCD1LG2…) — label as proxy, NOT IHC |
| TMB | DNA/WES | **no** | flagged `tmb`; route to multi-omics spec 020 |
| MSI / dMMR | DNA/IHC | proxy | `hope_msi_dmmr_proxy` (MMR gene expr); confirm with DNA later |
| hot vs cold | RNA | **yes** | `hope_tcell_inflamed_gep` (Ayers) + `hope_cytolytic_activity` (CYT) + `hope_ifng_signature` |
| ECOG | clinical | no | flagged `ecog_performance_status`; covariate if metadata present |
| iRECIST / pseudoprogression / durable remission | radiological/clinical | no | **response-LABEL definition**, not a score → spec 010 FR-006 |
| composite | — | yes (RNA subset) | `hope_composite_rna` favorability score, claim_class=mechanism_hypothesis |

So M4 scores the **RNA subset** as `hope_*` criteria and correlates the composite to
response; the DNA/clinical/radiological parts are explicitly deferred/flagged so HOPE is
never overstated as measured PD-L1/TMB/MSI. This also cleanly motivates spec 020
(multi-omics) as the place TMB + true MSI enter.

## Remaining refinements
- Add a true co-expression or offline PPI backend if a future full run produces enough signal genes to justify hub discovery.
- If mounted expression matrices are available, derive direct HOPE gene-expression criteria (`checkpoint`, `CYT`, MMR proxy) instead of relying only on existing Stage 09 score columns.
- Literature-weighted `hope_composite_rna` can replace the current score-proxy approach if a defensible weighting scheme is chosen.
