# Research: Spec 008

## Baseline Evidence

Spec 007 verified run:

`results/full_pipeline_20260508_204646`

Key baseline:

- PRE_RESPONSE analyzed cohorts: 22
- Signature genes: 163
- Patient manifest rows: 1188
- Immune ssGSEA score rows: 869
- Immune layer summary rows: 4345

## Allocation Finding

Current curated manifest rows: 1314.

Rows with timing + response that can map to PRE/POST/ON response contrasts: 1120.

Rows currently unallocated: 194.

All current unallocated rows have `unknown_response`.

Largest unallocated cohorts:

| Cohort | Unallocated rows |
|---|---:|
| gse202069_hcc_anti_pd1 | 66 |
| gse93157_nsclc_pd1 | 40 |
| gse195832_hnscc_pd1 | 30 |
| gse235910_hnscc_afatinib | 26 |
| gse106128_melanoma_dcs | 12 |
| gse96619_melanoma_pd1 | 10 |

## ClawBio Relevance

Installed ClawBio references:

- `rnaseq-de`: count matrix + metadata + formula + contrast + reproducibility bundle.
- `bio-orchestrator`: explicit routing and report generation.
- `diff-visualizer`: downstream visualization from completed DE tables.

Spec 008 applies these principles locally rather than replacing the current thesis pipeline.

