# B proposed software and environment contract

**Source correction, 6 September 2026:** the CPC portal `WGS_BASED_PURITY_ESTIMATION` field matches original WGS/OncoScan SNP-call agreement, not tumour purity. It must not populate a purity covariate or count toward purity availability. Genuine cellularity alternatives require their own method/specimen/scale validation. [Verified correction](../../docs/research/B_PURITY_FIELD_CORRECTION.md).

**PROPOSED / NOT IMPLEMENTATION-READY — v0.1.** Interfaces below are requirements for future implementation. No module/CLI listed here is claimed to exist or to have passed a scientific test.

## Pipeline boundaries

`source audit -> identity reconciliation -> assay parsing -> annotation/QC contract -> fixed molecular score -> TCGA nested development -> model lock -> external evaluation -> sensitivity/figures -> C handoff`

Separate responsibilities: importers preserve raw fields and provenance; identity mapping resolves independent units; feature builders implement only the approved score/probe rules; the training module receives TCGA identifiers only; the evaluator loads an immutable fitted artifact and has no fitting method; reporting consumes exported results. C export consumes a separately frozen TCGA discovery result and never an external result directory. Modules must expose deep, narrow interfaces such as a validated cohort bundle, fitted bundle and evaluation bundle, rather than global mutable data frames shared across stages.

Raw/controlled data and execution products belong under an approved AIU project data/run root. Repository paths contain code, approved small metadata and manifests. A run root is immutable once evaluated; intermediate checkpoints contain source/config hashes, stage status and dependency versions. Resuming requires those hashes to match. Full cohort retrieval must verify full checksums independently of existing partial-stream hashes.

## Input/output schemas (required fields)

| Artifact | Fields and invariants |
|---|---|
| `sources.jsonl` | source_id, accession/release, exact_url, retrieved_utc, access_class, licence_or_terms_url, local_path, byte_count, checksum_algorithm/value, completeness(full/partial/metadata), role. Signed URLs/credentials forbidden. |
| `specimens.parquet` | cohort, patient_id, specimen_id, focus_id nullable, aliquot_id, assay_id/GSM, source_origin_id, platform, modality, match_evidence, match_status, rule_version, inclusion/reason. Unknown focus is explicit; unique assay ID, many assays may share patient. |
| `expression` | specimen_id, stable_gene_id, symbol, value, abundance_type, annotation_release. Finite values required for primary U; summary rows are not genes; duplicate gene mappings rejected until approved collapse. |
| `methylation` | assay_id, probe_id, beta nullable, detection_p nullable, source_missing_token, processing_release. beta finite in [0,1] or missing; detection P separately typed; no conversion of NA to zero. |
| `gene_universe.tsv` / `probe_map.tsv` | ordered stable gene IDs and source mapping; probe_id, target_gene_id, annotation_build/release, promoter_category, mask_status/reason, source. Multi-gene annotation must preserve aligned gene/group pairs. |
| `covariates.parquet` | specimen_id, patient_id, age_years, gleason_primary/secondary/sum, approved_grade_category, purity_value/method/scale/source_specimen, optional CNA fields. Unit conversion documented; tumour purity cannot use an unverified focus bridge. |
| `eligibility.tsv` | patient/specimen, stage/fold, rule_version, all rule pass flags, final inclusion, exclusion reason. Source/QC gating reproducible; paired f0/f1 evaluation set identical. |
| `score_features.parquet` | patient/specimen, U_hash, score_version, eight gene percentiles, Y, promoter aggregates, Q_hashes, coverage counts, eligible flags. No silently varying score denominator. |
| `fitted_bundle` | training_patient_hash, config_hash, U/Q hashes, mapping versions, baseline/features/order, fold IDs, all fitted scaling/filter statistics, alpha, coefficients/intercepts, dependency versions, freeze timestamp, reviewer receipt. No external patient in training IDs. |
| `external_predictions.parquet` | patient/specimen, frozen_model_hashes, Y, f0, f1, paired squared errors, eligibility version; one row per approved patient. |
| `evaluation.json` | n, SSE0/1, SST, R2_0/1, Delta_R2, bootstrap interval/seed/count, undefined count, estimand/population/contract hashes, status(valid/undefined), reason. Nonfinite metrics serialize as null plus reason, not zero. |
| `B_to_C_query.tsv` | stable_gene_id, symbol, disease_direction(up/down), effect_type/value, uncertainty, source_cohort, lineage/purity/domain/CNA flags, selection_rule_version, measured_annotation, signed_query_hash. External-validation-derived selection prohibited. |

Every persisted output has a small sidecar recording source and parent artifact hashes, stage version, UTC time, git commit and whether it is exploratory. Schema versions change on semantic changes, not only renamed columns.

## Real-format importer requirements

The actual TCGA methylation example is headerless; retain its first probe. Its NA tokens and non-cg probes require explicit parsing/classification. TCGA STAR expression has a GENCODE-v36 comment and N_ summary rows; use the named TPM column, not a positional column guessed from an old template. The CPC methylation header lacks its first probe-ID label: reconstruct only this verified shape (788 header fields, 789 row fields) after checking every row; otherwise fail with diagnostics. Beta and `_Dectection_Pval` columns are 394 paired measurements, not 788 patients. CPC expression has seven annotation fields before 213 patient columns. These are verified examples, not permission to assume every future release has the same format. See canonical B_readiness.md and checksummed artifacts.

## Candidate environment, not a resolved lock

AIU is the main execution server. The existing `docs/execution/aiu_python_inventory.json` reports Python 3.11.16, numpy 2.4.6, pandas 2.3.3, scipy 1.17.1 and scikit-learn 1.9.0. These are **candidate direct version pins based on the observed inventory**, pending an isolated project import/smoke test and compatibility review; they are not a complete resolved dependency lock or proof that this analysis ran. Required plotting/parquet packages and the pinned annotation/probe-mask artifact remain to be selected and documented. Do not mutate the existing shared environment to satisfy a speculative specification.

[Ridge documentation](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html) documents alpha and intercept behaviour; pin the exact estimator parameters, solver and precision when implementation is reviewed. [R2 documentation](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.r2_score.html) must be checked for finite-value handling: compute the specified SSE/SST directly or explicitly retain undefined constant-target behaviour, rather than accepting a convenience default. Serialization format, package hashes, OS/BLAS/thread counts and transitive lock are implementation deliverables after successful resolution, not invented here.

If the VPN is unavailable, perform only authorised local documentation/schema work and queue AIU validation with a dated pending record. A local or synthetic pass cannot be reported as full AIU cohort validation. Never save SSH keys, VPN secrets or environment tokens in logs, GitHub or Notion.
