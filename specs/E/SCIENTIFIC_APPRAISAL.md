# Scientific appraisal — public-data core

## Decision

Proceed with a self-contained computational design. Do not require an original experiment for core completion. However, do not keep an experimental primary endpoint while removing its measurements, and do not replace missing biological constraints with convenient constants.

The contribution changes from prospective local kinetic prediction to **evidence-constrained scheduling and explicit identification of what the existing measurements can and cannot decide**. That may yield a conditional schedule preference, no robust preference, or a constructive demonstration that incompatible schedules can fit the same public evidence.

## Evidence and novelty

Moj et al. (S001) provide a vorinostat PK/HDAC/platelet modelling precedent but explicitly used published and unpublished inputs. Exact reproduction cannot be assumed. Wang et al. (S002) already combined epigenetic pharmacology, checkpoint QSP and virtual trials in breast cancer; their original scripts are described as available on request. Neither precedent validates prostate schedule predictions. See `source_registry/REFERENCES_V2.md`.

Gameiro et al. (V201) report relevant vorinostat/entinostat exposure and antigen-specific lysis experiments, including LNCaP. These create a public biological curation route; they do not establish a prostate checkpoint-blockade schedule comparison or a resolved recovery constant. Rodems et al. (S004) identify public source-data supplements for different DNMT/HDAC treatments. Drug identities and assay contexts must remain distinct.

Simply joining existing models is insufficient novelty. The proposed added work is an auditable primary-study constraint set, a fair sequence contrast, uncertainty-separated inference, explicit evidence-removal/alternative-structure tests, and counterexamples where claims are not identified. A bounded search in this revision is not proof of worldwide novelty; update before submission.

## Three possible completion profiles

**C-SCHEDULING:** sufficiently recoverable external exposure/temporal PD/function data support quantitative reduced-model calibration or constraints. Execute all levels; report the predeclared primary contrast and independent evaluations available at each level. Schedule conclusions remain model-conditional unless an independent measured schedule test exists.

**C-IDENTIFIABILITY:** public exposure and biological measurements exist but the timing/functional connection cannot be identified. Execute and evaluate the exposure component, encode the actual measurement constraints, and establish the non-identifiability of the scheduling contrast mathematically or using credible alternative parameterisations. Complete the QSP/ensemble analysis as an uncertainty/identifiability result, not a validated patient simulator. This is a substantive quantitative analysis, not a source list.

**C-INCOMPLETE:** only model diagrams, metadata or arbitrary priors are available; the public constraint set cannot support either profile. Report the source failure, revise the lead/context or scientifically re-scope before fitting. No automatic wet-lab dependency is added. Completion of software alone cannot close the paper.

## Feasibility and falsification

PK may be independently evaluable while prostate delivery is not. A static phenotype may constrain an amplitude but not its recovery rate. Antigen-specific lysis without antibody comparison cannot identify blockade benefit. Mean curves cannot identify population covariance. These limitations can themselves define the quantitative question, provided the paper shows their consequences rather than merely listing them.

The lead is selected from public recoverability and biological relevance before new modelling outcomes are inspected. Local stock and local assay availability are not core selection criteria. Public null/adverse observations must be retained. No robust ranking is an admissible result; an empty admissible parameter set indicates incompatibility or model failure, not robust efficacy.

## Removed hidden dependencies

No local HLA assay, donor, reagent purchase, original washout series, original checkpoint assay, biological-paper acceptance or D result is required. Versioned A–C results can provide optional context; E must also work with a frozen public-only contextual definition. No gene score is converted directly to a kinetic constant. The E_LAST extension receives the completed foundation; it cannot silently redefine it.
