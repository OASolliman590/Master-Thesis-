# Validation architecture

Validation levels are cumulative but not interchangeable. A higher level does not erase limitations at a lower level.

## Level 0 — numerical and identity validity

Required before any biological interpretation:

- query and compound IDs;
- source/release hashes;
- full feature universe and ordering;
- matrix/metadata concordance;
- scorer parity and adversarial fixtures;
- dose/time/unit parsing;
- duplicate and release-overlap policy;
- deterministic outputs and provenance.

Synthetic fixtures validate software behaviour only.

## Level 1 — internal robustness

Outcome-blindly prespecified analyses include:

- `Q_M` versus `Q_E` query comparison;
- alternate frozen query sizes or weights;
- model/dose/time/project sensitivity;
- C1 anchor versus other declared contexts;
- rank and candidate stability;
- QC/HIQ sensitivity;
- coverage and annotation-release sensitivity.

A favourable internal sensitivity is not independent validation.

## Level 2 — independent measured perturbation

This level carries the proposed primary. It requires:

- separate originating experiment;
- full measured RNA/protein/chromatin feature space as specified;
- frozen treatment/control contrast;
- identifiable biological replicates;
- source-specific design and uncertainty;
- no outcome-based experiment selection;
- explicit overlap audit.

Measured disagreement remains a result. A source with unresolved controls, replicate identity or intervention metadata does not pass by convenience.

## Level 3 — orthogonal mechanism and immune context

Possible evidence:

- CRISPR/knockdown/knockout with intervention type retained;
- target engagement and chromatin/protein readouts;
- rescue/dependency experiments;
- Perturb-CITE-seq in its native melanoma/TIL context;
- TISMO or other original mouse immune experiments;
- drug-alone immune-function assays.

Genetic loss is not assumed equivalent to partial pharmacological inhibition.

## Level 4 — translational plausibility

- human PK and formulation;
- free/total exposure uncertainty;
- active metabolites;
- model/disease relevance;
- regulatory and safety context;
- experimental form and procurement feasibility.

This level does not establish tumour exposure or recommend dosing.

## Level 5 — prospective wet-lab validation

- drug-class target engagement;
- post-washout molecular restoration;
- protein/surface confirmation;
- viability and apoptosis control;
- HLA/antigen-dependent immune recognition where designed;
- valid factorial epigenetic-priming × ICI interaction where designed.

## IFNG and inflammatory references

An IFNG reference is a Level 1/3 state-resemblance analysis depending on its source. It does not by itself prove pathway dependence, prostate specificity or immune function. The exact payload, control, model, duration and measured/inferred feature space must be verified before use.

## Combination evidence

Distinguish:

1. drug alone;
2. ICI alone;
3. combination;
4. additive response;
5. formal interaction/synergy;
6. sequence/timing.

Separate single-agent datasets cannot establish synergy. Combination studies enter C only when the epigenetic and ICI arms, control and interaction estimand are reconstructable.

## Validation freeze order

1. Freeze queries and source-admission rules.
2. Validate scorers and identities.
3. Run C2 discovery and freeze candidate interpretations.
4. Freeze eligible independent contrasts without reading outcomes.
5. Run Level 2 primary/validation.
6. Append Levels 3 and 4.
7. Produce the prospective Level 5 handoff.
