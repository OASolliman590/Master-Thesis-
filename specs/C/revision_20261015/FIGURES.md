# Four-figure evidence plan

Every panel must disclose source, release, unit, verified `N`, independent `N`, intervention/control, analysis, uncertainty, missingness and claim ceiling.

## Figure 1 — Clinical-to-regulatory query architecture

| Panel | Question | Source/unit | Analysis | Permitted conclusion |
|---|---|---|---|---|
| 1A | How do A, B and C connect? | Versioned handoffs | Evidence-flow diagram | Provenance, not causality |
| 1B | How were `Q_E` and `Q_M` matched? | Gene/programme rows | Quotas, overlap and leakage audit | Fair query construction |
| 1C | What evidence supports each gene? | A/B row evidence | Effect/uncertainty and regulatory annotations | Patient-supported hypothesis |
| 1D | What is assay coverage? | Query genes by source | Measured/inferred/absent matrix | Coverage limits |

## Figure 2 — Bounded perturbation discovery and C1 calibration

| Panel | Question | Source/unit | Analysis | Permitted conclusion |
|---|---|---|---|---|
| 2A | Which curated compounds/contexts are measured? | Compound×cell×dose×time×project | Coverage tensor | Assay availability, not efficacy |
| 2B | What does the C1 common anchor show? | LINCS collapsed signature | Raw WTCS with components | Finite context-specific connectivity |
| 2C | How context-dependent are C2 results? | Signature/project | Context-specific heatmap/trajectories | Heterogeneity across measured contexts |
| 2D | Where do `Q_M` and `Q_E` disagree? | Candidate/context | Rank/score disagreement | Changed interpretation, not improvement by itself |

## Figure 3 — Independent measured and mechanistic validation

| Panel | Question | Source/unit | Analysis | Permitted conclusion |
|---|---|---|---|---|
| 3A | Does `Q_M` respond more than `Q_E`? | Biological replicate; original study | Sample-level paired score and limma contrast | Relative molecular responsiveness |
| 3B | Is the result stable across studies/programmes? | Original study | `delta_s`, `Delta_Q`, LOO | Finite-set consistency/heterogeneity |
| 3C | Is restoration separable from stress/viability? | Source-native outcomes | Parallel evidence, no pooled scale | Competing explanation assessment |
| 3D | Is the chemical effect mechanistically coherent? | Genetic/chromatin/protein experiment | Direction-preserving evidence matrix | Mechanistic consistency, not equivalence |

## Figure 4 — Translational prioritisation and handoff

| Panel | Question | Source/unit | Analysis | Permitted conclusion |
|---|---|---|---|---|
| 4A | Which models match the patient barrier? | Cell line/model | Baseline lesion and target map | Model relevance |
| 4B | Are exposures interpretable? | Human PK/formulation and in-vitro context | Exposure relationship categories | Plausibility/uncertainty |
| 4C | Which candidates are non-dominated? | Candidate evidence row | Tiers and Pareto plot | Distinct candidate roles |
| 4D | What will be tested prospectively? | Experiment handoff | Controls/readouts/decision tree | Prospective hypothesis only |

## Missing panels

A missing independent source, PK datum or functional result remains a labelled empty/blocked panel or table row. It is not replaced by another prediction or hidden by shortening the paper.
