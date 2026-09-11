# Paper A: ICBatlas-first source expansion and paired epigenetic evidence

Checked 11 September 2026. Bounded primary-source literature/metadata audit; no matrices downloaded, patients admitted, models fitted or eligibility totals established. The A-P2 selection in `docs/decisions/AB_IMMUNE_BARRIERS_20260911.md` controls. This note expands the acquisition queue; it does not replace the source-specific audits in `specs/A/DATA.md`.

## ICBatlas is the starting catalogue

The original publication explicitly includes RNA-seq and expression arrays, pretreatment and on-treatment specimens, and source-dependent processing (including log transformation and ComBat). Its stated R/NR rule is CR/PR versus SD/PD. These are resource descriptions, not verification of each original clinical endpoint or an acceptable pooled training matrix. [Yang et al., methods, Table 1 and Figure 1](https://guolab.wchscu.cn/static/ICBatlas/ICBatlas.pdf).

Figure 1 visibly supplies these identifiers (deduplicated labels, not independent-study counts):

| Identifier class | Literal labels to resolve against original studies |
|---|---|
| GEO | GSE176307, GSE111636, GSE67501, GSE93157, GSE122220, GSE136961, GSE140901, GSE99070 |
| SRA/ENA | SRP128156, SRP011540, SRP094781, SRP230414, ERP105482, SRP070710, SRP150548, SRP250849, SRP302761, SRP183455, SRP217040, ERP107734, SRP155030 |
| Other labels | IMvigor210, PMID:32472114, PMID:33806963, TCGA |

Source: [ICBatlas Figure 1B](https://guolab.wchscu.cn/static/ICBatlas/ICBatlas.pdf). Supplementary Tables S1/S2 remain the needed accession/publication/assay crosswalk; they were not secured in this audit. Do not infer cancer/assay mappings from OCR position. The legacy site returned a web retrieval error; the [Guo laboratory site](https://guolab.wchscu.cn/ICBatlas/) returned no extractable text. No live catalogue export is claimed.

Proposed acquisition work:

1. Resolve every literal identifier to the originating publication/trial and exact downloadable expression/clinical objects. Keep unresolved entries in the manifest instead of silently omitting them.
2. Link atlas aliases to existing Riaz, Rose and Hugo records before selecting development/test roles. A repeated accession, publication reanalysis, treatment stratum or repository copy does not create an independent cohort.
3. Recover original response categories, assessment system, timing, regimen and patient-to-specimen links. Apply the existing ORR contract; an atlas R/NR column alone is insufficient to settle discrepancies already found in the original-study audits.
4. Prefer original per-study data for discovery. Verify units, full feature universe and normalization history before TPM admission. Arrays need a separately declared assay branch; log-transformed/pooled batch-corrected matrices must not be silently treated as raw TPM or fitted across held-out studies.
5. Record prior exposure to atlas-derived DEGs, response scores and cohorts. Atlas outcome-derived gene lists cannot select features using final-test patients.

The steps above are proposed safeguards under the repository's existing data/split contracts, not claims about completed atlas retrieval. Keep all source-level admission counts unknown until actual joins and QC succeed.

## Actual RNA plus measured epigenetic candidates

| Priority / originating study | Primary-source evidence | Access and endpoint disposition |
|---|---|---|
| First public paired audit: Hossain et al., Cancer Letters 2025 | The paper reports pretreatment melanoma EPIC DNA methylation plus RNA-seq in first-line anti-PD1 monotherapy, with integrated methylome/transcriptome analysis. Its data statement identifies RNA **GSE213145** and methylation **GSE264158**. [Paper](https://doi.org/10.1016/j.canlet.2025.217638), [author repository](https://ourarchive.otago.ac.nz/esploro/outputs/journalArticle/Pre-treatment-DNA-methylome-and-transcriptome-profiles/9926720242801891) | Strong paired-study candidate; exact same-patient and same-biopsy intersection, original response definition and eligible paired N remain unverified. GSE213145 is a reused earlier RNA study, so 2022 and 2025 publications must not count as independent validation. Retrieve both matrices, clinical supplement and explicit crosswalk before admission. |
| Newell et al., Cancer Cell 2022, PMID34951955 | Concurrent baseline whole-genome, transcriptome, methylome and immune-infiltrate examination in advanced cutaneous melanoma treated with anti-PD1 with/without anti-CTLA4. [Original abstract](https://pubmed.ncbi.nlm.nih.gov/34951955/) | Real multiomic ICI study, not a methylation-surrogate claim. The abstract's 77 total patients is **not** established paired RNA+methylation eligibility. Exact assay intersection, accessions/access tiers, pretreatment IDs and response adjudication require full methods/supplements. Prior cohort reuse/overlap also needs review. |
| Seremet et al., Journal of Translational Medicine 2016 | RNA-seq and MBD-seq were performed on 12 melanoma metastases in a study of ipilimumab alone or ipilimumab plus TriMixDC-MEL; study grouping was durable benefit versus no benefit. [Original article](https://link.springer.com/article/10.1186/s12967-016-0990-x) | Real paired-assay candidate, but 12 lesions is not 12 eligible baseline patients. Mixed specimen timing and combination treatment require patient/lesion/treatment mapping. Durable-benefit groups cannot be relabelled ORR. Public machine-readable matrices and accession were not secured. Authors reported no corresponding methylation differences in their differentially expressed genes; do not assume paired measurements establish methylation-mediated expression. |
| EPICA / Anichini et al., 2025 | The main metastatic melanoma cohort has RRBS, RNA-seq and other assays; a separate adjuvant-ICB group was methylation-profiled. Processed WES, RRBS, RNA-seq, Clariom S and microarray data are deposited under **10.5281/zenodo.15584210**. [Original article and data statement](https://link.springer.com/article/10.1186/s13046-025-03474-9) | Useful paired molecular resource and separate ICI-associated epigenetic candidate. Do not assume the adjuvant subset has paired RNA, or turn recurrence/adjuvant outcomes into metastatic measurable-disease ORR. Inspect sample-level modality membership and clinical timing before assigning any A branch. |

The [GSE213145 primary record](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE213145) lists 20 RNA profiles and `GSE213145_featCount.csv.gz`, an author count object, and cites PMID36248850. A [sample record](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSM6573402) explicitly describes pre-anti-PD1 tissue and featureCounts on GRCh37. These facts establish a real RNA acquisition route, not a paired denominator or TPM readiness. The GSE264158 direct page could not be retrieved in this audit; its identifier is publication-backed, while current matrix availability and patient crosswalk remain unverified.

Do not substitute [GSE202097](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE202097) merely because Newell is an author: its GEO title is *Comparative genomics of melanoma subtypes*, with PMID36098958. It is not automatically the checkpoint-treated cohort cited above.

## ICI methylation studies that do not establish paired RNA here

| Study | What is actually supported | Paper A disposition |
|---|---|---|
| EPIMMUNE / Duruisseaux 2018, NSCLC | Tumour methylation signature and FOXP1 methylation validation with anti-PD1 outcomes. The reported discovery/validation/marker populations are different analysis groups. [Author-hosted original record](https://diposit.ub.edu/items/f1959bc1-1482-46ad-ad85-d24e7a0147e4) | Methylation evidence; paired patient RNA was not established by the inspected source. Do not add the study's full population to an RNA roster. |
| Metastatic melanoma methylation-response study, 2024 | Pretreatment tumour methylation with radiological iRECIST outcomes; BioProject **PRJNA984630**. [NCBI submission](https://www.ncbi.nlm.nih.gov/bioproject/PRJNA984630), [original paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC10963567/) | Methylation-only for this audit; verify original iRECIST trajectories if any endpoint comparison is pursued. No paired RNA claim. |
| Advanced/metastatic HNSCC, 2022 | Tumour DNA methylation, immunological markers and anti-PD1 radiological response. [Original paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC8961155/) | Methylation-only for this audit. PD-L1 protein/IHC does not supply transcriptome data. |
| Sarcoma, 2021 | Tumour methylation profiles associated with anti-PD1 monotherapy response. [Original paper](https://jitc.bmj.com/content/jitc/9/3/e001458.full.pdf) | Separate epigenetic corroboration; paired RNA not established. |
| INSPIRE cfMeDIP-seq, 2024 | Plasma methylation/fragmentation before and during pembrolizumab. [Original paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC11145176/) | Blood/plasma assay and kinetics branch; not interchangeable with paired baseline tumour RNA/methylation. Patient-linked tumour RNA would require a separately verified crosswalk. |

“Not established” means this bounded audit did not verify the pairing, not proof the material never existed. No methylation-only study should be dropped from the epigenetic evidence inventory, but it must not inflate RNA discovery or paired multiomic counts.

## Required paired-data admission record

For each candidate record study/trial identity; source patient ID; RNA specimen ID; epigenetic specimen ID; same-biopsy versus same-patient/different-lesion status; dates relative to all regimen components; assay/platform, genome build and processed units; full raw response definition; original clinical locator; access tier; file URL/hash/terms; and exclusions. Report `n_rna`, `n_epigenetic`, `n_patient_linked`, `n_same_specimen`, `n_baseline`, and `n_endpoint_eligible` separately after verification.

Keep the expanded RNA responder/nonresponder discovery as A's backbone. Attach measured epigenetic evidence as a qualified subset with its own missingness/selection analysis. Do not require every RNA cohort to have methylation, impute methylation from RNA, pool unpaired assays into artificial patients, or let paired-subset/final-test outcomes select the frozen RNA signature. A methylation-expression association remains distinct from causal epigenetic reversibility or prostate ICI efficacy.

No newly eligible counts, independent test reservation or full downloadable paired package is established by this note. The strongest concrete next retrieval is the Hossain publication-linked GSE213145/GSE264158 pair, alongside the full ICBatlas source crosswalk and Newell supplements/access records.
