# LINCS and numerical scorer contract

## Separation of scorers

Paper C uses two distinct numerical layers:

1. **Independent measured primary:** sample-level directional rank scoring and limma treatment contrasts defined in `ANALYSIS_CONTRACT.md`.
2. **LINCS C2/C1:** signature-level raw connectivity scoring over the fixed L1000 feature universe.

Neither score is silently substituted for the other.

## LINCS raw WTCS

For a genuine bidirectional disease query and perturbation vector `z` over ordered universe `G`:

- rank the full universe by `z`;
- calculate weighted enrichment for `UP` and `DOWN` with absolute expression weights;
- combine according to the pinned official `getCombinedES` call path with `rescale=false`;
- orient the display explicitly so larger restoration means stronger opposition to disease.

The current proposal uses raw WTCS. It does not call a custom percentile, normalised score or empirical query-null statistic “tau”.

## One-sided queries

If only one direction is biologically supported, use a reviewed one-sided weighted enrichment statistic. Do not add genes to the opposite set merely to make WTCS computable. One-sided and bidirectional scores are reported in separate fields and are not directly ranked without an approved normalisation.

## Required numerical parity

Before real scoring, an implementation must match the pinned official reference on independently generated fixtures covering:

- positive and negative enrichment;
- same-direction UP/DOWN enrichment;
- exactly zero enrichment on one or both sets;
- equal positive/negative extrema;
- tied perturbation values;
- duplicate gene identifiers;
- absent query genes;
- overlapping UP/DOWN sets;
- empty and full-universe sets;
- non-finite values;
- deterministic ordering and gene-universe hashes.

A Python implementation is acceptable only after parity. `cmapPy` input support is not proof of WTCS parity.

## Feature universe and coverage

- preserve the complete ordered feature universe supplied to the scorer;
- never subset to query genes and rerank;
- deduplicate features under a frozen annotation rule before scoring;
- reject matrix/metadata ID discordance;
- report query coverage as landmark, best-inferred, other-inferred and absent;
- never describe inferred immune genes as independently measured expression.

## Signature and overlap policy

For each signature retain:

- release;
- `sig_id`;
- `distil_id` set and collapse weights;
- project/plate where available;
- cell, dose, unit and duration;
- QC and HIQ fields;
- compound canonical identity;
- overlap with previous releases.

Exact duplicate instance sets are not counted twice. Partial overlap requires an explicit policy or source-level reaggregation; otherwise the comparison remains blocked.

## C1 calibration

C1 retains the exact PC3/24-hour/1.11111 micromolar condition for decitabine, entinostat and tazemetostat because metadata established common measured coverage before expression outcomes were inspected. Report each compound separately with component signatures and project identity. No treatment-superiority p-value, class-effect estimate or biological confidence interval is permitted.

Other shared doses and HIQ restrictions are prespecified sensitivities, never selected because they look stronger.

## Query-specificity null

A matched random-query null may be reported as a secondary diagnostic when it preserves:

- programme/direction sizes;
- landmark/inference strata;
- eligible gene universe;
- fixed random seed and draw count;
- a declared one-sided statistic and multiplicity family.

It is not a p-value for drug efficacy or biological replication. Gene exchangeability limitations are reported.
