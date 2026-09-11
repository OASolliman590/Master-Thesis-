# Recovered legacy MSc pipeline: source-only reference

Retrieved from NMRbox on 11 September 2026 for the user's manual Grok inspection. The 358 files in `source/` retain their original bytes and relative paths. `MANIFEST.json` records SHA-256 and size for every file. This is a selected source archive, not a full server backup, new implementation, successful rerun or scientific acceptance.

## Provenance and completeness

Source: `phosphorus.nmrbox.org:/home/nmrbox/0000/osoliman/ici_thesis_pipeline_canary_20260626_110044/ici_thesis_pipeline_canary`.
The original `NMRBOX_CANARY_BUNDLE.md` identifies the recovered Mac source and a June 26 canary export; later July work exists in this directory. Preserve those distinctions. Historical specs and checked tasks are records, not current instructions or reproduced validation.

AIU's known mirror is `/home/omics/projects/ici_thesis_pipeline/canary/ici_thesis_pipeline_canary`. SSH timed out on 11 September; today's export was taken from NMRbox only. A September 5 audit compared 19 selected files, but that does not establish complete or current mirror identity.

Included: Python/R/shell source, tests' source code, original specs, YAML configuration, environment recipe, container definition, scheduler source, and selected cohort-level/gene-level configuration TSVs. The original source README is under `source/README.md`.

Excluded deliberately: results, figures, reports, logs, downloaded inputs/data, all sample/patient manifests, expression/methylation matrices, notebook/binary outputs, test fixture data, GMT/reference downloads, `.env` profiles, caches/bytecode, Apple metadata and Git internals. This archive therefore cannot reproduce the historical run by itself. Do not execute its launch scripts unchanged: they retain original Mac/NMRbox paths and scheduler assumptions. No live credentials were identified by the local credential-pattern scan; no credentials were intentionally collected.

## Start inspection here

- `source/src/pipeline/`: retrieval, intake, QC, within-cohort differential expression, meta-analysis, signatures, immune-state scoring, validation, TCGA and methylation integration modules. Module presence is not evidence of completion.
- `source/scripts/` and `source/tests/`: prior orchestration and executable expectations; fixtures are intentionally omitted.
- `source/configs/merged_47_studies_track_stratified.tsv`: 47 historical registry rows, NOT 47 independently eligible ICI cohorts.
- `source/configs/timer_candidate_cohort_roster_pre_response.tsv`: 24 historical candidate rows.
- `source/configs/timer_candidate_cohort_roster_treatment_delta.tsv`: 11 historical candidate rows.
- `source/configs/immune_gene_sets_registry*.tsv`: preserved gene-set registry variants; no new membership freeze.

Some old rows include ACT or dendritic-cell treatment, assumed response/timing, accession aliases and counts inconsistent with later source audits. Preserve the old files as evidence and correct these in the NEW Paper A admission registry, never by silently editing this archive. Cross-atlas duplicates and prior outcome exposure must be reconciled before assigning held-out validation roles.

Grok should map each reusable component to the current A1-A7 contract, reuse only after checking behavior, and implement missing current requirements. The active Paper A spec and A/B decision override historical models, labels, gene-selection and validation rules. Do not import this archive into the active package or include its historical tests in routine current test discovery.
