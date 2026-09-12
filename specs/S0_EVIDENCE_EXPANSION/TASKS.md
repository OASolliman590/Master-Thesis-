# Execution tasks and acceptance

**Start with X0 and X1 only.** This kit is a review draft. These are bounded source/reuse tasks, not a mandate to run all papers or a claim that the expanded scientific analyses are ready. Existing A-P2/B-P/C/D contracts remain controlling.

## Task map

| Task | Deliverable | Dependency and release |
|---|---|---|
| X0 — selective legacy reuse | `legacy_reuse.tsv` plus inspected caller/test evidence | Can start now; do not execute historical launch scripts or alter archived bytes |
| X1 — original-study expansion | Search log, original-study crosswalk, source objects, assay/timepoint/endpoint coverage, exposure and unresolved decisions | Can start with X0; no biological scores or model fitting |
| X2 — processed-data adapters | Source-specific identity/measurement validators, schemas and adversarial fixtures | Implement only the reviewed source/adapter contracts; raw-data fallback prohibited |
| X3 — statistical release | Exact estimands, assay routes, exclusions, covariates, test families, split registries and precision assessment | Requires admitted candidate structure; independent scientific review before real fitting |
| X4 — A biological/prediction integration | Development-only biological effects and unchanged A-P2 pipeline, separate handoff artifacts | Software fixtures after X2/X3 design; real run only after its explicit release |
| X5 — A.1 longitudinal/regimen analysis | Verified timing/paired contrasts, interaction synthesis and NMA-feasibility report | Source-specific pairing and full-rank model gates; not a compulsory separate paper |
| X6 — B multi-omics context | Clinical/specimen-state audit, view intersections and qualified regulatory/latent-factor analyses | Existing B-P preserved; A-derived modules wait for A's frozen product; fixed B module need not wait |
| X7 — cell/spatial corroboration | Qualified references, donor-level cellular/spatial statistics and interpretation | Optional supported branches; lack of spatial data does not stop the RNA backbone |
| X8 — C/D source and model interfaces | Preserved C evidence architecture; actual perturbation coverage; independent D benchmark eligibility | Production remains sequential and separately released; no simulated measurements |
| X9 — reproduction/publication package | Evidence-linked figures, tables, methods, provenance, limitations and manuscript ownership | Real analyses completed and reviewed; journal acceptance is not an acceptance test |

## X0: inspect only reusable components

Read the archive README and manifest. Inspect the recovered intake, clinical mapping, time/response contrast routing, expression preprocessing, within-cohort DE, meta-analysis, immune scoring, TCGA mapping and relevant tests. Use file paths, hashes and function names in `legacy_reuse.tsv` with disposition `reuse_after_tests`, `adapt`, `replace`, `out_of_scope` or `not_inspected`.

Mandatory cases include `06_within_cohort_de/harmonize.py` (missing-value zero fill and assay transforms), `de_models.py` (unknown/non-count fallback), and `09_immune_state/ssgsea.py` (legacy rank mean versus GSVA backend). Inspect upstream validation/callers before judging their effect on historical results. The large `cli.py` is a candidate implementation source, not automatically a validated workflow. Missing fixtures remain missing; recreations must be visibly synthetic.

Preserve historical `PRE_RESPONSE`, `ON_RESPONSE`, `POST_RESPONSE`, `TREATMENT_DELTA`, `DELTA_RESPONSE` and pan-cancer aliases. Compare actual semantics and patient/contrast membership hashes before reuse. Prior outcomes/model exposure must be carried forward, not erased by a new checkout.

Acceptance: each selected reusable function has an actual inspected source and risk/test mapping. No requirement to repair the entire old codebase. No statement that a module works merely because its filename exists.

## X1: the first useful scientific handback

Owned output root: `docs/research/expansion_20260912/` and future patient-free source tables under `specs/S0_EVIDENCE_EXPANSION/`. Preserve all existing paper registries and archived data as sources; write corrections into new tables.

Deliver:

1. `search_log.tsv`: source family, exact query/date, result IDs, pagination/completeness, screening and follow-up.
2. `study_crosswalk.tsv`: original study/trial, publications, accession/resource aliases, overlap evidence and unresolved edges.
3. `source_objects.jsonl`: source-level records with actual access/units/transforms, retrieval evidence and unknowns. Validate against the proposed schema or document a reviewed schema amendment.
4. `coverage_by_question.tsv`: paper/module, assay, tissue, treatment, timepoint, response definition, pairing level, patient/experiment unit and each verified denominator. Unknown N stays unknown.
5. `exposure_and_split_feasibility.tsv`: prior exposure, source overlap and whether a structurally valid development/test scheme is possible. Do not select held-out studies by their measured performance.
6. `FIRST_HANDBACK.md`: what is available, the most useful missing evidence, specific next retrievals, legacy reuse findings and a short decision list. Include negative/unavailable sources, not only successes.

At source-inventory completion every preserved source family must have a disposition. At an interim checkpoint clearly mark incomplete searches; do not substitute the five previously audited GEO examples for the expanded roster. A response must not advertise 77 studies, 47 cohorts or historical pipeline sample totals as verified eligibility.

## X2: adapter tests that must fail closed

Implement validated public boundaries, not a chain of scripts coupled by implicit filenames. Preserve original IDs and source locators. Separate retrieval, identity, endpoint mapping, assay processing and analysis-stage release.

Required adversarial fixtures: unknown measurement units; TPM mislabelled as counts; missing values confused with zero; incomplete feature universes; repeated patients/assays; two original columns sharing a name; baseline versus on-treatment swaps; progression biopsy mislabelled scheduled follow-up; primary-tumour code mislabelled treatment-naive; different lesions called the same specimen; gene/probe mapping collisions; mixed protein scales; missing coordinates; reused controls; and forged/missing provenance hashes. Fixtures test software, not biology.

The candidate source JSON schema validates record structure only. X2 must add relational checks, actual object/header/ID verification, date semantics, nonnegative/compatible counts, declared biological units and authorized access. A schema pass is not a scientific-admission receipt.

## X3: decisions to freeze, not defaults to guess

Specify the analysis-specific cohort set, estimand, measurement/effect scale, original endpoint/time window, patient/experiment unit, covariates, missingness, multiplicity, pooling hierarchy, heterogeneity/interval method and meaningful precision target. Verify the sample/class/paired structure using admitted metadata, not published headline counts. Outcome-free simulations may assess design precision and implementation with explicit synthetic labels.

Preserve the existing A-P2 and B-P primary endpoints. New analyses need named secondary/discovery families; no automatic promotion of a favourable result. Clinical NMA requires its own comparative-network feasibility and risk-of-bias review. One final-test cohort cannot be dropped after evaluation merely to improve the aggregate.

## X4–X8 implementation safeguards

Use isolated branches/worktrees and owned modules; do not alter B while implementing A. Reuse existing schema/hash/resume patterns only after checking compatibility. Final-test expression/labels/timepoints cannot alter training transformations, features, tuning or handoff products. Test these invariants by deliberately changing held-out inputs.

For longitudinal models, test known interaction sign, patient grouping, full-rank fixed/random-effects designs and shared-control dependence. For integration, test exact subject/feature ordering, missing views, training-only transforms, same-patient modality ablations and no pseudo-label leakage. For spatial data, preserve patient/section nesting and distinguish coordinates from expression embeddings.

AIU remains the principal execution host. Discover actual available environments, supported package APIs, scheduler and running jobs before dispatch. No guessed model IDs, credits, paid compute, new providers or raw downloads. A connection failure leaves a pending remote-validation receipt; do not relaunch an unknown running job or claim an unrun test passed.

## X9: figures and publication ownership

Every figure needs source tables, patient/experiment denominators, units, uncertainty, exclusions and a claim ceiling. Use design diagrams before results, never synthetic graphs disguised as findings.

Proposed evidence ownership: A owns baseline cross-study biology and frozen prediction; A.1 owns longitudinal/regimen interactions if separately viable; B owns prostate regulatory and stage-aware multi-omics context; C owns intervention evidence; D owns the independent benchmark. Shared cohorts and reused figures must be disclosed. Do not duplicate the same baseline contrast under a new paper name.

Prepare paper-specific methods and a protocol-deviation table after actual execution. Validate citation identity and dataset versions. A valid null result stays publishable in principle; acceptance or a target publication count is not guaranteed.
