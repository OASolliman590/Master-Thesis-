# Reconciling the legacy 117-study list, 2 Nov 2026

**Status: revised after Astra's high review (`REVIEW_ASTRA_HIGH.md`, 11 corrections applied).** Source: the 2 Oct 2026 study-clearance list `ALL_117_STUDY_USE_REGISTRY.csv` (85 ICI rows, 32 prostate rows), restored from `archive/internal_project_20261101.tar`; sha256 ae54d135…, matching the A-DAV-04 record. Every row's verdict is in `RECONCILIATION.tsv`. The current single registry is `docs/cohorts/REGISTRY.tsv`; the 117 list is a historical lead list, and none of its rows was ever analysis-cleared.

User decisions applied (2 Nov): controlled-access sources are dropped; spatial data are out (single-cell plan); the signed single-cell plan cuts standalone single-cell downloads.

## Verdict counts (117 rows)
covered 28 · not needed 19 · not useful 19 · excluded 18 · no expression 9 · dropped 7 · no new data 6 · check 6 · lead 3 · added 2.

## Questions asked by the user
- **The two new ICI leads:** both are public and now in the registry as candidates. GSE181815 is pembrolizumab in thymic carcinoma (10 patients, 5 responders versus 5 non-responders, RNA-seq). GSE213145 is anti-PD-1 monotherapy in melanoma (20 patients with RNA-seq, clinical-benefit endpoint).
- **The 32 prostate rows against Paper B:** none is in Paper B's data list, which is untreated TCGA-PRAD and CPC-GENE by design. **None fits Paper A's response analyses:**
  - most combine ICI with ADT, chemotherapy, radiotherapy, evofosfamide, vaccines or CD40/IL-8 agents;
  - others are non-ICI immunotherapies, single cases, trial reports without expression data, or controlled access.
  - Two "check" items: GSE314805 (NanoString, mixed immunotherapies, PSA response) and GSE274229 (prostate myeloid ICI-resistance single-cell, a possible Paper B interpretation reference).
- **Single-cell (21 ICI rows):** useful only as already planned. Eight are inside the Lin atlas or its source cohorts. The rest are cut by the signed plan (cite only), are integrated databases superseded by the atlas, or are not ICI-treated.
- **Spatial (7 + 2):** not used (user decision).
- **Proteomics (6 + 3):** not useful for A or B. They are blood or serum proteomics with no link to the tumour expression panels; discussion only.
- **Pathology and radiology (5 + 1):** not useful; no expression data; discussion only.
- **The 4 old "primary candidates":** IMvigor210 (locked; listed under another name), Miao RCC (dropped, controlled), and the two new leads above.

## Leads worth action (ranked after Astra's review)
1. **GSE213145 plus its methylation companion GSE264158 (Hossain 2025):** RNA, response and possibly paired DNA methylation in ICI-treated melanoma, which matters for Paper B's methylation-ICI argument. Resolve the public methylation object, the patient and specimen intersection, and the response labels (2-4 h).
2. **GSE165745:** 24 anti-PD-1 melanoma samples (12 R / 12 NR) on a NanoString Wnt/immune panel; verify baseline timing, response and panel coverage (1-2 h). An A-BIO candidate, which I had wrongly dismissed.
3. **Cho (GSE126044) and Jung (GSE135222) are two separate studies;** I had merged them. Locate each methylation object and its pairing (2 h at most).
4. **Repair crosswalks:** Braun (ICB-BULK-029 is Braun), the MGH family (ICB-BULK-019), atlas eligibility per row, and the prostate regimen contradictions (1 h).
5. **GSE181815 thymic:** verify the 5-versus-5 sampling, timing and individual outcomes (1-2 h); descriptive value only.
6. **Snyder/Nathanson and companion bulk** (Jerby-Arnon, GSE200996, GSE205506): check only for extra eligible baseline patients (2 h at most).

Dropped: open-ended Cabrita, Chen and Weber searches; GSE314805 admission (PD-1 plus a DNA vaccine); a standalone GSE274229 download. Cloughesy is deferred.

## Corrected per-type answers
- **Single-cell:** only the signed descriptive SC-1 (21 h cap). Companion **bulk** checks do not revive single-cell response analysis.
- **Spatial:** stays cut.
- **Proteomics:** a poor fit for the current analyses; no serum proteomics. TCGA RPPA stays allowed in B-MX where coverage permits.
- **Pathology:** no image-model work. Existing patient-linked purity, infiltration or PD-L1 annotations can serve as covariates.
- **Prostate rows:** none is a new eligible B-P cohort or a ready A response cohort; context only. No listed source gives paired methylation, RNA and ICI response in prostate.
- **Methylation in ICI-treated patients:** Jung is not the only source. GSE264158 (melanoma) and the signed B-V guadecitabine cohorts also exist.
