# PAPER D SCIENTIFIC REVISION REPORT

## A hybrid virtual tumour-microenvironment model for epigenetic priming and immunotherapy

**MSc thesis:** *Epigenetic Priming for Enhanced Immunotherapy: A Multi-Omics Strategy to Sensitise Prostate Cancer to Immune Checkpoint Blockade*  
**Review date:** 12 October 2026  
**Repository reviewed:** `OASolliman590/Master-Thesis-`  
**Main commit reviewed:** `a8278c776da7c6b096cc14139d729979db286b50`  
**Historical repository reviewed:** `OASolliman590/epigenetic-ici-priming-thesis` at `96c16794bafc8946ae9f0bdcef81d5f3a599542b`  
**Status:** scientific-design review; no model training, PhysiCell execution, parameter fitting, gene-panel freezing, or treatment simulation was performed  
**Readiness:** **not implementation-ready**

---

## Evidence labels used in this report

| Label | Meaning |
|---|---|
| **VERIFIED** | Confirmed from a live repository, final paper, official documentation, primary dataset record, or supplied protocol. |
| **PROVISIONAL** | Supported by a preprint, search-indexed article text, or incomplete upstream documentation; requires final source verification. |
| **UNKNOWN** | The necessary source, metadata, supplement, licence, or local environment evidence was not accessible or not present. |
| **PROPOSED** | A design recommendation, not an implemented or validated result. |
| **BLOCKER** | Failure prevents the associated claim, endpoint, or phase from proceeding. |

This report deliberately separates observed biology, learned prediction, literature priors, fitted parameters, rule-based assumptions, simulation outputs, and prospective wet-lab evidence.

---

# 1. Executive verdict: what Paper D should actually be

## 1.1 Decision

**Paper D should not presently replace its existing narrow benchmark with a full virtual-TME or patient digital-twin paper.** The scientifically defensible structure is a staged hybrid:

1. **D0 — mandatory provenance and reproduction foundation**  
   Reproduce the selected upstream perturbation-model path and reconstruct a validated Lin-derived TIME observer to the extent permitted by the final supplement, processed object, and available code.

2. **D1 — mandatory, controlling primary analysis**  
   Preserve the current Paper D question: determine whether a frozen perturbation-response model predicts independently measured, held-out perturbation effects in a compatible prostate or prostate-relevant context better than strong simple baselines.

3. **D2-lite — conditional secondary platform and candidate standalone extension**  
   Build a deliberately small, uncertainty-aware, rule-based virtual TME; add learned molecular coupling only after cell-intrinsic prediction and molecular-to-phenotype mappings pass independent validation. D2-lite may generate predeclared combination and sequence hypotheses, but those predictions remain hypothesis-generating unless validated in held-out multicellular data or prospectively in the wet-lab system.

4. **D3 — future PhD programme**  
   Defer patient-specific initialization, schedule optimization, individualized counterfactuals, and any “digital twin” terminology until patient-specific longitudinal, spatial, PK/PD, and prospective validation data exist.

## 1.2 Controlling primary endpoint

Until an eligible independent perturbation benchmark is identified, **the existing D1 primary remains the only defensible controlling primary**:

> Among pre-specified, model-compatible perturbation–context conditions whose training overlap is resolved, does a frozen perturbation model improve replicate-aware prediction of measured expression and programme changes over no-change, perturbed-mean, same-drug context-average, ridge, and nearest-neighbour baselines?

A D2 primary should be considered only after a separate approval gate. The preferred future D2 primary would be one of the following, in descending order of strength:

1. **P4: prospective wet-lab prediction** — preregistered prediction of new tumour–immune functional results;
2. **P3: held-out multicellular outcome** — tumour burden, viable-tumour loss, immune infiltration, composition, or spatial features;
3. **P2: held-out TME-state transition** — only if genuinely independent longitudinal data with compatible treatment, pairing, and clinical labels are available.

Unmeasured combination ranking must not be the primary endpoint.

## 1.3 Why the full D2 concept is not yet identifiable

The principal limitation is not whether PhysiCell can execute. It is whether the proposed biological couplings can be identified and independently tested. At present:

- no verified longitudinal prostate ICI single-cell cohort has been found that can serve as a prostate transition test set;
- the current D audit found no released, model-compatible, independent prostate single-cell chemical-perturbation test object;
- STATE and Tahoe-derived models predict transcriptional states within specific vocabularies and contexts; they do not validate immune-cell behaviour, spatial dynamics, ICI action, or treatment synergy;
- ICI acts primarily through multicellular receptor–ligand and contact-dependent mechanisms and should not be represented as an ordinary tumour-cell drug token;
- the molecular-to-phenotype bridge contains more uncertain mappings than the available data can currently calibrate;
- a multicellular spatial model with many cell types, diffusible fields, and signalling networks would be structurally non-identifiable against the currently available endpoints;
- the Lin study is observational and pan-cancer. It supplies an observer and transition benchmark, not causal control coefficients for prostate treatment simulation.

## 1.4 MSc and publication verdict

| Candidate | MSc suitability | Standalone publication potential | Verdict |
|---|---:|---:|---|
| D1 alone | High if eligible test data exist | Modest to moderate | **Retain as mandatory foundation** |
| D1 + D2-lite with held-out multicellular validation | Moderate | Moderate to high if it beats strong baselines | **Preferred conditional Paper D** |
| D1 + D2-lite + preregistered wet-lab validation | Moderate but demanding | Highest defensible potential | **Best publication design if feasible** |
| Full D2 clinical transition simulator without prospective validation | Low | Weak despite technical complexity | **Do not adopt** |
| D3 patient-specific digital twin | Very low | Future programme only | **Defer** |

## 1.5 Proposed working title

A title should avoid “digital twin” and avoid implying clinical validation. A defensible provisional title is:

> **Benchmarking and Prospectively Testing a Hybrid Prostate Virtual-TME Model for Epigenetic Priming and Checkpoint Interaction**

If no prospective multicellular validation is achieved, use a narrower title:

> **A Validation-Gated Framework for Coupling Single-Cell Perturbation Prediction to Prostate Tumour–Immune Simulation**

---

# 2. Current Paper D audit

## 2.1 Live repository state

**VERIFIED:**

- Main branch commit: `a8278c776da7c6b096cc14139d729979db286b50`.
- Existing branches at review: `main`, `review/evidence-expansion-20260912`, and `review/paper-b-scientific-revision-20260928`.
- No Paper D revision or implementation branch was present.
- Paper D remains represented by the open conditional-benchmark issue and the files under `specs/D/`.
- The current specification is explicitly versioned as an unrun, conditional benchmark and does not claim implementation readiness.
- The historical repository does not contain an identifiable current virtual-TME implementation.

**UNKNOWN:**

- uncommitted or unpublished local work;
- live AIU scheduler jobs and local data caches;
- exact CPU, RAM, GPU, CUDA, storage quota, and queue policy on the intended execution host.

## 2.2 Current scientific question

The live specification asks whether a released virtual-cell model can predict independently measured prostate chemical-perturbation expression changes more accurately than a same-drug response baseline. It correctly limits claims to compatible perturbations and contexts, prohibits unsupported unseen-drug claims, and requires training-overlap and vocabulary checks.

## 2.3 Retain, revise, replace, condition, or remove

| Current element | Decision | Rationale |
|---|---|---|
| Narrow D1 perturbation benchmark | **Retain** | It has a clear estimand, measurable ground truth, and meaningful failure result. |
| Frozen-model evaluation | **Retain** | Prevents test-set adaptation and preserves interpretation. |
| Exact drug–dose/context vocabulary gate | **Retain and strengthen** | Silent unknown-label or global-control fallback invalidates inference. |
| Same-drug and simple baselines | **Retain and expand** | Necessary after Systema and subsequent metric-calibration work. |
| Training-overlap audit | **Retain as mandatory** | Unknown overlap blocks an independent-test claim. |
| Hashes, seeds, environment, output receipts | **Retain** | Required for reproducibility. |
| STATE as the only candidate | **Revise** | Add a task-specific registry including Tahoe-x1+STATE, PIE, and optional comparators; do not assume interchangeability. |
| “Prostate” eligibility based only on a line label | **Revise** | Must include biological context, treatment identity, dose, duration, control, replicate, and training overlap. |
| Global expression accuracy as central evidence | **Revise** | Add perturbation discrimination, programme-level recovery, calibration, and Systema-style metrics. |
| D1 as proof of virtual-TME validity | **Remove** | V1 transcriptional prediction does not validate multicellular behaviour. |
| Lin reproduction | **Add as D0 foundation** | Supplies an empirically anchored observer and external transition target, not novelty. |
| Minimal rule-based PhysiCell model | **Add conditionally** | Serves as the transparent D2 baseline. |
| Learned molecular coupling | **Conditional** | Only after bridge mappings have evidence, calibration data, uncertainty, and held-out tests. |
| Full patient digital twin | **Defer/remove from MSc claims** | Patient-specific calibration and prospective validation are absent. |
| ICI as a tumour-cell chemical token | **Prohibit** | Mechanistically incorrect unless a narrowly defined cell-intrinsic assay supports it. |
| Arbitrary gene-to-behaviour coefficients | **Prohibit** | Produces uninterpretable, non-identifiable simulations. |
| Simulation-only synergy claim | **Prohibit** | Synergy requires a frozen null model and measured combination data. |

## 2.4 Current assets worth preserving

The present specification already contains several high-value controls:

- explicit separation of State Embedding and State Transition;
- model/checkpoint pinning;
- fail-closed handling for unsupported labels;
- controls for unchanged output and global-control fallback;
- replicate-aware rather than cell-as-replicate evaluation;
- acknowledgement that LINCS and existing bulk prostate datasets do not satisfy the native single-cell benchmark;
- no clinical, TME, or unseen-drug overclaim.

These should become the D0/D1 layer of the revised architecture rather than being discarded.

---

# 3. Lin et al. appraisal and reproducibility plan

## 3.1 Verified final-paper facts

The final Cancer Cell article reports:

- 441 samples from 241 patients across ten cancer entities;
- a newly generated paired cutaneous melanoma cohort of 17 patients sampled at day 0 and 6–16 days after anti-PD-1 with or without anti-CTLA-4;
- integration with sequential scRNA-seq data from 15 independent studies;
- a hierarchical reference-guided deep-phenotyping framework;
- 77 immune and stromal subtypes;
- four conserved TIME states;
- approximately 40% of tumours changing TIME state during therapy;
- favourable transitions toward inflamed or B-cell-enriched states and unfavourable persistence/transition toward myeloid dominance;
- a 59-gene baseline signature evaluated in 1,383 baseline tumours across 19 independent cohorts;
- raw Essen cohort data under EGA accession `EGAS50000000459`;
- processed scRNA-seq and Visium data under Zenodo DOI `10.5281/zenodo.19586163`.

The Zenodo v2 record contains:

- `seurat_full.qs2`, 4.0 GB, MD5 `a3486788163889f8cc910ea0115d70ac`;
- Visium outputs for D993, D2398, D2816, and D2989;
- 6.7 GB total deposited files;
- no displayed licence in the record’s rights field.

## 3.2 What remains unresolved

The final article text was indexed, but the complete final supplementary files and a public analysis-code repository could not be retrieved during this review. Therefore the following must remain **UNKNOWN** rather than reconstructed from summaries:

- the exact 15-study roster and per-study accession map;
- exact patient, sample, pair, cancer, regimen, dose, and timepoint counts by source study;
- exact response definitions and adjudication rules per cohort;
- whether and how regimen mixtures, chemotherapy combinations, and neoadjuvant settings were handled;
- the reference atlases and classifiers used for each lineage in the 77-subtype hierarchy;
- exact quality-control, doublet, malignant-cell, integration, normalization, and compositional-analysis methods;
- the mathematical definition of the four TIME states and state assignment uncertainty;
- the exact paired-patient transition estimand;
- spatial validation sample selection and quantitative endpoints;
- the 59-gene feature-selection sequence, tuning, leakage controls, and exact training/test boundaries;
- full patient and cohort independence across the single-cell atlas, bulk derivation set, and 19 validation cohorts;
- final code availability and software version lock;
- the licence governing the Zenodo processed object.

These unresolved items are not minor documentation gaps. They block exact reproduction, independent-test designation, and reuse of the published state observer as if it were a fully specified software component.

## 3.3 Reproduction tiers

### Tier L0 — source resolution

Required before data analysis:

1. obtain final Table S1 and all supplementary methods/tables;
2. resolve every source study, accession, patient ID, sample ID, specimen, regimen, timepoint, and outcome definition;
3. compare final article composition with preprint v3;
4. locate public code or obtain a code-availability statement from the authors;
5. resolve Zenodo licence and downstream redistribution conditions;
6. create a patient/sample overlap ledger against Paper A/A.1 cohorts.

**Gate:** no claim of exact reproduction until L0 is complete.

### Tier L1 — object inventory reproduction

Reproduce:

- total cells, patients, samples, studies, cancers, and paired cases;
- source-native labels and harmonized labels;
- assay/platform and timepoint distributions;
- response and survival label counts;
- missingness and duplicated identifiers.

Agreement criterion: exact counts where the final supplement supplies them; otherwise discrepancy must be explained and frozen.

### Tier L2 — observer reproduction

Reproduce, as permitted:

- broad compartments;
- 77-subtype mapping or a predeclared coarser hierarchy when the object cannot support exact reconstruction;
- sample-level compositions;
- four-state assignment;
- assignment confidence and sensitivity to preprocessing/classification choices.

The observer must be evaluated independently of treatment-outcome analysis. Source-native labels must be preserved.

### Tier L3 — longitudinal transition reproduction

Reproduce:

- paired-patient eligibility;
- pre/on/post ordering;
- state-transition matrix;
- state persistence and transition uncertainty;
- association with response and survival using the patient as the biological unit.

### Tier L4 — bulk and spatial reproduction

Reproduce only after exact methods are available:

- bulk projection/score calculation;
- signature derivation and external-cohort evaluation;
- Visium state localization, neighbourhood, and co-localization analyses.

## 3.4 Role in Paper D

Lin et al. may be used for:

- observer development and stress-testing;
- a versioned TME-state ontology;
- pan-cancer external transition targets;
- favourable/unfavourable transition definitions;
- secondary comparison with the 59-gene signature;
- spatial corroboration methods.

It may not be used as:

- proof that a prostate TME has the same state structure;
- proof that an epigenetic drug causes a favourable transition;
- a causal mapping from expression to agent behaviour;
- a source of universal transition probabilities for prostate cancer;
- an independent test if the same patients or studies are used for observer development or parameter fitting.

## 3.5 Novelty consequence

The following are no longer adequate novelty claims:

- building another pan-cancer longitudinal single-cell atlas;
- defining four or another small number of static TIME states;
- showing that on-treatment change correlates with ICI outcome;
- deriving another baseline transition-associated signature;
- observing inflamed/B-cell enrichment and myeloid resistance.

The defensible extension is prediction and prospective testing of intervention-induced transitions, with explicit uncertainty and no causal claim before experimental confirmation.

---

# 4. Effect on Paper A.1 novelty and ownership

Paper A.1 and Paper D must remain analytically distinct.

| Topic | Paper A.1 ownership | Paper D ownership |
|---|---|---|
| Observed response-by-time effects | Primary | Input/benchmark only |
| Observed treatment-associated programme changes | Primary | Validation target only |
| Pharmacological-context heterogeneity | Primary | Scenario constraints only |
| Observed TIME transitions | Primary where data permit | Observer/held-out target only |
| Prediction of unmeasured transitions | No | Primary D contribution |
| Counterfactual schedule hypotheses | No | Conditional D contribution |
| Mechanistic spatial simulation | No | Conditional D contribution |
| Prospective model prediction | No | Paper D handoff to wet lab |

Lin et al. strengthens A.1 as an external framework but reduces novelty for a purely observational transition atlas. A.1 should quantify observed longitudinal effects with cohort-aware models and may reproduce or compare TIME transition patterns. D should start where observation ends: frozen prediction, calibrated simulation, and prospective hypothesis testing.

A shared observer is acceptable, but the data split and ownership ledger must record whether it was developed, calibrated, or tested in each paper.

---

# 5. Competing Paper D framings

## 5.1 Comparison

| Dimension | D1: perturbation benchmark | D2: hybrid virtual-TME | D3: patient digital twin |
|---|---|---|---|
| Scientific estimand | Held-out molecular perturbation prediction | Held-out multicellular transition/outcome prediction | Patient-specific counterfactual outcome optimization |
| Ground truth required | Independent perturbation expression | Longitudinal, functional, composition, or spatial outcomes | Patient-specific longitudinal multi-modal outcomes and exposure |
| Present data readiness | Low-to-moderate; eligibility unresolved | Low | Very low |
| Parameter burden | Limited | High | Very high |
| Structural identifiability | Potentially manageable | Major risk | Currently unacceptable |
| Wet-lab connection | Indirect unless selected drugs overlap | Direct | Direct but unsupported |
| Novelty | Modest | Potentially strong if validated | High vision, low credibility now |
| MSc scope | Appropriate | Appropriate only as D2-lite | Inappropriate |
| Main failure mode | No eligible independent test set | Model complexity exceeds evidence | “Digital twin” overclaim |
| Recommended status | **Mandatory** | **Conditional** | **Future PhD** |

## 5.2 Challenge to the preliminary preference

The preliminary preference—D0/D1 mandatory, D2 standalone candidate, D3 future—is directionally correct but still too permissive toward D2. D2 should not automatically become the standalone paper merely because D1 runs. Promotion requires all of the following:

1. a reproducible observer;
2. an independent cell-intrinsic benchmark or an explicitly scoped failure result;
3. at least one calibrated pairwise tumour–immune interaction endpoint;
4. programme-to-behaviour mappings with measured protein or functional evidence;
5. a minimal rule-based and nonspatial baseline;
6. held-out multicellular or prospective wet-lab ground truth;
7. global sensitivity and non-identifiability reporting;
8. no leakage between parameter fitting and final evaluation.

Without these, D2 is a methods framework or thesis-only exploratory module, not a validated standalone virtual-TME paper.

---

# 6. Recommended primary question

## 6.1 Current controlling question

**PROPOSED wording, preserving the existing primary:**

> In model-compatible perturbation–context conditions with resolved training overlap, does a frozen single-cell perturbation model predict independently measured prostate or prostate-relevant expression and immune-programme changes more accurately than strong non-learned and linear baselines?

## 6.2 D2 secondary question

> Conditional on a validated state observer and calibrated minimal tumour–immune rules, does coupling frozen perturbation predictions to a spatial agent-based model improve prediction of held-out multicellular outcomes over a nonspatial population model and a minimal rule-only PhysiCell model?

## 6.3 Hypothesis-generating question

> Which predeclared epigenetic-drug and ICI schedules are predicted, within stated uncertainty, to move specified prostate TME archetypes toward response-associated states without unacceptable tumour- or immune-cell toxicity?

This third question cannot carry the primary claim unless matched combination data or prospective experiments test it.

## 6.4 Claim ceiling

Even if D2 passes, the maximum defensible claim before prospective testing is:

> The hybrid model generated calibrated, data-constrained hypotheses that reproduced selected held-out molecular or multicellular features better than pre-specified baselines.

It is not:

- causal control of TIME transitions;
- patient-specific treatment recommendation;
- proof of clinical efficacy;
- proof of synergy;
- a validated digital twin.

---

# 7. Thesis and protocol position

The submitted MSc protocol centres on:

- cross-cancer responder/non-responder programmes;
- evaluation of immune deficits and epigenetic regulation in prostate cancer;
- prioritization of epigenetic modulators;
- prostate-cell molecular validation and, where feasible, immune co-culture.

It does not require a virtual TME or digital twin. Paper D is therefore an added conditional computational contribution. It is thesis-consistent only when it serves the protocol’s biological question and does not delay the required computational and wet-lab deliverables.

## 7.1 Paper boundaries

- **A:** pretreatment ICI response programmes and clinical prediction.
- **A.1:** observed longitudinal response-by-time and pharmacological-context effects.
- **B:** prostate immune deficits, regulatory evidence, composition, localization, and reversible barriers.
- **C:** measured perturbation evidence and pharmacologically constrained epigenetic-drug prioritization.
- **D:** frozen virtual perturbation prediction, multiscale simulation, counterfactual hypotheses, model validation, and prospective predictions.
- **Wet-lab paper:** molecular restoration, protein confirmation, immune-cell effects, tumour–immune interaction, functional response, and combination testing.

## 7.2 Non-duplication rules

- D may import frozen A/A.1/B/C artefacts; it must not silently re-estimate and redefine them.
- D cannot use simulated reversal as a substitute for C’s measured perturbation evidence.
- D cannot use a simulated immune state as a substitute for the wet-lab functional endpoint.
- D cannot claim independent validation on any cohort used to derive A/A.1 programmes or the Lin observer.

---

# 8. Data-source architecture

## 8.1 Required source classes and permitted roles

| Source class | Primary role | Forbidden shortcut |
|---|---|---|
| Observational scRNA-seq | Ontology, initialization, state distributions | Treating cross-sectional differences as treatment effects |
| Longitudinal ICI scRNA-seq | Observer/transition benchmark | Treating cells as independent patients |
| Spatial transcriptomics/protein | Localization, exclusion, neighbourhood validation | Inferring cell–cell function from co-location alone |
| Chemical perturbation scRNA-seq | D1 molecular prediction | Assuming immune or multicellular action |
| Genetic perturbation scRNA-seq | Bridge/mechanism stress-test | Treating gene perturbation as pharmacological equivalence |
| Cytokine perturbation scRNA-seq | IFN/cytokine-state mapping | Applying one cell type’s response universally |
| Bulk perturbation | External direction/program corroboration | Calling it single-cell validation |
| Protein/functional perturbation | Programme-to-behaviour calibration | Inferring function from RNA alone |
| Combination-therapy data | Interaction and sequence validation | Calling additive simulation “synergy” |
| Tumour-growth/immune-killing data | ABM calibration and held-out test | Fitting and testing on the same experiment |
| Prospective wet-lab data | Frozen final prediction test | Updating the model before reporting the prospective result |

## 8.2 Candidate source-role matrix

| Source | Verified content | Proposed role | Independence warning |
|---|---|---|---|
| Lin et al. final + Zenodo | Pan-cancer longitudinal ICI scRNA, four TIME states, spatial objects | Observer reproduction; pan-cancer transition target | Observer development and test sets must be separated; Paper A/A.1 overlap must be audited |
| Kiviaho et al. prostate scRNA/spatial atlas | Cross-sectional localized, treated, CRPC, and benign prostate states | Prostate ontology, archetype initialization, spatial validation | Not a longitudinal ICI test set |
| Arc scBaseCount | Large observational repository with standardized processing | Discovery, source resolution, optional representation inputs | Study-level labels can propagate to controls; training overlap likely |
| Tahoe-100M | 100.6M cells, 1,344 samples, cancer cell lines, chemical perturbations | Chemical benchmark and training-overlap audit | 24-hour cancer-cell-line domain; no immune cells, ICI interaction, or spatial TME |
| STATE | Frozen transcriptional state-transition candidate | D1 predictor | Checkpoint/context/drug/dose vocabulary and fallback behaviour must pass |
| Tahoe-x1 | Representation foundation model; transition use requires post-training/state-transition layer | Optional representation or coupled predictor | Tx1 alone is not a validated universal perturbation simulator |
| PIE | Released unseen-context/perturbation predictor with pinned splits and knowledge sources | Candidate comparator if chemical task compatibility is verified | New release; chemical/prostate role and model licence require checkpoint-specific audit |
| Systema | Perturbation-specific evaluation framework | Metrics and strong baselines | Developed primarily for genetic perturbations; adapt carefully to chemical tasks |
| TISMO | Uniform bulk in-vitro/in-vivo immunotherapy model resource | External immune-programme corroboration | Mostly murine/bulk; not human prostate single-cell validation |
| Perturb-CITE-seq melanoma co-culture | Genetic perturbations with RNA/protein in immune pressure | Bridge stress-test for immune evasion behaviours | Cancer/context and perturbation modality differ from prostate drugs |
| Planned AIU wet lab | Prostate molecular and tumour–immune functional assays | Prospective D validation | Assays, cell source, reagents, and endpoints must be frozen before model reveal |

## 8.3 Source record contract

Every source object must contain:

- source record ID and immutable version;
- publication and originating experiment;
- repository, accession, release, checksum, and retrieval date;
- access conditions and exact licence;
- patient/donor/model, cancer, disease state, specimen, cell line, and cell type;
- treatment generic name, salt/form, concentration, unit, duration, sequence, and control;
- modality, feature space, identifiers, normalization, and preprocessing;
- biological N, replicate unit, plate/batch, and cells per unit;
- patient/sample/specimen/assay identity graph;
- known/possible model training overlap;
- allowed roles: training, adapter, calibration, development, final test, external corroboration, parameter prior;
- limitations and claim ceiling;
- gate status G0–G10.

## 8.4 Data-validation gates

| Gate | Requirement | Failure consequence |
|---|---|---|
| G0 source discovered | Candidate located | No eligibility claim |
| G1 original study resolved | Publication, experiment, object, and accession linked | Cannot use source |
| G2 measurement validated | Platform, units, identifiers, normalization, controls known | No quantitative comparison |
| G3 perturbation identity validated | Drug/form/concentration/duration/schedule/control exact | No perturbation benchmark or parameterization |
| G4 biological unit validated | Patient/donor/experiment/plate/replicate/cell nesting known | No valid uncertainty or inference |
| G5 ontology compatible | Source-native labels mapped with confidence | No forced fine-state analysis |
| G6 model compatible | Genes, transform, context, perturbation vocabulary, output match | Inference fails closed |
| G7 training overlap resolved | Training/development/independent/unknown assigned | Unknown cannot be called independent test |
| G8 benchmark role approved | Training/calibration/development/final-test role frozen | No final-test access |
| G9 parameterization approved | Parameter, units, uncertainty, source, calibration target specified | Cannot drive simulation |
| G10 prospective validation approved | Contrast, output, assay, and success/falsification criteria frozen | No prospective claim |

A source may pass one role and fail another. For example, Tahoe-100M may pass G2–G6 for a supported cancer-cell-line chemical benchmark while failing as an immune-cell, ICI, combination, or multicellular validation source.

## 8.5 Split and overlap architecture

Separate ledgers are required for:

- model pretraining;
- model post-training/fine-tuning;
- observer development;
- adapter development;
- parameter calibration;
- model selection;
- final retrospective test;
- prospective wet-lab test.

The highest independent unit governs splitting. All cells from one patient, donor, experimental replicate, plate, or source study remain together as appropriate. Random cell splits cannot support patient, study, cell-line, drug, or context generalization claims.

---

# 9. Virtual-cell model appraisal

## 9.1 STATE

**Verified strengths**

- separates State Embedding from State Transition;
- supplies released checkpoints for observational and perturbational tasks;
- supports AnnData-based training and inference;
- supplies Cell-Eval compatibility;
- has explicit code and model-use licences;
- supports chemical, genetic, and signalling tasks through separate data/configuration paths.

**Critical limitations**

- task support is checkpoint-specific, not universal;
- context generalization may include partial target-context perturbations in training and must not be mislabeled zero-shot;
- drug, dose, cell context, control, feature map, and transform must match exactly;
- transcriptional output is not a validated cell-behaviour prediction;
- no evidence was found that an ICI antibody is a valid tumour-cell perturbation token;
- unknown-label and global-control fallback risks require fail-closed tests;
- code is CC BY-NC-SA and model use is subject to a non-commercial licence and acceptable-use restrictions.

**Decision:** retain as the first D1 candidate because the existing specification is already designed around it, but evaluate it as one registered model, not as the definition of “virtual cell.”

## 9.2 Tahoe-x1

**Verified strengths**

- released 70M, 1.3B, and 3B checkpoints;
- pretrained on large observational and perturbational corpora;
- code is Apache-2.0;
- provides representation-learning and state-transition post-training resources.

**Critical limitations**

- the foundation model and Tahoe-100M dataset are distinct objects;
- only the 3B checkpoint was described as having a chemical token in the reviewed documentation;
- perturbation prediction is not established by the embedding model alone; the published workflow couples embeddings to a State Transition post-training layer;
- no verified direct zero-shot unseen-compound generator, ICI-antibody mechanism, or combination predictor was found;
- full training of the 3B model is scientifically unnecessary and computationally unjustified for this MSc;
- checkpoint-specific weight licence and permissible downstream use must be recorded separately from the code licence.

**Decision:** do not train from scratch. Consider released inference or a smaller representation model only if it adds a pre-specified comparison that STATE alone cannot answer.

## 9.3 PIE

PIE was released after the current Paper D specification and therefore changes the landscape. It is designed to generalize perturbation effects across unseen contexts and perturbations using a Perceiver-IO architecture, curated knowledge sources, control-state information, and perturbation evidence. The official recipes publish datasets, knowledge sources, splits, and checkpoints and include within- and cross-dataset evaluations.

Limitations for Paper D:

- the currently highlighted evidence is heavily genetic-perturbation and Replogle-oriented;
- exact chemical, prostate, dose, and ICI suitability must be audited before inclusion;
- output remains molecular, not multicellular or spatial;
- official cross-dataset training is resource-intensive, although released checkpoints reduce that burden;
- the code is non-commercial share-alike, and the checkpoint/model licence must be recorded.

**Decision:** add PIE to `MODEL_REGISTRY.md` as a candidate comparator. It does not automatically replace STATE.

## 9.4 scGPT, Geneformer, scFoundation, RegFormer, Nicheformer, and related models

These models are important landscape references but should not be included merely to create a large model comparison.

- scGPT, Geneformer, and scFoundation are general single-cell foundation models with downstream perturbation or representation tasks; they require task-specific adaptation and may have substantial pretraining overlap.
- RegFormer adds regulatory priors and reports genetic-perturbation and drug-response tasks, but its published drug response is not equivalent to generating post-treatment single-cell distributions in prostate co-culture.
- Nicheformer is relevant to spatial representations but is not a treatment-response simulator.

**Decision:** include a model only when its output contract matches a frozen endpoint and it can be evaluated fairly under the same information conditions. Otherwise cite it in the novelty review and exclude it from implementation.

## 9.5 Evaluation implication from Systema and later metric-calibration work

Systema demonstrated that simple perturbed-mean or matching-mean baselines can match complex models under common metrics and that systematic treatment-versus-control variation can inflate performance. A subsequent 2026 analysis argues that some metrics are themselves poorly calibrated and that deep models can outperform uninformative baselines when positive controls and calibrated metrics are used.

Therefore Paper D must do both:

1. include strong simple baselines and perturbation-specific references;
2. include positive-control or data-ceiling analyses demonstrating that the metric can detect a genuinely informative prediction.

The paper must not pre-decide that deep models fail or succeed. The benchmark should be designed so either outcome is interpretable.

---

# 10. Tahoe-100M and Tahoe-x1 appraisal

## 10.1 Tahoe-100M verified properties

- 100,648,790 cells and 1,344 samples in the official Arc atlas documentation;
- cancer-cell-line chemical perturbation design;
- metadata including plate, sample, drug, drug-plus-concentration, cell line, and cell name;
- approximately 379 drugs at three concentrations plus vehicle in the released model vocabulary reviewed by the current D audit;
- 24-hour exposure in the primary study;
- cancer-cell lines rather than a multicellular immune TME;
- data available through the Arc Virtual Cell Atlas/Google Cloud Marketplace and Hugging Face releases;
- Hugging Face dataset metadata reports CC0-1.0, while access and egress terms must still be recorded.

## 10.2 What Tahoe-100M cannot establish

It does not, by itself, validate:

- immune-cell drug responses;
- antibody checkpoint blockade;
- contact-dependent killing;
- fibroblast exclusion;
- myeloid polarization;
- longitudinal patient transitions;
- combination or sequence effects;
- clinical response;
- an unmeasured duration outside the 24-hour design.

## 10.3 Prostate eligibility

The exact prostate-line coverage, compounds, concentrations, plates, replicates, and checkpoint training status must be queried from the current metadata release. A cell-line name alone is insufficient. Eligibility requires:

- relevant prostate cell context;
- treatment matching a Paper C/wet-lab candidate;
- supported concentration and 24-hour timing;
- adequate biological or plate replication;
- independent measurement object not used by the evaluated checkpoint;
- sufficient genes and transform compatibility.

The current D audit found no released zero-shot prostate context satisfying all conditions. This remains a **BLOCKER**, not evidence that no such condition can ever be constructed.

---

# 11. PhysiCell/PhysiBoSS appraisal

## 11.1 Capability

PhysiCell supplies the required software primitives:

- three-dimensional off-lattice agents;
- BioFVM diffusion;
- mechanics, adhesion, migration, proliferation, death, contact interactions, immune attack, and phagocytosis;
- treatment schedules, random seeds, restartable simulations, and structured outputs;
- rules-based phenotype control;
- parallel parameter sweeps.

The latest stable release identified during review was PhysiCell 1.14.2. PhysiBoSS 2.2.3 couples PhysiCell to MaBoSS stochastic Boolean networks.

## 11.2 Scientific appraisal

The software is not the limiting factor. The limiting factors are:

- parameter source quality;
- unit consistency;
- context transfer;
- independent calibration endpoints;
- structural identifiability;
- validation against held-out multicellular data.

## 11.3 Decision

Begin with a **minimal rule-based PhysiCell model**, not PhysiBoSS. Add a Boolean/ODE intracellular network only if:

1. the network controls a pre-specified endpoint;
2. its nodes and logic are supported in the specific cell type;
3. parameter/state uncertainty is represented;
4. it improves held-out prediction over the simpler rule model.

A detailed signalling network in every agent would increase complexity without necessarily increasing predictive validity.

---

# 12. Recommended hybrid architecture

## Layer 0 — provenance and split controller

Controls source versions, licences, overlap, hashes, roles, and test-set access. No downstream layer may read an object that has not passed the relevant gates.

## Layer 1 — state observer

Inputs:

- source-native single-cell or spatial data;
- frozen ontology version;
- validated feature/programme definitions.

Outputs:

- broad compartment and major-cell-type probabilities;
- optional compatible fine subtype;
- tumour and immune programme scores;
- continuous TME-state probabilities;
- composition and transition labels with uncertainty.

The observer is separately evaluated for classification, calibration, robustness, and study transfer.

## Layer 2 — cell-intrinsic perturbation engine

Supports only registered combinations of:

- model/checkpoint;
- feature map and transform;
- cell context;
- perturbation modality;
- drug identity and concentration;
- duration/control convention.

Outputs molecular distributions or pseudobulk effects, not agent behaviours.

## Layer 3 — molecular-to-phenotype bridge

A versioned translation table maps programme-level molecular changes to uncertain behaviour parameters. Every mapping has evidence, units, context, function, prior, calibration source, validation source, and claim limit.

## Layer 4 — minimal multicellular simulator

Initial D2-lite populations:

1. malignant prostate cells;
2. CD8 effector/exhausted T cells represented as one population with a state variable;
3. suppressive myeloid/macrophage cells;
4. fibroblast/stromal barrier cells.

Optional DC, B/TLS, Treg, endothelial, or NK populations are admitted only when their addition improves a pre-specified held-out endpoint and has independent calibration data.

Initial fields:

- oxygen;
- one CXCL9/10-like immune-recruitment field;
- one treatment-exposure field **or** an IFN-γ field, not both unless supported.

## Layer 5 — treatment and schedule engine

Represents:

- vehicle;
- epigenetic agent alone;
- ICI alone in immune-functional contexts;
- concurrent combination;
- epigenetic priming followed by ICI;
- reverse sequence;
- only pre-approved additional combinations.

## Layer 6 — validation and interpretation

Produces:

- comparison with strong baselines;
- uncertainty intervals and sensitivity ranks;
- failure receipts;
- explicit validation level V0–V8;
- permitted conclusion and prohibited extrapolations.

## Architecture principle

Success in one layer cannot compensate for failure in another. A good RNA prediction cannot validate a killing rule; a calibrated ABM cannot repair an invalid observer; a visually plausible spatial trajectory is not evidence of clinical validity.

---

# 13. State ontology

## 13.1 Versioned hierarchy

1. **Compartment:** malignant, T/NK, B/plasma, myeloid, dendritic, stromal, endothelial.
2. **Major cell type:** tumour, CD8 T, CD4/Treg, macrophage/monocyte, DC, B/plasma, fibroblast, endothelial, etc.
3. **Fine subtype:** only where source resolution and classifier confidence support it.
4. **Functional programme:** activation, exhaustion, antigen presentation, IFN response, suppressive myeloid, stromal exclusion, TLS/B-cell programme, proliferation, stress, apoptosis.
5. **Tumour programme:** prostate lineage, AR state, antigen-presentation deficit, IFN competence, epigenetic suppression, stress/cytotoxicity.
6. **TME archetype:** probabilistic state assignment rather than forced label.
7. **Transition:** change in continuous state probabilities plus optional discrete label.

## 13.2 Mapping confidence

- exact;
- compatible;
- broader parent;
- ambiguous;
- unsupported.

Source-native labels are never overwritten. A transcriptomic programme is not called a functional behaviour unless protein or functional evidence supports that interpretation.

## 13.3 Recommended prostate archetypes

Use cohort-level archetypes, not patient digital twins:

- immune-quiescent;
- myeloid-dominant;
- inflamed;
- B-cell/TLS-enriched;
- stromal/excluded.

These labels must be derived from prostate data and compared with, not simply copied from, Lin TIME states. Disease-state strata—localized untreated, metastatic, castration-sensitive, castration-resistant, and prior-treatment context—should remain metadata or separate initialization families unless data support joint archetypes.

---

# 14. Molecular-to-phenotype bridge

## 14.1 Why this is the most vulnerable layer

Expression effects are not behaviours. The same transcriptomic change may have different consequences by cell type, protein abundance, receptor occupancy, exposure, metabolic state, and spatial context. The bridge is therefore a formal model component that requires its own validation.

## 14.2 Required mapping record

Each mapping must contain:

- mapping ID and version;
- recipient cell type and disease context;
- molecular programme, genes/proteins, and assay modality;
- expected direction and temporal window;
- source evidence tier;
- measured versus model-predicted status;
- mathematical mapping function;
- target behaviour and unit;
- prior/range and uncertainty distribution;
- calibration data and final-test data;
- sensitivity rank and identifiability status;
- supported extrapolation domain;
- permitted claim and falsification criterion.

## 14.3 Initial behaviours eligible for consideration

Only programme-level mappings with evidence should be considered:

- tumour proliferation and apoptosis;
- antigen presentation/recognition competence;
- IFN responsiveness;
- CXCL9/10-like recruitment signal;
- PD-L1 abundance as a modulatory—not efficacy—readout;
- tumour susceptibility to antigen-specific killing;
- T-cell activation/exhaustion balance;
- myeloid suppression or phagocytic state;
- stromal migration barrier.

## 14.4 Prohibited mapping patterns

- one RNA gene directly assigned to one behavioural coefficient without validation;
- a model-importance score converted to a mechanistic rate;
- a mouse effect size copied to human prostate without uncertainty and context qualification;
- tumour-cell drug response imposed on immune cells;
- RNA change interpreted as surface protein or functional killing;
- parameter fitting and validation on the same endpoint.

## 14.5 Staged calibration

1. molecular perturbation;
2. tumour-cell phenotype;
3. immune-cell phenotype;
4. pairwise tumour–immune interaction;
5. four-population composition/spatial behaviour;
6. treatment response.

Weakly identified parameters must remain uncertainty ranges and must not be interpreted biologically.

---

# 15. Prostate-TME initialization

## 15.1 Recommended level

Start with **cohort archetypes**. Patient-specific initialization is not approved.

## 15.2 Inputs

Each initialization record should include:

- prostate disease and treatment state;
- source studies and sample inclusion;
- cell-type proportion distributions;
- tumour programme distributions;
- immune activation/exhaustion distributions;
- spatial organization summary;
- stromal barrier geometry or proxy;
- tumour burden and domain geometry;
- oxygen/nutrient boundary assumptions;
- chemokine/cytokine initial conditions;
- uncertainty and alternative initialization ensembles.

## 15.3 Data-source principle

No single atlas should define every parameter. For example:

- prostate scRNA may inform composition and programmes;
- prostate spatial data may inform neighbourhood and exclusion metrics;
- functional co-culture may inform killing and activation;
- literature may define broad prior ranges;
- prospective AIU data may test rather than retroactively determine final predictions.

## 15.4 Initialization validation

Before treatment simulation, the untreated model must reproduce pre-specified baseline features over an ensemble of seeds:

- stable cell counts within expected stochastic range;
- composition distributions;
- tumour growth or viability trajectory;
- immune infiltration/exclusion summary;
- spatial neighbourhood metrics;
- programme/state observer outputs.

If the untreated system is not valid, treatment comparisons are uninterpretable.

---

# 16. ICI mechanism model

## 16.1 Mechanistic representation

ICI should enter the model through immune–tumour or immune–APC interactions, not as a generic tumour-cell transcriptomic perturbation. For anti-PD-1/PD-L1, candidate effects include:

- modifying the probability that a recognized contact becomes productive;
- modifying killing rate or duration conditional on antigen/HLA recognition;
- modifying T-cell persistence or exhaustion-state transition;
- modifying suppression imposed by PD-1/PD-L1 engagement.

For anti-CTLA-4 and anti-LAG-3, distinct mechanisms and contexts are required. They cannot share a single “ICI strength” coefficient.

## 16.2 Required controls

- no immune cells;
- tumour cells alone;
- immune cells alone;
- antibody isotype;
- no-antigen or HLA-blocking condition where relevant;
- baseline antigen/HLA competence;
- no-checkpoint-ligand or low-ligand sensitivity analysis.

## 16.3 Claim ceiling

The current planned wet-lab protocol correctly recognizes that an antibody cannot establish efficacy in tumour monoculture. Paper D should mirror this: ICI simulation is eligible only in a defined immune-functional system.

---

# 17. Epigenetic-drug mechanism model

## 17.1 Representation

Epigenetic agents should be represented through source-supported, cell-type-specific programme effects constrained by Paper C pharmacology and measured exposure. Candidate tumour-cell pathways include:

- antigen processing and presentation;
- IFN response and viral-mimicry-related programmes;
- chemokine secretion;
- checkpoint-ligand induction;
- proliferation, apoptosis, and stress.

Immune-cell effects require separate evidence for:

- viability;
- activation/exhaustion;
- suppressive function;
- differentiation;
- cytokine secretion.

## 17.2 Critical caution

Epigenetic drugs are not uniformly immune activating. Their effects vary by compound, target, concentration, duration, schedule, and cell type. A favourable tumour-cell programme can coexist with immune-cell toxicity or compensatory checkpoint induction.

## 17.3 Parameter contract

Each effect must retain:

- generic and formulation identity;
- concentration and exposure unit;
- duration and washout;
- sequence relative to ICI and immune-cell addition;
- recipient cell type;
- measured versus predicted status;
- target engagement evidence;
- uncertainty and extrapolation limit.

Commercial tablet availability is not equivalent to a research-grade, identity-verified, sterile, cell-culture-ready reagent. The prospective wet-lab handoff must distinguish in-stock, ordered, accessible, and proposed compounds.

---

# 18. Combination and sequence design

## 18.1 Bounded initial registry

The first release should contain only:

1. vehicle/control;
2. one selected epigenetic agent alone;
3. one selected ICI alone;
4. concurrent combination;
5. epigenetic priming then ICI;
6. ICI then epigenetic agent.

A second epigenetic agent or ICI is admitted only after the first scenario family passes calibration and has a realistic wet-lab route.

## 18.2 Scenario record

- scenario ID/version;
- tumour archetype and cell model;
- immune source/context;
- compounds, targets, formulation, and mechanism;
- concentration/exposure profile;
- start/stop times, washout, and sequence;
- evidence source and unsupported assumptions;
- outputs and validation level;
- null model;
- status: simulated, retrospectively tested, prospectively frozen, prospectively tested;
- permitted conclusion.

## 18.3 Synergy

A simulated combination effect is not synergy. A synergy claim requires:

- pre-specified null model;
- matched doses and timing;
- measured single-agent and combination outcomes;
- uncertainty at the correct biological unit;
- no post hoc selection of the best null model.

For the planned wet-lab factorial, the most biologically relevant primary analysis is the **epigenetic-priming × anti-PD-1 interaction**, not simply whether the combination arm has the largest mean.

---

# 19. Primary-endpoint alternatives

| Endpoint | Strength | Current feasibility | Recommendation |
|---|---|---:|---|
| P1: cell-intrinsic perturbation accuracy | Direct independent molecular ground truth | Conditional on data discovery | **Current primary** |
| P2: TME-state transition prediction | Clinically anchored | No verified prostate ICI transition test set | Secondary/pan-cancer only for now |
| P3: multicellular outcome prediction | Directly tests D2 | Requires held-out functional/spatial data | Preferred D2 retrospective primary |
| P4: prospective wet-lab prediction | Strongest anti-overfitting evidence | Requires final experimental system and preregistration | Preferred confirmatory primary if feasible |
| Unmeasured combination ranking | Weak | Easy to simulate, hard to validate | Never primary |

## 19.1 P1 estimand

Unit: perturbation–context condition summarized over biological/plate replicates.  
Target: measured post-treatment effect relative to matched control.  
Primary contrast: registered model versus same-drug context-average or strongest pre-specified baseline.  
Secondary: perturbation discrimination, programme direction, pathway recovery, calibration, and failure analysis.

## 19.2 P2 estimand

Unit: paired patient.  
Target: follow-up continuous TIME-state probabilities and/or transition class.  
Primary contrast: hybrid model versus baseline persistence and empirical/Markov transition models.  
Restriction: no prostate-specific claim without prostate data.

## 19.3 P3 estimand

Unit: independent experiment/donor/model condition.  
Target: viable tumour burden, killing, composition, infiltration, or spatial metric.  
Primary contrast: learned hybrid model versus nonspatial and minimal-rule baselines.

## 19.4 P4 estimand

Unit: preregistered biological replicate/donor experiment.  
Target: direction and magnitude interval for a frozen molecular or functional contrast.  
Model update: prohibited until the prospective result and discrepancy analysis are archived.

---

# 20. Required baselines

## 20.1 Cell-intrinsic

- no change;
- control mean;
- global perturbed mean;
- same-drug mean across other contexts;
- same-context mean across other drugs;
- linear/ridge model;
- nearest-neighbour context or perturbation;
- positive-control/data-ceiling estimate from replicate splits.

## 20.2 TME transitions

- remain in baseline state;
- empirical overall transition matrix;
- cancer-specific transition matrix;
- baseline composition-only logistic model;
- simple Markov model;
- longitudinal mixed model where appropriate.

## 20.3 Multicellular/spatial

- nonspatial population ODE or count model;
- untreated observed baseline composition;
- minimal rule-only PhysiCell;
- ablations removing each learned bridge component;
- spatially randomized or barrier-free comparator where biologically justified.

## 20.4 Combination

- additive single-agent effect;
- one pre-specified pharmacological null such as Bliss only when the endpoint and design justify it;
- rule-based non-interactive schedule model.

Complex models must not receive more information than baselines. Baseline hyperparameters and source access must be symmetrical.

---

# 21. Calibration strategy

## 21.1 Parameter registry

Each parameter record includes:

- name, component, and unit;
- prior/range and distribution;
- source and evidence tier;
- calibration dataset and held-out dataset;
- transformation and mapping function;
- posterior/accepted ensemble;
- uncertainty and identifiability class;
- global sensitivity rank;
- frozen version and hash.

## 21.2 Staged calibration

1. validate cell-intrinsic molecular effects;
2. calibrate tumour-cell proliferation/death and target engagement;
3. calibrate immune-cell viability/activation separately;
4. calibrate pairwise contact/killing/recruitment;
5. calibrate untreated multicellular composition/spatial organization;
6. calibrate treatment response;
7. lock parameters before final test.

## 21.3 Methods

Candidate methods include:

- likelihood-free/approximate Bayesian computation;
- ensemble rejection/importance weighting;
- Bayesian optimization for bounded calibration;
- surrogate models for expensive simulations;
- Sobol/Morris or another justified global sensitivity method.

No method can rescue insufficient observables. Parameters that remain practically or structurally non-identifiable must be reported as such and propagated as uncertainty.

---

# 22. Validation ladder

| Level | Question | Minimum evidence |
|---|---|---|
| V0 | Does official upstream software reproduce? | Pinned environment, official fixture, expected output/hash/tolerance |
| V1 | Does the model predict held-out molecular effects? | Independent compatible conditions; strong baselines; replicate-aware uncertainty |
| V2 | Does it transfer across context/study? | Held-out context/study/cell line with overlap audit |
| V3 | Does the observer recover known cell/TME states? | Source-native labels, calibration, external-study transfer |
| V4 | Does the simulator predict composition/programmes? | Held-out biological units; baseline comparison |
| V5 | Does it predict spatial features? | Neighbourhood/infiltration/exclusion metrics in held-out spatial data |
| V6 | Does it predict longitudinal transitions? | Paired patients; no cell-level pseudoreplication |
| V7 | Does it predict combination response? | Matched single-agent/combination data and frozen null |
| V8 | Does it predict new wet-lab results? | Preregistered frozen predictions and independent experiment |

A model passing V0/V1 must not be called a validated virtual TME. A defensible “validated hybrid virtual-TME” label requires at minimum V3 plus a relevant V4 or V5 and an independently tested treatment endpoint; V8 is strongly preferred.

---

# 23. Uncertainty and identifiability

## 23.1 Uncertainty classes

Report separately:

- measurement uncertainty;
- biological heterogeneity;
- sampling uncertainty;
- foundation-model/checkpoint uncertainty;
- stochastic simulation uncertainty;
- parameter uncertainty;
- structural-model uncertainty;
- ontology/observer uncertainty;
- domain-shift uncertainty;
- training-overlap uncertainty.

## 23.2 Required outputs

- ensemble rather than single trajectories;
- prediction intervals or accepted-parameter ranges;
- seed-to-seed variability;
- observer probability rather than only hard state;
- sensitivity ranks;
- alternative structural-model results;
- calibration and reliability plots where applicable;
- explicit “unknown overlap” category.

## 23.3 Biological unit

Cells are subsamples, not independent patients or experiments. Uncertainty for clinical or experimental claims must be estimated at patient, donor, experiment, plate, or cell-line-condition level as appropriate.

---

# 24. Wet-lab handoff

## 24.1 Existing protocol constraints

The current internal protocol identifies:

- PC3 and 22Rv1 as molecular discovery models;
- HLA-A*02-positive/PSMA-positive LNCaP as the antigen-specific functional target;
- DU145 as optional validation;
- decitabine, entinostat, and tazemetostat as the principal protocol drug classes;
- a primary epigenetic-priming × anti-PD-1 factorial;
- specific viable-tumour loss at 48 hours as the primary functional endpoint;
- HLA blocking as essential to establish antigen-restricted recognition;
- a four-donor pilot and six-donor target if feasible.

The protocol also warns that allogeneic or HLA-mismatched killing cannot be interpreted as tumour-antigen-specific checkpoint sensitization.

## 24.2 D-to-wet-lab prediction packet

Each frozen handoff must include:

- exact tumour model and qualification criteria;
- immune-cell source and HLA/antigen context;
- research-grade intervention identity;
- concentration range and rationale;
- priming, washout, immune-cell addition, antibody, and readout schedule;
- predicted molecular programme changes;
- predicted protein/surface changes;
- predicted functional effect with interval;
- control and falsification arms;
- minimal qPCR, protein/flow, and functional readouts;
- expected positive, null, opposite, and toxic outcomes;
- interpretation of contradiction;
- model version, input hash, parameter hash, and prediction freeze timestamp.

## 24.3 Minimum functional design

- vehicle;
- epigenetic drug alone;
- ICI alone;
- priming then ICI;
- concurrent combination if resources permit;
- tumour-only controls;
- immune-only controls;
- isotype control;
- HLA-blocking/antigen-specificity control.

ICI success cannot be claimed from tumour monoculture. RNA restoration alone supports molecular priming, not immunotherapy sensitization.

## 24.4 Inventory caveat

The supplied procurement list and prior discussion do not constitute a fully reconciled inventory. Ordered, locally available, commercially obtainable, and physically in-stock research-grade materials must be distinguished. PC3 ordering, flow-cytometer configuration, immune-cell source, antibody receipt, research-grade epigenetic reagents, and assay-compatible controls remain readiness items.

---

# 25. Gene/readout panel architecture

## 25.1 Decision at this stage

No final gene list should be frozen during scientific framing. Final entries require:

- frozen Paper A/A.1 programmes;
- Paper B prostate direction and regulatory evidence;
- Paper C measured perturbation direction and pharmacology;
- verified Lin signature derivation and independence;
- cell-type attribution;
- protein/functional evidence;
- compatibility with the selected wet-lab model and instruments.

## 25.2 Four required panels

### Panel T — tumour-cell epigenetic priming

Purpose: molecular restoration, target engagement, antigen presentation, IFN competence, chemokine output, checkpoint regulation, toxicity/stress, and proliferation/apoptosis controls.

### Panel I — immune-cell epigenetic priming

Purpose: determine whether the selected epigenetic exposure improves, impairs, or redirects CD8, CD4/Treg, myeloid, DC, and optional B-cell states.

### Panel R — ICI-success/favourable-transition

Purpose: assess whether the co-culture moves toward a frozen response-associated state using independent A/A.1/Lin and functional evidence.

### Panel F — failure/resistance

Purpose: detect myeloid dominance, immune quiescence, stromal exclusion, exhaustion, compensatory checkpoint induction, stress, and treatment toxicity.

## 25.3 Panel-entry contract

Each entry requires:

- gene/protein and stable identifier;
- cell type and programme;
- expected direction and timing;
- A/B/C/D/Lin provenance;
- observed versus predicted status;
- evidence tier and independent sources;
- qPCR suitability;
- flow/Western suitability;
- functional relevance;
- alternative explanations;
- positive/negative controls;
- confidence and removal criterion.

## 25.4 Panel releases

For each of T/I/R/F produce:

1. extended discovery panel;
2. minimal qPCR panel;
3. protein/flow/Western panel;
4. functional assay mapping.

A gene is not selected solely because it has high model importance. RNA is not treated as protein or function.

---

# 26. Revised figure plan

## Figure 1 — evidence and architecture

**Question:** what is measured, learned, assumed, simulated, and prospectively tested?  
**Content:** Lin observer; prostate mapping; A/A.1/B/C interfaces; source-role matrix; overlap ledger; architecture; train/calibration/test separation.  
**Unit:** source study, patient, and model object.  
**Conclusion ceiling:** design and provenance only.

## Figure 2 — D1 cell-intrinsic benchmark

**Question:** does a frozen model recover perturbation-specific effects beyond simple baselines?  
**Content:** eligibility flow; model/baseline comparison; data ceiling; programme-level accuracy; calibration; failure cases; training-overlap strata.  
**Unit:** independent perturbation–context condition/replicate.  
**Conclusion ceiling:** molecular prediction in the tested domain.

## Figure 3 — D2-lite multicellular validation

**Question:** does learned coupling improve held-out multicellular/spatial prediction over minimal models?  
**Content:** four-cell-type model; fields; calibrated interactions; nonspatial and rule-only baselines; predicted versus observed outcomes; sensitivity/non-identifiability.  
**Unit:** independent experiment/donor/model condition.  
**Conclusion ceiling:** tested multicellular endpoints only.

## Figure 4 — bounded sequence hypotheses and prospective handoff

**Question:** which predeclared schedules merit experimental testing and what would falsify them?  
**Content:** scenario registry; archetype heterogeneity; uncertainty; frozen T/I/R/F assay architecture; prospective experiment and claim ceiling.  
**Conclusion ceiling:** hypothesis nomination unless prospective results are available.

No result panel should be generated before its analysis release. Each panel record must specify question, source, unit, model, comparator, uncertainty, validation level, and permitted conclusion.

---

# 27. Compute and resource feasibility

## 27.1 Verified repository documentation

The current AIU environment documentation records system Python 3.10.12, an `omics-py` Python 3.11.16 environment, R 4.5.3, and a simple per-GPU job helper. It does not establish the exact execution-node CPUs, RAM, GPU model/VRAM, CUDA, storage, scheduler quotas, or current jobs.

## 27.2 Feasible first operations

Likely low-to-moderate resource tasks, after environment verification:

- source metadata and overlap audits;
- Zenodo object inventory;
- official STATE/Cell-Eval smoke tests;
- pseudobulk baselines;
- observer development on stratified subsets;
- minimal PhysiCell CPU runs;
- small parameter sweeps and surrogate prototypes.

## 27.3 Prohibited or approval-required operations

- full Tahoe-x1 3B training;
- large multi-node fine-tuning;
- indiscriminate download of the full Arc Virtual Cell Atlas;
- large all-combination simulations before scenario gating;
- fitting thousands of ABM parameters simultaneously.

## 27.4 Compute readiness gate

Before implementation record:

- host/cluster and scheduler;
- CPU cores and RAM per job;
- GPU model, count, VRAM, driver, and CUDA;
- local/scratch/project storage and egress constraints;
- container/runtime;
- checkpoint sizes and expected runtime from a small tracer;
- licence compatibility;
- cost and quota approval.

Arc VCA access now uses a requester-pays Marketplace bucket; the exact prefix size must be checked before transfer. A root-bucket sync is prohibited.

---

# 28. Risks and blockers

## 28.1 Critical blockers

| Blocker | Consequence | Resolution |
|---|---|---|
| Final Lin supplement/code not resolved | No exact observer/signature reproduction | Retrieve supplement/code or obtain author clarification |
| Zenodo data licence not displayed | Reuse/redistribution uncertainty | Resolve with Zenodo metadata/authors/institution |
| No eligible independent prostate perturbation test object | D1 cannot run as specified | Systematic source search; controlled-data request; prospectively generate test data; or declare D1 infeasible |
| Unknown STATE/Tahoe/PIE training overlap | No independent-test claim | Checkpoint-specific training manifest and source accession matching |
| No prostate longitudinal ICI scRNA test set | No prostate P2 primary | Use pan-cancer external benchmark only or prospective model system |
| Molecular-to-behaviour mappings lack functional data | D2 learned coupling uninterpretable | Pairwise assays, protein/function evidence, uncertainty ranges |
| Wet-lab immune source/HLA system not fixed | Prospective endpoint cannot freeze | Select and qualify antigen-specific system |
| Actual compute inventory unknown | Runtime plan unreliable | Environment probe and small tracers |

## 28.2 Major scientific risks

- domain shift from cancer cell lines to patient tumour cells;
- domain shift from melanoma/pan-cancer ICI to prostate cancer;
- confounding by regimen, chemotherapy, timepoint, and disease setting;
- observer labels reflecting composition rather than function;
- parameter non-identifiability masked by visually plausible trajectories;
- overfitting through iterative use of the same retrospective datasets;
- apparent model success driven by systematic treatment effects;
- toxicity or proliferation effects masquerading as immune restoration;
- compensatory checkpoint induction misread as favourable priming;
- source overlap across Papers A/A.1/D.

## 28.3 Stop rules

Stop or rescope when:

- no eligible independent D1 condition passes G0–G8;
- a model does not beat strong baselines on perturbation-specific and calibrated metrics;
- the observer fails external-study transfer;
- D2 parameters are non-identifiable for the selected endpoint;
- the rule-only model performs as well as learned coupling;
- no prospective immune-functional experiment can be executed within the thesis timeline.

A negative result is publishable only when the benchmark, baselines, and data eligibility are rigorous.

---

# 29. Standalone publication assessment

## 29.1 D1 only

Potential contribution:

- rigorous, leakage-aware evaluation of virtual-cell prediction in an independently measured prostate context;
- documentation of failure modes and domain-shift limits.

Weakness:

- novelty is limited if it is merely another model benchmark;
- eligibility data may not exist;
- wet-lab connection is indirect.

Publication assessment: viable as a focused methods/benchmark paper if the test set is genuinely independent and the evaluation reveals a substantive result.

## 29.2 D1 + D2-lite retrospective

Potential contribution:

- a modular framework linking molecular prediction to a minimal, interpretable multicellular simulator;
- direct comparison against nonspatial and rule-only baselines;
- data-grounded prostate archetypes.

Weakness:

- still vulnerable to bridge and parameter identifiability;
- retrospective multicellular data may be sparse.

Publication assessment: plausible standalone paper only if held-out multicellular/spatial prediction improves over baselines and uncertainty is transparent.

## 29.3 D1 + D2-lite + prospective wet lab

Potential contribution:

- prospective test of frozen predictions;
- direct thesis integration;
- evidence about where virtual-cell models succeed or fail under immune and multicellular context shift.

Publication assessment: strongest and most defensible design, but dependent on a tractable HLA/antigen system, research-grade reagents, flow configuration, and timeline.

## 29.4 D3

A patient-specific digital twin would require patient-specific molecular/spatial initialization, longitudinal calibration, exposure/PK–PD, and prospective patient-level evaluation. It is not defensible as the current MSc Paper D.

---

# 30. Decisions requiring approval

The following strategic decisions materially change Paper D and require explicit approval before repository modification or implementation:

## Decision D-A — controlling primary

**Recommendation:** retain D1/P1 as the controlling primary; do not replace it now.  
**Approval requested:** accept / reject.

## Decision D-B — D2-lite status

**Recommendation:** add D2-lite as a gated secondary architecture and candidate standalone extension, not as an automatic primary.  
**Approval requested:** accept / reject.

## Decision D-C — D3

**Recommendation:** designate patient-specific digital-twin optimization as a future PhD programme and prohibit the term “digital twin” in the MSc paper unless patient-specific calibration and validation become real.  
**Approval requested:** accept / reject.

## Decision D-D — endpoint promotion rule

**Recommendation:** permit promotion from P1 to a D2 primary only after a held-out multicellular endpoint or preregistered prospective wet-lab endpoint is available and all readiness gates pass.  
**Approval requested:** accept / modify.

## Decision D-E — Lin data/code access

**Recommendation:** authorize controlled retrieval of the final supplement and, if needed, contact with the authors/EGA access steps; do not infer missing methods from summaries.  
**Approval requested:** authorize / defer.

## Decision D-F — model scope

**Recommendation:** audit STATE first; register Tahoe-x1 and PIE as conditional comparators; do not train a large model.  
**Approval requested:** accept / modify.

## Decision D-G — prospective experiment family

**Recommendation:** after Paper C and reagent reconciliation, freeze one epigenetic agent × anti-PD-1 sequence family in the antigen-specific prostate co-culture as the preferred D8 test.  
**Approval requested later:** drug, cell line, immune source, dose range, and schedule.

## Decision D-H — repository action

**Recommendation:** after D-A through D-F are approved, create `review/paper-d-virtual-tme-revision-20261012` (or repository-conforming equivalent), preserve the existing D kit, and add a revision subdirectory or versioned migration map.  
**Approval requested:** authorize branch/specification work after scientific decisions.

---

# 31. Recommended minimum viable Paper D

## 31.1 Mandatory package

1. exact source/model provenance and licence registry;
2. Lin source-resolution and observer reproduction plan;
3. D1 eligibility search with a documented no-go outcome if no test set exists;
4. frozen model/checkpoint and feature/perturbation contracts;
5. strong baselines, positive-control/data-ceiling analysis, and perturbation-specific metrics;
6. study/patient/experiment/cell-line/drug split and overlap ledgers;
7. a failure-mode analysis;
8. no D2 claim unless D2 gates pass.

## 31.2 Conditional D2-lite package

1. four-population rule-based PhysiCell model;
2. oxygen plus one recruitment field and at most one additional exposure/IFN field;
3. cohort-archetype initialization;
4. one selected epigenetic agent and one ICI mechanism;
5. programme-level bridge with uncertainty;
6. nonspatial and minimal-rule baselines;
7. held-out functional/spatial or prospective wet-lab endpoint;
8. global sensitivity and structural-ablation analysis.

## 31.3 Explicit exclusions

- patient treatment recommendation;
- universal pan-cancer control model;
- full 77-cell-subtype simulation;
- large foundation-model training;
- unrestricted Cartesian drug/sequence search;
- causal claim from observational transition matching;
- synergy without measured combination data.

---

# 32. Proposed Paper D Spec Kit structure

The existing `specs/D/` must be preserved. The revised kit should either be versioned under `specs/D/revision_20261012/` or use a migration document that retains the original files.

```text
specs/D/
├── README.md
├── ORIGINAL_D1_MAPPING.md
└── revision_20261012/
    ├── README.md
    ├── PAPER_D_SCIENTIFIC_REVISION_REPORT.md
    ├── PROTOCOL_AND_THESIS_ROLE.md
    ├── SCIENTIFIC_AIM_AND_CLAIMS.md
    ├── NOVELTY_AND_CLOSEST_STUDIES.md
    ├── LIN_TIME_REPRODUCTION.md
    ├── DATA_ACQUISITION_AND_VALIDATION.md
    ├── CELL_STATE_ONTOLOGY.md
    ├── MODEL_REGISTRY.md
    ├── PERTURBATION_CONTRACT.md
    ├── PROSTATE_TME_INITIALIZATION.md
    ├── MOLECULAR_TO_PHENOTYPE_BRIDGE.md
    ├── VIRTUAL_CELL_ARCHITECTURE.md
    ├── PHYSICELL_TME_CONTRACT.md
    ├── ICI_MECHANISM_CONTRACT.md
    ├── EPIGENETIC_DRUG_CONTRACT.md
    ├── COMBINATION_AND_SEQUENCE.md
    ├── CALIBRATION_AND_IDENTIFIABILITY.md
    ├── ANALYSIS_AND_ENDPOINTS.md
    ├── VALIDATION_AND_BASELINES.md
    ├── UNCERTAINTY_AND_SENSITIVITY.md
    ├── IN_SILICO_EXPERIMENT_REGISTRY.md
    ├── WETLAB_HANDOFF.md
    ├── WETLAB_GENE_PANEL_CONTRACT.md
    ├── FIGURES.md
    ├── SOFTWARE_ARCHITECTURE.md
    ├── PREREGISTRATION_AND_DECISIONS.md
    ├── TICKETS_AND_TESTS.md
    ├── REPRODUCE_AND_READINESS.md
    ├── UNRESOLVED_QUESTIONS.md
    ├── schemas/
    │   ├── source_record.schema.json
    │   ├── model_checkpoint.schema.json
    │   ├── training_overlap.schema.json
    │   ├── biological_sample.schema.json
    │   ├── perturbation_identity.schema.json
    │   ├── treatment_schedule.schema.json
    │   ├── cell_state_ontology.schema.json
    │   ├── simulation_parameter.schema.json
    │   ├── molecular_phenotype_mapping.schema.json
    │   ├── tme_initialization.schema.json
    │   ├── simulation_scenario.schema.json
    │   ├── model_output.schema.json
    │   ├── validation_benchmark.schema.json
    │   ├── validation_receipt.schema.json
    │   ├── wetlab_prediction.schema.json
    │   └── gene_panel_entry.schema.json
    ├── templates/
    ├── model_cards/
    ├── source_manifests/
    ├── overlap_ledgers/
    ├── validation_receipts/
    ├── wetlab_panels/
    └── tickets/
```

---

# 33. Data-acquisition and validation sub-kit

## 33.1 Workflow

```text
source discovery
  → original-study resolution
  → object/accession resolution
  → licence and access review
  → measurement/identity validation
  → biological-unit graph
  → ontology mapping
  → model compatibility
  → training-overlap resolution
  → role assignment
  → immutable manifest + checksum
  → benchmark/parameterization approval
```

## 33.2 Required receipts

For each admitted object create:

- retrieval receipt;
- checksum receipt;
- schema-validation receipt;
- identity and nesting receipt;
- perturbation-identity receipt;
- ontology-mapping receipt;
- model-compatibility receipt;
- overlap receipt;
- split-role receipt;
- licence/use receipt;
- known-limitations record.

## 33.3 Fail-closed conditions

- unresolved patient/sample identity;
- missing concentration unit;
- unknown control;
- unsupported model label;
- ambiguous salt or compound alias;
- unknown duration when duration is material;
- unknown training overlap for an independent-test claim;
- absent licence for planned redistribution;
- source-native labels overwritten without mapping;
- cells used as independent biological replicates.

---

# 34. Machine-readable contracts

Every model output must carry:

- model family and exact version;
- checkpoint URI/identifier and hash;
- code commit and environment lock hash;
- source record IDs and input hashes;
- feature map and normalization version;
- perturbation and schedule IDs;
- ontology version;
- TME initialization and parameter hashes;
- random seed(s);
- software/container metadata;
- output hash;
- validation level and status;
- training-overlap class;
- permitted claim.

A model-output record without these fields is not admissible to a figure or wet-lab handoff.

---

# 35. In-silico hypothesis registry

| ID | Hypothesis | Initial status | Required ground truth | Claim ceiling before validation |
|---|---|---|---|---|
| H1 | Epigenetic treatment restores tumour immunogenicity programmes | Eligible after D1/C reconciliation | Tumour molecular/protein assays | Molecular priming |
| H2 | Epigenetic treatment improves or impairs immune-cell state | Blocked until immune-cell perturbation evidence | Immune-cell viability/state/function | Cell-type-specific hypothesis |
| H3 | Priming increases chemokine-mediated recruitment | Conditional | Chemokine protein plus migration/infiltration | Recruitment hypothesis |
| H4 | Priming increases antigen presentation and recognition | Priority candidate | HLA/APM protein plus HLA-dependent killing | Antigen-presentation-mediated sensitization |
| H5 | Treatment remodels suppressive myeloid state | Conditional/high domain shift | Myeloid functional/composition data | External-corroboration hypothesis |
| H6 | Priming-before-ICI outperforms concurrent/reverse sequence | Hypothesis-generating | Matched sequence experiment | Sequence nomination, not clinical superiority |
| H7 | Benefit differs by prostate TME archetype | Secondary | Independent archetype-stratified data | Context-dependence hypothesis |
| H8 | Baseline/induced resistance state blocks favourable transition | Exploratory | Failure/resistance panel plus function | Resistance mechanism candidate |

Every registry entry must include comparator, output, wet-lab readout, success threshold, falsifying outcome, uncertainty, and claim ceiling. “The simulation changed” is never a success criterion.

---

# 36. Bounded implementation tickets and readiness gates

## D0 — source and upstream reproduction

| Ticket | Deliverable | Acceptance gate |
|---|---|---|
| D0-01 | Freeze approved scientific amendment | Signed decision ledger |
| D0-02 | Pin live repo/upstream commits and licences | Hash-validated registry |
| D0-03 | Retrieve final Lin supplement/code or document failure | Source-resolution receipt |
| D0-04 | Inventory Zenodo object without full analysis | Counts/metadata/checksum report |
| D0-05 | Build overlap ledgers for A/A.1/C/Lin/Arc/Tahoe | No unknown overlap in final-test candidates |
| D0-06 | Reproduce official STATE fixture | Expected output within tolerance |
| D0-07 | Reproduce official Cell-Eval fixture | Metric/version receipt |
| D0-08 | Reproduce Lin observer core or record irreducible gap | Agreement/discrepancy report |

**D0 go/no-go:** no D1 final test until model and source provenance pass. No D2 observer claim until Lin/prostate observer is validated.

## D1 — cell-intrinsic benchmark

| Ticket | Deliverable | Acceptance gate |
|---|---|---|
| D1-01 | Search and qualify independent prostate conditions | At least one G0–G8 object or formal no-go |
| D1-02 | Freeze endpoint, metrics, baselines, and splits | Preregistration hash |
| D1-03 | Implement fail-closed perturbation resolver | All alias/unit/fallback tests pass |
| D1-04 | Implement baseline suite | Information-parity tests pass |
| D1-05 | Run real-data tracer | Feature/context assumptions validated |
| D1-06 | Execute frozen benchmark | Immutable receipts |
| D1-07 | Release failure/robustness analysis | No hidden condition filtering |

**D1 go/no-go for D2 learned coupling:** model must provide useful programme-level predictions beyond strong baselines in the intended domain, or D2 must use measured perturbation inputs rather than learned outputs.

## D2 — minimal virtual TME

| Ticket | Deliverable | Acceptance gate |
|---|---|---|
| D2-01 | Freeze four-population scope and fields | Parameter-count and evidence review |
| D2-02 | Implement nonspatial population baseline | Unit and conservation tests pass |
| D2-03 | Implement minimal rule-only PhysiCell | Deterministic replay and schedule tests pass |
| D2-04 | Build untreated archetype ensembles | Baseline validation passes |
| D2-05 | Calibrate pairwise interactions | Separate calibration/test objects |
| D2-06 | Global sensitivity/identifiability analysis | Non-identifiable parameters reported |

## D3 — learned molecular coupling

| Ticket | Deliverable | Acceptance gate |
|---|---|---|
| D3-01 | Bridge registry with evidence and priors | No unsupported mapping |
| D3-02 | Couple measured effects first | Rule-only comparison complete |
| D3-03 | Couple frozen model predictions | D1 gate passed |
| D3-04 | Ablation and structural uncertainty | Learned layer improves held-out endpoint |

## D4 — longitudinal transition validation

Proceed only with an eligible independent longitudinal test set. Compare persistence, empirical transition, Markov/logistic, composition-only, and hybrid models. Patient is the unit.

## D5 — bounded combination hypotheses

Proceed only after D2/D3 validation. Freeze a small scenario registry; propagate uncertainty; do not claim synergy without measured data.

## D6 — prospective wet-lab validation

Freeze predictions before experimental access. Report result and discrepancy before any model update.

---

# 37. Required software and scientific tests

## Provenance/model tests

- wrong checkpoint and changed file hash;
- incompatible licence;
- missing feature map;
- unknown training overlap;
- upstream version drift.

## Perturbation tests

- unknown drug fails closed;
- alias collision;
- salt/form mismatch;
- concentration unit conversion;
- unsupported dose/duration;
- unsupported combination;
- control mismatch;
- global-control fallback detection.

## Cell-state tests

- missing/duplicate genes;
- gene-order mismatch;
- wrong transform;
- unsupported cell type;
- batch/context mismatch;
- ontology mapping confidence.

## Inference tests

- unchanged output detection;
- seed dependence;
- input-order invariance where expected;
- train/test leakage;
- checkpoint-output contract;
- numerical tolerance and NaN/overflow handling.

## PhysiCell tests

- unit consistency;
- diffusion and boundary conditions;
- schedule timing;
- cell interaction rules;
- conservation where appropriate;
- deterministic seed replay;
- restart/resume equivalence;
- output schema and hash;
- nonphysical rate/range rejection.

## Bridge tests

- sign reversal;
- missing evidence;
- incompatible cell type;
- unbounded parameter;
- unsupported extrapolation;
- programme/protein/function mismatch.

## Validation tests

- cell pseudoreplication;
- patient/study/plate overlap;
- calibration/test leakage;
- baseline information advantage;
- metric selected after outcome access;
- invalid confidence interval;
- observer development/test reuse.

## Wet-lab handoff tests

- mixed cell-type panel;
- RNA treated as protein/function;
- unavailable assay or reagent;
- direction not defined;
- missing control/falsification arm;
- antibody applied without immune-functional context.

Synthetic tests validate software behaviour only. Real-data tracers validate source and format assumptions. Neither establishes biological validity.

---

# 38. Readiness state at the end of this review

| Domain | Status | Reason |
|---|---|---|
| Scientific framing | **Ready for user decision** | A staged design and claim hierarchy are defined |
| Existing D1 preservation | **Ready** | Current kit is scientifically useful and should remain |
| Lin exact reproduction | **Blocked** | Final supplement/code/licence unresolved |
| D1 implementation | **Blocked** | Independent eligible prostate benchmark unresolved |
| Model registry | **Partially ready** | STATE/Tahoe/PIE landscape identified; checkpoint cards need full audit |
| Prostate observer | **Partially ready** | Strong candidate atlases exist; frozen mapping not built |
| Molecular-to-phenotype bridge | **Not ready** | Evidence and calibration matrix not built |
| Minimal PhysiCell | **Design-ready, not science-ready** | Software scope can be specified; parameter evidence not frozen |
| Prospective wet lab | **Partially ready** | protocol exists; inventory, HLA/immune source, and reagents require reconciliation |
| Large-model training | **Not approved** | No scientific need or compute justification |
| Draft PR | **Not started by design** | Major amendment requires approval first |

---

# 39. Recommended immediate sequence after approval

1. Freeze decisions D-A through D-F.
2. Create the review branch without modifying main.
3. Preserve and map the old D1 files.
4. Build the source/model/licence/overlap registries first.
5. Resolve Lin final supplement and code.
6. Run only official upstream smoke tests and small data tracers.
7. Complete the D1 eligibility search before building a TME simulator.
8. Reconcile Paper C candidates and the wet-lab inventory.
9. Freeze the observer and bridge evidence contracts.
10. Build the minimal rule-only D2 model only after its calibration endpoints are identified.

---

# 40. Source register

## Thesis repositories and internal materials

- `OASolliman590/Master-Thesis-`, main commit `a8278c776da7c6b096cc14139d729979db286b50`.
- `OASolliman590/epigenetic-ici-priming-thesis`, commit `96c16794bafc8946ae9f0bdcef81d5f3a599542b`.
- Current files under `specs/D/` and `docs/research/D_virtual_benchmark.md`.
- Paper A/A.1 evidence-expansion branch and Paper B scientific-revision branch.
- Submitted MSc protocol supplied in the project library.
- `Epigenetic_Priming_WetLab_Protocol_v2.md`, supplied in the project library.
- `Product (2).docx`, treated as procurement/source information rather than proof of physical inventory.

## Primary papers, datasets, and official software

1. Lin Z, Chandra M, Srinivas N, et al. *Tumor immune microenvironment remodeling predicts response to checkpoint inhibitor therapy.* Cancer Cell. 2026;44(9):1847–1861.e6. DOI `10.1016/j.ccell.2026.08.007`; PMID `42679812`.
2. Lin et al. preprint v3. DOI `10.1101/2024.06.30.601413`; CC BY-NC-ND 4.0.
3. Lin processed data. Zenodo DOI `10.5281/zenodo.19586163`; licence field unresolved at review.
4. Arc Institute STATE repository, commit `9bbfe78a434a55205e4de834e1ea99f85f7a3add`; `arc-state` 0.11.3; code/model licences recorded separately.
5. Arc Virtual Cell Atlas repository, commit `4f7bb170c61d2fafce70f67db6e52c7d9af1be4b`.
6. Tahoe-100M primary study. DOI `10.1101/2025.02.20.639398`; official Arc/Hugging Face releases.
7. Tahoe-x1 repository, commit `167cc19fce5888c7738b0f73f61cb4a8d3d1d457`.
8. PIE repository, commit `21a526add9ff3a81b4f962d9b16bbae570052c63`; preprint DOI `10.64898/2026.10.02.756297`.
9. Viñas Torné R, et al. *Systema: a framework for evaluating genetic perturbation response prediction beyond systematic variation.* Nature Biotechnology. DOI `10.1038/s41587-025-02777-8`.
10. *Deep learning perturbation models can outperform baselines on calibrated metrics.* Nature Biotechnology. DOI `10.1038/s41587-026-03307-w`.
11. scGPT. Nature Methods. DOI `10.1038/s41592-024-02201-0`.
12. scFoundation. Nature Methods. DOI `10.1038/s41592-024-02305-7`.
13. Geneformer. Nature. DOI `10.1038/s41586-023-06139-9`.
14. RegFormer. Nature Communications. DOI `10.1038/s41467-026-72198-x`.
15. Nicheformer. Nature Methods. DOI `10.1038/s41592-025-02814-z`.
16. PhysiCell official repository/release 1.14.2; BSD-3-Clause.
17. PhysiBoSS official repository/release 2.2.3.
18. Kiviaho et al. prostate single-cell/spatial study and associated accessions `GSE278936`, `EGAD50000000603`, `GSE137829`, `GSE141445`, `GSE176031`, `GSE185344`, `GSE181294`, `PRJNA699369`, and `SCP1244`.
19. TISMO primary resource paper and official data portal.
20. Frangieh et al. Perturb-CITE-seq melanoma immune-pressure study.

## Evidence limitations of this source register

- The final Lin supplement and public code were not retrieved; exact methods and cohort composition remain unresolved.
- Some upstream model weight licences require checkpoint-specific model-card review.
- No local scheduler or hardware probe was run.
- No dataset was downloaded or analyzed during this scientific-review phase.

---

# Final recommendation

Approve a **staged D0/D1 + conditional D2-lite** structure. Preserve D1 as the controlling primary; treat D2-lite as a validation-gated extension; defer D3. Paper D becomes scientifically valuable not by connecting fashionable tools, but by testing whether molecular predictions add measurable value to a minimal multicellular model and whether frozen predictions survive independent or prospective experimental evaluation.
