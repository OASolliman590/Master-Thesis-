# Paper B: executable implementation contract

**11 September reconciliation:** W1-W5 are implemented and reviewed; W6 coding is released, W7-W8 remain pending. Existing code performs the fixed APM validation component. [IMMUNE_BARRIER_FRAMEWORK.md](IMMUNE_BARRIER_FRAMEWORK.md) now controls the broader scientific evidence/figure plan. MethylCIBERSORT: W3 methylation/provenance input, W4 separately frozen composition preparation, W8 sensitivity analyses, W7 visualization. Do not change the current W5/W6 baseline or add unfrozen scores. Historical proposed paths/gap descriptions below record the design; consult current PROGRESS for completion. The original four APM figures remain a component-level report, not the full broadened paper.

Updated 11 September 2026. This is the controlling engineering sequence; ANALYSIS.md controls scientific choices. Existing components are reusable code, not a finished pipeline. This document does not freeze unresolved biological inputs.

## What works now

| Component | Actual entry point | Boundary |
|---|---|---|
| Four assay format inspectors | `python -m tools.b_formats inspect` | Checks supplied uncompressed bytes; does not acquire or transform cohorts |
| Annotation converters | `python -m tools.b_annotation_normalize prepare` / `validate-table` | Implements B-G2; official normalized exports still pending |
| Gene registry | `python -m tools.b_gene_registry build` | Source-backed membership/mapping/coverage; no scoring |
| Prediction engine | `python -m tools.b_prediction develop` / `evaluate` | Validated numeric feature TSVs to frozen models and paired external metrics |
| Strict component check | `python tools/check_paper_b.py` | Runs all four test directories; any skip, error or empty directory fails |

Use `--help` on each actual module for arguments. Existing source and tests under `tools/` and `tests/` are the implementation evidence. A successful component check is not an assay-to-figure run.

## One delivery sequence, with connected artifacts

Implement the following in order in this repository. Do not create another isolated helper ticket without connecting it to this sequence. Proposed module paths below do not yet exist. Every stage must consume its predecessor's recorded artifacts, validate their hashes and emit a manifest. No arbitrary shell commands in workflow configuration.

| Stage / proposed owner module | Inputs | Required outputs and acceptance |
|---|---|---|
| W1 `tools/b_workflow` | Versioned config; explicit interpreter; permitted source manifest | `plan.json` with stage dependencies, input hashes, outstanding scientific gates and commands. Implement `plan`, `run --mode synthetic`, and `resume`. Atomic completion records; changed parent hash invalidates descendants. An interrupted stage must not look complete. |
| W2 `tools/b_acquire` | Exact public object URLs/access tier; expected checksum and size when known | Immutable raw cache, download receipt, compressed/decompressed hashes. Stream to temporary file; validate before publication; reject HTML/error bodies. No silent accession substitution. Fixture HTTP tests exercise interruption and checksum mismatch. Annotation/public metadata acquisition does not require model release. |
| W3 `tools/b_cohort` | Raw assays, B-G2 annotations, B-G1 mappings, explicit specimen/replicate policy | Canonical specimen, expression, methylation, covariate and exclusion tables from SOFTWARE_CONTRACT.md. Adapter feeds parsed records rather than treating B-F1 summaries as data. Fail on ambiguous focus joins; preserve detection-P pairs and NA. One patient per evaluation row. |
| W4 `tools/b_features` | Canonical assays; explicit P/U/Q, detection-P, missingness, covariate policy | Score records, promoter features and per-fold feature-state bundles with exact gene/probe membership, eligibility and exclusions. Hand-calculated rank/tie/promoter fixtures. Changing an inner-validation beta must not change inner-training probe selection. |
| W5 extend `tools/b_prediction` | W4 fold-aware feature interface; TCGA-only development IDs and fixed training contract | Nested paired predictions, final transforms/probe state and frozen baseline/extended numeric bundles. Reuse existing ridge/evaluation code and its tests. **Do not feed one globally selected feature table into nested CV when probe eligibility is learned from training values.** |
| W6 existing evaluator + adapter | Frozen model AND upstream feature state, evaluation lock, independently eligible external specimens | Apply training-selected probes and transforms without refit; emit paired predictions, SSE/SST, Delta_R2 and bootstrap intervals. CPC outcome changes cannot alter any frozen bytes. Preserve negative and undefined results. |
| W7 `tools/b_report` | W3 exclusions/coverage, W5 development artifacts, W6 evaluation | Four actual figures below, machine-readable source tables and manuscript report. Each plotted value traceable to an output row. No manually entered illustrative values in a real report. |
| W8 registry-driven analyses / C export | Individually frozen secondary or exploratory contracts; separately frozen TCGA-only query rules | Three planned secondary results when enabled; M0-M6 coverage/context reports; approval-evidence target table; qualified LUAD comparison and signed C handoff. Disabled/unresolved analyses receive a reason, not invented scores. A primary run can finish while an optional analysis is pending. |

### Critical interface gap to fix in W4-W5

ANALYSIS.md proposes CpG finite-coverage selection within each training fold. B-P1 currently accepts an already constructed patient-feature table. That interface alone cannot implement the proposed fold-specific CpG selection. Extend development with a fold-local assay/feature-provider interface returning fitted feature state and transformed held-out rows. Persist final TCGA probe state beside the model and require its hash at external evaluation. Preserve the existing table interface for its declared fixed-feature use and regression tests. Do not silently resolve this mismatch by selecting probes globally or changing the scientific QC rule.

## Target one-command acceptance (to implement, not available today)

```text
python -m tools.b_workflow plan --config specs/B/workflow.synthetic.json
python -m tools.b_workflow run --mode synthetic --config specs/B/workflow.synthetic.json --output RUN_DIR
python -m tools.b_workflow resume --output RUN_DIR
```

The implementer must deliver that synthetic config and tiny raw assay/annotation/specimen fixtures as part of W1-W4. Synthetic policy values must be visibly fixture-only; they cannot become real defaults. Start from raw STAR-like expression and methylation plus CPC-like array formats, not just existing numeric prediction TSVs. The final command must traverse W2-W7 with real ridge computation and create four figures. W8 must exercise an enabled fixture contract and a blocked-unfrozen contract. Every artifact carries `synthetic=true`.

Acceptance: fresh run succeeds; same inputs reproduce scientific payloads within declared numerical tolerance; resume performs no completed work; tampered input invalidates dependents; malformed identity fails; external patient overlap fails; no-skips component regression passes. A failure must name the stage and preserve diagnostic receipts without publishing successful downstream artifacts. This is the software-completion milestone. Remote real-cohort validation is a different milestone.

## Real-data gates are stage-specific

- Public documentation, access checks, acquisition of permitted sources, identifier normalization and metadata coverage may proceed without computing biological outcomes. Respect source access/redistribution terms and record source versions.
- Real feature construction/development requires the relevant E1-E4/E6 contracts: P/U/Q, specimen linkage, covariates/purity comparability, eligibility, QC and precision/freeze. Missing fields cause a machine-readable blocked state. Implement the software with explicit parameters now; do not invent scientific defaults.
- External evaluation additionally requires the frozen training artifacts and evaluation release receipt. No joint ComBat, CPC-guided probe choice, external recalibration or performance-based population selection.
- Ayers GEP18, official full IFNG Hallmark and HOPE_18 remain the three planned secondaries. Ayers signed weights/normalization and HOPE scoring cannot be inferred from membership. M0-M6 and broader approved-immunotherapy targets remain in scope under EXPLORATORY_MODULES.md; they are not automatically scored or added to primary predictors.
- VPN downtime queues AIU execution; it does not stop local software implementation. Local success never counts as an AIU test.

## Four-figure delivery contract

Every figure must have a plain-language explanation beside it: what is plotted, how to read axes/colours/intervals, what the computed result supports, and what it cannot establish. Generate explanations from the actual results, including negative/undefined outcomes; label synthetic figures prominently. Export the underlying plotted table and a readable report linking all four figures. This is an acceptance requirement, not optional manuscript polishing.

1. Cohort/source flow and measured cross-platform coverage: patient exclusions, gene/probe coverage, specimen evidence and final eligibility. Counts come from W3, never the headline accession sample count.
2. Molecular measurement and methylation context: declared TCGA-only program/probe summaries and composition limitations, with retained negative associations. No external endpoint exploration before lock.
3. Paired TCGA development performance: out-of-fold observations/predictions and baseline-versus-extended errors, labelled internal development evidence.
4. Frozen external validation: paired external predictions, baseline/extended R2, primary Delta_R2 interval and prespecified transport/sensitivity panels. Null/negative results use the same layout.

## Documentation and method anchors

- Python [venv](https://docs.python.org/3.12/library/venv.html) and [subprocess](https://docs.python.org/3.12/library/subprocess.html): explicit environment executable, argument arrays, `shell=False`, checked exit codes and bounded timeouts.
- [SciPy installation](https://scipy.org/install/): official binary distributions and isolated environments. `requirements-windows.txt` records the tested local component stack, not a complete future scientific environment.
- [Ridge](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html) and [GridSearchCV](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GridSearchCV.html): estimator/selection APIs. BP1_prediction_engine.md fixes solver, alpha grid, preprocessing and splits; do not inherit changing defaults.
- [Foroutan et al. 2018](https://doi.org/10.1186/s12859-018-2435-4) supports single-sample rank-scoring methodology; our exact formula remains in ANALYSIS.md and is not asserted to be an identical published score.
- Source-specific evidence, assay formats and provenance: DATA_AND_SOURCES.md, SOURCE_MANIFEST.json and docs/research/B_MEASUREMENT_CHECKPOINT.md. Annotation normalization follows ANNOTATION_NORMALIZATION.md and its source receipts.

The next deliverable is W1-W4 connected to the existing model engine, followed by W5-W8, not another delegation setup or speculative redesign. Completion is measured by executable artifacts and the acceptance above.
