# Pharmacological-context analysis

## Required context fields

Record actual agent, target/class (PD-1, PD-L1, CTLA-4 or another documented target), monotherapy/combination, every component, sequence, available dose/schedule, line, prior ICI/systemic/radiotherapy exposure, concomitant steroids/immunosuppression, cancer/subtype, disease state, tissue/lesion and window relative to each component. Unknown treatment history remains unknown. Regimen_id is not a substitute for patient-level episode/component records.

## Analysis hierarchy

First estimate within the originating study and actual regimen. Synthesize within the same cancer and compatible regimen/window. A class-level summary is permitted only when the within-class context and across-class comparison are supported, not merely because drugs share a target name. Before any moderator fit, create a cancer × study × regimen × class × timing × prior-treatment cross-tab, map independent families and check full rank. Perfect class–cancer/study confounding blocks a class-specific interpretation. Near-confounding and sparse levels require uncertainty/sensitivity reporting rather than nominal adjustment.

For an identifiable moderator, predeclare the contrast, reference level, effect scale, covariates, independent unit, degrees-of-freedom method and multiplicity family. Meta-regression is study-level and susceptible to ecological interpretation; it cannot recover a patient-level class effect from aggregate labels. Do not attribute differences in R/NR molecular separation to clinical efficacy. A null moderator or absent class comparison does not invalidate a qualified within-regimen longitudinal effect.

## Sequence and combination attribution

A biopsy after chemotherapy or epigenetic induction but before ICI measures that interval's observed change, not an isolated ICI effect. COMBAT BAT timing is the concrete source-specific guardrail; TONIC-like induction designs similarly require original arm/episode timing. A combination response cannot be partitioned into individual drug efficacy without an appropriate comparative design. Prior ICI creates a different baseline context and is not erased by defining a new treatment start.

## Reporting

Every moderator row reports study/cancer/regimen support, paired patient N, window range, missing context, estimability, effect/interval and prohibited interpretations. Where comparison is not identifiable, publish the stratified evidence map and explicit confounding structure. Candidate mechanistic explanations are hypotheses tied to source biology, not conclusions from a coefficient. Pharmacological context adds value by identifying what differs and what cannot be separated; it need not yield a ranking of drugs.
