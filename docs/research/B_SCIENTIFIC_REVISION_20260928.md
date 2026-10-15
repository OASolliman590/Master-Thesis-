# Paper B Scientific Revision Report

**28 September 2026 | Scientific review proposal | No new biological results**

Repository baseline: `a8278c776da7c6b096cc14139d729979db286b50`. This report accompanies [the proposed revision kit](../../specs/B/revision_20260928/README.md). References R01–R25 are defined in that kit's `REFERENCES.md`. Repository observations refer to the pinned baseline, not to uninspected work on the user's computer or AIU.

## 1. Executive verdict

Paper B should be a **prostate-centred investigation of clinically anchored immune-expression alterations and competing regulatory explanations**, ending in a frozen set of restoration-test hypotheses. It should not be sold as an ICI-response predictor in untreated TCGA patients, a causal methylation study, or a catalogue of drugs that sensitise prostate cancer.

The central scientific question is: **Which programmes reproducibly associated with observed ICI response are underrepresented in defined prostate comparisons, and which associated molecular changes remain plausible regulatory explanations after composition, genetic disruption, disease state and measurement are considered?**

Use “immune deficit” operationally: a lower measured programme relative to a declared comparator, not proof of deficient immune function. A tumour can have abundant antigen-presentation RNA without effective antigen presentation, and low bulk expression can reflect absent expressing cells. The study must distinguish those possibilities rather than assuming a drug should raise every response-associated gene.

**Retain B-P.** The accepted `AB_IMMUNE_BARRIERS_20260911.md` already makes external Delta_R2 the single confirmatory estimand within the fixed APM validation module. No new primary endpoint is needed merely to broaden the biological story. Broader hypotheses remain secondary/exploratory until their own contracts are approved. The paper may have one central scientific aim without pretending that one scalar predicts every part of that aim.

The strongest feasible architecture is RNA–methylation–clinical/specimen linkage, with CNA and mutation as competing-explanation layers; independent prostate molecular replication; and one carefully qualified cellular or protein/chromatin corroboration layer. MOFA2, spatial analysis, miRNA and broad pan-cancer extensions are conditional, not prerequisites or substitutes for replication.

## 2. Current-design audit

| Element | Classification | Scientific disposition |
|---|---|---|
| Prostate-centred A→B→C logic | Retain | Appropriate thesis spine, but each arrow carries a different evidence level. |
| B-P external paired Delta_R2 | Retain | Existing confirmatory APM module; do not replace after a null result. |
| Eight-gene P as all of Paper B | Replace | It is a constructed partial MHC-I-related expression endpoint, not the full biological question. |
| Exact P/U/Q, cross-platform score and baseline | Unresolved | Membership, promoter semantics, specificity, covariate comparability and precision need freeze. |
| A classifier coefficient as responder differential expression | Remove | Conditional predictive weights and gene-wise response associations are different quantities. |
| LUAD as observed ICI-positive control | Replace | Retain registered secondary tissue/context comparison; no observed response labels. |
| Equal PRAD/LUAD sample sizes | Revise | Use all eligible cases; balancing only predeclared sensitivity, not a statistical requirement. |
| Automatic joint ComBat | Remove | Do not remove the cancer contrast or manufacture identifiability when batch and cancer coincide. |
| Hypermethylation-only candidate filter | Revise | Preserve as the registered hypothesis subset; add separate domain, genetic and cellular alternatives. |
| ESTIMATE | Retain | Coarse RNA immune/stromal context, not detailed fractions or independent purity. |
| CIBERSORT/CIBERSORTx | Conditional | One pinned assay-compatible reference and mode; inferred fractions are uncertain. |
| MethylCIBERSORT | Retain | Accepted methylation-derived composition sensitivity; prostate/reference/probe gates remain. |
| CNA and mutation context | Revise | Make alternatives explicit in the core evidence matrix; missing assays limit claims, not the RNA cohort. |
| RPPA/proteomics/ATAC | Conditional | Only measured targets with legitimate specimen links; same-patient assays are orthogonal, not independent cohorts. |
| MOFA2 | Conditional | Keep only if stable factors explain an identifiable cross-view question beyond direct models. |
| DIABLO on RNA-derived pseudo responders | Remove | Circular target; not clinical validation. DIABLO is a method in mixOmics. |
| Survival models | Conditional | Only a separately justified clinical question with usable events; not an obligatory figure. |
| Single-cell/spatial | Conditional | Resolve cell origin or regional exclusion, with donor-aware inference and actual relevant readouts. |
| Weighted master barrier score | Remove | Evidence dimensions are not commensurate; preserve missing and contradictory evidence. |
| Existing format/registry/fold-local/evaluation infrastructure | Retain | Reuse compatible components; distinguish code, historical synthetic tests and real analysis. |
| Current status documents/issues | Revise | Several stale statements contradict later code/receipts. Do not infer current tests from progress prose. |

## 3. Thesis-protocol reconciliation

The submitted eight-page protocol commits to clinical responder discovery, PRAD/LUAD expression and methylation comparison, a high-in-responder/low-in-PRAD/hypermethylated prioritisation hypothesis, and experimental epigenetic intervention. It does not authorise silently replacing observed clinical response with a TCGA-derived label.

The detailed [five-way crosswalk](../../specs/B/revision_20260928/PROTOCOL_CROSSWALK.md) distinguishes submitted commitments, accepted user amendments, proposed extensions, implemented software and actual biological evidence. Institutional approval of the later scientific amendments remains **UNKNOWN**. The signed administrative pages should not be copied into this public repository.

The low-detection-P exclusion wording needs an explicit correction: large detection P ordinarily indicates unreliable array measurement. Apply the source-specific definition and reviewed threshold, not a generic rule imposed on processed beta files that lack those measurements [R21].

## 4. Exact revised aim and secondary aims

**Primary scientific aim:** identify clinically anchored prostate immune-expression alterations and determine which have reproducible evidence compatible with epigenetic regulation rather than being explained solely by cellular mixture, genetic disruption, clinical context or assay differences.

Secondary aims are to characterize disease-state and cellular context; evaluate the fixed APM methylation model's external incremental prediction; and export an auditable discovery-only hypothesis set for independent perturbation prioritisation. Neither the primary aim nor a positive B-P result establishes reversibility or ICI sensitisation.

A reference is mandatory. Proposed within-prostate tumour-versus-adjacent-tissue comparisons test a disease-associated alteration; adjacent tissue is not healthy population tissue or an ICI-responsive state. PRAD versus LUAD remains a separate registered lineage/context contrast. A programme need not be lower in both, and disagreement is informative. Do not select the reference yielding the desired sign after looking at results.

## 5. Hypotheses and testing hierarchy

**Existing confirmatory hypothesis:** specified promoter methylation adds externally transported information about the frozen APM RNA endpoint beyond the specified clinical/tumour-content baseline, measured by paired CPC-GENE Delta_R2. Membership and full analysis freeze remain outstanding.

**Proposed secondary families:** (i) A-derived programmes differ in declared prostate comparisons; (ii) cognate promoter methylation has associations with expression under predefined clinical/genetic adjustment; (iii) discovery-selected relationships recur in a qualified independent prostate population; (iv) disease-state interactions are present where directly tested. Preserve either methylation sign. Freeze programme membership, comparison and multiplicity family before analysis.

**Exploratory hypotheses:** domain/histone mechanisms, miRNA links, latent factors, cellular localization and spatial relationships. These can provide mechanistic corroboration but must not be promoted into confirmatory claims after favourable results. A documented null or opposite-direction result remains reportable.

## 6. Novelty audit

| Closest work | Established overlap | Consequence for B |
|---|---|---|
| Guo 2023 [R01] | Prostate immune repression involving hypomethylated domains and repressive chromatin, with experimental follow-up. | Methylation-associated immune loss or generic EZH2 restoration is not new. |
| Morel 2021 [R02] | Prostate EZH2 inhibition, immune-related expression and checkpoint-combination biology. | Clinical immune-signature anchoring and epigenetic priming alone are insufficient novelty. |
| Arbet 2026 final atlas [R03] | Large prostate methylation atlas, multi-omics and molecular/clinical prediction. | Do not claim first methylation–RNA/CNA integration or first predictive modelling. |
| Sinha 2019 [R04] | Localized prostate proteogenomics, including the CPC source family. | Protein integration is established; audit source overlap. |
| Mizuno 2025 [R05] | Advanced-prostate intraindividual RNA/methylation/histone heterogeneity. | Competing chromatin mechanisms and multi-site integration are already studied. |
| Singh 2026 [R06] | Context-dependent DNMT1/EZH2/chromatin relationships in prostate models. | A universal demethylation→restoration assumption is unsafe. |
| MethylCIBERSORT [R07]; Thorsson [R08] | Composition-informed immune states and pan-cancer molecular context. | Deconvolution plus TCGA immune classification is not a new contribution. |
| Hirz 2023 and Kiviaho 2024 [R09,R10] | Prostate cellular/spatial states and treatment-context analyses. | Adding cell maps or spatial pictures is not novelty; resolve a specific ambiguity. |
| Earlier TCGA methylation-driver studies [R24] | Methylation/expression integration and prognosis-oriented candidates. | A smaller gene list or another model is weak differentiation. |

Arbet's final abstract reports 3,001 methylomes and 884 samples with DNA and/or RNA; those numbers do not mean 884 fully paired patients. Its final methods, exact cohort inventory and relevant result tables were not fully accessible in this review. Novelty clearance against the complete final article is therefore **unfinished**, not negative. The official PrCaMethy target list does not establish absence of APM genes from genome-wide analyses.

**Defensible contribution hypothesis:** clinically selected programmes yield a different, reproducible prostate hypothesis set once cellular, genetic and regulatory explanations are separated, with a frozen independent validation boundary and experiments capable of distinguishing those explanations. This becomes a contribution only if actual evidence changes a biological interpretation or constrains an important hypothesis. No “first” claim is justified by this review.

## 7–12. Data, omics, clinical state, composition, integration and validation

The [data contract](../../specs/B/revision_20260928/DATA_CONTRACT.md) assigns each source a question rather than accumulating databases. Discovery is TCGA-PRAD; CPC-GENE is the fixed-module external molecular candidate, not an automatically eligible 210-patient dataset. Repeated publications, portals and reused specimens are represented as source relationships, not summed cohorts.

Core views are RNA and measured methylation with clinical/specimen information. CNA and mutation qualify alternative explanations; their missingness does not require discarding every RNA-only patient. Protein, ATAC, miRNA, single-cell and spatial evidence enter only on the appropriate linked subset or as explicitly unpaired corroboration. Report N per modality, patient-linked N, same-specimen N, complete-view N and missingness patterns.

Clinical mapping must separate diagnosis stage from sampling state, primary from metastatic specimen, verified pretreatment status from undocumented treatment, and castration-sensitive from resistant disease. Unknown history is not untreated. Primary-prostate and previously treated metastatic populations are not pooled into one homogeneous cohort. These data describe cohort clinicopathological associations, not population prevalence.

Composition adjustments are sensitivities under stated assumptions. Attenuation does not prove confounding; persistence does not establish tumour-cell regulation. MOFA2 remains unsupervised and optional; DIABLO requires an observed legitimate target and is not used to reproduce a score-derived ICI label [R17–R20]. Detailed methods and limits are in [composition/integration](../../specs/B/revision_20260928/COMPOSITION_INTEGRATION.md).

Validation distinguishes independent molecular replication, different assays in the same patients, cellular localization, spatial corroboration and perturbation. A CPC protein assay from a reserved CPC patient is not a discovery input merely because it is a different modality.

## 13–14. Relationship with A, C and wet lab

Import A's gene/programme clinical association estimates and uncertainty separately from its frozen classifier. A positive classifier coefficient is not necessarily higher responder expression or a direction to induce. All-development biological products must be frozen before final-test inspection; B does not redesign A on the basis of prostate findings. A's current specification is not evidence that these new biological products already exist.

Freeze discovery candidate membership, contrasts, directions and selection rules before CPC or C results. External evidence may later be appended without selecting a new candidate set. Preserve evidence for, against, missing and contradictory. Any ordering must use a predeclared non-outcome-driven rule; do not add an arbitrary weighted barrier score.

C's current proposed WTCS analysis requires up and down sets from the **same disease axis**. An eight-gene endpoint or an all-down restoration list is not that query. Do not invent the opposite direction. A one-sided product requires a separately approved C endpoint amendment or remains ineligible for its current bidirectional primary.

B supplies the readout, clinical rationale, prostate/model context, expected baseline to verify, epigenetic evidence, alternatives and what a restoration experiment must distinguish. C selects interventions. Wet lab tests molecular restoration and then function. No wet-lab redesign or causal conclusion is authorised here.

## 15. Four-figure architecture

Figure 1 establishes clinical and assay accountability; Figure 2 shows declared prostate contrasts and composition context; Figure 3 separates regulatory associations from genetic/cellular alternatives and shows replication; Figure 4 combines the fixed APM external result with candidate-level evidence and the frozen handoff. The [panel contract](../../specs/B/revision_20260928/FIGURES.md) specifies source, unit, analysis, uncertainty and claim ceiling for every panel. Missing optional evidence removes or narrows a panel transparently; it is not filled with decoration.

## 16. Primary-endpoint decision

Keep the existing B-P estimand and its place inside the APM module. Its advantages are a precise external quantity, same-patient model comparison, and reusable locked-evaluation infrastructure. Risks include cross-platform endpoint transport, small or selected covariate-complete external populations, Qpure/ABSOLUTE differences, uncertain same-focus pairing and unstable SST. Even positive Delta_R2 with both individual R2 values negative may describe relative improvement without useful absolute prediction.

The eight genes are a constructed partial programme, not a published validated clinical assay. P, U and Q remain unfrozen; coverage inspection predates primary selection and must remain disclosed. A final precision criterion must be justified before external errors are examined. No adequate eligible N or meaningful-effect threshold is invented here.

**No replacement primary is recommended now.** Should measurement or precision gates fail, report the fixed module as non-estimable or seek an explicit prospective amendment before external analysis. B-R and a broad barrier index are not automatic substitutes. The broader scientific narrative must stand on its own evidence, not on a positive B-P p-value.

## 17. Feasibility and blockers

What can proceed: review approval, source-object/clinical/specimen audits, patient-free annotation preparation and a plan to reuse the existing software. What cannot yet proceed as a released biological analysis: A-derived scoring without A's frozen products; B-P without P/U/Q, baseline, eligibility and precision locks; reference-dependent candidate discovery without an approved contrast; external evaluation before the training/model lock.

The code inspection confirms an existing fold-local feature-fitting path and a no-refit evaluator. The connected W5/W6 path explicitly accepts fixture-only policies. Historical local W8 acceptance reports 147 passing tests; historical AIU W5 strict testing reports 115/116 with one missing-fixture failure. Those are not tests rerun in this review. Git clone/runtime download attempts failed; the user's dirty worktree and AIU state remain UNKNOWN. No current application-wide passing claim is made.

The next work should close measurement and source questions, not implement every optional tool. Source-specific blocked modules do not halt unaffected evidence preparation. Do not describe the proposed kit as biologically implementation-ready before its gates close.

## 18. Publication assessment

A standalone paper is plausible if it identifies or meaningfully constrains clinically relevant prostate regulatory hypotheses with reproducible molecular evidence and at least one corroborating layer that resolves an important alternative explanation. A precise negative B-P finding can be valuable but does not guarantee publication. A collection of familiar correlations, a latent-factor plot and a drug list is not enough.

The strongest manuscript would explain **which apparent barriers disappear when composition or genetic disruption is considered, which persist as regulatory hypotheses, and which directions cannot be defended**. A useful negative result may exclude a simple methylation explanation. A weak or imprecise result must remain labelled inconclusive.

If the substantive outcome is only a discovery query for C, a combined B/C manuscript may be scientifically stronger than two thin papers; that is a later user/supervisor decision, not permission to remove this chapter or suppress its prespecified endpoint.
