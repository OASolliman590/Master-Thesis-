# Paper D ↔ Paper E interface

| Paper D owns | Paper E owns |
|---|---|
| spatial/contact tumour–immune behaviour | systemic and tissue PK/PBPK |
| cell-intrinsic prediction benchmark | exposure-dependent target engagement |
| incremental value of molecular predictions | induction, persistence, washout, recovery |
| multicellular/spatial observation model | virtual clinical populations |
| functional and spatial counterfactuals | pharmacological schedule optimisation |

## Allowed E → D driver

A frozen time-indexed exposure or pharmacodynamic trajectory with model/version, units, uncertainty, parameter/source hashes, population/archetype label, and permissible interpretation.

## Allowed D → E output

A frozen response surface or reduced-order relationship linking local driver state to declared tumour–immune outcomes, with domain and uncertainty limits.

## Shared-experiment ledger

Every experiment records whether it was used for D calibration, D model selection, D final test, E calibration, E model selection, E final test, wet-lab publication, or exploratory analysis. The same experiment cannot be labelled untouched validation for a coupled D–E system after it informed either component.

Neither paper must wait for the other: D may initially use measured drivers; E may proceed with nonspatial pharmacodynamic outputs.
