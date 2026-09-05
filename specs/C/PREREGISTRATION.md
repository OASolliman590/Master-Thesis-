# Paper C preregistration and factual grilling ledger

Version 0.1, 5 September2026. **Draft; not preregistered, approved or ready for production.** No drug-expression values were inspected in the completed metadata readiness audit. Historical work and the supplied prior plans constitute prior exposure and must be inventoried before any claim that the entire thesis is outcome-naive. A tag cannot retroactively preregister analyses already performed.

## Proposed single primary outcome

For each of decitabine, entinostat and tazemetostat: `R_c = -mean(WTCS)` across unique QC-passing Level5 signatures at PC3,24h, exact pert_dose1.11111uM, using one frozen B discovery-derived bidirectional disease query and one ordered assayed gene universe. The endpoint is a finite-release descriptive reversal score with three compound-specific estimates. It is not comparative treatment efficacy, an estimable class effect or a validated immune-killing surrogate.

The anchor is the lowest common QC-passing measured dose in the complete metadata audit; it is **proposed** and requires scientific review. Exact IDs and counts are in `docs/research/C_lincs2020_readiness/thesis_anchor_summary.json`: decitabine2collapsed signatures/5instances; entinostat1/2; tazemetostat1/3. Tazemetostat is non-HIQ there and comes from a different project. No biological CI, drug-superiority p-value, fixed minimum reversal, canonical-gene recovery gate or favorable compound ordering is required. The primary query is not B's fixed eight-gene expression endpoint.

## Decision register

Statuses: `established_fact` means source-supported evidence; `proposed_material_decision` needs review before effect inspection; `conditional_design` cannot execute until its stated gate resolves; `unknown` must not be converted to an assumption. Accepted process rules are distinct from approval of scientific choices.

| ID | Decision | Status | Requirement to resolve |
|---|---|---|---|
| C-D01 | Preserve all agreed source roles in DATA.md | Accepted scope/process rule | Source removal requires a recorded scope decision |
| C-D02 | Primary negative-WTCS at lowest common PC3/24 h / 1.11111 uM | Proposed material decision | Scientific review of assay anchor and finite-context claim |
| C-D03 | Equal signature weighting within each compound-condition | Proposed material decision | Review unequal project coverage; show every component score |
| C-D04 | One B discovery-only bidirectional query, plus frozen expression-only comparator | Conditional design | B derivation, signed directions, selection budgets and hashes must exist |
| C-D05 | QC-pass primary; HIQ restriction secondary | Proposed material decision | Review functional-selection implications, keep non-HIQ visible |
| C-D06 | Raw WTCS primary, no automatic tau | Proposed material decision grounded in source semantics | Reference numerical parity; no invented tau distribution |
| C-D07 | Class inference only after identity and design-rank gates | Conditional design | Structure/MOA curation and adequate compound×project×context overlap |
| C-D08 | Additional prostate perturbations provide preferred measured validation | Conditional design | Actual accession interventions, controls, genes and biological units |
| C-D09 | Perturb-CITE-seq/TISMO/LJP4 retained as separate contextual evidence | Accepted scope; analyses conditional | Actual manifests, original-study units and compatible endpoints |
| C-D10 |10,000 matched-query null draws, fixed seed, three-compound BH family | Proposed material decision | Exchangeability/matching assessment and recorded seed before draws; no biological treatment p-value claim |
| C-D11 | Standalone manuscript versus combining with B | Unresolved substantive decision | Evaluate what methylation/context changes beyond familiar rankings and whether measured evidence tests it |

Neither dates nor silence approve these items. The review disposition must name approver/reviewer, evidence, timestamp, version and affected analysis before a decision becomes frozen.

## Grilling ledger: answer facts before preferences

All source checks below are dated5 September2026; original release dates differ. Linkable local artifacts identify inspected fields and hashes. Scientific recommendations are labelled rather than presented as source facts.

| Question | Answer /classification | Primary evidence and inspected fields | Spec consequence |
|---|---|---|---|
| Does tazemetostat actually occur in LINCS? | Fact: yes as E-7438, BRD-K11215326, with134chemical rows across contexts | [Compound dictionary](https://s3.amazonaws.com/macchiato.clue.io/builds/LINCS2020/compoundinfo_beta.txt), cmap_name/aliases/InChIKey; `C_pharmacology_contracts/verified_coverage_summary.json`; full signature audit | Use structure-aware identity; never infer absence from name-only search |
| Is prostate coverage merely a dictionary entry? | Fact: full file has55,253PC3 and35,442VCAP chemical signatures | [siginfo_beta](https://s3.amazonaws.com/macchiato.clue.io/builds/LINCS2020/siginfo_beta.txt), pert_type/cell_iname; `C_lincs2020_readiness/audit_summary.json`, full SHA1a38d7…40201 | Record actual assay rows separately from model catalogues |
| Is the selected primary exposure measured for all three? | Fact:1.11111,3.33333,10uM all have PC3/24h QC-pass coverage; lowest choice is a proposal | `thesis_anchor_summary.json`, pert_dose/unit/time/QC/distil_ids | Freeze exposure before scoring; no invented interpolation |
| Does matching exposure remove batch confounding? | Fact/inference: no; tazemetostatMOAR005 differs from REP/PBIOA projects at lowest dose | Same exact anchor artifact, sig_id/project_code/det_plates | No treatment-superiority inference; show project labels |
| Why not require HIQ? | Fact: official HIQ combines technical and functional recall criteria; lower-dose tazemetostat is non-HIQ | [Field definitions](https://s3.amazonaws.com/macchiato.clue.io/builds/LINCS2020/LINCS2020%20Release%20Metadata%20Field%20Definitions.xlsx), is_hiq/qc_pass/nsample; `field_definitions.json` | Proposed QC-pass primary, HIQ sensitivity; avoid activity-selected eligibility |
| Can the three classes be compared by counting signatures? | Fact: exposure/project imbalance; raw labels include BIX-01294 and multiple azacitidine IDs | `epi_panel_supplemented.json`; [BIX primary mechanism](https://doi.org/10.1016/j.molcel.2007.01.017) | Curate independent molecules and mechanisms; class inference conditional |
| Is only one EZH2 compound available? | Fact: EI1 adds3PC3/24h rows to tazemetostat; exhaustive class coverage unknown | `EI1_rows.json`; [Qi2012](https://doi.org/10.1073/pnas.1210371110); dictionary EI1/EI-1 | Missing EZH annotations cannot define the class universe |
| Can2017 independently validate2020? | Fact:292,419old instance IDs recur;112,188old signature IDs recur | `audit_summary.json`; [PhaseII original](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE70nnn/GSE70138/suppl/GSE70138_Broad_LINCS_sig_info_2017-03-06.txt.gz) | Release robustness only until disjoint instances shown; PhaseI audit still unknown |
| Does WTCS need tau? | Fact: QueryL1k documents raw/normalized scores and reference-null FDR, not automatic historical tau | [Pinned QueryL1k](https://github.com/cmap/cmapM/blob/8f0e7bc4c38efbdf3f96f5ac72ee26792907a99c/docs/SigToolDemo.md); methods_manifest.json | Primary raw WTCS; no relabelled permutation percentile |
| Are exact-zero ES and ties defined? | Fact: unequal sign labels retain half-difference, including one zero; pre/post tie preserves posthit; rank ties still need verification | Pinned getCombinedES/fastESCore in `core_methods_manifest.json` and artifact_checksums | Source-parity fixtures before production, no guessed conventions |
| Do code templates establish scorer correctness? | Fact: no current C production scorer was run; metadata scripts only | Actual audit run.log; environment.contract.json | Environment recreation and reference/real-slice smoke gates remain open |
| Can B's eight-gene endpoint be used as the disease query? | Design constraint: not automatically; primary requires a distinct signed disease axis with two nonempty directions | B handoff currently unresolved; C ANALYSIS.md | Block query admission; one-sided fallback requires amendment |
| Must canonical immune genes be recovered? | Design judgement: no; absence can be a valid scientific result | Earlier8-of-18gate was a historical proposal, not adopted | Never manufacture directions/genes or assert pipeline failure from biology |
| Does promoter anticorrelation prove tumour-cell silencing? | No; association can reflect cell composition and confounding | B analysis/provenance contract, not an intervention experiment | Name methylation-supported association; keep cell-origin caveat |
| Does PRISM dictionary overlap prove measured sensitivity? | Fact: no; named compounds/models occur but actual nonmissing matrix intersection is unaudited | [PRISM19Q4v4 record](https://api.figshare.com/v2/articles/9393293), cached treatment/model dictionaries | Sensitivity coverage stays unknown until matrix-level join |
| Does DepMap essentiality identify an immune-gene regulator? | No; gene effect measures dependency in an assayed context | [DepMap source](https://depmap.org/portal/), actual selected matrices pending | Context annotation only; direct regulatory evidence separate |
| Does DrugBank access prevent the whole paper? | Fact: provider download pause observed; substitute lawful available ChEMBL identity layer while retaining DrugBank status | [DrugBank release page](https://go.drugbank.com/releases/latest), `C_pharmacology_contracts.md` | Block only unavailable adapter; source deletion not implied |
| Can plasma free Cmax be equated to culture exposure? | No; free-medium/intracellular exposure and duration can differ; human PK extraction unknown | Original PK/regulatory records not selected yet | Annotate assumptions; no patient dose claim |
| Does Perturb-CITE-seq directly validate our drugs? | Fact: genetic human melanoma perturbations with different conditions, not these prostate chemical experiments | [Frangieh2021](https://www.nature.com/articles/s41588-021-00779-1), `C_immune_context.md` | Orthogonal target/condition evidence; targeted-unmeasured remains visible |
| Are scPerturb and SCP1064 independent? | Fact: versions of the same originating Frangieh study | [Zenodo10044268](https://zenodo.org/records/10044268), source filenames | One originating-study ID; no double validation count |
| Does TISMO prove prostate ICI sensitisation? | Fact: publication mouse/cytokine/ICB totals; actual relevant overlap unknown | [TISMO primary](https://pmc.ncbi.nlm.nih.gov/articles/PMC8728303/), current manifest unresolved | Preserve species/animal/experiment and condition-specific claim |
| Is LJP4 a verified prostate IFNG reference? | Fact: IFNG appears in22-entry list; paper describes six breast lines; payload unverified | [Ligands](https://maayanlab.cloud/L1000CDS2/ligands), `C_immune_context/l1000cds2_ligands.json` | Retain conditional reference, no prostate label or independence assumption |
| What would the manuscript add? | Proposal: demonstrate what methylation/context changes versus expression-only and test it with independent measurements | Six original studies in `docs/research/C_novelty_comparison.md`, including Chang2022/Morel2021/OncoLoop2023 | Predeclare comparator; familiar annotated rankings alone trigger combine/scope review |

## Freeze record and deviations

Before first effect inspection, record: approved spec commit/tag and timestamp; query and comparator hashes; B discovery/validation/exposure registry; source object URLs/releases/hashes; included conditions and exclusions; ordered gene universe; technical QC and duplicate policies; exact scorer/environment; seed/null definition if used; all primary/secondary estimands and families; validation contrast manifests; reviewer disposition. The preregistration artifact itself gets a persistent public or private registry identifier with access status. A Git tag alone is a versioned record, not proof of public prospective registration.

Amendments must preserve the previous version, timestamp, reason, whether relevant outcomes had been seen, impact on estimand/selection/multiplicity, and reviewer decision. A missing query direction, loss of anchor coverage, inadequate independent validation, class nonidentifiability or inaccessible source triggers an explicit amendment/gate. None permits selecting a favorable substitute silently. Report negative/null findings and unavailable source layers alongside successful analyses.

Current gates: all-four-package scientific review pending; C-D02 throughC-D06 not approved; B handoff absent; Level5 values/extraction route unverified; runtime/parity/lock absent; independent measured validation and contextual units unresolved; canonical code tickets not dispatchable. Metadata audit completeness does not close these scientific gates.
