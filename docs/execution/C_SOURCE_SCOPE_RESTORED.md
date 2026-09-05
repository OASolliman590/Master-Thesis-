## Scope correction v0.3 — restored Claude source architecture

The user confirmed that the third paper in the current programme is the pharmacology paper (Paper C; Paper 4 in Claude's original six-paper numbering). The supplied Claude conversation explicitly included LINCS/CMap, DepMap/CCLE, PRISM/GDSC, DrugBank/ChEMBL, Perturb-CITE-seq, TISMO and an LJP4 interferon-reference arm, with TCGA providing the patient disease axis.

The v0.2 assessment omitted the immune-context sources and over-centred GSE199800/GSE216053. Its C coverage table was incomplete and must not be used as evidence that the broader design is infeasible. Restore the full source architecture below. GEO perturbations are additional measured corroboration. The v0.2 fixed-eight-gene measured endpoint is a proposed refinement, not an agreed replacement for the original disease-signature reversal endpoint; the final primary endpoint must be reconciled with the restored design before preregistration.

### Sources and their distinct roles

- **TCGA-PRAD/LUAD and Paper B:** establish the patient expression/methylation axis and a discovery-frozen signed query. Within-PRAD analysis addresses lineage confounding; composition and cell origin need explicit handling.
- **LINCS/CMap:** central drug-discovery/signature-reversal screen, prostate contexts where actually available, with wider contexts as a sensitivity analysis. Audit compound, dose, duration, measured/inferred genes and release coverage. Preserve the reversal-direction oracle. This remains an integral analysis.
- **CCLE:** characterize the baseline molecular context of prostate models, including expression and measured methylation where the selected release supports it. Missing methylation coverage cannot be assumed complete.
- **DepMap:** annotate target/regulator dependencies and context selectivity. Dependency does not establish which immune gene a regulator controls.
- **PRISM/GDSC:** annotate measured sensitivity/growth effects and distinguish these from the immune-program endpoint. These may overlap other resource releases and are not automatically independent validations.
- **DrugBank and ChEMBL:** harmonize compound identities, targets, mechanism and bioactivity annotations, subject to access/licensing and source provenance. Use primary clinical pharmacology studies or regulatory labels for exposure claims; database annotations alone cannot establish clinically achievable unbound exposure.
- **Perturb-CITE-seq / Frangieh / SCP1064:** orthogonal functional annotation from genetic perturbations in melanoma–autologous TIL co-cultures, with RNA/protein and condition-specific evidence. Link perturbation effects on immune evasion/killing to candidate genes. A loss-of-function phenotype does not prove that drug-induced upregulation will improve killing. Annotate genes without screen coverage as untested rather than automatically discard them. [Primary study](https://www.nature.com/articles/s41588-021-00779-1).
- **TISMO:** orthogonal mouse immune-context evidence from cytokine-treated cell lines and syngeneic in vivo ICB studies. Freeze orthologue mapping and distinguish baseline response association from treatment-induced changes, tissue composition and tumour-size effects. It is not direct validation of our drugs in human prostate co-culture. [Primary resource paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC8728303/).
- **LINCS LJP4:** the supplied conversation proposed an interferon-direction reference. Retain this planned arm, but verify exact ligand, cell-line and exposure coverage before calling it an IFN-gamma reference; the original statement is a proposal, not a completed release audit.
- **GSE199800 and GSE216053:** additional measured prostate perturbation/corroboration sources. The prior metadata recount remains useful; these sources do not replace the seven named resource families.
- **STATE:** exploratory coverage extension or the separate conditional methods paper, not primary immune-context evidence.

### Restored analysis and manuscript structure

Patient-supported disease signature → LINCS reversal → model/target and sensitivity context → compound/exposure annotation → orthogonal immune-context corroboration. The additional GEO contrasts can test measured restoration where independent and compatible.

1. **Figure 1:** disease signature and coverage across the complete source architecture, including source overlap and missingness.
2. **Figure 2:** LINCS reversal, prostate/context specificity and measured prostate corroboration.
3. **Figure 3:** Perturb-CITE-seq functional gene evidence, TISMO immune-context concordance and the verified interferon-reference arm.
4. **Figure 4:** integrated pharmacological evidence: CCLE/DepMap context, PRISM/GDSC sensitivity, DrugBank/ChEMBL annotations, exposure and experimental shortlist.

The central question is restored to: which epigenetic compounds reverse a patient-supported prostate immune-deficiency program, and which candidates receive convergent functional, immune-context and pharmacological support? These evidence types remain separate; adding databases does not make all findings independent or prove clinical ICI sensitisation.

**Coverage status:** source purpose is now restored; complete release-level eligibility, shared-gene coverage, perturbation direction, study overlap and usable comparison counts for the restored arms still require assessment. The prior recommendation about compound-specific claims remains appropriate, but the C novelty/feasibility appraisal must consider these restored layers.
