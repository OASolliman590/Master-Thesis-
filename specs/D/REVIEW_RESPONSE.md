# D internal review corrections

5 September 2026. Internal read-only review identified three issues; these corrections do not approve the scientific design or establish data availability.

1. Whole-context leakage: VALIDATION_AND_FIGURES now excludes every treatment response from the held-out prostate context from transition training/tuning, including other drugs. A condition-only split supports a different claim.
2. Control mixture: ANALYSIS now requires the same control replicate identities and equal-replicate weights for observed and predicted differences, with per-control-replicate prediction before aggregation. The required adapter behavior has a test in TICKETS_AND_TESTS.
3. Circular runtime gate: D-I02 establishes G7; it no longer requires G7 or the prostate production validator in advance. It requires a separately reviewed bounded reproduction contract, resources/terms and all-four-kit review; it cannot close prostate scientific gates.

Independent Opus review and Astra disposition of the integrated four-kit snapshot remain separate release requirements.
