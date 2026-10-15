# A1 bounded tickets and test oracles

Shared DAV pairing/identity/matrix tickets are reused, not rebuilt. A1 owns statistical estimands/context/reporting after data release. Each ticket lists inputs, expected artifacts, failures and review; no real analysis is authorized by its existence.

| Ticket / owner | Dependencies and inputs | Deliverables | Acceptance / stop |
|---|---|---|---|
| A1-T01 / source curator | DAV episode/endpoint/assay contracts | Source-specific window and pair-policy registry, missingness taxonomy | Exact day/category provenance; COMBAT/induction sequence guard; unknowns not guessed |
| A1-T02 / pairing implementer | Shared DAV matrix builder, A1-T01 | Port/adapt deterministic multiwindow selection and audit | Row permutation, duplicate lesion/resequencing, regimen switch, multiple follow-ups and cross-patient pair tests |
| A1-T03 / statistical implementer | Released paired rows; frozen model/scale | Continuous paired-change/direct interaction and qualified repeated/count adapters | Known sign, one-group nonestimability, rank failure and convergence tests; no separate-significance shortcut |
| A1-T04 / meta implementer | A1-T03; family/covariance registry | Compatible-window synthesis and influence | At least two independent families; shared baseline/arms handled; incompatible scales rejected |
| A1-T05 / statistician | Context completeness and design cross-tab | Moderator identifiability receipt and qualified estimates | Perfect drug-class/cancer confounding blocks only that claim; no automatic ecological causal interpretation |
| A1-T06 / curator+statistician | Actual comparative-arm source packet | NMA feasibility report, not automatic NMA code | Check connected network/transitivity/endpoint/window/selection; R/NR cannot be treatment nodes |
| A1-T07 / biology/reporting owner | Released results and optional modalities | longitudinal_support.tsv, four figures, thesis/manuscript evidence review | Counts/uncertainty/limitations present; negative results retained; no baseline duplication or causal rate exports |

## Adversarial fixture plan

Use explicitly synthetic IDs and known truth, never plausible-looking real study identifiers. Include: two follow-ups in reversed order; baseline after prior CTLA-4 exposure but before PD-1; source 'post' anchored to progression; follow-up after discontinuation; response from a different episode; one response stratum missing; all patients sharing one study; different assays at two times; duplicated baseline in two windows; nonrandom missing biopsy by observed deterioration. The oracle asserts pair IDs, exclusion reasons, rank/estimability and scientific labels, not just execution completion.

## TDD and fresh evidence

For recovered behavior, first execute a focused characterization against the exact old function and log whether the reported bug reproduces. Write a failing test for the intended semantics, port the smallest required change, then run focused and relevant full suites. Archive unchanged old bytes and record code/config/environment hashes. Distinguish specification-schema tests, synthetic statistical tests, real-source format tracers and real-cohort validation. No old test count becomes current, and an unexecuted R/dream backend is explicitly NOT_RUN even if JSON fixtures pass.

A1 analysis release requires scientific/statistical review of windows, model/scale, multiplicity and selection assumptions. A1 publication promotion is never a prerequisite for implementing a properly released longitudinal component.
