# Review and validation status

12 September 2026. This milestone adds documentation, a search plan, a candidate-source schema and Codex handoffs. Existing analysis code, paper primary endpoints, historical archive bytes, main-branch history and wet-lab documents are not changed by the proposed tree.

## Evidence inspected

The live repository baseline is `a8278c776da7c6b096cc14139d729979db286b50`. Current scope and source contracts, AGENTS/GOAL, the recovered archive README, original-study queue, selected historical source helpers and source-aware search results were inspected. The submitted eight-page protocol supplied by the user was used for the high-level mapping. A bounded primary-method and source-lead review is recorded in REFERENCES_AND_NOVELTY.md.

The source-code review is selective, not a certification or rerun of the legacy pipeline. The identified helper behaviours require caller/test investigation; this kit does not infer that every historical output is invalid. New study leads have not passed patient/object-level admission.

## Checks completed and their limits

The candidate-source schema was checked locally against the JSON Schema Draft 2020-12 meta-schema. A clearly synthetic candidate record was accepted. Seven adversarial variants were rejected: negative count, unknown paper, malformed hash, unsupported retrieval claim, unsupported admission claim, raw FASTQ object type and undeclared field. These are structural checks only, not patient-pairing, permission or scientific validation. The checked schema JSON's canonical parsed content must match the committed schema; textual formatting need not be identical.

The Markdown uses five Mermaid design diagrams with GitHub-supported fenced syntax. Browser rendering of the diagrams has not been tested here. No plot of biological results is provided. Repository readback/PR verification is required when the integration commit is published.

No real biological model, source-expanded meta-analysis, deconvolution, MOFA/DIABLO fit, perturbational model, AIU job or full pipeline regression ran in this milestone. No Codex agent, optional literature connector or background task was launched. Independent scientific and code review remain pending.

## Required before real analyses

Complete X0/X1 source and reuse evidence, review the processed-assay contracts, establish original-study and patient/specimen independence, freeze the exact analysis and precision rules, approve the relevant stage release, and validate the actual execution environment and pipeline. Do not let optional blocked assays stop an otherwise valid released core; do not represent them as completed either.

The next handoff is Prompt 1 and the first milestone is FIRST_HANDBACK.md. There is no requirement to resolve all papers' scientific results before this useful source milestone can finish.
