# Reproduction and readiness

## Current readiness

- Decisions: approved.
- Dated specification: populated.
- Schemas/examples: locally validated.
- D1 qualifying dataset: UNKNOWN / not admitted.
- D1 checkpoint/runtime reproduction: not run by this package.
- Lin reproduction: not run.
- D2 assay qualification: not established.
- D2 calibrated model: not implemented.
- Prospective prediction: not frozen.
- Repository branch/PR: not created by this package.

## Readiness gates

### R-SPEC

Approved decisions, complete files, schemas/examples valid, cross-links and checksums valid.

### R-D1-SOURCE

At least one G0–G8 candidate with exact biological units, full measured output space, supported label, matched controls, compatible duration, resolved overlap, and fixed baseline rows.

### R-D1-RUNTIME

Pinned environment/checkpoint loads; official fixture reproduces; fallbacks are rejected; output placement/order verified.

### R-D2-ASSAY

Qualified cells, controls, receptor/ligand/HLA/antigen context, reproducible baseline and endpoint, and separated calibration/test experiments.

### R-D2-MODEL

Nonspatial and rule-only baselines pass; parameters are source/calibration linked; sensitivity and identifiability are reported; held-out prediction is frozen.

### R-PROSPECTIVE

Prediction, intervention, comparator, assay, meaningful effect, uncertainty, and falsification criterion are sealed before evaluation data access.

A schema pass is not scientific readiness.
