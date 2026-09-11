# Quickstart: Spec 019 — Stage 10 Validation

```bash
python -m pipeline.cli validate run \
  --signature results/signature/pre_response_signature_v1.tsv \
  --results-root results/current_run \
  --contrast PRE_RESPONSE \
  --heldout-evaluation results/validation/heldout_evaluation.tsv \
  --out results/spec_019_validation
```

## Held-out schema
`heldout_evaluation.tsv` must include:
- `auc` in `[0,1]`
- `effect_concordance` in `[0,1]`

## Key outputs
- `validation_concordance_summary.tsv`
- `validation_readiness_status.tsv`
- `validation_external_holdout.tsv`
