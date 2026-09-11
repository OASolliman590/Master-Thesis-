# Implementation Plan: ICI Discovery + Immune-State Interpretation to PRAD Epigenetic Validation (v1)

**Branch**: `002-ici-discovery-meta-pipeline` | **Date**: 2026-03-21 | **Spec**: `specs/002-ici-discovery-meta-pipeline/spec.md`  
**Input**: Feature specification from `specs/002-ici-discovery-meta-pipeline/spec.md`

## Summary

Implement three linked workstreams:

1. **Workstream A (coverage + discovery)**: retrieval, dataset intake, cohort promotion audit, within-cohort DE/meta, and signature freeze.
2. **Workstream B (immune-state interpretation)**: ESTIMATE, CIBERSORTx, ssGSEA, HOPE/HOPE-18, marker correlations, and cohort-level effects.
3. **Workstream C (mechanistic validation)**: held-out validation, GDC TCGA PRAD/LUAD mapping/projection, TCIA IPS secondary overlay, and methylation integration.

`PRE_RESPONSE` remains the primary discovery contrast. Immune-state scoring is downstream interpretation and does not replace discovery statistics.

## Technical Context

**Language/Version**: Python 3.11 primary; R 4.3+ hooks for DE/meta/methylation and scoring wrappers  
**Primary Dependencies**: pandas, pydantic, pyarrow, numpy, scipy, statsmodels; Salmon/tximport for raw ingestion; DESeq2/edgeR for raw-count DE; GSVA (ssGSEA) and ESTIMATE for immune scoring; CIBERSORTx outputs as inputs  
**Storage**: File-based TSV/Parquet outputs plus markdown/QMD reports under repo-local artifacts  
**Testing**: pytest contract + integration smoke tests  
**Target Platform**: Local workstation first, HPC-compatible command model second  
**Project Type**: Single CLI scaffold with modular stages  
**Constraints**: heterogeneous metadata, mixed input classes, cross-cancer heterogeneity, sparse paired samples, method-concordance ambiguity, non-independent TCIA annotations  
**Scale/Scope**: discovery starts from frozen core cohorts; cohort expansion audit grows candidate cohort universe by curation rules

## Constitution Check

Gates applied:

- **Reproducibility Gate**: all stages emit deterministic contracts and run manifests.
- **Traceability Gate**: every promoted cohort/sample retains accession and label provenance.
- **Separation Gate**: discovery inference remains in-pipeline (within-cohort DE then meta-analysis).
- **Continuous-First Gate**: immune-state statistics use continuous models as primary; strata are sensitivity-only.
- **No-Leakage Gate**: validation and TCGA layers do not refit discovery signatures.

Gate status: **PASS**

## Project Structure

### Documentation (this feature)

```text
06_analysis_pipeline_repo/specs/002-ici-discovery-meta-pipeline/
├── plan.md
├── spec.md
├── research.md
├── quickstart.md
├── contracts/
│   └── io-contracts.md
└── tasks.md
```

### Source Code (repository root)

```text
06_analysis_pipeline_repo/
├── src/
│   └── pipeline/
│       ├── cli/
│       ├── common/
│       └── modules/
│           ├── 00_retrieval/
│           ├── 01_dataset_intake/
│           ├── 02_cohort_audit/
│           ├── 03_manifest/
│           ├── 04_ingest_expression/
│           ├── 05_qc/
│           ├── 06_within_cohort_de/
│           ├── 07_meta_analysis/
│           ├── 08_signature_scoring/
│           ├── 09_immune_state/
│           ├── 10_validation/
│           ├── 11_tcga_gdc_map/
│           ├── 12_tcga_projection/
│           ├── 13_tcia_overlay/
│           ├── 14_methylation_integration/
│           └── 15_reports/
├── configs/
├── tests/
│   ├── contract/
│   ├── integration/
│   └── unit/
├── logs/
├── results/
└── docs/
```

## External Archetypes Reviewed (GitHub MCP)

- `nf-core/fetchngs`: accession-first public retrieval patterns for GEO/SRA/ENA.
- `saketkc/pysradb`: accession crosswalk and metadata query patterns.
- `seandavi/GEOquery`: GEO matrix/metadata retrieval in Bioconductor workflows.
- `ncbi/sra-tools`: run-level fallback retrieval with `prefetch`/`fasterq-dump`.
- `nf-core/rnaseq`: robust RNA-seq stage boundaries and QC practice.
- `snakemake-workflows/rna-seq-star-deseq2`: pragmatic DE-oriented stage decomposition.
- `csoneson/ARMOR`: lightweight reproducible RNA-seq statistical architecture.
- `cran/metaRNASeq`: p-value combination sensitivity meta-analysis.

## Workstream Policies

### Workstream A: Discovery

- Discovery cohorts come from `core_discovery_cohorts_v1.tsv`.
- Candidate cohorts are expanded through primary-source accession tracing and promotion audit.
- Third-party precomputed DEG/ROC tables are never primary discovery statistics.
- Discovery inference remains within-cohort DE then cross-cohort meta-analysis.

### Workstream B: Immune-State Interpretation

- Methods: ESTIMATE, CIBERSORTx (absolute + relative), ssGSEA, HOPE/HOPE-18.
- Applies to RNA cohorts only; non-RNA cohorts are explicitly excluded with reasons.
- Continuous models are primary; median/quartile groups are secondary sensitivity layers.
- Immune-state outputs are interpretation/context layers, not discovery replacement.
- ssGSEA/HOPE/HOPE-18 must use cohort-specific gene sets (GMT) registered in a registry file; no proxies.
- CIBERSORTx inputs must be provided explicitly (absolute + relative outputs).

### Workstream C: Mechanistic Validation

- TCGA source-of-truth is GDC.
- Build strict barcode-level `tcga_sample_map.tsv`.
- Project frozen signatures into PRAD/LUAD, then attach TCIA IPS as secondary annotation.
- Integrate promoter methylation after expression and immune-state projection.

## Contrast and Inference Policy

- Primary contrast: `PRE_RESPONSE`.
- Secondary contrast: `TREATMENT_DELTA` (paired/blocked where possible).
- Tertiary contrast: `ON_RESPONSE` for timing-consistent cohorts only.
- Inference unit: cohort first, then meta-analysis.
- Explicitly disallowed: pooled cross-cancer discovery DE with blanket batch correction.
- Immune-state association policy: continuous-score tests primary; dichotomized splits secondary.

## Special Cohort Routing

Some GEO cohorts are scientifically valuable but do not fit the default `PRE_RESPONSE` / `TREATMENT_DELTA` / `ON_RESPONSE` discovery mold. These must be routed to dedicated methods rather than forced into responder modeling.

- `gse135222_srp217040_nsclc_pdl1`: treat as an ICI-treated NSCLC comparative multi-omics cohort with linked RNA-seq (`GSE135222`) and methylation array (`GSE119144`).
- Planned method:
  - expression-only exploratory clustering and immune-program scoring within the RNA arm
  - methylation-expression integration focused on immune-evasion and interferon-related programs
  - promoter / CpG-region methylation to expression coupling and pathway-level concordance
  - no primary responder-vs-nonresponder DE unless paper-grade clinical labels are recovered later

- `gse202069_hcc_anti_pd1`: treat as a mixed HCC series with two analytical layers rather than a single response cohort.
- Planned method:
  - primary layer: `tumor vs adjacent/nontumor` expression analysis across the full series
  - secondary layer: manual extraction of the anti-PD1-treated tumor subset (`n=17`) for later immunotherapy-specific annotation
  - subtype / program association for the treated subset only after explicit clinical mapping
  - no direct entry into `PRE_RESPONSE` discovery until the treated subset manifest is curated separately

## Cohort-by-Cohort Execution Plan (v1)

Each cohort runs independently with explicit inputs and tool selection. No cohort proceeds to DE or immune scoring without validated inputs and method eligibility.

1. **Input resolution**
   - Inputs: accession-resolved expression file (raw counts or processed matrix), sample manifest rows for the cohort.
   - Output: cohort-specific expression matrix + metadata table.
2. **QC (RNA)**
   - Tools: Python QC module (library size, zero fraction, outlier flags).
   - Output: `results/cohort_qc/<cohort_id>/qc_metrics.tsv` and `sample_outlier_flags.tsv`.
3. **Within-cohort DE**
   - If `input_class=raw_counts`: DESeq2 or edgeR via R wrapper (`scripts/rna_deseq2.R` or `scripts/rna_edger.R`).
   - If `input_class=processed_matrix`: Welch t-test on log2 expression (Python).
   - Output: `results/within_cohort_de/<contrast>/<cohort_id>.tsv`.
4. **Special routing**
   - `gse202069_hcc_anti_pd1`: execute `tumor vs adjacent` DE as the primary contrast.
   - `gse135222_srp217040_nsclc_pdl1`: execute RNA+methylation concordance branch; no responder DE.
5. **Meta-analysis**
   - Inputs: per-cohort DE tables for the same contrast.
   - Output: `results/meta_analysis/<contrast>/meta_effects.tsv`.
6. **Immune-state scoring**
   - Inputs: cohort-specific GMT gene set (registry), CIBERSORTx absolute + relative outputs.
   - Tools: GSVA (ssGSEA) + ESTIMATE (R scripts), CIBERSORTx outputs imported, HOPE/HOPE-18 computed only if gene sets present.
   - Output: `results/immune_state/*` (scores + cohort effects).

## Artifact Policy

Versioned outputs per run:

- `retrieval/`
- `dataset_intake/`
- `cohort_audit/`
- `sample_manifest.tsv`
- `cohort_qc/`
- `within_cohort_de/`
- `meta_analysis/`
- `signature_sets/`
- `immune_state/`
- `validation/`
- `tcga_gdc_map/`
- `tcga_projection/`
- `tcia_overlay/`
- `methylation_integration/`
- `reports/`

Each run emits `logs/run_manifest.yaml` with config, inputs, and software versions.
