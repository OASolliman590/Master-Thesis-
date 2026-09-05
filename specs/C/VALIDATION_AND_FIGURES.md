# Paper C — Validation and four-figure evidence plan

Status: proposed; no panel contains results yet.

## Validation boundaries

The B discovery query is frozen independently of C perturbation scores. B's external patient cohort cannot tune C queries. LINCS2017 and2020 overlap heavily; re-running the same biological instances with a different release/scorer is a reproducibility check, not independent validation. Two scoring algorithms on one matrix test numerical robustness, not two independent biological findings.

Independent measured prostate perturbations are the preferred test of the inferred immune-expression interpretation. GSE199800/GSE216053 remain candidates until their actual interventions, controls, measured genes and biological replication are verified. Freeze all eligible contrasts before inspecting their direction. If no compatible measurements exist, the manuscript must clearly retain a prediction ceiling and reconsider standalone scope. No positive concordance threshold is required for an eligible validation result.

Frangieh genetic immune screens support target/condition-specific hypotheses in their native context, not the same drug experiment. SCP1064/scPerturb are one study. TISMO must trace every sample to original experiments and account for animal/study groups, species and immunotherapy timing. A database-level split that leaves one original study in both sets is invalid. LJP4 IFNG agreement is a reference comparison; source overlap and inferred-versus-measured space must be reported.

Any model or candidate selection fitted during discovery must be frozen before the corresponding held-out outcome is inspected. Holdout alteration tests should prove it cannot change features, thresholds, mappings or selected treatments. No unrestricted search for the validation subset showing best agreement.

## Four figures

| Figure / panel | Question and source | Analysis and uncertainty | Permitted claim |
|---|---|---|---|
| 1A patient/query provenance | What disease axis is tested? B/TCGA discovery; PRAD/LUAD secondary | Cohort/split flow and frozen gene-selection diagram; actual patient exclusions | A defined molecular query, not established clinical resistance |
| 1B measured coverage | Which gene and compound conditions exist? LINCS manifest | Gene-space tier and drug×cell×dose×time heatmap; counts by true unit, missing-state legend | Coverage, including absent and inferred readouts |
| 1C query concordance | Does the methylation-supported query differ from expression-only? Same frozen discovery patients | Signed effect/overlap plot; discovery uncertainty from B, explicit shared data | Added constraints change the query; no automatic improvement |
| 2A primary reversal | Three drugs, PC3/24h/1.11111 micromolar | Individual WTCS and R_c; project labels, QC/HIQ status, no unjustified biological CI | Finite assay-context reversal estimates |
| 2B exposure/context sensitivity | Full curated LINCS prostate panel | Dose/time trajectories and context ranks; show unbalanced coverage, never interpolate absent drug contexts as measured | Context dependence; no unidentifiable class superiority |
| 2C expression-only comparison | Frozen two-query analysis | Prespecified rank/discordance summary and specificity-null diagnostics if valid | Which interpretations differ and need independent evidence |
| 3A measured prostate check | Verified additional GEO experiment(s) | Prespecified gene/module effects with independent-replicate intervals if estimable; all eligible contrasts | Measured direction in that model/intervention only |
| 3B immune context | Perturb-CITE-seq and TISMO original studies | Separate assay/condition estimates; biological-unit counts, targeted/not-targeted distinction | Orthogonal support, disagreement or no coverage |
| 3C IFNG reference | Verified LJP4 payload | Compatible gene-space agreement with source/lineage labels and overlap audit | Reference similarity in its actual context |
| 4A model/viability context | CCLE/DepMap, PRISM/GDSC | Model expression/dependency and source-scale sensitivity; missingness and screened range | Baseline relevance and growth sensitivity |
| 4B pharmacological plausibility | Original human PK + DrugBank/ChEMBL identity | Reversal versus documented exposure ratio/range; assumptions and missing free-medium values visible | Plausibility limits, not a dosing recommendation |
| 4C evidence conclusion | All panels, linked by compound/context | Transparent evidence table including contradictions and unavailable arms; no opaque weighted score | A justified experimental shortlist or a documented failure of the assumed shortlist |

If a conditional panel remains unavailable, mark it unavailable in the evidence map and amend the figure/manuscript scope before submission. A blank evidence slot is not grounds to fabricate validation or quietly replace an agreed source.
