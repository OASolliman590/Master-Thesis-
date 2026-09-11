# Quickstart: Downstream Biological Interpretation

All commands read a **reviewed run root** read-only and write only under
`<root>/interpretation/`. Use the portable R runtime (spec 094) for the R backends.

Use these commands only when intentionally building or refreshing the
interpretation layer. For routine readiness verification without rewriting the
reviewed root, use the verification commands below.

```bash
cd "06_analysis_pipeline_repo"
ROOT=results/analysis_id_runs_t7_20260607_stage07_scale_provenance
PYTHON="${PYTHON:-python3.13}"
export PYTHONPYCACHEPREFIX=/private/tmp/epigenetic_thesis_pycache
RUN_MANIFEST="$ROOT/interpretation/interpret_run_manifest.yaml"

# M1 enrichment (ranked GSEA + ORA) — per analysis_id
for A in PRE_RESPONSE PAN_ICB_RESPONSE__PRE_TREATMENT ICI_COMBINATION_RESPONSE__PRE_TREATMENT; do
  "${PYTHON}" -m src.pipeline.cli interpret enrich --results-root "$ROOT" --analysis-id "$A" \
    --collections configs/immune_gene_sets_registry.tsv --out "$ROOT/interpretation" \
    --run-manifest "$RUN_MANIFEST"
done

# M2 network + hubs (needs expression mounted for co-expression)
"${PYTHON}" -m src.pipeline.cli interpret network --results-root "$ROOT" --analysis-id PRE_RESPONSE \
  --expression-manifest results/geo_tables/geo_tables_summary.tsv \
  --downloads-root results/retrieval/downloads --out "$ROOT/interpretation" \
  --run-manifest "$RUN_MANIFEST"

# M3 cross-cancer hub meta
"${PYTHON}" -m src.pipeline.cli interpret hub-meta --results-root "$ROOT" --out "$ROOT/interpretation" \
  --run-manifest "$RUN_MANIFEST"

# M4 immunophenotype + HOPE-RNA criteria
"${PYTHON}" -m src.pipeline.cli interpret immunophenotype --results-root "$ROOT" \
  --criteria-registry configs/immunophenotype_criteria_registry.tsv --out "$ROOT/interpretation" \
  --run-manifest "$RUN_MANIFEST"

# M5 RNA-inferred epigenetic state
"${PYTHON}" -m src.pipeline.cli interpret epi-infer --results-root "$ROOT" \
  --expression-manifest results/geo_tables/geo_tables_summary.tsv --out "$ROOT/interpretation" \
  --run-manifest "$RUN_MANIFEST"
```

## Verify
- `interpretation/enrichment/<analysis_id>/gsea.tsv` non-empty, computed on `meta_effect_random` (SC-001).
- `interpretation/network/<analysis_id>/hub_genes.tsv` has a `permutation_fdr` column; may report `insufficient_signal` on thin analysis_ids (SC-002, a pass).
- `interpretation/immunophenotype/phenotype_response_assoc.tsv` present (SC-003).
- `interpretation/epigenetic/inferred_scores.tsv` labeled as proxy/hypothesis (SC-004).
- Frozen signature + run root checksums unchanged (SC-006):
  `PYTHONPYCACHEPREFIX=/private/tmp/epigenetic_thesis_pycache python3.13 -m pytest tests -k interpretation -q`
- Full local readiness without rewriting the reviewed root:
  `PYTHONPYCACHEPREFIX=/private/tmp/epigenetic_thesis_pycache python3.13 scripts/phase3_readiness_dashboard.py --out-dir runtime_audits/phase3_readiness_20260704_smoke`

## Notes
- If T7 expression is not mounted, M2/M4/M5 degrade to score-based outputs and write an input-audit noting the gap (mirror `immune_effects_input_audit.tsv`).
- Never point `--out` at a committed run root's non-`interpretation/` area.
