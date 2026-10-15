# Dependencies and release logic

## Independent lanes

```text
D0-M model/source provenance ───────► D1 molecular benchmark
          │
          └──── optional validated molecular input ───► D2-LEARNED

D0-O observer provenance ──────────► Lin-dependent transition claims

Qualified wet-lab assay + measured parameters ───────► D2-PAIR
                                                        │
Measured myeloid/stromal/spatial evidence ────────────► D2-TISSUE
                                                        │
Frozen predictions + separate evaluation experiment ─► Prospective validation

Paper E frozen exposure/PD trajectory ────────────────► optional D driver
```

## Release rules

| Release | Required gates | Does not require |
|---|---|---|
| Source/contract software | repository review, schemas, synthetic tests | biological data availability |
| D1 real tracer | G0–G7 for one condition, source permission | Lin observer |
| D1 final benchmark | G0–G8, frozen test, exact baseline, precision decision | D2 |
| D2-PAIR calibration | qualified assay, measured observables, parameter registry | D1 or Lin |
| D2-PAIR held-out test | separate calibration/test experiments and frozen outputs | learned coupling |
| D2-LEARNED | D1 utility in intended domain plus measured bridge | D2-TISSUE |
| D2-TISSUE | measured added compartments and independent validation targets | B/TLS unless represented |
| Prospective combination test | preregistered scenario and assay qualification | proof of clinical benefit |

## Stop conditions

A blocked lane does not silently block unrelated lanes. It blocks only claims that depend on it. A negative result completes its evaluation but prevents unsupported deployment of the failed component.
