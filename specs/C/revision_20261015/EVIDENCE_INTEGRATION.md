# Evidence integration and candidate prioritisation

## First output: transparent evidence matrix

Each candidate record follows `schemas/candidate_evidence.schema.json` and includes:

- canonical parent identity, salt/formulation and aliases;
- mechanism subclass and direct/indirect targets;
- C2 context-specific discovery scores and component signatures;
- C1 calibration where applicable;
- `Q_M` and `Q_E` results and disagreement;
- L1000 landmark/inference/absence coverage;
- independent measured validation;
- target/genetic/chromatin evidence;
- immune-context or functional evidence;
- viability, cell-cycle and stress evidence;
- cell-model relevance;
- PK/formulation/regulatory plausibility;
- current wet-lab availability as a separate field;
- contradictions, missing evidence and claim ceiling.

## No default total score

The initial integration is qualitative-structured, not a weighted sum. Missing evidence is `UNKNOWN`; it is not assigned zero or treated as agreement.

## Rule-based evidence tiers

### Tier A — experiment-ready scientific candidate

- desired-direction evidence in at least one independent measured prostate experiment;
- coherent mechanism or target engagement;
- no dominant toxicity/stress explanation at the proposed context;
- relevant model and assayable baseline lesion;
- interpretable formulation/exposure and no unresolved identity blocker.

### Tier B — promising with one major gap

Examples include strong measured restoration with unresolved PK, strong mechanism with no independent prostate transcriptome, or plausible exposure with context-limited molecular evidence.

### Tier C — hypothesis-generating

LINCS-only, non-prostate-only, predominantly inferred-feature, unresolved identity, or major stress-confounded candidates.

### Tier D — contradicted or currently unsuitable

Repeated opposite-direction evidence, incompatible model, invalid experimental form, unresolved severe confounding or a claim that exceeds available evidence.

## Pareto set

Within eligible candidates, identify non-dominated candidates across prespecified dimensions:

- independent molecular restoration;
- mechanistic support;
- relevant-model support;
- low toxicity/stress concern;
- pharmacological plausibility;
- experimental feasibility.

Do not force one global winner when candidates are optimal for different objectives.

## Permitted nominations

The final handoff may name different candidates as:

- best measured molecular restorer;
- best mechanistically supported candidate;
- best translationally plausible candidate;
- best immediately feasible pilot;
- informative negative/control candidate.

Scientific priority, procurement priority and feasible pilot status are separate fields.

## Weighting amendment

A formal MCDA or Bayesian integration requires a separate, preregistered amendment with weights/priors fixed before viewing the desirable ordering. It is not the default implementation.
