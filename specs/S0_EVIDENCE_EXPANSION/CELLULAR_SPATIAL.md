# Cellular, methylation-composition and spatial evidence

**Proposed shared module.** B retains ownership of MethylCIBERSORT reference qualification; A may reuse the qualified adapter in measured-methylation ICI subsets under a separate admission record. No reference, tool version, numerical QC threshold or live hosted-service transfer is approved merely by naming a method.

## What each method actually adds

| Method/data | Supported role | Unsupported shortcut |
|---|---|---|
| CIBERSORT / qualified CIBERSORTx mode | Reference-dependent cell-mixture estimates from bulk expression | Not a direct cell count, not every immune state, not tumour-intrinsic methylation |
| ESTIMATE | Expression-derived immune/stromal scores and model-based purity context | Not a 22-cell-type population table or spatial-exclusion assay |
| MethylCIBERSORT | Reference-dependent composition estimates from DNA methylation | Not reconstruction of each immune cell's methylome or proof of immune-cell epigenetic reprogramming |
| Single-cell/sorted-cell measurements | Cell-compartment localization and separately measured state changes | Cells from one patient are not independent clinical patients |
| Spatial transcriptomics or multiplexed protein imaging | Locations, neighbourhoods and tumour/immune spatial relationships | A spot is not necessarily a cell; bulk abundance alone cannot establish exclusion |

The original methods establish these roles, not successful application to this thesis's datasets. [R4,R5,R14,R16]

## 1. RNA composition contract

Pin original implementation/license, reference matrix, supported cell types, gene IDs, input scale and platform-specific preprocessing. In relative mode, fractions have a reference-dependent denominator and sum constraint; they are not percentages of all tumour cells. CIBERSORTx and CIBERSORT are not interchangeable names for the same computation. Check RNA-seq versus array normalization requirements and record them explicitly. Do not use a log-scale matrix as linear abundance merely because software accepts it.

Emit method/version/reference/mode, specimen ID, estimate, units/denominator, supported feature coverage and QC/failure reason. Global deconvolution-fit P-values are not per-cell-fraction confidence intervals. Predeclare QC inclusion and retain failures in the cohort flow; do not remove samples because their inferred cells oppose the hypothesis.

Analyse baseline and longitudinal composition separately under patient-level grouping. Fractions are compositional: choose a justified subset/contrast or suitable log-ratio model with a declared zero policy; do not put every fraction and an intercept into an ordinary unrestricted regression. ESTIMATE scores and cell fractions have different meanings and should not be merged into one unlabeled abundance measure.

## 2. MethylCIBERSORT contract

Require actual measured beta profiles plus a compatible externally defined reference and probe/build mapping. Verify reference suitability for tumour context, cell classes and platform; a blood-only reference is not automatically a validated tumour deconvolution panel. Document what methylation QC was already performed and which checks cannot be reproduced from processed values.

Report reference probe coverage and overlaps with promoter predictors. Composition estimates and methylation predictors from the same assay can be statistically dependent. Shared patients and shared assay features make this a complementary measurement route, not independent external replication.

The appropriate questions are: do methylation-derived mixture estimates support a composition explanation; do RNA and methylation methods agree at defensible broad cell classes; and how sensitive are methylation-expression associations to these estimates? Do not subtract two methods' numerical fractions unless their cell classes and denominators are comparable.

To claim epigenetic states *within* an immune cell type, seek sorted-cell/single-cell epigenetic measurements or a separately validated cell-type-specific inference method. MethylCIBERSORT alone does not provide that result. Attenuation after adjustment does not prove confounding; persistence does not prove malignant-cell causality. Composition may also mediate tumour signalling. [R5]

## 3. Single-cell and spatial corroboration

Use processed count/abundance objects and original donor/specimen/timepoint metadata. Where count-based expression inference is appropriate, aggregate counts by patient/specimen/cell type and use a supported pseudobulk design, or another donor-aware model. Do not sum arbitrary corrected embeddings or log values and label them counts. Rare populations and capture bias need explicit coverage/precision reporting.

Spatial admission requires patient/section/region IDs, coordinates, technology/resolution, normalization, measured marker coverage, segmentation/annotation provenance where applicable and specimen timing. Processed cell tables or region/spot matrices are preferred; no raw image reconstruction is initiated.

Candidate patient-level readouts: immune density within annotated tumour versus stroma, prespecified tumour-border localisation, cell-type neighbourhood/contact summaries where resolution allows, and compartment-specific programme expression. Distances need physical units, region-size/cell-density context, boundary handling and an appropriate within-section null model if a spatial hypothesis is tested. Multiple regions/sections are nested in the patient; they do not inflate clinical N.

A predicted ligand-receptor interaction is a computational hypothesis, not a measured functional interaction. A separately sampled spatial cohort can localize a programme but does not prove it is the cellular mechanism in every bulk cohort.

## 4. What would make this scientifically useful?

Distinguish an abundance-linked response signal from a programme observed within malignant or immune compartments. Examine whether response-associated temporal changes are reproduced at the protein or cellular level and whether supported spatial localization changes their interpretation. Contradictions and absence of assay coverage are valuable outputs; do not select only corroborating views.

Using these methods is not itself novelty. The published TONIC spatial/longitudinal work and recent melanoma multimodal proteomics already combine response, time and cell context. The thesis must establish what its independent cross-study synthesis and prostate regulatory handoff add. [R16,R17]

Outputs: method qualification record; cell-class ontology; per-assay coverage/QC; patient-level composition/spatial statistics; declared gene/CpG overlaps; patient-aware effect/uncertainty tables; and limitations. Keep simple RNA composition available when richer modalities cannot be admitted.
