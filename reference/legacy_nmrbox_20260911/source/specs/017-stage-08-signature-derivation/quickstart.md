# Quickstart: Spec 017 — Stage 08 Signature Derivation

## Start from the RNA-seq pipeline repo

```bash
cd "/Users/omara.soliman/Desktop/Research/11- Epigenetic's Master Thesis/2-Experimental/Computation Arm/06_analysis_pipeline_repo"
```

## Rebuild the known handoff report

```bash
python3.13 -m src.pipeline.cli report build --run-root results/slice2_ready_20260406_222238
```

This is a historical report checkpoint. The current corrected Stage 06/07 pilot root for Stage 08 maturation is:

```text
results/analysis_id_runs_t7_20260530
```

Do not freeze signatures from the historical report root unless the output is explicitly labelled as legacy.

## Run tests before changing implementation

```bash
python3.13 -m pytest -q
```

If bytecode cache writes fail:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/epigenetic_thesis_pycache python3.13 -m pytest -q
```

## Intended Stage 08 flow

Current CLI shape:

```bash
python3.13 -m src.pipeline.cli signature derive \
  --contrast PRE_RESPONSE \
  --meta-dir results/analysis_id_runs_t7_20260530/meta/PRE_RESPONSE \
  --out results/stage08_signature_derivation
```

Target matured CLI shape for this spec cycle:

```bash
python3.13 -m src.pipeline.cli signature derive \
  --analysis-id PRE_RESPONSE \
  --run-root results/analysis_id_runs_t7_20260530 \
  --thresholds configs/signature_thresholds.yaml \
  --out results/stage08_signature_derivation/PRE_RESPONSE
```

Both forms should remain blocked or pilot-labelled until Stage 09 immune scoring is regenerated or explicitly documented as blocked for the same corrected run root.

## Verify outputs

Expected outputs:

```text
results/stage08_signature_derivation/signature_registry.tsv
results/stage08_signature_derivation/responder_signature_core.tsv
results/stage08_signature_derivation/responder_signature_tiered.tsv
results/stage08_signature_derivation/signature_derivation_audit.tsv
results/stage08_signature_derivation/signature_loco_derivation_manifest.tsv
```

## Claim guardrails

- Discovery signature: allowed.
- Internal robustness: allowed when same samples are reused.
- External validation: only allowed for held-out or external ICI-treated cohorts.
- TCGA projection: allowed as prognostic/projection framing, not ICI-response validation.
