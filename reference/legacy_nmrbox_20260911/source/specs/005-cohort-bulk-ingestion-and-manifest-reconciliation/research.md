# Research Notes: Cohort Bulk Ingestion and Manifest Reconciliation (Spec-005)

## Purpose

Capture the decision-locked rationale behind the ingestion reconciliation cycle before implementation work.

## Locked Decisions

### Decision 1: Legacy cohort IDs remain canonical

- **Decision**: retain existing cohort ID conventions (for example `gse126044_srp183455_nsclc_pd1`) in manifests and downstream joins.
- **Why**: prevents broad backward-compatibility breaks across Specs 002-004 artifacts.

### Decision 2: Path mismatch solved via folder mapping, not cohort renaming

- **Decision**: add `downloads_folder` mapping so T7 folder names and canonical cohort IDs can diverge safely.
- **Why**: T7 reconciled folders are already normalized and used operationally; rewriting all cohort IDs would be high-risk churn.

### Decision 3: Full 30-cohort GEO ingestion is required

- **Decision**: run intake/manifest rebuild against all 30 GEO cohorts in `cohorts_source_geo_merged30`.
- **Why**: current underpowered signature risk is linked to sparse sample-level manifest coverage, not stage implementation.

### Decision 4: Full publication-level curation is in scope

- **Decision**: curate all cohorts with manual publication review, not a reduced subset.
- **Why**: maximizes scientific coverage and reduces hidden label/timing ambiguity.

### Decision 5: Supplementary metadata extraction is additive

- **Decision**: use `extract-geo-metadata` output as supplementary evidence, merged with SOFT heuristics and disagreement flags.
- **Why**: MINiML-structured fields can improve confidence where free-text SOFT parsing is ambiguous.

### Decision 6: External tooling shortlist finalized

- **Decision**: skip `geo-analyzer`, `GeoAnalystBench`, `TidyGEO`, and `GREP2`; use only `extract-geo-metadata` for this cycle.
- **Why**: shortlisted alternatives were irrelevant, unclear, or stale for the current GEO sample metadata objective.

## Blockers This Cycle Directly Addresses

- empty or underpowered `PRE_RESPONSE` meta-signature due manifest sparsity
- mismatch between cohort IDs and T7 folder names causing fragile expression resolution
- over-reliance on sync stubs for broad cohort inventory without sample-level analysis utility

## Non-Goals

- processing the 9 non-GEO FASTQ/SRA cohorts in this cycle
- introducing CIBERSORTx acquisition changes
- redesigning router/meta/signature architecture
- replacing manual curation with fully automated label assignment
