# Benchmarks: Downstream Biological Interpretation

**Branch**: `027-downstream-biological-interpretation` | **Date**: 2026-07-03

First reviewed-root output-scale baseline captured on 2026-07-04 from
`results/analysis_id_runs_t7_20260607_stage07_scale_provenance/interpretation/`.
Exact runtime and memory baselines are still pending because the current
`interpret_run_manifest.yaml` records command timestamps and outputs, but not
per-command durations or peak memory. Runtime baselines should be measured on the
next approved full run.

| Module | Input scale | Runtime target | Memory target | Notes |
|---|---|---|---|---|
| M1 enrichment | ~58k ranked genes × N analysis_ids | < 3 min / analysis_id | < 4 GB | fgsea is fast; collection load dominates |
| M2 network | expression matrix (mounted) | < 15 min / analysis_id | < 16 GB | co-expression is the cost driver; PPI-only path is cheap |
| M3 hub-meta | ~hundreds of hub genes | < 2 min | < 2 GB | reuses Stage 07 meta engine |
| M4 immunophenotype | 853 samples × criteria | < 5 min | < 8 GB | per-sample scoring |
| M5 epi-infer | expression matrix | < 20 min | < 16 GB | method-dependent; pilot first |

## First reviewed-root output baseline

Evidence source:
`results/analysis_id_runs_t7_20260607_stage07_scale_provenance/interpretation/`
and `runtime_audits/phase3_readiness_20260704_smoke/phase3_readiness_dashboard.md`.

| Module | Output evidence | Baseline scale | Interpretation |
|---|---|---:|---|
| M1 enrichment | 3 analysis IDs, each with `gsea.tsv`, `ora.tsv`, and `dotplot_data.tsv` | 14 data rows per GSEA/ORA table; 28 dotplot rows per analysis ID | Ranked `meta_effect_random` enrichment is populated for PRE, pan-ICB PRE, and ICI-combination PRE |
| M2 network | `network/PRE_RESPONSE/{edges.tsv,hub_genes.tsv,hub_difference.tsv}` | 1 status row in `hub_genes.tsv` | Thin signal correctly gates hub emission as `insufficient_signal` with `n_signal=23`, `min_signal_floor=25` |
| M3 hub meta | `hub_meta/{cross_cancer_hub_meta.tsv,forest_data.tsv}` | 1 status row | Cross-cancer hub meta propagates the insufficient-signal state and keeps cancer as a moderator-only field |
| M4 immunophenotype | `immunophenotype/{sample_phenotype.tsv,phenotype_response_assoc.tsv,hope_skipped_criteria.tsv}` | 3,412 sample-phenotype rows; 4 association rows; 4 skipped non-RNA HOPE rows | RNA-derivable HOPE criteria scored; TMB, PD-L1 IHC, ECOG, and iRECIST routed away from RNA scoring |
| M5 epi-infer | `epigenetic/{inferred_scores.tsv,epi_response_assoc.tsv,epi_input_audit.tsv}` | 7,677 inferred-score rows; 9 association rows | Layer-4 RNA-inferred epigenetic immune proxies emitted as mechanism-hypothesis, not measured methylation |
| Claim-class audit | dashboard claim scan | 21 claim-class tables checked | All reviewed-root interpretation TSVs carry non-blank `claim_class` values in the allowed set |

## Regression budget
- No module may exceed 1.5× its recorded baseline runtime after it is measured.
- M2/M5 must short-circuit (and log) within 30 s when expression is not mounted.

## Correctness guards (not perf, but tracked here)
- Enrichment must reproduce identical GSEA tables given the same ranked input + collection version (seed fixed).
- Hub permutation FDR stable across two seeded runs within tolerance.
- SC-006 checksum test: zero bytes changed outside `interpretation/`.
