# A engineering and reproduction contract

Proposed interfaces; no production CLI or workflow currently exists. Commands below become acceptance requirements for implementation tickets, not claims that they already run.

## Observable seam and architecture

One end-to-end analysis entry point consumes a pinned cohort bundle and a frozen analysis configuration, then emits eligibility, patient scores, endpoint contrasts and provenance. Tests exercise that public boundary; source-specific parsing remains inside adapters. Keep extraction, label mapping and scoring separable so a failed source is nonestimable with a reason rather than silently omitted from a pooled result.

The configuration must declare `primary_choice` as unresolved/A-P1/A-P2 and separate enabled modules: fixed-score sensitivity, discovery, molecular transport and clinical transport. Confirmatory execution rejects unresolved primary choice. Source-audit work may proceed without scoring. A required frozen-source failure yields `incomplete_primary`, never an apparently successful reweighted aggregate; optional branch failures remain explicit without being promoted to primary evidence.

Proposed CLI: `python -m thesis.paper_a run --config analysis.json --output <run-dir>`. `--audit-only` validates manifests and labels without reading outcome-associated scores or fitting models. These are proposed commands whose implementation must be verified before tickets close.

Workflow: source manifest → source-specific import → original-study/patient reconciliation → endpoint/assay eligibility report → locked CYT score → paired endpoint contrast → cohort/cancer summary and uncertainty → secondary and prostate reports → figures/provenance. The source/label and expression branches meet only after unique patient/specimen matching. No batch correction across all source studies is implicitly introduced.

## Input and output schemas

UTF-8 TSV tables with header, explicit field types and a schema version; `NA` means unknown and must be configured explicitly rather than treating a legitimate identifier as missing. Use strings for identifiers, never spreadsheet numeric coercion. All input datasets have originating_study_id and source_file_sha256.

| Artifact | Key and required fields | Invariants |
|---|---|---|
| source_manifest | source_id; accession, original URL, retrieval timestamp, release, checksum, bytes, assay, scale, identifier annotation, access/license/redistribution status | Checksum and expected schema verified before use; source errors recorded |
| patients | study_id+patient_id; sample_id, specimen_id, original identifiers, biopsy timing, regimen, cancer, source locator | One selected eligible baseline specimen per patient; clinical/expression join validated |
| clinical | study_id+patient_id; response_original, criteria, assessment timing, mapping_version, ORR, DCR, exclusion_reason; optional event/time/unit | Source-supported categories only; both labels accompany same patient; future timing never silently becomes baseline |
| expression | sample_id+gene_id; abundance numeric, abundance_scale, feature_annotation, source locator | Both CYT genes nonnegative, unambiguous and scale-compatible; missing distinct from zero |
| score_registry | score_id+version; genes, weights, direction, transform, source DOI, development cohort IDs | No score selection based on this evaluation's performance |
| patient_scores | study_id+patient_id+score_id; value, coverage, included, reason | Stable order-independent matching; no repeated patients |
| contrasts | cohort_id+score_id; n_patients, original category counts, auc_orr, auc_dcr, delta, uncertainty method, bounds, status | Undefined AUC has null value and explicit reason; never zero by default |
| run_manifest | run_id; commit, config/input/output hashes, environment, RNG/seed, start/end, statuses, exposure registry | Successful status requires every required artifact and gate, not merely process exit |

Additional proposed schemas: `branch_manifest` records cohort/cancer membership, explicit numeric frozen weights, branch eligibility and required/optional status; `secondary_registry` records every test ID/score version/endpoint/test method/family membership and fixed family size; `split_registry` records original-study/patient IDs assigned to every inner/outer/final split; `fitted_model` records training IDs, feature filters/scalers, C/l1_ratio/solver, convergence, coefficients and source hashes; `transport_contract` records score scale, comparator cohort, feature requirements, pathology/clinical endpoint provenance and permitted claims. Derived handoff artifacts retain the frozen model version and its pre-final-test timestamp.

Discovery runs expose stages `audit`, `development`, `freeze-handoff`, `final-test` through the same public boundary with explicit module/stage configuration. Final-test execution verifies immutable development-model hashes before reading final labels. A transport run cannot refit that model. Schema names and module interfaces remain proposed implementation requirements, not existing commands.

Each source object is admitted by schema and provenance, not by filename extension. Workbook COMBAT IDs such as `1.00` need a source-specific documented normalization; arbitrary numeric-looking clinical IDs must not all be cast to integers. Derive joins in a separate reviewable table.

## Tool documentation and environment

AIU import smoke check on 5 September2026 succeeded for NumPy2.4.6, pandas2.3.3, SciPy1.17.1 and scikit-learn1.9.0 in the existing Python3.11.16 omics-py environment. This verifies imports only. It does not lock the environment or establish equivalence to author pipelines.

Use scikit-learn's binary `roc_auc_score` as a reference numerical implementation and compare with the explicit pairwise definition in ANALYSIS.md, including ties. [Official API](https://scikit-learn.org/1.9/modules/generated/sklearn.metrics.roc_auc_score.html). pandas input options must explicitly preserve identifiers and missing-value vocabulary; [versioned read_csv documentation](https://pandas.pydata.org/pandas-docs/version/2.3/reference/api/pandas.read_csv.html). A generic bootstrap call does not implement patient/category/cohort grouping by itself. Use explicit grouped resampling; if SciPy bootstrap is used, verify the installed API and its paired-resampling behavior against [SciPy1.17 documentation](https://docs.scipy.org/doc/scipy-1.17.1/reference/generated/scipy.stats.bootstrap.html).

Proposed runtime pins: Python3.11.16, NumPy2.4.6, pandas2.3.3, SciPy1.17.1, scikit-learn1.9.0. Before readiness resolve a dedicated Linux environment or a reproducibly exported existing environment, with package/build hashes and a fresh recreation check. No fabricated complete lockfile is provided. Plotting, workflow orchestration, testing and secondary score package versions remain to be selected and verified against actual APIs. Do not update the shared AIU environment silently.

## Tests and real-data smoke checks

- Original CR/PR/SD/PD fixture produces known paired labels; unknown and censored fields remain excluded appropriately. This fixture tests mapping, not clinical efficacy.
- A patient with pre/on-treatment specimens never becomes two independent baseline subjects. Accession aliases and trial reuse do not create independent cohorts.
- Hand-enumerated positive/negative pairs verify AUC tie handling and Delta sign. All-equal scores give0.5 when both classes exist; single-class AUC is nonestimable.
- Misordered expression/clinical records still join correctly or reject; ambiguous IDs and duplicate selected specimens fail the affected cohort.
- Missing GZMA is not filled with zero; negative/log-scale input cannot enter the TPM scorer. Whole-matrix FPKM conversion uses the declared feature universe.
- Changing a holdout outcome cannot alter a fitted transform, feature list or selected model in any later approved trained-model branch.
- Resampling retains two labels and one score for each patient; category/cohort weighting is checked using unequal cohort sizes. A no-SD cohort yields identical endpoints, not a forced biological discovery.
- Canonical O/SD/PD bootstrap gives identical results for equivalent CR/PR versus merged PRCR input when canonical patient ordering and seed are identical. Quantile convention is checked against an explicit small replicate vector. Undefined unstratified replicates do not produce a silently filtered unconditional interval.
- A frozen cohort failing after manifest admission produces an incomplete primary rather than renormalized weights. The separately frozen all-cohort sensitivity cannot overwrite the A-P1 primary.
- Hand-enumerated O/SD/PD pairwise concordances reproduce both AUC decompositions; changing category counts while keeping category distributions fixed is not mislabelled a learned biological effect.
- Secondary multiplicity includes all fixed M registry entries; nonestimable computational p=1 placeholders remain null/reason-coded in scientific output.
- Discovery: changing outer/final labels cannot alter training features, means/scales, hyperparameters or B/C handoff. Inner source folds are disjoint by original study and patient, convergence failures are visible, and every final prediction uses the frozen model checksum.
- Prostate: a missing required gene does not become zero; zero reference IQR and constant composition covariates produce nonestimable statistics. Sequential COMBAT endpoints cannot enter the A-P1 response mapper or be labelled isolated nivolumab validation.
- Real-data smoke: audited GSE91061 clinical records with its actual original matrix; verify sample join, units, both genes, record-to-patient counts, one complete run and reproduce its artifact hashes. No required AUC threshold: negative/null findings are valid.

## AIU run and restart plan

Main checkout `/home/omics/projects/ici_thesis_pipeline/master-thesis`; data stay in a separate permitted data/cache directory. Start with one small cohort, CPU-only, one worker and thread cap1; measure memory/runtime before wider execution. No GPU is required for the proposed primary. Resource limits are design defaults, not measured budgets. Retain process/job handle and logs if a long job is dispatched; use the verified queue/runtime contract and never assume omq enforces memory limits.

Write outputs to a unique temporary run directory; promote completion only after input hashes, schema and required outputs pass. Resume only matching commit/config/input hashes, otherwise create a new run. On interruption write a partial state; inspect an existing AIU job before restarting. Add unrun checks to pending_validation.json and never tag an incomplete run validated.

Reproduction deliverable: manifest-based retrieval instructions, environment lock and recreation log, exact CLI/config, cohort eligibility table, original-to-canonical identifier mapping, score/contrast tables, figure source data and captions, and a report of all exclusions/unknowns. A synthetic test pass cannot replace the real-data smoke or full declared workflow.

DISCOVERY.md and TRANSPORT.md extend the workflow with their own real-data tracers and bounded A05/A06 tickets. Do not mark full Paper A complete when only the CYT tracer succeeds. Newly checked tool references: [LogisticRegression1.9](https://scikit-learn.org/1.9/modules/generated/sklearn.linear_model.LogisticRegression.html), [LeaveOneGroupOut1.9](https://scikit-learn.org/1.9/modules/generated/sklearn.model_selection.LeaveOneGroupOut.html), [NumPy2.4 quantile](https://numpy.org/doc/2.4/reference/generated/numpy.quantile.html), checked5 September2026. Fit/import behavior still needs a version-pinned smoke test before production readiness.

## Source-derived identifier acceptance cases

Riaz original metadata has two distinct columns named Response. Preserve both by source position/schema; never let a dictionary parser overwrite one. Use original BOR for the declared category ontology, retaining NE. The audited eight terminal-punctuation reconciliations are source-specific and must retain raw IDs and collision checks; they do not authorize generic punctuation stripping. Prior-ipilimumab strata share one source-cohort identifier.

Hugo includes an on-treatment profile and two baseline specimens from one patient; freeze a source-supported specimen rule before scoring and never split those specimens between training/test. Rose contains repeat sequencing and two unmapped current-TPM columns; preserve unassigned records without fabricating labels. These are proposed future acceptance cases, not new production tests claimed passed.
