# Feature Specification: ICI Discovery + Immune-State Interpretation to PRAD Epigenetic Validation (v1)

**Feature Branch**: `002-ici-discovery-meta-pipeline`  
**Created**: 2026-03-21  
**Status**: Draft  
**Input**: User direction to run primary-source cohort expansion, study-preserving responder discovery, immune-state interpretation (ESTIMATE/CIBERSORTx/ssGSEA/HOPE), and GDC TCGA PRAD/LUAD methylation mechanism with TCIA IPS as secondary annotation.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Retrieve and inspect discovery datasets before modeling (Priority: P1)

As the analysis owner, I need a reproducible retrieval and intake layer so each discovery cohort is accession-resolved, download-audited, and input-classified before harmonization and DE.

**Why this priority**: If acquisition and intake are ad hoc, downstream harmonization and DE become irreproducible.

**Independent Test**: Build a valid retrieval ledger and dataset-inspection table for all cohorts in the frozen discovery manifest.

**Acceptance Scenarios**:

1. **Given** `core_discovery_cohorts_v1.tsv`, **When** retrieval runs, **Then** each cohort has a resolved accession crosswalk (`GSE`/`GSM`/`SRP`/`SRX`/`SRR` where available), source URI, and retrieval status.
2. **Given** retrieved or linked inputs for a cohort, **When** intake inspection runs, **Then** each sample is assigned an `input_class` (`FASTQ`, `raw_counts`, `processed_matrix`) with assay and file-type evidence.

---

### User Story 2 - Run primary-source all-cancer cohort expansion audit (Priority: P1)

As the analysis owner, I need all-cancer candidate cohorts discovered from primary sources mapped against my inventory so I can expand coverage without losing accession-level provenance.

**Why this priority**: This is how we increase cohort coverage while preserving accession-level provenance.

**Independent Test**: Emit `cohort_promotion_audit.tsv` with role decisions and supporting provenance fields.

**Acceptance Scenarios**:

1. **Given** candidate cohorts from GEO/SRA/PubMed/ClinicalTrials tracing, **When** audit runs, **Then** each row includes accession traceability and role decision.
2. **Given** a candidate cohort lacking traceable accession or timing/response context, **When** decision is applied, **Then** it is marked `hold`, not promoted into discovery by default.

---

### User Story 3 - Build canonical sample-level metadata for discovery contrasts (Priority: P1)

As the analysis owner, I need one canonical sample-level metadata table so all downstream DE and meta-analysis steps use consistent response and timing labels.

**Why this priority**: Without stable sample metadata, every later inference step becomes non-reproducible.

**Independent Test**: Generate a valid `sample_manifest.tsv` from discovery manifest plus retrieval/intake outputs and confirm all required fields and label vocabularies pass contract checks.

**Acceptance Scenarios**:

1. **Given** retrieval and inspection outputs, **When** manifest build runs, **Then** each included sample receives standardized `response_label`, `timing_category`, and `input_class`.
2. **Given** a cohort with ambiguous labels, **When** harmonization rules are applied, **Then** the sample is flagged with explicit exclusion reason rather than silently misclassified.

---

### User Story 4 - Run study-preserving DE and cross-cohort meta-analysis (Priority: P1)

As the analysis owner, I need DE to run inside each cohort and then be meta-analyzed across cohorts so heterogeneity is handled explicitly.

**Why this priority**: The thesis discovery layer depends on credible cohort-level inference, especially for responder biology.

**Independent Test**: Run DE for at least one cohort and generate `PRE_RESPONSE` meta-analysis output with sensitivity results.

**Acceptance Scenarios**:

1. **Given** pretreatment responder and non-responder samples, **When** DE runs, **Then** `PRE_RESPONSE` results are produced without equal-size downsampling.
2. **Given** cohort-level DE tables for one contrast family, **When** meta runs, **Then** random-effects output and p-value-combination sensitivity output are both emitted.

---

### User Story 5 - Add immune-state interpretation as downstream module (Priority: P1)

As the analysis owner, I need a multi-method immune-state layer so discovery signatures are interpreted using complementary transcriptomic views rather than one score family.

**Why this priority**: This strengthens biological interpretation while keeping the DE/meta engine as the primary discovery source.

**Independent Test**: Emit `estimate_scores.tsv`, `cibersort_absolute.tsv`, `cibersort_relative.tsv`, `ssgsea_scores.tsv`, `hope_types.tsv`, `hope18_scores.tsv`, `marker_correlations.tsv`, and `cohort_level_effects.tsv`.

**Acceptance Scenarios**:

1. **Given** RNA-seq cohorts in discovery/validation/TCGA, **When** immune scoring runs, **Then** per-sample scores and method metadata are emitted for ESTIMATE, CIBERSORTx, ssGSEA, and HOPE/HOPE-18.
2. **Given** cohort-specific gene-set registry entries and CIBERSORTx outputs, **When** immune scoring runs, **Then** scores are produced only from those inputs and no proxy/placeholder outputs are emitted.
3. **Given** a methylation-only or non-RNA cohort, **When** immune scoring is invoked, **Then** the cohort is excluded with explicit reason and no silent fallback.
4. **Given** score outputs and response labels, **When** association analysis runs, **Then** continuous-score models are primary and median/quartile stratifications are emitted only as sensitivity outputs.

---

### User Story 6 - Validate frozen signatures and execute PRAD/LUAD methylation mechanism layer (Priority: P2)

As the thesis owner, I need frozen discovery signatures tested on held-out cohorts and then projected into GDC TCGA PRAD/LUAD with TCIA IPS overlay and methylation integration.

**Why this priority**: This is the mechanistic epigenetic-priming validation layer of the thesis.

**Independent Test**: Score one held-out cohort and emit `tcga_sample_map.tsv`, `tcia_ips_annotations.tsv`, projection table, and `tcga_immune_methylation_integration.tsv`.

**Acceptance Scenarios**:

1. **Given** frozen signatures, **When** validation scoring runs, **Then** no validation cohort is used in signature re-fitting.
2. **Given** PRAD/LUAD GDC inputs, **When** projection and methylation modules run, **Then** outputs include candidate-level expression direction, immune-state context, methylation direction, and integrated prioritization flags.
3. **Given** TCIA IPS annotations, **When** overlay runs, **Then** annotations are attached to TCGA records as secondary reference fields and are flagged as non-independent of TCGA.

### Edge Cases

- Discovery cohorts listed but with unavailable or moved links.
- Candidate cohorts with incomplete accession provenance.
- Mixed `FASTQ`, `raw_counts`, and normalized matrices in one accession family.
- Very small responder counts that destabilize model fitting.
- Genes absent in one or more cohorts after filtering/harmonization.
- Strong heterogeneity where direction-consistency and pooled effect conflict.
- RNA-unsupported cohorts being mistakenly routed into immune-state modules.
- Discordant immune-state methods (for example high ESTIMATE with low cytotoxic ssGSEA signal).
- TCGA sample-barcode collisions across multiple aliquots/files.
- Probe-to-gene ambiguity for promoter methylation summaries.
- Missing TCIA IPS annotations for subset samples.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST use `02_data_inventory/core_discovery_cohorts_v1.tsv` as the only v1 discovery cohort authority.
- **FR-002**: The system MUST provide retrieval and intake modules that resolve discovery accessions and classify `input_class`.
- **FR-003**: The retrieval layer MUST emit accession crosswalk fields (`GSE`, `GSM`, `SRP`, `SRX`, `SRR`, `BioProject`) when available.
- **FR-004**: The system MUST include a cohort expansion audit module for candidate cohorts discovered from primary sources.
- **FR-005**: The cohort expansion audit output MUST classify each candidate as `already_covered`, `promote_discovery`, `promote_validation`, `context_only`, or `hold`.
- **FR-006**: The system MUST NOT ingest third-party precomputed DEG/ROC outputs as primary discovery statistics.
- **FR-007**: The system MUST build a canonical `sample_manifest.tsv` before any expression modeling.
- **FR-008**: The canonical sample manifest MUST include `cohort_id`, `sample_id`, `patient_id`, `cancer_type`, `therapy_class`, `therapy_agent`, `specimen_type`, `timing_category`, `response_label`, `pair_id`, `input_class`, and `analysis_role`.
- **FR-009**: The system MUST support exactly three contrast families in v1: `PRE_RESPONSE`, `TREATMENT_DELTA`, and `ON_RESPONSE`.
- **FR-010**: The system MUST treat `PRE_RESPONSE` as the primary discovery contrast family.
- **FR-011**: The system MUST preserve study-level inference by running DE within cohort before cross-cohort synthesis.
- **FR-012**: The DE engine MUST use all usable labeled samples and MUST NOT force equal-sized downsampling.
- **FR-013**: The system MUST support separate raw and processed ingestion paths and must record normalization/model assumptions.
- **FR-014**: The system MUST emit per-cohort QC outputs before DE.
- **FR-015**: The system MUST emit cohort-level DE outputs with effect, uncertainty/statistic, `p_value`, and `FDR`.
- **FR-016**: The system MUST harmonize gene identifiers before meta-analysis.
- **FR-017**: The system MUST perform random-effects meta-analysis as primary and p-value-combination as sensitivity.
- **FR-018**: The system MUST produce gene-level and pathway-level discovery signatures.
- **FR-019**: The system MUST run leave-one-cohort-out sensitivity for primary meta outputs.
- **FR-020**: The system MUST keep validation cohorts out of discovery signature fitting.
- **FR-021**: The system MUST score frozen signatures on validation cohorts and report concordance/discrimination metrics when available.
- **FR-022**: The system MUST treat GDC as source-of-truth for TCGA PRAD/LUAD mechanistic analysis.
- **FR-023**: The system MUST generate `tcga_sample_map.tsv` with strict barcode-level RNA/methylation mapping and usability flags.
- **FR-024**: The system MUST project frozen signatures into PRAD and comparator cohorts without pooled discovery re-fitting.
- **FR-025**: The system MUST integrate promoter methylation summaries for frozen transcriptomic candidates.
- **FR-026**: The system MUST emit versioned artifact directories for retrieval, cohort expansion audit, discovery, immune-state interpretation, validation, and TCGA mechanism layers.
- **FR-027**: The system MUST log inclusion/exclusion reasons at cohort and sample levels, including responder-label provenance.
- **FR-028**: The system MUST record run configuration and software versions per run.
- **FR-029**: The system MUST expose stage-wise CLI commands that can run independently.
- **FR-030**: The immune-state module MUST run downstream of DE/meta and MUST NOT replace discovery inference.
- **FR-031**: The system MUST emit ESTIMATE outputs (`ImmuneScore`, `StromalScore`, `ESTIMATEScore`, purity proxy) for eligible RNA cohorts.
- **FR-032**: The system MUST emit CIBERSORTx outputs in both absolute and relative modes with method metadata.
- **FR-033**: The system MUST emit ssGSEA outputs from a frozen immune-program panel and log the exact gene-set version used.
- **FR-034**: The system MUST emit HOPE A/B/C/D class labels and a continuous HOPE-18 score.
- **FR-035**: The immune-state association layer MUST treat continuous scores as primary tests; dichotomized strata are sensitivity-only outputs.
- **FR-036**: The system MUST emit `marker_correlations.tsv` and `cohort_level_effects.tsv` for response/timing associations.
- **FR-037**: The immune-state module MUST exclude non-RNA cohorts with explicit exclusion reasons.
- **FR-038**: TCIA IPS MUST be ingested as secondary annotation for TCGA records and MUST be flagged as non-independent from TCGA.
- **FR-039**: The system MUST emit `tcga_immune_methylation_integration.tsv` combining projection, immune-state context, TCIA overlay, and methylation signals.
- **FR-040**: The immune-state module MUST require an explicit cohort-to-gene-set registry (GMT path per cohort) and MUST NOT compute ssGSEA/HOPE outputs when registry entries are missing.
- **FR-041**: The immune-state module MUST require explicit CIBERSORTx absolute and relative outputs; if missing, it must log a blocking error and skip CIBERSORTx-derived effects.
- **FR-042**: The system MUST emit step-wise RNA-seq visualization artifacts (QC/EDA, DE, meta, immune) plus a machine-readable visualization index.

### Key Entities *(include if feature involves data)*

- **Discovery Cohort Manifest**: Cohort-level registry for v1 discovery inclusion.
- **Retrieval Ledger**: Per-cohort acquisition status, source URLs, accession crosswalks, and integrity checks.
- **Dataset Inspection Record**: Cohort/sample-level intake classification with assay and file-format evidence.
- **Cohort Promotion Audit Record**: Candidate-cohort-to-accession mapping with coverage and role decisions.
- **Canonical Sample Manifest**: Sample-level harmonized metadata table with response and timing labels.
- **Cohort DE Result**: Within-cohort contrast output for one contrast family.
- **Meta Effect Record**: Gene-level meta-analysis row with pooled effect and heterogeneity fields.
- **Discovery Signature Set**: Frozen gene/pathway signature output per contrast family.
- **Immune State Score Record**: Per-sample ESTIMATE/CIBERSORTx/ssGSEA/HOPE outputs with score provenance.
- **Immune Cohort Effect Record**: Cohort-level response/timing effects for immune-state features.
- **Validation Score Record**: Per-sample score and cohort-level validation metrics for frozen signatures.
- **TCGA Sample Map Record**: PRAD/LUAD sample-level RNA/methylation mapping and usability flags.
- **TCIA Annotation Record**: PRAD/LUAD IPS-style annotation mapped to TCGA sample IDs.
- **TCGA Projection Record**: Candidate behavior in PRAD and comparator cohorts after signature freezing.
- **Methylation Integration Record**: Candidate-level expression, immune context, and promoter methylation integration output.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A GitHub-ready repo scaffold exists under `06_analysis_pipeline_repo` with updated spec/plan/contracts/quickstart/tasks for the three-workstream design.
- **SC-002**: Primary-source all-cancer cohort promotion audit output is generated with role decisions and provenance fields.
- **SC-003**: Retrieval and intake inspection artifacts are generated for all discovery cohorts with missing/unavailable entries explicitly logged.
- **SC-004**: At least 95% of discovery samples are harmonized or explicitly excluded with documented reason.
- **SC-005**: Each included discovery cohort emits a QC bundle and at least one valid within-cohort DE output.
- **SC-006**: Primary `PRE_RESPONSE` meta-analysis outputs are generated with leave-one-cohort-out sensitivity.
- **SC-007**: Immune-state outputs are generated for all eligible RNA cohorts, and ineligible cohorts are explicitly excluded.
- **SC-008**: `marker_correlations.tsv` and `cohort_level_effects.tsv` are generated using continuous-first models.
- **SC-009**: Validation scoring runs on held-out cohorts without signature re-fitting.
- **SC-010**: `tcga_sample_map.tsv`, projection output, and `tcia_ips_annotations.tsv` are generated and linked at sample level.
- **SC-011**: `tcga_immune_methylation_integration.tsv` is generated with directionality fields for expression, immune state, and methylation.
- **SC-012**: Final reports clearly separate discovery inference from interpretation overlays (immune-state and TCIA annotations).
- **SC-013**: A visualization index is generated with stage-tagged figure paths for each executed track.
