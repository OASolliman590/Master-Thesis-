# Implementation readiness and release gates

## Work permitted now

- maintain source and identity registries;
- resolve original-study metadata and access;
- build schemas and validators;
- implement synthetic/adversarial scorer fixtures;
- establish official WTCS parity;
- implement query validation on fictional data;
- build source adapters without reading outcomes for endpoint selection;
- perform a tiny permitted real-data I/O smoke after numerical parity;
- prepare environment and storage manifests.

## Work not yet permitted

- real perturbation scoring used to alter the endpoint;
- final `Q_E`/`Q_M` construction before B release;
- execution of the proposed primary;
- candidate freeze or “winner” selection;
- class-superiority inference;
- wet-lab protocol modification or biological execution;
- treating Paper D output as validation;
- merging this review branch automatically.

## Readiness gates

| Gate | Requirement | Current status |
|---|---|---|
| C-R0 | Scientific framework approved and documented | CLOSED by user decision |
| C-R1 | Existing C/historical code and data reuse audit complete | PARTIAL |
| C-R2 | B-to-C handoff schema implemented and B query frozen | OPEN |
| C-R3 | Compound universe/identity release frozen | OPEN |
| C-R4 | Independent-source admission and contrasts frozen | OPEN |
| C-R5 | WTCS and one-sided scorer parity | OPEN |
| C-R6 | Sample-level primary scorer and limma engine synthetic tests | OPEN |
| C-R7 | Tiny permitted real-data smoke with no biological conclusion | OPEN |
| C-R8 | Biological configuration freeze and explicit analysis release | OPEN |
| C-R9 | C2 discovery run and candidate-interpretation freeze | OPEN |
| C-R10 | Independent measured primary/validation run | OPEN |
| C-R11 | Context, mechanism and pharmacology append | OPEN |
| C-R12 | Reproducible figures/evidence tables and wet-lab handoff | OPEN |

## Production readiness definition

Paper C is not production-ready because a command exists or a synthetic test passes. Production readiness requires C-R1 through C-R8, source-specific permissions, complete provenance and an explicit release decision.

## Minimum viable MSc path

If independent sources remain limited:

1. freeze matched queries;
2. complete a bounded C2 discovery analysis;
3. use every eligible independent measured source descriptively;
4. integrate context/viability/PK transparently;
5. nominate one or two experiments;
6. obtain prospective molecular wet-lab validation.

This can support a thesis chapter but may not sustain a separate computational publication without adequate Level 2 evidence.
