# Implementation Plan: Downstream Biological Interpretation

**Branch**: `027-downstream-biological-interpretation` | **Date**: 2026-07-03 | **Spec**: `specs/027-downstream-biological-interpretation/spec.md`

## Summary

Add an `interpret` CLI verb group and a `10_interpretation` module directory that consume a reviewed run root read-only and emit a new `interpretation/` subtree. Five modules (M1–M5), each independently runnable and independently testable. R heavy-lifting goes through the portable R runtime (spec 094); Python handles orchestration, ranking, and network topology.

## Current code alignment

- Executable repo: `06_analysis_pipeline_repo`.
- Reviewed run root (default input): `results/analysis_id_runs_t7_20260607_stage07_scale_provenance`.
- Consumes: `meta/<analysis_id>/meta_effects.tsv` (cols incl. `gene_symbol`, `meta_effect_random`, `meta_se_random`, `meta_p_value`, `meta_fdr`, `n_cohorts_contributed`, `direction_consistency`, `heterogeneity_i2`), `signature/<analysis_id>/responder_signature_tiered.tsv`, `immune_state/`, plus expression matrices via the existing expression-manifest + downloads-root (T7).
- Gene sets: `configs/immune_gene_sets_registry*.tsv`, `configs/expanded_gene_set_atlas_rules.tsv`.

## Architecture

```
src/pipeline/modules/10_interpretation/
  enrich.py            # M1  GSEA (ranked) + ORA
  network.py           # M2  co-expression / PPI network + hub detection
  hub_meta.py          # M3  cross-cancer hub meta-regression
  immunophenotype.py   # M4  criteria scoring + phenotype class + response assoc
  epi_infer.py         # M5  RNA-inferred epigenetic-regulator / methylation proxy
  contracts.py         # shared I/O schemas + claim-class stamping
scripts/interpret/
  fgsea_enrich.R       # M1 backend (fgsea / clusterProfiler)
  coexpr_wgcna.R       # M2 optional co-expression backend
  regulator_activity.R # M5 backend (VIPER/dorothea-style) [pilot]
src/pipeline/cli.py    # new subparsers: interpret {enrich,network,hub-meta,immunophenotype,epi-infer}
```

CLI shape (mirrors existing verb-noun style):
```
python -m pipeline.cli interpret enrich          --results-root <root> --analysis-id <id> --collections <registry> --out <root>/interpretation
python -m pipeline.cli interpret network         --results-root <root> --analysis-id <id> --expression-manifest ... --downloads-root ... --out <root>/interpretation
python -m pipeline.cli interpret hub-meta        --results-root <root> --out <root>/interpretation
python -m pipeline.cli interpret immunophenotype --results-root <root> --criteria-registry <tsv> --out <root>/interpretation
python -m pipeline.cli interpret epi-infer       --results-root <root> --expression-manifest ... --out <root>/interpretation
```

## Tooling decisions
- **Enrichment**: `fgsea` (ranked GSEA) primary; `clusterProfiler` for ORA/plots; `gseapy` as Python fallback if R runtime unavailable.
- **Network**: co-expression via WGCNA (R) when expression is mounted; PPI backbone (STRING offline snapshot) as fallback; centrality/hub in `networkx`/`igraph`; hub significance by node-degree permutation.
- **Cross-cancer meta**: reuse the Stage 07 inverse-variance RE + Knapp-Hartung machinery with cancer as moderator.
- **Immunophenotype**: extend Stage 09 gene-set scoring; add a `criteria_registry.tsv` so new criteria (incl. HOPE) are data, not code.
- **Epi-infer (pilot, finalize in research)**: regulator activity (dorothea/VIPER-style) + optional published RNA→methylation predictor; scored per sample, related to response.

## Milestones
1. **M0 Audit + contracts** — lock input columns, output schemas, claim-class stamping, `interpretation/` layout.
2. **M1 Enrichment** — ranked GSEA + ORA per analysis_id.
3. **M2 Network + hubs** — with permutation guard + thin-signal floor.
4. **M3 Cross-cancer hub meta**.
5. **M4 Immunophenotype** — criteria registry + response association (HOPE slot reserved).
6. **M5 Epi-infer** — regulator/methylation-proxy + response association.
7. **Integration** — tests, reproducibility bundles, docs, CHANGELOG, sign-off.

## Dependencies
- Spec 094 portable R runtime (fgsea/clusterProfiler/WGCNA/dorothea).
- Mounted expression matrices (T7) for M2/M4/M5 co-expression + per-sample scoring; modules degrade to score-based + record the gap when offline.
- A stable reviewed run root (do not run against a mid-flight run).

## Rollback
All modules are additive, read-only consumers. To revert: delete `<root>/interpretation/` and drop the `interpret` subparsers + `10_interpretation` module dir. No core-stage (00–15) code is modified, so the frozen signature and existing run roots are untouched by construction (FR-017, enforced by SC-006 checksum test).

## Scientific risks
- Thin signal → over-interpreted pathways/hubs. Mitigation: ranked-stat GSEA + permutation hub FDR + signal floor + claim-class stamping.
- Co-expression needs enough samples per contrast; small cohorts → report instability, don't force modules.
- RNA-inferred epigenetics is a *proxy/hypothesis*, never a methylation measurement — label accordingly (FR-019).
