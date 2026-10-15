# Paper C framework amendment — 15 October 2026

**Authority:** the user explicitly approved the scientific direction recorded here after review of the live Paper C specification, repository evidence, submitted MSc protocol and current wet-lab plan. This is a thesis-design amendment and repository decision. It is not an institutional protocol amendment, external preregistration, permission to run biological analyses, or evidence that any perturbation restores immune function.

## Approved decisions

1. **Paper C adopts the C3 evidence-based experimental-prioritisation framework.** The paper-level question is whether patient-supported regulatory evidence changes which epigenetic interventions credibly restore clinically anchored prostate immune programmes after measured perturbation, context, mechanism, viability and pharmacology are considered.
2. **A bounded C2 screen is the discovery engine.** It may screen a curated epigenetic-compound universe across eligible prostate contexts, but it must preserve compound identity, model, dose, time, project, assay coverage and biological unit. It may not become an unrestricted database screen or an opaque ranked list.
3. **C1 is demoted to secondary calibration.** The decitabine/entinostat/tazemetostat PC3, 24-hour, 1.11111 micromolar LINCS comparison remains useful as a finite-release numerical and provenance calibration. It is not the Paper C primary, does not estimate comparative efficacy, and does not identify a drug-class effect.
4. **The proposed primary is the paired independent-measured comparison of the methylation-supported query, `Q_M`, against the matched expression-only query, `Q_E`.** The exact estimand is developed in `specs/C/revision_20261015/ANALYSIS_CONTRACT.md`. It asks whether methylation-supported genes show greater desired-direction molecular responsiveness than an equally sized expression-only query in pre-admitted independent prostate perturbation experiments.
5. **The proposed primary is not yet analysis-released.** It requires a frozen B-to-C handoff, matched query budgets, independent-source admission, adequate measured-gene coverage, source-specific contrasts and validated software. Outcome values may not determine those choices.
6. **Independent measured evidence is central.** LINCS discovery, genetic perturbations, mouse immune-context resources, viability screens, pharmacology and virtual-cell predictions have distinct roles and may not substitute for one another.
7. **Evidence integration uses transparent tiers and Pareto reasoning.** Missing evidence is `UNKNOWN`, not zero. Scientific priority, translational plausibility, experimental feasibility and current stock availability remain separate outputs.
8. **Paper D remains separate.** A virtual prediction cannot count as independent corroboration of another prediction and cannot fill missing measured validation in C.
9. **The wet-lab arm remains prospective.** Paper C may nominate compounds, models, exposure windows and readouts. It may not claim molecular restoration, immune killing, ICI interaction or clinical benefit until the corresponding experiment is performed.

## What this decision supersedes

If merged, this decision supersedes only the following proposals in the 5 September 2026 Paper C draft:

- C1 as the proposed Paper C primary;
- a common PC3/24-hour/1.11111 micromolar condition as the paper-defining endpoint;
- any implication that the three named compounds form a comparative efficacy experiment.

It preserves the prior source architecture, identity discipline, WTCS parity requirement, context analyses, measured-validation requirement, pharmacology layer and claim ceilings unless the revision kit states a stricter rule.

## What remains unresolved

- the final genes, programmes, sizes and directions in `Q_E` and `Q_M`;
- whether enough independent measured studies pass admission for a standalone primary;
- exact source-specific contrasts and verified independent replicate counts;
- the final curated compound universe;
- current physical wet-lab inventory, formulation and certificate status;
- the production scorer and real-data execution release;
- publication venue and publication outcome.

## Release boundary

This decision authorises documentation, source/metadata audits, schema development, synthetic/adversarial tests and a tiny permitted real-data smoke test after numerical parity. It does **not** authorise reading perturbation outcomes to alter the endpoint, executing the biological primary, freezing candidates, changing the wet-lab protocol or merging the review branch automatically.
