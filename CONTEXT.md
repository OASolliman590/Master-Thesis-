# Epigenetic priming thesis

**A/B scope amendment, 11 September 2026:** docs/decisions/AB_IMMUNE_BARRIERS_20260911.md controls. A selects responder/non-responder discovery (A-P2), with response-definition sensitivity secondary. B studies clinically anchored immune deficits and epigenetic correlates; fixed APM prediction is a validation component. MethylCIBERSORT is a separately qualified composition sensitivity. C/D and wet-lab scope remain unchanged.

The programme investigates prostate immune regulation and interventions that may restore immune-recognition programmes, while distinguishing clinical associations, molecular perturbation effects and functional immune evidence.

## Language

**Paper A**: The study of clinical immune-signature robustness, response definitions and transferability. Its clinical response evidence comes from ICI-treated cohorts.

**Paper B**: The prostate patient study of measured methylation-associated immune regulation. Its molecular associations are distinct from proof of clinical treatment benefit.

**Paper C**: The pharmacological prioritisation study integrating signature reversal, model context and orthogonal functional/immune evidence. It is the third current paper and Claude's original Paper 4.

**Paper D**: The conditional study of virtual-cell prediction against an independent measured perturbation benchmark.

**Registered protocol**: The submitted thesis proposal supplied by the user. Its institutional approval status cannot be inferred from later planning notes or computational output.

**Wet-lab plan**: A detailed proposed experimental design. The v2 plan critiques and revises the earlier handover; neither document is a record of completed experiments.

**Objective response**: A clinical outcome defined by complete or partial response under the source study's documented assessment criteria.

**Disease control**: A clinical outcome that may include stable disease alongside complete and partial response. It is not interchangeable with durable clinical benefit without duration and follow-up information.

**Immune phenotype**: An observed or estimated property of immune activity or composition. An RNA-derived phenotype is not an independently observed ICI-response label.

**Disease signature**: A signed molecular description of the disease state. Its direction is distinct from the direction of a desired restorative perturbation.

**Signature reversal**: A measured or predicted perturbation opposing the signed disease signature. It does not by itself establish immune killing or clinical benefit.

**Methylation-associated regulation**: A relationship between measured DNA methylation and molecular expression after considering alternative explanations. Bulk anticorrelation alone does not prove causal silencing.

**Independent biological unit**: The patient, donor, culture or experiment supporting the specific inference. Multiple specimens, wells, cells or profiles need not represent independent biological units.

**Orthogonal corroboration**: Evidence using a distinct assay or biological setting to examine a related claim. Different analyses of overlapping data are not automatically independent validation.

**Not screened**: A gene or compound outside an assay's tested coverage. It is distinct from a tested negative result.

**No orthologue**: An unresolved or absent cross-species mapping for the specified mapping rule. It is distinct from lack of biological effect.

**Implementation-ready spec**: A reviewed design whose required scientific, data and interface decisions are settled sufficiently for its declared tickets. A complete conditional design can remain unready for execution.

**Regimen-specific response**: A response observed under the study's actual treatment sequence or combination. It does not identify the benefit attributable to one component without an appropriate comparison.

**Endpoint sensitivity**: The change in a fixed analysis when the clinical outcome definition changes on the same patients. It is distinct from improved prediction or proof that one outcome definition is superior.

**Supported perturbation**: A treatment identity and exposure represented by the selected model's verified input vocabulary. A successful software prediction does not establish support if an unknown treatment falls back to a control representation.

**Context transfer**: Evaluation of a treatment represented during model training in a separately held-out biological context. It differs from prediction for a completely unseen treatment.

**Native expression representation**: The exact feature identifiers, order, transformation and scale expected or produced by a selected model. Matching only the number of features does not establish compatibility.

**Reproduction**: Re-execution of a previously released analysis with its declared inputs and methods. It differs from validation using independent experiments.

**Unknown training overlap**: Incomplete provenance about whether a model encountered evaluation data. It is not evidence that the evaluation set is unseen.

### Data acquisition

**Source object**: One exact file retrieved from an official repository or author release. It is identified by the SHA-256 of its complete bytes, together with its locator and version.
_Avoid_: dataset, download, file (when the exact object is meant)

**Data classification**: The origin of a record's data: invented test data (synthetic) or real patient-level data from a source object. It says nothing about whether the record passed any check.
_Avoid_: status, readiness

**Field map**: A cohort-specific declaration of how a source object's fields and sample titles correspond to patients, specimens, timepoints and outcomes. It contains rules, never patient rows.
_Avoid_: adapter config, cohort parser

**Source of record**: The source object whose raw value is treated as primary for a given fact, such as an author clinical table for best overall response. Other sources of the same fact are corroborating.
_Avoid_: ground truth, gold standard

**Corroborating label**: A raw value for the same fact taken from a secondary source object (for example a GEO characteristic). It is kept unchanged and compared with the source of record, never silently merged into it.

**Harmonized resource**: A third-party reprocessing of a cohort, such as cBioPortal or CRI iAtlas. It is used only as a cross-check and is never a source of record.

**Ingestion proposal**: A record derived automatically from source objects through a field map. It carries a source locator, and it remains a proposal until clean joins pass or a reviewer resolves it.

**Worksheet item**: One unresolved conflict or unknown raised by ingestion, with pointers to its evidence. It is resolved only by a recorded human decision.
_Avoid_: issue, ticket, finding (when a source ambiguity is meant)

**Measurement representation**: One specific processed form of an assay's measurements (for example author hg19 FPKM, or NCBI GRCh38 TPM) with its own unit, transform and feature IDs. Representations of the same samples are kept side by side and never converted into one another.
_Avoid_: normalisation, version (when a different representation is meant)

**Reviewer worksheet**: The single per-cohort, per-branch list of worksheet items and admission gate questions, with evidence pointers, that a named human signs. Admission reads the signed worksheet and never infers a decision.
_Avoid_: checklist, review form

**Cell composition estimate**: An estimated cell-type fraction from a reference-based deconvolution of bulk data (for example quanTIseq on RNA, MethylCIBERSORT on methylation). An RNA-derived composition estimate is not an independent covariate for RNA outcomes.

**Naive-to-ICI bridge**: A comparison of the same cancer's treatment-naive reference tumours (TCGA) with pretreatment tumours from ICI-treated cohorts, by expression structure, position or concordance of frozen effects. It is not a validation of either set and does not test response itself.

**Drug class**: The immunotherapy target class a patient received, normalised to anti-PD-(L)1 axis, anti-CTLA-4, or dual anti-PD-1 plus anti-CTLA-4. A drug name or a raw source label is not a drug class until it is mapped.

**Synthesis stratum**: A set of studies whose per-study effects are combined in one meta-analysis, defined by cancer, by drug class, or by both. A stratum with one or two studies is reported by the small-k rule, never pooled into a mixed group.

**A-LONG**: The secondary product of Paper A that measures within-patient change during ICI treatment, specified in `specs/A1/`. Papers A and A.1 are one manuscript; A-LONG corroborates baseline results and never changes them.
