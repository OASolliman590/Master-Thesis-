# Validation and baselines

## D1 baselines

- no change;
- global perturbed mean;
- fixed same-supported-drug–dose–duration mean across permitted non-test contexts (**primary comparator**);
- same-context mean across other drugs, secondary only;
- ridge/linear model;
- nearest-neighbour;
- replicate split as positive-control/data-ceiling diagnostic.

All baselines receive equivalent permitted information. Final-test outcomes cannot tune them.

## D2 baselines

- observed untreated baseline;
- nonspatial population count/ODE model;
- minimal rule-only PhysiCell;
- measured-driver model;
- learned-coupling ablation, when released.

## Validation ladder

| Level | Evidence |
|---|---|
| V0 | official software reproduction |
| V1 | held-out molecular perturbation benchmark |
| V2 | held-out context/study transfer |
| V3 | state observer recovery |
| V4 | held-out multicellular outcome/composition |
| V5 | held-out spatial pattern |
| V6 | longitudinal transition |
| V7 | measured combination |
| V8 | preregistered prospective wet-lab prediction |

Passing V0/V1 does not validate multicellular biology. A null/negative result can complete a level and restrict later use.
