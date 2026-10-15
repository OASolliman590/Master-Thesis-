# Software architecture

## Modules

1. `source_registry` — immutable source/object identity and terms.
2. `condition_resolver` — compound/salt/dose/time/control identity.
3. `feature_contract` — ordered genes, namespace/version, transform.
4. `overlap_ledger` — training/development/test lineage.
5. `bundle_validator` — typed G0–G10 eligibility.
6. `d1_baselines` — exact fixed baseline plus secondary baselines.
7. `d1_evaluator` — losses, `theta`, denominators, failures.
8. `observer` — source-native state mapping/probabilities.
9. `d2_nonspatial` — count/ODE baseline.
10. `d2_spatial_adapter` — PhysiCell input/output/run provenance.
11. `bridge_registry` — measured/learned molecular-to-behaviour mappings.
12. `scenario_registry` — interventions, schedules, outputs, validation.
13. `wetlab_handoff` — frozen prospective prediction packets.
14. `reporting` — traceable tables, figures, claim labels.

## Information boundary

Inference and baseline workers cannot read held-out treated outcomes. Evaluation receives sealed predictions, frozen baselines, and truth only after model/checkpoint/features/conditions are sealed.

## Provenance

Every model output carries model version, checkpoint hash, source-data hashes, input hash, parameter hash, seed, environment/container identity, output hash, role, and validation status.

## Restart

Stage keys are content-addressed. Changed upstream identities invalidate downstream work. Partial outputs are written atomically and never marked complete without a validated receipt.
