# A independent review response

Revision0.2, 5 September2026. These are specification corrections, not approval of a primary choice or claims of passed data gates. No production analysis was run.

| Finding | Disposition and exact revised contract | Remaining gate |
|---|---|---|
| 1. Original discovery scope only named | Added DISCOVERY.md, competing A-P2 endpoint, training-only regularised cohort-held-out pipeline, independent-test definition and B/C handoff; added A05 ticket | Primary A-P1 versus A-P2 unresolved; sufficient independent cohort/assay structure unverified |
| 2. No-SD primary membership ambiguous | ANALYSIS.md now requires O/SD/PD for A-P1; separately frozen no-SD/all-cohort sensitivity and weights | Actual cohort admission/precision |
| 3. Bootstrap not executable | Canonical O/SD/PD strata, fixed weights,2,000 PCG64-seeded replicates, percentile0.025/0.975, NumPy linear quantiles; explicit nonestimable unstratified sensitivity if any invalid replicate | Proposed numerical settings need precision/stability review; no biological results |
| 4. Prostate transport unnamed | Added TRANSPORT.md with cohort/source gates, exact median/IQR and pathology-correlation statistics, separate regimen-specific clinical AUROCs; added A06 | TCGA-LUAD/PCaDB manifests, orthogonal pathology coverage, clinical timing/units/access |
| 5. Delta composition dependence hidden | Added O/SD/PD concordance decomposition and Figure2D; interpretation distinguishes category weights from separation | Source-supported categories and full data |
| 6. Frozen-source failures could reweight | ANALYSIS/DATA/ENGINEERING require incomplete primary; no automatic renormalization; reduced-set sensitivity is separate | Parser/run-status implementation |
| 7. Replication confused with context change | ANALYSIS/README/FIGURES distinguish same-cancer reproducibility from cross-cancer/regimen transport | Comparable independent same-cancer cohorts not asserted |
| 8. Secondary testing denominator vague | Explicit frozen test/score/family registry and fixed M; nonestimable computational p=1 only for BH, scientific values remain null/reason-coded | Actual signatures and source-correct test methods must be locked before A03 |

Additional documentation checked against official pages: scikit-learn1.9 LogisticRegression (`l1_ratio`, C, SAGA; deprecated penalty), LeaveOneGroupOut, and NumPy2.4 quantile. Links are adjacent to their method contracts. Numerical learner/threshold/split proposals are declared design choices, not facts inferred from cited studies. Existing A/B evidence supplies cohort statements; this revision invents no new eligible N.

Scope retained: clinical signature robustness, endpoint definitions, discovery-derived responder products, clinical cross-cohort/cancer evaluation, prostate molecular characterization and available regimen-specific clinical exploration. Conditional data gates do not approve narrowing or substitute proxy outcomes for clinical validation.
