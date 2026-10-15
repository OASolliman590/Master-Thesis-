# Bounded implementation and migration tickets

Shared acquisition DAV-T01–DAV-T14 remain owned by ../A_DATA_ACQUISITION_VALIDATION/TICKETS_AND_TESTS.md. Do not duplicate their parsers, identity store, pairing builder or release engine. The following tickets depend on shared receipts and extend analysis functionality. A ticket is not an execution permission; release it through the integrator. No real biological run is included in the current packet.

| ID / owner | Dependencies; inputs | Deliverable / port decision | Acceptance and stop rule |
|---|---|---|---|
| A-M01 / recovery implementer | Pinned three-way trees, authorized storage list | Full component/hash/function inventory; salvage exact retrieval/IO utilities | Original bytes unchanged; missing locations explicit; no historical tests called current |
| A-M02 / schema implementer | Shared schemas and episode-binding amendment | Consumer join/receipt validator; reuse shared IDs | Adversarial episode mismatch, alias collision, patient/sample cardinality and private-output tests; no shadow store |
| A-M03 / assay implementer | DAV source/assay releases | Port qualified annotation and count/continuous routing | TPM-as-counts and unknown-unit fail; missing/zero distinct; duplicates resolved by config, not row order |
| A-B01 / statistician+implementer | A-M02/03; A-BIO numerical release | Study-effect adapters, rank/contrast audit, complete result schema | Synthetic sign/scale/rank/covariate tests; full tested universe retained; no real run before release |
| A-B02 / meta implementer | A-B01; independent family/covariance registry | Compatible-scale synthesis and influence | Incompatible scales/shared controls rejected; small-k/nonconvergence explicit; negative effects retained |
| A-B03 / biology curator | Programme registry; A-B01; optional modality receipts | Source-correct programme/context products | Version/coverage tests; no coefficient-to-mechanism substitution; optional branch failure isolated |
| A-P01 / ML implementer | A-M02/03; grouped split/statistical config | Nested elastic-net pipeline, not legacy DEG signature | Held-out label/expression mutation cannot alter training; invalid folds fail, no random-patient fallback |
| A-P02 / evaluator | A-P01 final frozen model; final-test release | Paired AUC difference and fixed-weight aggregate | Same patients, tied/undefined AUC, joint resampling, no source-drop renormalization, all source failures visible |
| A-P03 / endpoint implementer | Admitted O/SD/PD; fixed CYT | A-P1 decomposition/joint bootstrap | Algebra identity, no-SD zero, absent PD undefined, fixed score across endpoints; learned score optional independent |
| A-H01 / integrator | A-BIO/context release; optional A-PRED/A1 | B/C artifacts and hash manifest | Test mutations cannot change handoff; effect/coefficient schemas distinct; public privacy scan |
| A-R01 / reporting implementer | Frozen analysis outputs/receipts | Four figures and reproduction bundle | Panel N/source/uncertainty/claim fields; no-result placeholders; fresh build/resume checks |

## Test plan with scientific mutation oracles

Identity: duplicate accessions/publications/resequencing/lesions cannot increase unique N; numeric-looking IDs retain zeros; normalization collisions block. Outcomes: preserve original CR/PR/SD/PD/NE; undefined binary/PSA/DCB/censored labels cannot become ORR. Timing: progression and regimen changes never become generic on-treatment; row permutation cannot change pair selection. Assays: negative/unknown units fail, missing genes remain missing, partial FPKM cannot create TPM, annotation ambiguity cannot be silently summed.

Prediction: mutate held-out labels and abundances independently and compare feature/config/handoff hashes; permute study aliases to test family grouping; force one-class folds, nonconvergence and a required-source failure. Do not accept a test that checks only that a function returns. Inference: toy data with a known interaction sign, response main-effect alias under fixed patient effects, shared baseline covariance and mismatched effect scales must expose errors.

For each behavior change, write and run a failing characterization/adversarial test before the smallest fix, then run focused and relevant full suites. Record original/ported versions and exact commands. Synthetic software tests are not clinical validation; source-format tracers validate only their measured dimensions; historical real-data reports remain historical until reproduced. A ticket closes only with its receipt, review, tests and allowed-scope evidence—not a count of files written.
