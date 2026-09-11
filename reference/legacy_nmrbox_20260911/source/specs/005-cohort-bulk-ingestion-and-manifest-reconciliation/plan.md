# Implementation Plan: Cohort Bulk Ingestion and Manifest Reconciliation (Spec-005)

**Branch**: `005-cohort-bulk-ingestion-and-manifest-reconciliation` | **Date**: 2026-04-12 | **Spec**: `specs/005-cohort-bulk-ingestion-and-manifest-reconciliation/spec.md`  
**Input**: Feature specification from `specs/005-cohort-bulk-ingestion-and-manifest-reconciliation/spec.md`

## Summary

Execute a data-operations cycle that removes the current ingestion bottleneck by reconciling legacy cohort IDs to T7 folder names, rebuilding GEO manifests for all 30 cohorts, and re-running intake/verification stages with full cohort coverage.

Primary outcome target: move from empty-signature risk caused by manifest sparsity to a powered, non-empty discovery signature path.

## Technical Context

**Language/Version**: Python 3.11/3.13 for CLI + utility scripts, shell for orchestration  
**Primary Dependencies**: pandas, pytest, existing pipeline CLI, optional `extract-geo-metadata` stack (`beautifulsoup4`, `openpyxl`)  
**Storage**: file-based TSV/markdown artifacts in `configs/`, `results/`, and `specs/`  
**Testing**: pytest regression + stage-level output/row-count assertions  
**Target Platform**: local workstation + mounted T7 external storage  
**Project Type**: ingestion and curation expansion cycle with one minimal production path-resolution update  
**Constraints**: keep legacy-style cohort IDs, avoid architecture redesign, preserve backward compatibility

## Constitution Check

Gates applied:

- **Truthfulness Gate**: readiness outputs must represent actual sample-level coverage, not sync stubs.
- **Continuity Gate**: legacy cohort IDs remain valid in manifests and reports.
- **Compatibility Gate**: path-resolution change must fallback cleanly when `downloads_folder` is absent.
- **Coverage Gate**: manifests must scale from 13 to 30 GEO cohorts before verification rerun.

Gate status: **PASS**

## Workstreams

### Workstream A: Path Resolution Layer

- build reconciliation ledger between legacy IDs and T7 folder names
- add `downloads_folder` to expression-manifest contract
- update expression resolver with backward-compatible folder fallback

### Workstream B: Discovery Manifest Rebuild

- expand discovery manifest to all 30 GEO cohorts
- preserve existing 13 rows verbatim
- append remaining cohorts with consistent naming and metadata defaults

### Workstream C: Supplementary Metadata Extraction

- integrate `extract-geo-metadata` tooling path
- produce supplementary sample-level metadata outputs
- merge supplementary metadata with SOFT-derived metadata and disagreement flags

### Workstream D: Full Intake Rebuild

- rebuild GEO tables and sample manifests using 30-cohort manifests
- run gene-audit preflight and method inspection/curation sheet generation

### Workstream E: Publication-Level Curation

- fill study-level curation fields for all cohorts
- apply curation to rebuild final curated manifest and remove sync stubs

### Workstream F: Verification Evidence Run

- execute full pipeline with rebuilt manifests and T7-mounted expression paths
- verify signature non-emptiness and readiness contracts
- publish reconciliation report with final inventory/eligibility outcomes

## Implementation Policies

### Policy 1: Cohort-ID continuity with explicit folder mapping

- preserve legacy cohort IDs used across prior specs/run artifacts
- introduce explicit folder mapping (`downloads_folder`) instead of renaming cohorts

### Policy 2: Manual curation remains mandatory for thesis-grade claims

- heuristics and supplementary metadata can pre-fill labels
- publication-reviewed curation remains the authority for final include/exclude and pair assignment

### Policy 3: Verification standards are contract-driven

- success criteria are evaluated from explicit row/count artifacts
- blocked criteria must be surfaced as status, not hidden by command success

## Artifact Policy

New or updated artifacts in this cycle:

- `specs/005-cohort-bulk-ingestion-and-manifest-reconciliation/*`
- `configs/cohort_id_reconciliation_ledger.tsv`
- expanded `configs/discovery_geo_focus.tsv` and `configs/geo_input_routing_manifest.tsv`
- rebuilt `results/geo_tables/geo_tables_summary.tsv` with `downloads_folder`
- `results/spec_005/supplementary_metadata_merged.tsv`
- `results/spec_005/ingestion_reconciliation_report.md`
