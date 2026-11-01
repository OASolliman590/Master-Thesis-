# Source strategy: pending decision, 30 Oct 2026

**Status: DECIDED by the user on 30 Oct 2026 — Hybrid.** (Originally recorded as open.) The user flagged this as a big upcoming decision and asked for it to be recorded in the spec kit. Nothing here changes RC2, the 29 Oct amendment or any admission.

## The question
Where should Paper A/B patient expression and response data come from?

| Option | What it means | For | Against |
| --- | --- | --- | --- |
| **1. Per-study sources (current)** | Each cohort comes from its own GEO / author / cBioPortal object, with a field map, V3 and a signed worksheet | Closest to each source; already working (5 cohorts) | Mixed representations (FPKM / TPM / upper-quartile); some pipelines undocumented; slow, cohort by cohort |
| **2. Raw re-processing (nf-core on the cluster)** | One pinned pipeline over all public FASTQ | Fully documented and uniform | About 2.4 TB; partial coverage only (controlled studies such as Liu, IMvigor210 and Braun cannot be included); days of compute; re-linking every run to its patient |
| **3. Harmonized collections** | Take uniformly processed cohorts from curated ICB collections: ORCESTRA/PredictIO `ClinicalICB` (BHK lab), IOhub, CPI1000+ (Litchfield 2021), CRI iAtlas, TIDE, TIGER | Possibly one documented pipeline across many cohorts, and fast; may cover controlled studies through their open processed derivatives | Their processing, response definitions and patient selection are third-party choices that must be verified; overlap between collections; licences; final-test protection |
| **Hybrid** | A harmonized collection as primary where its pipeline is documented, per-study sources as sensitivity, raw only for gaps | Combines the strengths | More bookkeeping |

## The user's research summary (30 Oct), recorded as UNVERIFIED claims
Each claim below must be checked against a primary source before any decision:
- ORCESTRA/PredictIO distributes the ICB cohorts as R `ClinicalICB` / `MultiAssayExperiment` objects on Zenodo or ORCESTRA, under open licences, with RECIST, irRECIST, PFS and OS mapped.
- IOhub's processed `.rds` objects are in a GitHub `data/` folder (`hansolo-bioinfo/IOhub`, repository name unverified).
- CPI1000+ has uniformly reprocessed RNA-seq and WES for 1,008 patients across 12 studies, with processed matrices in the supplement or GitHub, and raw data controlled.
- CRI iAtlas has an API and Synapse (`syn10337516`, unverified), plus notebooks.
- TIDE offers per-cohort downloads (`tide.dfci.harvard.edu`) and TIGER per-study downloads.
- "ORCESTRA + IOhub cover more than 70% of public ICB cohorts" (unsupported; needs counting).

## Criteria for the decision (checked per collection and per cohort)
1. **Documented processing** (aligner, quantifier, versions, reference and annotation). Undocumented processing has the same status as iAtlas today.
2. **Response definitions**, mapped per patient to our endpoint ontology. ORR and SOURCE_BINARY are never merged; "SD/PD = non-responder" binarisation stays one labelled endpoint among others.
3. **Patient identity and selection:** traceable to the original study IDs; which patients were dropped and why.
4. **Overlap and deduplication** across collections and with our admitted cohorts.
5. **Licence** and redistribution terms.
6. **Final-test protection:** IMvigor210 appears in most collections. Its files in any collection inherit UNTOUCHED_FINAL_TEST and must not be opened for development.
7. **Exposure:** downloading a collection that ships precomputed response-associated results (signature scores, AUCs) must not leak into development choices. Those parts are not opened.
8. **Coverage gain**, counted as new cohorts, new cancers and new patients relative to `docs/integration/20261030-data-assessment/ICBATLAS_INTAKE.md`.

## Evidence (30 Oct 2026, `docs/research/ICB_DATABASES_HARVEST_20261030.md` §5)
| Collection | Verdict | Main reason |
| --- | --- | --- |
| ORCESTRA / PredictIO | CROSS_CHECK_ONLY; per cohort USABLE_AS_SOURCE for gap cohorts, through V3 | Open (CC0/CC-BY) objects, but **two processing routes**: kallisto + GENCODE v40 (version and index undocumented) versus the authors' own matrices. Its binary response reassigns SD by 6-month PFS. 21 released objects; IMvigor210 included (locked) |
| IOhub | NOT_USABLE | No downloadable data, no licence, batch-corrected across cohorts, precomputed scores |
| CPI1000+ | NOT_USABLE as data | Uniform pipeline described, but no expression released |
| CRI iAtlas | CROSS_CHECK_ONLY | Open API, undocumented processing, ships scores |
| TIDE | NOT_USABLE | Site blocked (403); quantile-normalized, centred data |
| TIGER | CROSS_CHECK_ONLY | Unversioned FPKM pipeline, no licence, no new cohorts |

**The "more than 70% coverage" claim is false:** ORCESTRA ∪ IOhub cover 28 of 86 public ICI cohorts (33%), and ORCESTRA alone covers 19 once IMvigor210 is excluded (22%). None of the 34 newer GEO cohorts is in either. No collection provides one documented, uniform pipeline, so option 3 does not deliver standardization.

**New open cohorts found by the harvest:** Jerby-Arnon validation (112), Cui/PUCH (55), Snyder 2017 urothelial (25, kallisto counts on Zenodo), Nathanson (24), AMADEUS (pan-tumour; n to verify), Chen 2016 (NanoString), Limagne, Schalper GBM, and one public-FASTQ set (salivary, 116 GB). The largest new cohorts (IMvigor010 728, IMmotion151 823, SU2C-MARK) are controlled.

## Rule for using a collection as a source
All four must hold for the cohort in question: (1) a licence permits use; (2) the processing is documented well enough to pass V3, with any gaps stated; (3) patient IDs trace back to the original study; (4) it provides a cohort not obtainable from the original authors, GEO or cBioPortal. Otherwise the collection is a cross-check only.

## Decision record
**Decision (user, chat, 30 Oct 2026: "Yes, hybrid"):**
1. **Per-study sources stay primary:** GEO, author files and cBioPortal, each through a field map, V3 and a signed worksheet.
2. **ORCESTRA/PredictIO** is a cross-check. It becomes the source only for gap cohorts we cannot get otherwise (for example Cui/PUCH, Nathanson, Jerby-Arnon), each through V3 and a signature like any other source. Its derived SD rule is never used in place of our endpoint ontology.
3. **iAtlas and TIGER** are cross-check only for any **new** cohort; iAtlas fails on undocumented processing and adds no new cohorts, TIGER on no licence, unversioned processing and no new cohorts. This does not undo two earlier decisions: Gide's expression is the iAtlas profile delivered through cBioPortal (admitted under the documented-processing exception, `BATCH2_CBIOPORTAL_20261030.md`), and IMvigor210's cBioPortal files are iAtlas's (the authors' package is held for the final test). **IOhub, CPI1000+ and TIDE** are not used as data.
4. **Raw re-processing** on the cluster follows the middle path: only where it adds patients or cancers (Zhao, Kim, GSE145996, the salivary set). It starts with a pilot and a concordance check against one processed cohort. Full re-processing of already-admitted cohorts is not planned.
5. **IMvigor210 stays UNTOUCHED_FINAL_TEST in every collection.** Its objects are never downloaded from ORCESTRA or iAtlas.

## recount3 added (user, 30 Oct 2026: "Yes, add recount3")
recount3 (Monorail: STAR 2.7.3a, hg38, GENCODE v26 gene sums; licence **public domain**, per the AWS Open Data registry entry) passes the four-test rule for:
- **Gide:** the primary representation becomes recount3, replacing the iAtlas upper-quartile profile. The iAtlas profile becomes a sensitivity, and the undocumented-processing exception is no longer needed once this is admitted.
- **Kim 2018 (gastric):** a new cohort; recount3 is its representation. Per-patient response labels still need a source; the paper's supplement has clinicopathology but no response.
- **Riaz and Hugo:** recount3 is a uniform **sensitivity** representation. Their admitted primaries (author FPKM) are unchanged.
Retrieved 30 Oct with the pipeline fetcher from `recount-opendata.s3.amazonaws.com` (HTTPS) into `.scratch/runtime/<c>/store-recount3/`, using plans `tools/a_dav/fetch_plans/<c>_recount3.json`. Each project has gene sums G026, SRA/project/QC metadata and the G026 annotation, about 30 MB in total. The coverage-sum-to-count conversion must follow recount3's documented method, pinned with source evidence before V3.
