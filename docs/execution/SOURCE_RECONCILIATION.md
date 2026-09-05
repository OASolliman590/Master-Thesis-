# Source reconciliation and first grilling round

Status: evidence/decision register in progress; not a frozen statistical analysis plan. Updated 5 September 2026.

## Source hierarchy

The original submitted protocol defines the thesis question and registered method descriptions; formal institutional approval cannot be inferred from blank signature/date fields. The July handover and wet-lab v2 are planning documents, not results. The v2 document explicitly critiques/replaces parts of the handover. User-approved September scope corrections preserve A/B/C/D and the full Paper C source architecture. Neither original spec-kit tests nor later assistant recommendations make their scientific assumptions true.

## Resolved factual questions and open decisions

| ID | Question | Evidence-backed answer | Kind/status | Source and exact locator | Effect on specifications |
|---|---|---|---|---|---|
| S01 | Does the thesis include laboratory work? | The submitted protocol includes cell-model selection, epigenetic treatment and qPCR/Western readouts. RNA-seq and functional co-culture are described as possible extensions. | Source fact; resolved | Submitted protocol PDF/text, page6, In Vitro Validation | Preserve laboratory interfaces; computational outputs do not replace required experiments |
| S02 | Are later laboratory plans records of completed experiments? | Both are plans; v2 explicitly identifies itself as a research-design protocol. | Source fact; resolved | Wet-lab v2, section1; handover section1 | Do not claim experimental validation exists |
| S03 | Which inherited experimental assumptions changed? | v2 challenges unmatched tumour recognition, expression-scale Bliss, IC20-only selection, and a second checkpoint as the primary factorial. | Source fact about document differences; not independent endorsement of every v2 detail | Wet-lab v2 sections3.2–3.3 versus handover sections3,5,7–9 | Preserve the differences in protocol mapping; do not silently treat both plans as equivalent |
| S04 | Is orthogonal immune-context evidence part of C? | Yes: inherited Paper4 spec FR24–FR30 and current user correction explicitly retain Perturb-CITE-seq, TISMO and the proposed LJP4 arm. | User decision/source fact; resolved | Existing Paper4 docs/spec.md FR24–FR30; C_SOURCE_SCOPE_RESTORED.md | Full source architecture remains in scope; actual access and comparison counts still need verification |
| S05 | Is the current C primary endpoint already agreed? | No. The inherited kit centres reversal/thesis-drug placement; v0.2 proposed a fixed eight-gene measured contrast; v0.3 marks that change as unagreed. | Unresolved design choice | Existing Paper4 docs/preregistration.md H1; September correction | Grill the exact estimand before registration; do not label either alternative approved |
| S06 | Does failure to recover eight canonical genes prove a pipeline fault? | The inherited kit makes that assertion, but no supplied evidence establishes it as a technical invariant. | Unsupported biological success gate; design correction proposed | Existing Paper4 docs/spec.md section3.2/FR09; config gate | Separate technical QC from genuine negative biology; reviewer to assess replacement |
| S07 | Can co-normalised PRAD/LUAD matrices establish a lineage-free immune contrast? | Co-normalisation alone cannot identify immune effects separately from tissue differences; the kit itself acknowledges lineage confounding. | Inference from design; resolved limitation | Existing Paper4 docs/spec.md sections3 and7; submitted protocol comparative aim | Preserve within-PRAD analysis and explicitly bounded LUAD context |
| S08 | Does a bulk RNA immune phenotype independently validate prostate ICI response? | No response label is supplied by deriving another score from the same expression data. Clinical-response and molecular-phenotype endpoints are separate. | Statistical/design fact; resolved boundary | Existing Paper3 docs/spec.md sections1.4/2; latest goal | Do not chain associations into validated prostate benefit or use overlapping deconvolution as independent ground truth |
| S09 | Are all prostate methylation–expression relationships expected to be inverse promoter associations? | The submitted protocol cites Guo2023, whose full-text investigation documents an opposing domain-hypomethylation/repressive-chromatin route. | Primary-source mechanism evidence; independent audit available | docs/research/B_paired_prostate.md; DOI10.1016/j.cell.2023.05.028 | B must retain both directions/regions in evidence; a promoter-only result cannot represent all epigenetic mechanisms |
| S10 | Does an empty new repository mean old work should be rebuilt first? | No. The user explicitly made old work optional reuse; the intended new private repository was empty on current inspection. | Current environment fact and user decision; resolved | Live gh repo view/contents; activated goal | Begin evidence contracts and spec kits; no historical pipeline repair prerequisite |

## Frontier before specifications can be implementation-ready

- A: retain clinical-score robustness and prostate transferability scope while deciding one primary endpoint and defining genuinely independent phenotype evidence. The narrowed CYT endpoint was a proposal, not approval.
- B: decide a fixed primary molecular target and model comparison after real paired features/covariates are inspected; account for the observed methylation mechanism heterogeneity.
- C: reconcile reversal discovery with measured corroboration into one primary endpoint; verify locally executable documented scoring and source-specific coverage. Stage6 annotates evidence rather than deleting untested genes.
- D: pin a checkpoint, assay-compatible independent test conditions and pretraining exclusions; complete the conditional design without pretending the benchmark exists.
- Across all papers: define exact independent units, source overlap, registered versus proposed changes, precision and claim boundaries before code production.

New public-source research and Opus consultation will refine this frontier. Decisions requiring the user will be presented with evidence and explicit recommendations; facts that can be looked up will not be delegated back to the user.
