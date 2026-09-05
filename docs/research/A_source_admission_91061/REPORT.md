# Paper A: original-source admission audit of Riaz/GSE91061 and Hugo/GSE78220

6 September 2026, Cairo. Research only. Neither proposed A-P1 nor A-P2 is selected, narrowed or cancelled. No score, model, expression association or performance statistic was calculated. Counts below are source/metadata counts, not final eligibility.

**Useful positive conclusion:** all 51 Riaz baseline profiles can now be linked to the original author's patient/visit metadata, separating CR, PR, SD and unevaluable response and identifying prior-ipilimumab strata. A real FPKM header matches all 109 GEO sample titles. **Important limits:** the publication/code exclusion discrepancy is unresolved, full expression suitability is untested, and biological patient independence from Hugo is not proved. Hugo supplies 26 distinct baseline patients, not 28.

## 1. Original source and immutable provenance

Riaz et al., *Cell*, online 12 October 2017; issue 2 November 2017, DOI [10.1016/j.cell.2017.09.028](https://doi.org/10.1016/j.cell.2017.09.028), PMID29033130, PMCID5685550. Its “Data and Software Availability” points directly to the author's [bms038_analysis repository](https://github.com/riazn/bms038_analysis). The inspected revision is commit **137111c38a32f8626ee6a436e14ac667bd31b1e7**, committed 12 February 2018. `riaz_repo_commit.json` verifies the commit and underlying tree; source URLs are pinned to that revision.

The original source files are:

- [`data/SampleTableCorrected.9.19.16.csv`](https://github.com/riazn/bms038_analysis/blob/137111c38a32f8626ee6a436e14ac667bd31b1e7/data/SampleTableCorrected.9.19.16.csv): patient/visit, BAM name, original BOR, two distinct identically named `Response` columns, trial `USUBJID`, and prior-treatment cohort.
- [`data/bms038_clinical_data.csv`](https://github.com/riazn/bms038_analysis/blob/137111c38a32f8626ee6a436e14ac667bd31b1e7/data/bms038_clinical_data.csv): patient-level clinical annotation, original BOR and alternative response groupings. No survival analysis was performed.
- [`data/genomic_data_per_case.csv`](https://github.com/riazn/bms038_analysis/blob/137111c38a32f8626ee6a436e14ac667bd31b1e7/data/genomic_data_per_case.csv): the author's README identifies this as essentially Table S4, with modality/visit availability flags.
- [`rnaseq/TableS6.A.R`](https://github.com/riazn/bms038_analysis/blob/137111c38a32f8626ee6a436e14ac667bd31b1e7/rnaseq/TableS6.A.R): original baseline DEG code, inspected as text and never executed.

## 2. Patients, timing and response definition

The paper's patient-enrolment methods identify **CA209-038 / NCT01621490**. The relevant study patients received nivolumab; baseline biopsy was 1–7 days before its first dose, followed by a same-site biopsy around cycle1 day29. Baseline therefore means **pre-nivolumab**, not treatment-naive. The original 68-patient genomic group comprised 35 who had progressed on ipilimumab and 33 ipilimumab-naive patients; those are not RNA-subset denominators. Response assessment used RECIST1.1, normally every eight weeks, with confirmation of progression on subsequent imaging. The paper specifies best overall response unless indicated otherwise. [Original methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC5685550/)

GEO has 109 RNA profiles from 65 title-derived patient codes: 51 `Pre` and 58 `On`. There is one baseline profile per baseline patient code. The original author's 108-row sample table includes all 51 baseline records. Forty-three match the GEO title exactly after removing `.bam`; eight require the explicitly documented terminal `.digit` → `-digit` punctuation reconciliation. All eight retain the same patient, visit and remainder of the specimen identifier. No ambiguous normalized key occurs. All original names and the rule are retained in `Riaz_baseline_source_crosswalk.tsv`.

| Baseline category | All 51 | Ipilimumab-naive | Progressed on ipilimumab |
|---|---:|---:|---:|
| CR | 3 | 2 | 1 |
| PR | 7 | 4 | 3 |
| SD | 16 | 5 | 11 |
| PD | 23 | 12 | 11 |
| NE | 2 | 2 | 0 |
| Total | 51 | 25 | 26 |

These are exact original `BOR` counts, not inferred splits of GEO `PRCR`. GEO combines CR/PR into ten `PRCR` and maps the two source NE records to `UNK`; collapsed categories agree with the original patient clinical file. Source `Cohort` is `NIV3-NAIVE` or `NIV3-PROG`. Thus the category-evaluable ceiling remains **49** before source-specific QC/eligibility, with O10/SD16/PD23. The prior-ipilimumab groups are strata of **one originating cohort**, not independent validation studies. [GSE91061](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE91061)

**Critical parser detail:** source `SampleTableCorrected...csv` contains two headers named `Response`: zero-based column10 carries `PRCR/SD/PD/NA`; column11 carries `LB/NB` groupings. `BOR` is column9. A naive dictionary reader overwrites one `Response` column. `audit_metadata.py` checks the original header positions and exports the two meanings separately; the original CSV is untouched. Neither LB nor the source's alternative `myBOR2` response grouping is silently translated into objective response.

## 3. Why published baseline RNA N=45 cannot simply become our N

The original paper reports baseline transcriptomic analysis of 45 patients. Its RNA methods also describe excluding Patient3 as a PCA outlier. However, Patient3 is present in both the current GEO FPKM header and the source annotation, with BOR=PR.

The original baseline source code removes missing `Response`, selects pretreatment samples and explicitly excludes **Pt48_Pre, Pt67_Pre, Pt52_Pre and Pt27_Pre** (comment “Exclude 4 samples”). The rationale for these four exclusions is not stated there. Applying those named removals to the 49 category-labelled baseline records gives an **arithmetic route to 45**, but this audit did not execute the script or verify its complete count-matrix intersection. The code does not explicitly remove Pt3 at that step. Table-S4-equivalent availability metadata has 51 baseline RNA flags, so availability alone does not resolve the discrepancy.

**Facts:** source availability, actual current header, original publication and exclusion code are preserved independently. **Inference:** differing preprocessing/analysis stages or versions could explain the counts. **Unresolved:** which specimen/QC rule explains Pt3 and the four named exclusions, and the exact analysis-ready source population. Do not automatically inherit those exclusions or recreate a target N of45. A proposed new eligibility policy must be outcome-independent, justified and frozen before scoring; any departure from author exclusions must be disclosed.

## 4. Real processed-file check and scale limits

The [GEO FPKM object](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE91nnn/GSE91061/suppl/GSE91061_BMS038109Sample.hg19KnownGene.fpkm.csv.gz) was inspected through a **64,000-byte compressed prefix only**. It yielded the complete header and 127 complete feature rows:

- 109 unique sample columns, exactly equal to all GEO sample titles; no extra/missing titles.
- An empty first-column label followed by numeric gene identifiers; all inspected complete rows have110 fields.
- The source metadata explicitly identifies gene IDs as **NCBI Entrez**, reference **hg19 / TxDb.Hsapiens.UCSC.hg19.knownGene**, and FPKM generated with DESeq2v1.12.4's robust estimate. The raw-count, FPKM and rlog deposits are separate representations.

`Riaz_FPKM_header.csv` retains only the header; `metadata_summary.json` records shape and identifier examples, without assay values. The prefix hash is not a full-object checksum. It does not verify all genes, GZMA/PRF1 coverage, full-matrix nonnegativity/missingness, annotation uniqueness or a valid complete-feature FPKM→TPM conversion. The source's older per-sample descriptions mention118-sample filenames, while the series/current real header is109; preserve the actual object/version rather than trusting that stale filename text. Do not feed the author rlog matrix into the proposed TPM contract or reuse its published CYT values without an independently verified scale/definition.

Hugo's GEO lists a roughly6.8MB `GSE78220_PatientFPKM.xlsx` workbook; the original RNA methods specify hg19, TopHat2 and Cuffquant/Cuffnorm FPKM. That workbook was **not downloaded or header-certified here**. It remains a separate file/annotation admission gate. [Hugo original RNA methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC4808437/)

## 5. Hugo counts and cross-study overlap

Hugo et al., *Cell*, 24 March 2016, DOI [10.1016/j.cell.2016.02.065](https://doi.org/10.1016/j.cell.2016.02.065), PMCID4808437. The original paper explicitly includes one early on-treatment RNA specimen and two pretreatment sites from patient27. The [GSE78220 metadata](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE78220) makes these concrete:

- 28 profiles represent27 patients; Pt16/GSM2069836 is on-treatment.
- 27 pretreatment specimens represent **26 distinct baseline patients**.
- Pt27A/GSM2069842 and Pt27B/GSM2069843 are two sites from the same patient, both labelled CR. No site was selected here; counting their shared patient label once gives CR4/PR10/PD12.
- All28 deposited RNA profiles specify **pembrolizumab**; their sites are UCLA23 and VIC5. Do not assign both nivolumab and pembrolizumab to this RNA subset merely because the broader paper includes both drugs.

The paper's broader responder grouping includes controlled SD and uses **irRECIST**, whereas these GEO RNA labels expose no SD. The absence of SD in the deposited subset does not establish equivalence to all RECIST1.1 response definitions. The exact updated TableS1A category crosswalk remains unverified; its supplement request failed. An [erratum](https://doi.org/10.1016/j.cell.2017.01.010) exists and was identified, but its full content was not retrieved in this audit. Do not manufacture SD or reclassify the author's original binary responder designation as objective response.

**Overlap evidence actually checked:** the two deposits share zero GSM, BioSample or SRA experiment identifiers. Their generic Pt-number labels overlap18 times, which is neither duplication evidence nor a valid join key. The current public [NCT01621490 registry](https://clinicaltrials.gov/study/NCT01621490) includes UCLA and Vanderbilt-Ingram among sites, so apparent different author affiliations do not prove recruitment independence. Part1 eligibility excludes prior anti-PD1/PDL1/PDL2 treatment while allowing the required prior anti-CTLA4 group. This limits plausible treatment sequences but is not a patient crosswalk, and the current multi-part registry is broader than the2017 RNA subset.

**Conclusion:** no reused deposited assay identifier was found. Biological patient independence remains **unresolved**, not disproved. Retain origin/trial-qualified IDs, request no author contact in this task, and do not count two drug labels or two accessions as proof of disjoint validation patients.

## 6. Signature-development exposure

| Signature/source | Verified development/use relationship | Admission implication |
|---|---|---|
| Fixed GZMA/PRF1 CYT | Rooney2015 defines the measure in TCGA solid tumours; Riaz methods explicitly apply the previously described CYT measure. [Rooney primary source](https://pmc.ncbi.nlm.nih.gov/articles/PMC4856474/), DOI10.1016/j.cell.2014.12.033 | No Riaz/Hugo outcome fitting was identified for this fixed two-gene definition. Our own past-run/model exposure still needs its separate ledger; this is not a claim of a prospectively untouched evaluation. |
| Hugo IPRES | Developed from the Hugo study's response-associated transcriptomic analyses. | GSE78220 cannot serve as independent validation of an IPRES score taken from that same development study. |
| Riaz baseline DEG signatures | Derived in the Riaz cohort; Figure3 also applies derived programs to combined Hugo/VanAllen datasets. | Riaz is development-exposed for those signatures. Previously used Hugo evaluation data is not newly untouched confirmation. |
| Optional other predictors | Their version-specific training, tuning and previous validation populations were not comprehensively audited here. | Keep predictor-specific exposure gates; do not generalize the CYT assessment to TIDE/TIS or a new learned score. |

This source evidence preserves both A-P1 endpoint sensitivity and A-P2 learned-signature discovery. It does not select the primary or designate either cohort as an untouched final test set.

## 7. Proposed spec changes and gate disposition

**Subgates now supported:** original Riaz treatment/response definitions;51 baseline patient identifiers; source-linked CR/PR/SD/PD/NE and prior-ipilimumab strata;109-column FPKM header/GEO identity; Hugo baseline duplicate/on-treatment accounting; zero direct deposited-assay-ID intersection.

**Still open:** source/QC exclusions and Pt3 discrepancy; complete expression identity/scale/gene coverage and annotation releases; Hugo clinical-category/correction reconciliation and deterministic site selection; biological cross-study overlap; predictor/old-run exposure; final development/test split feasibility and precision.

Proposed updates: replace Riaz's “PRCR cannot be split” limitation with the newly recoverable original BOR crosswalk; retain unevaluable labels. Add explicit prior-ipilimumab strata without creating pseudo-cohorts. Correct Hugo28 to26 baseline candidate patients and distinguish irRECIST. Add duplicate-header and terminal-punctuation reconciliation acceptance checks. Never treat metadata closure as cohort admission or endorse49/45/26 as final analytical N. Both proposed primaries and prostate characterization branches remain intact.

## 8. Receipts and access limitations

`requests.json` records exact URLs, UTC request times, body sizes, content types, hashes and failures. `hash_register.json` covers every local artifact except the report/register themselves and the reused original GEO/BioC cache inputs. New recorded response bodies total **945,779 bytes**. Retrievals were small metadata, code, XML and one64KB FPKM prefix; no full expression matrix or controlled-access object was downloaded. No downloaded analysis code was executed. Browser search/open byte sizes and HTTP transport overhead are unavailable and excluded from the byte sum.

The two local Riaz `.xlsx` filenames contain HTML reCAPTCHA responses, **not workbooks**, and were not used as scientific evidence. Hugo's supplement returned404. The valid author repository metadata provided a primary-source alternative already explicitly linked by the paper. No access challenge was bypassed. Public visibility does not establish redistribution permission; no raw/clinical source data were committed, pushed or copied to Notion.
