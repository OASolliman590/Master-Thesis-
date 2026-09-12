# Primary evidence, source leads and novelty ledger

Bounded review on 12 September 2026. This is not an exhaustive systematic search or a proof that no identical study exists. Links below support method roles and the existence of candidate studies; they do not establish patient-level eligibility or successful downloads. Numerical analysis settings in this kit are proposals, not facts borrowed from these references.

## Method and data references

### R1 — DESeq2

[Official analysis vignette](https://bioconductor.org/packages/release/bioc/vignettes/DESeq2/inst/doc/DESeq2.html). Supports count/estimated-count input distinctions, design matrices and contrasts. Do not supply TPM as counts. The concrete version/environment must be pinned at implementation.

### R2 — limma

[Official package documentation](https://bioconductor.org/packages/release/bioc/html/limma.html). Supports platform-appropriate linear-model differential expression, not a blanket fallback for unknown measurement units.

### R3 — Repeated measurements

Hoffman and Roussos, dream, DOI [10.1093/bioinformatics/btaa687](https://doi.org/10.1093/bioinformatics/btaa687). Candidate repeated-measures expression framework; source-specific model and rank checks remain required.

### R4 — RNA composition methods

Newman et al., CIBERSORT, DOI [10.1038/nmeth.3337](https://pmc.ncbi.nlm.nih.gov/articles/PMC4739640/). Yoshihara et al., ESTIMATE, DOI [10.1038/ncomms3612](https://www.nature.com/articles/ncomms3612). These support different outputs: reference-defined composition estimates versus immune/stromal scores and purity estimation. They are not direct cell counting or spatial assays.

### R5 — MethylCIBERSORT

Chakravarthy et al., DOI [10.1038/s41467-018-05570-1](https://www.nature.com/articles/s41467-018-05570-1). Methylation-based composition deconvolution; not direct reconstruction of within-cell-type epigenetic state.

### R6 — Network meta-analysis

[Cochrane Handbook, chapter 11](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-11). Comparative evidence networks, transitivity and consistency requirements. A pre-treatment biopsy does not create a randomized common comparator.

### R7 — Processed GDC RNA

[GDC mRNA analysis pipeline](https://docs.gdc.cancer.gov/Data/Bioinformatics_Pipelines/Expression_mRNA_Pipeline/). Official count and normalized expression products; exact release and source fields must be verified in the acquisition manifest.

### R8 — Sample identity and clinical fields

[GDC TCGA barcode](https://docs.gdc.cancer.gov/Encyclopedia/pages/TCGA_Barcode/) and [GDC dictionary](https://docs.gdc.cancer.gov/Data_Dictionary/viewer/). Support patient/sample/aliquot distinctions. Field existence does not establish completeness or treatment-naive status for a particular patient.

### R9 — TCGA clinical and immune context

Liu et al., TCGA clinical data resource, DOI [10.1016/j.cell.2018.02.052](https://gdc.cancer.gov/about-data/publications/PanCan-Clinical-2018). Thorsson et al., DOI [10.1016/j.immuni.2018.03.023](https://pmc.ncbi.nlm.nih.gov/articles/PMC5982584/). These are clinical/survival and immune-landscape resources, not labels validating a transported ICI-response predictor in untreated TCGA patients.

### R10 — Measured TCGA chromatin accessibility

Corces et al., DOI [10.1126/science.aav1898](https://gdc.cancer.gov/about-data/publications/ATACseq-AWG). A real measured ATAC subset and downloadable study resources; do not assume coverage of every TCGA patient or every proposed prostate programme.

### R11 — Established immune response programmes

Ayers et al., DOI [10.1172/JCI91190](https://www.jci.org/articles/view/91190). Existing cross-cancer response-associated immune-expression work. Source-correct comparator implementation and cohort-overlap audit are required.

### R12 — Contemporary cross-cancer prediction

Shen et al., COMPASS, DOI [10.1038/s41591-026-04502-7](https://www.nature.com/articles/s41591-026-04502-7), 2026 final publication. Direct novelty overlap with cross-cancer/cross-treatment transcriptomic prediction. This review verified the publication listing; the full comparator training/split and implementation audit remains a task. A preprint record must not replace the final-publication citation.

### R13 — Multi-omics integration

MOFA+, DOI [10.1186/s13059-020-02015-1](https://link.springer.com/article/10.1186/s13059-020-02015-1), and [official MOFA2 FAQ](https://biofam.github.io/MOFA2/faq.html): unsupervised variation and missing-assay considerations. DIABLO, DOI [10.1093/bioinformatics/bty1054](https://pmc.ncbi.nlm.nih.gov/articles/PMC6735831/): supervised multi-omics integration in mixOmics. These are different tasks, not three interchangeable algorithms.

### R14 — Processed spatial/cellular source route

[HTAN data access](https://humantumoratlas.org/data-access): processed higher-level data and distinct imaging/controlled sequencing routes. It does not establish ICI response labels or paired RNA/methylation for every atlas.

### R15 — Paired clinical epigenetic candidates

Hossain et al., DOI [10.1016/j.canlet.2025.217638](https://pubmed.ncbi.nlm.nih.gov/40089202/): pretreatment melanoma methylome/transcriptome and anti-PD-1 response. Existing repository source evidence identifies RNA GSE213145 and methylation GSE264158; this turn did not secure a complete processed pair or patient crosswalk. GEO browser retrieval was blocked/challenged. Newell et al., [PMID 34951955](https://pubmed.ncbi.nlm.nih.gov/34951955/), remains a repository-identified multi-omics ICI source candidate. Preserve its unresolved access/pairing status; do not substitute another Newell accession by author name alone.

### R16 — Spatial/longitudinal precedent and candidate

Greenwald et al., [Temporal and spatial composition of the tumor microenvironment predicts response to immune checkpoint inhibition in metastatic TNBC](https://pubmed.ncbi.nlm.nih.gov/41708895/), **Nature Cancer 2026**, DOI [10.1038/s43018-026-01114-5](https://doi.org/10.1038/s43018-026-01114-5). The final publication record and abstract were verified. It combines longitudinal multiplexed protein imaging with bulk RNA context in TONIC. It is not an exclusively spatial-RNA study.

The earlier [PMC11838242 record](https://pmc.ncbi.nlm.nih.gov/articles/PMC11838242/), also retained as the historical S08 search lead, is the **2025 preprint**, not the final article or another independent cohort. Its reported source routes include [processed analysis files on Zenodo](https://zenodo.org/records/14112853), imaging resources and controlled/request-based sequencing. These routes are leads only: reconcile them with the final publication, current terms, final patient subset and exact processed-object availability before admission. Neither version's published total is the eligible paired N for this thesis. No patient crosswalk or matrix was downloaded in this check.

### R17 — Recent multimodal proteomic precedent and candidate

[Multimodal blood based proteomic profiling reveals insights into mechanisms of immunotherapy resistance](https://www.nature.com/articles/s41467-026-74790-7), 2026. Serial plasma proteomics and cellular/tumour RNA context in melanoma. Blood and tumour are distinct compartments, and the paper describes temporal-matching limitations. Its published totals must not become an assumed matched multi-omics denominator. This is both a promising source lead and direct novelty overlap.

### R18 — Prostate mechanism counterexample

Guo et al., DOI [10.1016/j.cell.2023.05.028](https://pubmed.ncbi.nlm.nih.gov/37327786/), also cited in the submitted protocol and existing B framework. Hypomethylation-associated immune-gene repression motivates preserving alternative regulatory mechanisms rather than a universal promoter-hypermethylation narrative.

### R19 — Protein-resource route

[NCI data resources](https://dctd.cancer.gov/data-tools-biospecimens/data) and [PDC](https://pdc.cancer.gov/pdc/). Resource discovery only in this turn; study-level processed matrices, protein coverage and TCGA specimen overlap still require audit. PRIDE/MassIVE and study supplements are additional search targets, not pre-admitted studies.

## What has actually changed in the novelty hypothesis?

| Proposed addition | Already precedented | Candidate thesis-specific contribution requiring results |
|---|---|---|
| More baseline RNA cohorts and modern prediction | Ayers, ICI biomarker benchmarks, COMPASS | Independent and context-specific programme reproducibility with defensible handoff rather than another classifier alone |
| Pre/on-treatment and R/NR effects | Longitudinal ICI and TONIC/spatial studies | Consistently defined within-patient interaction synthesis across independent studies and exposure contexts |
| Methylation plus RNA | Hossain, Newell, MethylCIBERSORT | Separate mixture-driven from regulatory interpretations and test relevance to prostate candidate restoration |
| TCGA multi-omics and clinical patterns | TCGA immune landscape and extensive disease atlases | Externally anchored, stage-aware prostate regulatory evidence beyond RNA-only characterization |
| Protein or spatial corroboration | TONIC and the 2026 multimodal melanoma study | Test the specific cell-compartment/localisation interpretation of a frozen cross-study programme |
| Perturbational ranking | Existing C novelty comparison | Show what measured epigenetic/context evidence changes and validate those changes independently |

No method list proves novelty. The strongest proposed chain is **replicated clinical association -> independently contextualized cellular/regulatory evidence -> testable prostate restoration hypothesis**. Actual reversibility requires measured perturbation evidence, and immune/clinical benefit requires the relevant functional/clinical tests. Positive findings are not required for a valid study.

At X1/X3, extend this table with the closest studies' actual datasets, contrasts, endpoints, overlaps, strengths and unaddressed questions. Report uncertainty; do not claim first-in-field without a sufficiently systematic search.
