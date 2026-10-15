# Context of use and claim ladder

Intended use: research-level reconstruction, analysis of evidence-supported exposure/response constraints, conditional schedule comparisons and prioritisation of missing measurements. Not treatment selection, patient-specific prediction, dosing advice or a clinical efficacy trial.

| Level | Evidence required | Allowed language |
|---|---|---|
| Specification | Defined equations/contracts | Designed; proposed |
| Software | Fresh tests and parity where claimed | Implemented; numerically verified within stated tests |
| Systemic PK | Independent source observations matching analyte/population | Evaluated systemic exposure in the specified data context |
| Target/phenotype PD | Relevant measured public PD and separated held-out evidence | Calibrated/evaluated the specified assay response |
| Functional QSP | Qualified measured functional data and explicit context | Reproduces/predicts that assay; never all tumour immunity |
| Scheduling without measured independent schedule test | Constrained models, fair comparison, uncertainty | Conditional model-based ranking or no identified preference |
| Quantitative non-identifiability | Measurement-linked equivalence/counterexamples | Existing evidence does not identify the specified contrast |
| Population representation | Actual distribution targets, weights, held-out checks | Represents stated targets, not all patients |
| Prospective original validation | Frozen prediction and independently generated admissible observations | Reserved for E_LAST; absent by design from core |

Calling public experiments 'experimental evidence' is accurate only with source attribution. Calling them 'our biological validation' or 'new prospective validation' is not. No local-data assumption is hidden inside an external-evidence parameter prior.

Any human tumour exposure, clinical checkpoint response or clinical regimen inference requires a separate validation claim. PBMC, cell-line and non-prostate evidence retain their original labels. Model bounds are not confidence intervals unless a valid inference construction supports that interpretation. Virtual-ensemble fractions are not patient probabilities.
