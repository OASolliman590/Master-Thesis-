# Research: Automated Metadata Curation and Response Label Extraction

## Problem Statement

The RNA-seq meta-analysis pipeline has 30 GEO cohorts ingested but only 3 are DE-eligible for PRE_RESPONSE because 25 cohorts lack curated response labels. Investigation reveals that 12 of those cohorts have response labels embedded in SOFT `characteristics_ch1` fields — the pipeline's existing `_infer_response_from_text()` heuristic simply doesn't parse these fields.

## Tool Evaluation

### 1. getGeoMetadata (R Package)

**Source**: https://github.com/rkweku/getGeoMetadata
**Paper**: PMC9982356 (Bioinformatics Advances, 2023)

**What it does**: R package that fetches GEO metadata via HTTP and parses `characteristics_ch1` key-value pairs into tidy data frames with one column per characteristic key.

**Strengths**:
- Clean parsing of characteristics into structured columns
- Handles batch processing of multiple GSE IDs
- Lightweight alternative to GEOquery

**Limitations**:
- Requires R runtime
- Fetches via HTTP — we already have SOFT files locally
- No semantic harmonization of field names or values
- Response label extraction still requires downstream mapping

**Decision**: Deferred to Phase 6 as optional supplementary source. Primary extraction will use Python parsing of local SOFT files, avoiding an R dependency.

### 2. extract-geo-metadata (Python)

**Source**: https://github.com/rachadele/extract-geo-metadata

**What it does**: Python tool that parses MINiML XML files from GEO FTP to extract sample-level metadata.

**Status**: Already integrated in Spec-005 Phase 3. Run on all 30 cohorts. Results in `results/spec_005/supplementary_metadata_merged.tsv`.

**Findings**: Found supplementary response labels for only 3 cohorts (gse126044, gse218989, gse78220) that already had SOFT-parsed labels. Did not find additional response data for the uncurated cohorts.

**Conclusion**: MINiML XML does not contain response data that SOFT doesn't. The gap is in the SOFT parsing, not the data source.

### 3. Direct SOFT Characteristics Parsing (Python)

**The chosen approach**. The SOFT files are already downloaded on T7 for all 30 cohorts. The `characteristics_ch1` fields contain rich metadata that the pipeline's existing heuristic doesn't parse.

**Evidence of available data** (from manual inspection):

| Cohort | Response Field | Values | Timing Field |
|--------|---------------|--------|-------------|
| GSE91061 | `response` | PD, PR, CR, SD | `visit (pre or on treatment)` |
| GSE159067 | `best response on immunotherapy (recist)` | PD, PR, CR, SD | None |
| GSE106128 | `dth response` | TBD | None |
| GSE207422 | `pathologic_response` | TBD | None |
| GSE100797 | `recist`, `tumor.response` | TBD | `sample.timepoint` |
| GSE210287 | `response` | TBD | `timepoint` |
| GSE67501 | `response to anti-pd-1 (nivolumab) immunotherapy (response or no-response)` | response, no_response | None |
| GSE93157 | `response` | TBD | None |

## RECIST Response Mapping Standard

RECIST 1.1 (Response Evaluation Criteria in Solid Tumors) is the standard clinical response classification for solid tumors:

| RECIST | Description | Pipeline Label |
|--------|------------|---------------|
| CR | Complete Response | responder |
| PR | Partial Response | responder |
| SD | Stable Disease | non_responder |
| PD | Progressive Disease | non_responder |

This mapping is standard for immunotherapy meta-analyses. Some studies may use alternative schemes:
- Response/No Response (binary)
- Durable Clinical Benefit (DCB) / No Durable Clinical Benefit (NDB)
- Objective Response Rate (ORR: CR+PR vs SD+PD)

The response mapping config must be cohort-specific to handle these variations.

## Expression Column Name Mapping

GEO expression files frequently use study-specific patient IDs instead of GSM accession numbers:

| Cohort | Expression Column Pattern | SOFT Title Pattern | Transformation |
|--------|--------------------------|-------------------|---------------|
| GSE126044 | `Dis_01` | `RNA-seq_Dis_01` | Strip `RNA-seq_` |
| GSE78220 | `Pt1.baseline` | `Pt1` | Append timing suffix from description |
| GSE218989 | `SMC__Pat1` | `SMC__Pat1` | Direct match |
| GSE91061 | `Pt1_Pre_AD101148-6`? | `Pt1_Pre_AD101148-6` | Direct match to title |

The alias extraction must handle per-cohort transformation rules.

## Risk: Cohorts Without Response Data

~8 cohorts have no response data in any GEO metadata field:
- GSE135222, GSE145996, GSE195832, GSE202069, GSE235910, GSE96619
- Plus stub cohorts: GSE176307, GSE215011, GSE222932, GSE222934, GSE235919, GSE289583, GSE305240, GSE305511, GSE306800

These require manual publication review (Spec-007 scope) or remain excluded from the primary meta-analysis.
