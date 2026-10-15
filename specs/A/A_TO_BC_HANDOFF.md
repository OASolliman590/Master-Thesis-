# Versioned A → B/C handoff

## Products and freeze order

Release separate, patient-free products. A-BIO/context may be released without favourable or available A-P2. Freeze development-derived evidence and candidate rules before final-test inspection; freeze the predictor only after its prescribed development. Final-test results append a validity annotation tied to the original release and never rewrite its features/candidate set. Corrections require a new version, exposure disclosure and revalidation; an overwritten file is not a correction record.

| Artifact | Required fields / meaning |
|---|---|
| response_effects.tsv | feature/programme ID; contrast and endpoint; estimate, SE/interval; effect_scale_id; direction; study/cancer/regimen support; N; covariates; heterogeneity; coverage; contradictory effects; estimability; discovery release |
| frozen_predictor.tsv and model bundle | ordered feature IDs; coefficients/intercept; transforms and fitted parameters; scoring definition; software/model hash; development-family and split hashes; no raw patient IDs; convergence and training receipt |
| biological_context.tsv | immune function; cellular localization evidence; composition sensitivity; same-specimen/orthogonal modality support; source/regimen/time context; conflict/uncertainty; no inferred mechanism from coefficients |
| longitudinal_support.tsv | contrast/window/episode; response-time effect and scale; interval; paired N; study/cancer/regimen support; biopsy-selection, lesion and assay limitations; A1 release hash |
| handoff_manifest.json | semantic version; artifact SHA-256s; schema/config/code versions; source/admission/exposure/split hashes; development-only assertion; permitted/blocked uses; reviewers and actual dates |

## Receiver acceptance

B verifies all hashes and uses A-BIO as a clinical-reference association layer. B independently tests prostate deficits, regulatory context and cellular alternatives; the fixed B-P molecular endpoint is not altered. C consumes the signed A/B biological direction and regulatory evidence; predictor coefficient signs are not restoration directions. Contradictory and absent evidence remains in the table, not filtered away by model performance.

For each candidate distinguish response-associated abundance, predicted discrimination, localization, prostate deficit, epigenetic association and prospective reversibility. These are separate evidence assertions with different populations and uncertainty. No threshold or top-k handoff selection is frozen until the development-only selection rule is approved; all estimated effects remain available.

## Additional consumers

A1 may supply observed temporal evidence to D/E with episode/window and selection limits. It does not export a causal response function, calibrated kinetic constant or drug efficacy parameter. A future mechanistic model needs independent structural/parameter justification.

## Acceptance tests

Mutating held-out test expression, labels, pairing or modalities must not change A-BIO/context or predictor hashes. A receiver rejects absent hashes, unknown effect scales, mismatched schemas, renamed coefficients as effects, missing exposure lineage and any release populated by reserved data. A clinical validation annotation cannot alter candidate membership. Public artifacts contain study-level provenance and permitted aggregate counts only; patient membership remains a private hash-referenced record.
