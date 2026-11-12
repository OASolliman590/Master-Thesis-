# Joint Paper A + A-LONG figure and table plan

## Purpose and limits

This is a layout plan for a joint manuscript shell. The accompanying report
generator uses only fixed invented display values. Its figures, tables, and
supplement pages are not cohort summaries, biological findings, model
validation, or evidence that a scientific gate passed. The exact real outputs
remain unavailable.

Paper A has the single formal primary analysis. A-LONG is secondary. Shared
baseline patients do not count as independent replication, and A-LONG does not
change A-P2 or A-BIO features or results. No patient-level predictions or rows
are included.

Every generated figure and TSV row carries INVENTED DATA — MANUSCRIPT SHELL,
the invented classification, code version, fixture identifier, and fixture
hash. manifest.json records the source code hash and output hashes. No runtime
or product output is opened.

## Main figures

| Figure | Planned content | Shell constraints |
| --- | --- | --- |
| 1 | Cohort overview: study group, cancer group, drug class, platform, and sample count. | Invented cohort labels and counts only; no real cohort identity or eligibility claim. |
| 2 | Panel effect forests grouped by cancer and drug class. | Supplied invented estimates and intervals; retain nonsignificant, discordant, and unavailable rows. |
| 3 | Pooled-g/FDR gene display beside study-level g heatmap. | Generic invented gene labels; keep missing study effects blank; no top-gene selection rule. |
| 4 | Hallmark meta-analysis and fgsea summaries. | Separate metric panels; retain unavailable and nonsignificant examples; no pathway run or pooled conclusion. |
| 5 | A-P2 ROC examples and paired delta-AUROC. | Development and final-test labels remain distinct. The development aggregate is shown without an interval; the final-test paired delta carries the invented interval. Disclose M2/CYT overlap; the examples do not imply an independent comparator or a real validation. |
| 6 | SC-1 per-study custom composite-panel dotplots. | Invented nonnegative `median_log2_cpm_plus1` values; fixed-size composite dots and genuinely study-specific color bounds derived from each study's assessed values. An all-zero/unavailable study uses a visible 0–1 fallback. Assessed zero, `not_assessed`, and `insufficient_donors` remain distinct. This shell does not plot M5/M6 individual genes; if gene dots are shown in another layout, size them by `median_percent_cells_detected`, never coverage. No response-selected genes. Exact head-and-neck source/overlap remains unresolved and masked. |
| 7 | Exploratory SC-3 heatmaps of panel Hedges `g` by cohort and compartment. | RECIST, pathology, and T-cell expansion are separate metric-family panels. T-cell expansion is a nonclinical metric, not clinical response. `g` remains separate from DE `log2FoldChange`. The fixed color scale is symmetric; zero and unavailable cells are distinct. Values are invented only. |
| 8 | Joint A-LONG1B pairing/selection structure and A-LONG2B direct response-by-time estimates. | Show specimens, assays, and unique patients separately; also baseline/follow-up/paired patients, candidate/selected pairs, same-lesion support, and unavailable endpoint-evaluable counts. Add an aggregate timing schematic distinguishing exact-day from categorical/interval timing; its fixed invented days are not N12 choices. The central `delta_primary` contrast is `R_minus_NR_change`, R-minus-NR in ON minus PRE. Keep its interval and `NOT_ESTIMABLE` reason/missing estimate visible. `ancova_sensitivity` / `R_minus_NR_on_value_conditional_on_pre` remains a separate sensitivity, never central Delta. Real patient N is UNKNOWN; no patient rows or identities are shown. |

## Supplement shells

| Supplement | Component question | Shell content and limits |
| --- | --- | --- |
| S1 | Per-dataset QC/PCA/DE grids. | Invented layout only; it does not reproduce the outcome-free W2 work. |
| S2 | A-COMP composition layout. | Invented values only. N15 is unsigned; CIBERSORTx is not run; the shell does not indicate gate passage. |
| S3 · A-LONG1A | Which longitudinal sources exist? | Invented source flow counts independent study families, with regimen/window coverage. No real source/release or overlap receipt is admitted; patient, specimen, and assay N are separately UNKNOWN. Catalogue entries are not independent cohort counts. |
| S4 · A-LONG2A | What changes within each response group? | Separate invented `DELTA_R` and `DELTA_NR` intervals from `within_group_deltas.tsv`, `window=baseline_to_on`, plus an unavailable-support row. Within-group change is not the direct response interaction; significance in one group is not interaction evidence. |
| S5 · A-LONG2C | Which programme directions replicate? | Compare invented independent study-family/cancer direction rows and uncertainty; within-study effects use patient units. Real family/patient support remains UNKNOWN; no replication claim is made. Influence availability is explicitly UNAVAILABLE because no influence output is supplied. Shared baselines are not independent families. |
| S6 · A-LONG3C | Lesion, timing, and selection sensitivity. | Match invented primary and prespecified same-lesion, exact-day, and tighter-timing rows with intervals and `n_patients_used` support; label whether support is unchanged or changed per row. Selection, missing-biopsy, and influence results are UNAVAILABLE; missing biopsies are not assumed random. This is not a secondary-endpoint page and adds no route. |
| S7 · A-LONG3A | Moderator-design identifiability. | Gated/unavailable: independent studies plus paired-patient support; cancer, regimen, class, and window rank/confounding; all real N UNKNOWN; no estimates. |
| S8 · A-LONG3B | Released moderator-effect heterogeneity. | Gated/unavailable: independent-family unit; all real N UNKNOWN; not an efficacy ranking and no estimates. |
| S9 · A-LONG4A | Orthogonal cellular/modality context. | Gated/unavailable: patient units with nested cells/spots separately UNKNOWN; not causal proof and no estimates. |
| S10 · A-LONG4B | NMA feasibility and qualified temporal handoff. | Gated/unavailable: studies/programmes; all real N UNKNOWN; unsupported arrows are absent and no estimates are shown. |

The W10 shells map the public W8 field inventory as a layout guide. Schema
compatibility does not establish model validation or admit real sources. All
displayed values remain fixed invented values; no route, window, estimand,
independence rule, or model is computed here. N12/N13 and the Gide EDT
crosswalk remain user decisions. Future command templates are recorded in
the readiness document.

## Table shells and product-schema map

| Table | Purpose | Product mapping and limits |
| --- | --- | --- |
| 00 | Product-schema map. | Maps cohort, A-BIO, A-META, A-P2, A-COMP, exact SC-1 `unit_summary.tsv` and SC-3 `sc3_effects.tsv`/`de_results.tsv` fields, and the public W8 pairing, within-group delta, model-support, effect, synthesis, and synthesis-support field inventory to Figure 8 and S3–S10. Repeated effects distinguish contrast support from total fitted observations. Private pair rows remain excluded; influence availability is marked UNAVAILABLE. |
| 01 | Cohort and measurement eligibility. | Mirrors public cohort metadata fields: cancer, uniform drug class, platform, unit, transform, feature identifier, DE engine, and endpoint families. Invented rows are marked not evaluated. |
| 02 | Coverage and provenance. | Uses the A-BIO coverage field family and A-META effect coverage fields; includes fixture provenance metadata. It does not claim source eligibility. |
| 03 | Full effects and multiplicity families. | Mirrors A-META study-effect, synthesis, and subgroup field families. Rows are fixture-only; no inference, multiplicity procedure, or selection rule is added. |
| 04 | A-P2 validation shell. | Keeps the formal-primary role, development/final-test distinction, M2/CYT overlap disclosure, and the A-LONG secondary role. W1 development `primary_aggregates.tsv` and final `final_metrics.tsv` metric fields are mapped from public code. The final interval applies to paired `delta_auc`; no patient prediction rows are included. |
| 05 | A-LONG aggregate pairing and attrition. | Uses exact `pairing_summary.tsv` and longitudinal/model support fields and a clearly labeled derived unpaired-baseline count for invented single-window rows. Endpoint-evaluable counts remain unavailable before release. Contains no sample IDs or pair rows. |
| 06 | Open-gate display format. | Uses invented placeholder gate rows. Actual readiness blockers are listed separately in docs/validation/PAPER_A_READINESS.md. |

No public patient predictions, real cohort labels, restricted data, model
weights, or signed protocol/specification files are part of these shells.

## Sources and references

The references below support method and source names used in the manuscript
plan. W10 does not reimplement or run those methods.

- Hedges LV. Distribution theory for Glass's estimator of effect size and
  related estimators. *Journal of Educational Statistics*. 1981;6(2):107–128.
  [doi:10.3102/10769986006002107](https://doi.org/10.3102/10769986006002107).
- Liberzon A, et al. The Molecular Signatures Database Hallmark Gene Set
  Collection. *Cell Systems*. 2015;1(6):417–425.
  [doi:10.1016/j.cels.2015.12.004](https://doi.org/10.1016/j.cels.2015.12.004).
- Sergushichev AA. An algorithm for fast preranked gene set enrichment
  analysis using cumulative statistic calculation. *bioRxiv*. 2016.
  [doi:10.1101/060012](https://doi.org/10.1101/060012).
- Rooney MS, et al. Molecular and genetic properties of tumors associated with
  local immune cytolytic activity. *Cell*. 2015;160(1–2):48–61.
  [doi:10.1016/j.cell.2014.12.033](https://doi.org/10.1016/j.cell.2014.12.033).
- Finotello F, et al. Molecular and pharmacological modulators of the tumor
  immune contexture revealed by deconvolution of RNA-seq data. *Genome
  Medicine*. 2019;11:34.
  [doi:10.1186/s13073-019-0638-6](https://doi.org/10.1186/s13073-019-0638-6).
- Official plotting output reference:
  [Matplotlib Figure.savefig](https://matplotlib.org/stable/api/_as_gen/matplotlib.figure.Figure.savefig.html).
- Official TSV serialization reference:
  [Python csv module](https://docs.python.org/3/library/csv.html).
- Official fgsea package reference:
  [Bioconductor fgsea](https://bioconductor.org/packages/release/bioc/html/fgsea.html).
- Official random-effects meta-analysis package reference:
  [metafor documentation](https://wviechtb.github.io/metafor/).

The SC-1 output is `unit_summary.tsv`: it reports full-library per-donor
`log2(CPM+1)` values, with the custom-panel mean requiring 80% member
availability and the displayed summary taking the equal-donor median. The
product's outcome-free unit rules are 15 cells and 5,000 UMIs, baseline
recognized ICI-only, and at least five supporting donors for shown values.
Study scales are separate, with no cross-study pooling or compartment
z-scoring. Composite dots have fixed size; individual M5/M6 gene dots use
`median_percent_cells_detected` for size. Unassessed values are NA; measured
zero remains distinct. Insufficient-donor audit rows are not plotted.

SC-3 maps `sc3_effects.tsv` fields including `unit`, `m5m6_gene_flag`, `g`,
`status`, `reason`, `compartment`, `sc_endpoint_family`, and
`response_metric`. The `unit` prefix encodes compartment and metric family; it
is not itself the panel ID. `de_results.tsv` uses `log2FoldChange`, which is a
separate scale from Hedges `g`. RECIST can be pooled only where product
compatibility and small-k rules allow; pathology and T-cell expansion remain
per-study pending source-definition decisions. The latter is nonclinical.

The parent-inspected public W8 field inventory includes `pairing_summary.tsv`, `longitudinal_support.tsv`,
`a_long_effects.tsv`, and `a_long_synthesis.tsv` fields from the parent
code-only schema extract. Its `unit` and `effect_scale_id` keep AP2, CYT,
CUSTOM panels, and M5/M6 gene units distinct; raw-count/voom/dream is
unavailable. Candidate/sample rows, private pair manifests, overlap receipts,
and R retention are not manuscript inputs. No W1 result file was read. Repeated effect rows separate `n_observations_contrast` from
`n_observations_fitted`; contrast patient support is `n_R + n_NR`. Model
longitudinal-support effect rows report that contrast support. The readiness
document records the outstanding W8 correction and final verification. N12/N13 choices remain unsigned.
