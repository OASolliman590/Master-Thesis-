# Source identity, publication families and deduplication

## Originating study

One row represents one originating clinical trial, cohort or molecular study. GEO, SRA, ENA, BioProject, author repositories and atlas copies can all point to the same study.

Study classes are explicit:

- clinical ICI study;
- non-ICI comparator;
- vaccine study;
- adoptive-cell study;
- dendritic-cell study;
- mechanistic cell model;
- untreated molecular cohort.

Only eligible clinical ICI patients enter the Paper A response denominator.

## Publication family

A publication family groups the primary clinical report, molecular report, follow-up report, corrigendum, reanalysis and atlas reuse. Each publication record states which patients, assays, treatments and outcomes are reused.

Publications are never counted as independent cohorts merely because their titles differ.

## Source-object identity

One row represents one exact retrievable object. A repository landing page is not an object. A superseries is not automatically a matrix. Mirrors and reanalyses receive typed overlap edges.

## Patient and specimen identity

- IDs are strings; leading zeros and punctuation are preserved.
- Patient UIDs are stable project pseudonyms scoped to the originating study.
- Raw aliases remain in private authorized storage.
- Cross-study patient equality requires source-supported evidence.
- Multiple lesions are multiple specimens.
- Technical replicates and repeated sequencing are multiple assays, not patients.
- An assay header is linked to a specimen through an evidence-bearing crosswalk.

## Alias crosswalk

`study_alias_crosswalk.tsv` records:

```text
alias_type
alias_value
canonical_study_id
source locator
evidence type
certainty
reviewer
status
```

Alias normalization may remove harmless formatting for candidate matching, but the raw alias is retained and no merge occurs automatically.

## Overlap graph

Allowed edge types include:

- same study;
- same trial;
- publication reuse;
- accession alias;
- repository mirror;
- same patient;
- suspected same patient;
- same specimen;
- repeated sequencing;
- technical replicate;
- multiple lesions;
- reanalysis;
- shared controls;
- derived atlas matrix;
- prior model-training overlap.

Every edge states nodes, evidence, certainty, reviewer, date and implication for independence. Material unresolved overlap blocks claims of independence.

## Certainty scale

- `VERIFIED`: direct ID/crosswalk or explicit source statement;
- `PROBABLE`: multiple concordant attributes but no definitive crosswalk;
- `POSSIBLE`: weak or indirect evidence;
- `UNRESOLVED`: conflicting or insufficient evidence;
- `DISPROVED`: evidence shows distinct entities.

Only `VERIFIED` can merge patient or specimen identities. `PROBABLE` may trigger sensitivity analysis but not a definitive merge without review.

## Deduplication decision

Deduplication is branch-aware. Repeated assays can be retained for QC but only one biological representation is selected per branch under a frozen rule. Suspected cross-study patient overlap is handled conservatively in validation and final-test claims.

## Failure codes

```text
UNRESOLVED_ORIGINATING_STUDY
ACCESSION_ALIAS_CONFLICT
PUBLICATION_SUBSET_UNKNOWN
PATIENT_ALIAS_AMBIGUOUS
SPECIMEN_ALIAS_AMBIGUOUS
REPEAT_ASSAY_UNRESOLVED
MULTIPLE_LESIONS_NO_POLICY
MATERIAL_OVERLAP_UNRESOLVED
```
