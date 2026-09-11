# Quickstart: Spec 025 — Visualization Module

## TL;DR
```bash
# Regenerate every thesis figure from a committed results root:
python -m pipeline.cli viz build \
  --results-root results/<run> \
  --figure-registry configs/figure_registry.tsv \
  --out figures/<run>
```

## What you get
- `figures/<run>/<figure_id>.png` — one per registry row.
- `figures/<run>/<figure_id>.caption.txt` — caption + `scientific_note`.
- `figures/<run>/figure_manifest.tsv` — figure_id → source files, caption, scientific_note.

## Scientific labeling guarantees
- TCGA figures: titled **prognostic (TCGA, not ICB-treated)** — never "validation."
- Concordance figures: **cross-method robustness**, not validation.
- Composition figures: carry the D5 mediator caveat.
- Forest/ssGSEA figures read the **corrected** spec-016/018 outputs (harmonized effects, real GSVA).

## Map a thesis figure to a command
See `docs/runbooks/visualization.md` — it lists each thesis figure number → `figure_id` → the exact `viz build` invocation and source stage outputs.

## Verify determinism
```bash
python -m pipeline.cli viz build --results-root results/<run> --out /tmp/figs_a
python -m pipeline.cli viz build --results-root results/<run> --out /tmp/figs_b
# PNG bytes identical modulo embedded timestamp
```
