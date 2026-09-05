# Paper C — Epigenetic-drug prioritisation with contextual validation

Version 0.1, 5 September 2026. **Design proposal; not implementation-ready.** This is the third current paper, Claude's original Paper 4. No primary endpoint or source removal is approved by this draft.

## Question and contribution

Which measured epigenetic perturbations oppose a prostate immune-associated disease signature, and how does patient methylation evidence, independent measured perturbation evidence and pharmacology change the interpretation of an expression-only ranking?

The proposed primary outcome is condition-specific **negative WTCS**, with separate estimates for the three protocol compounds at the lowest common measured QC-passing PC3/24 h dose. This is a finite assay-context description. It does not estimate comparative drug efficacy or a class treatment effect. The dose is an assay anchor, not a recommended exposure. The broader compound screen, class comparisons where identifiable, context dependence and independent corroboration remain in scope.

The main novelty test is substantive: demonstrate what the patient methylation/context evidence changes relative to an expression-only prioritisation, then examine those changed interpretations with independent measurements. A longer database list is insufficient. Chang 2022 already combined prostate immune signatures, CMap/L1000 resources and GDSC; MD-Miner, OncoLoop and prior HDAC/EZH2 immune studies also overlap. See [the six-study comparison](../../docs/research/C_novelty_comparison.md). Rediscovering known drugs alone is unlikely to sustain a distinct manuscript.

## Thesis and source commitments

Paper B supplies a frozen discovery-derived molecular handoff; C tests perturbation direction and translational plausibility. A is not required to finish first if the B discovery handoff is independent of A. Keep TCGA PRAD/LUAD, LINCS, CCLE/DepMap, PRISM/GDSC, DrugBank/ChEMBL, Perturb-CITE-seq, TISMO and the proposed LJP4 IFNG reference. GSE199800/GSE216053 are additional measured prostate corroboration, not replacements. Each source has a distinct role and an explicit access/coverage gate in DATA.md.

Registered decitabine/entinostat/tazemetostat experiments remain separate. C may motivate a proposed experimental revision, but cannot silently change the approved protocol. Signature reversal in monoculture does not demonstrate immune killing, TME conversion or clinical ICI sensitisation. Human genetic screens and mouse ICB experiments test related claims in different settings, not the same prostate-drug clinical endpoint.

## Proceed, narrow, combine or defer

- Proceed to production only after the primary choice, disease query, usable matrix route, numerical scorer, independent units and meaningful validation route are reviewed and frozen.
- Keep a missing source visible with its exact unresolved role. A blocked supplementary annotation does not block unaffected work; removing an agreed scientific arm requires a documented decision.
- Class inference is conditional on structurally curated independent compounds and an identifiable exposure/project design. Dropping an unjustifiable class p-value is a claim restriction, not deletion of class coverage reporting.
- Consider combining C with B if the final evidence is only a familiar ranked list or the independent evidence cannot test what the methylation layer adds. This is a review criterion, not a decision already taken.
- A non-reversing result is valid. Failure to recover canonical immune genes is not a technical failure by itself. D and virtual predictions cannot fill missing measured validation.

## Package map

DATA.md defines coverage and provenance; ANALYSIS.md defines the proposed primary and secondary estimands; VALIDATION_AND_FIGURES.md binds four figures to evidence; ENGINEERING.md defines schemas, tools and reproduction; PREREGISTRATION.md records factual grilling, decisions and gates; references.bib contains core scientific references. Tickets are bounded proposals, not dispatchable production work.
