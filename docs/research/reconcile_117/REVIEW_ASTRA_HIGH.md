# Astra (gpt-6-astra, high) review of the 117-row reconciliation, 2 Nov 2026

Read-only review, kept verbatim except that absolute paths were made repository-relative. Its corrections are applied in RECONCILIATION.tsv and REPORT.md.

VERDICT: **Revise before acceptance:** the scope cuts are sensible, but the reconciliation misses a documented RNA-response lead, conflates methylation studies, and treats several unresolved classifications as facts. This is a local-evidence audit; availability was not rechecked online.

CORRECTIONS:

1. **ICB-BULK-020 — wrongly “no new data.”** The prior audit records **GSE165745: 24 anti-PD-1-treated melanoma samples, 12 responder/12 non-responder, public NanoString Wnt/immune panel**. Correct to **A-BIO candidate**. Check baseline timing, response definition, patient independence and frozen-panel coverage; the pharmacological paper title does not establish that these patients received the Wnt inhibitor. [Recorded evidence](docs/research/ICI_COHORT_SEARCH_EXPANDED_20261028.md)

2. **ICB-BULK-017 / 041 — “no expression” versus “covered” conceals an unresolved overlap.** The earlier audit records 21 RNA profiles through `skcm_mskcc_2014`; the registry admits seven baseline patients through GSE165278. Correct to **public processed RNA candidate, same Snyder/Nathanson family**. Compare patient IDs, timing and endpoints to establish whether any additional eligible patients exist; never count the publications independently.

3. **ICB-SC-002 / 010 / 011 — single-cell disposition does not settle companion bulk data.** Jerby-Arnon bulk remains a registry candidate; the earlier audit specifically flags GSE200996 and GSE205506 as possible bulk companions. Correct to **SC downloads cut; companion bulk eligibility unresolved**. Check actual assay objects, baseline specimens, patient-linked outcomes and overlap. Pathological response must remain separate from ORR.

4. **ICB-BULK-025 / 026 — two studies incorrectly collapsed into Jung.** Row 025 is **Cho/GSE126044**, whereas 026 is **Jung/GSE135222**. Correct to **two distinct methylation/RNA provenance audits**, with RNA already parked or signed respectively. Establish methylation accession, public object, specimen matching and endpoint separately. The repository already documents this identity correction. [Local verification](docs/research/USER_LEADS_VERIFICATION_20261030.md)

5. **ICB-BULK-027 — materially undervalued for Paper B’s argument.** GSE213145 also has a publication-backed methylation companion, **GSE264158**, through Hossain 2025. Correct to **A RNA candidate plus priority paired-methylation lead**. Same-patient/same-biopsy linkage and current public availability remain unverified; the 2022/2025 publications are not independent cohorts. Consequently, Jung would **not** be the “only ICI-treated methylation data”: the signed B-V plan also names guadecitabine cohorts with methylation. [Existing paired-evidence audit](docs/research/A_ICBATLAS_SOURCE_EXPANSION.md)

6. **ICB-BULK-029 / 019 — unnecessary rediscovery and unsupported naming.** Row 029’s recorded DOI identifies **Braun 2020**, already signed: correct to **covered, accession/publication crosswalk**. Row 019’s historical record points toward the **MGH GSE115821/GSE168204 family**, not established “Du 2018” or Riaz/Gide reuse: correct to **identity/overlap unresolved**, with no new-patient claim.

7. **ICB-BULK-012 / 044 — uncertainty promoted to fact.** GSE99070 is currently **on hold: ICI treatment not shown**, while an older audit claims an ICI subset; resolve that contradiction before saying “not ICI-treated.” For Weber, **no public object located** does not establish controlled access. Correct to **unresolved/parked**, without reopening genuinely controlled sources.

8. **ICB-SC-004 / 007 / 009 / 012 — “covered” is too broad or inconsistent.** BCC_Yost does not establish coverage of the separate squamous-cell row; Zhang’s chemotherapy cohort is explicitly excluded; GSE207422 is explicitly combination-excluded. Row 012’s historical family says `endo_PD1`, conflicting with its colorectal label. Correct to **verified subset only / excluded / identity unresolved**, as applicable—not eight uniformly usable atlas studies.

9. **PROST-BULK-002 — the proposed check ignores existing regimen evidence.** The local audit identifies **GSE314805 as PD-1 plus pTVG-HP DNA vaccine**, with PSA decline labels. Correct to **combination-excluded; contextual citation**, unless primary patient records establish a distinct eligible ICI-only subset. It is not a priority A admission task. [Recorded regimen](docs/research/ICI_COHORT_SEARCH_EXPANDED_20261028.md)

10. **PROST-SCRNA-004 — “possible interpretation reference” misses the existing prostate context.** Crosswalk GSE274229 to the atlas’s PCa_Hawley source before treating it as additional material. Correct to **citation/provenance check; no standalone download**. The signed plan already permits three baseline ICI-treated prostate patients, individually displayed, with no response contrast.

11. **ICB-BULK-022 / 023 — endpoint and treatment timing need sharper verdicts.** Cloughesy is **low-priority survival/treatment-window context**, not automatically a clinical-benefit cohort; separate pre-ICI from post-neoadjuvant tissue. Adjuvant durvalumab after completed trimodality therapy is not established concurrent combination treatment. Keep it outside current response analyses on **adjuvant endpoint/timing grounds**, pending protocol confirmation.

PER-TYPE ANSWERS:

- **Single-cell:** Useful for the signed descriptive SC-1 task only, within its 21-hour ceiling. Preserve the untreated prostate reference and small PCa_Hawley panel; companion **bulk** checks do not revive single-cell response analysis.
- **Spatial:** Keep cut. Published spatial findings can support interpretation; no new spatial processing is justified within 600 hours.
- **Proteomics:** “Not useful” overstates the case. These serum studies are poor fits for the current analyses, but **TCGA RPPA is already allowed in B-MX** where coverage permits; retain that narrow option without starting serum proteomics.
- **Pathology:** Skip image-model development. Existing patient-linked purity, infiltration or PD-L1 annotations can be useful context/covariates; histology and radiology should not be treated as interchangeable.
- **Prostate rows:** None establishes a new eligible B-P cohort or ready A response cohort. They still provide clinical/mechanistic context; no listed source establishes paired methylation–RNA–ICI response evidence in prostate.

RANKED ACTIONS:

1. **GSE213145/GSE264158:** resolve public methylation object, patient/specimen intersection and response labels — **2–4 hours**.
2. **GSE165745:** verify baseline response-linked panel and coverage — **1–2 hours**.
3. **Cho versus Jung:** correct identities, then locate methylation objects and pairing evidence — **2 hours maximum**.
4. **Repair crosswalks:** Braun, MGH, atlas eligibility and prostate regimen contradictions — **1 hour**.
5. **GSE181815:** verify selected 5-versus-5 sampling, baseline timing and individual outcomes — **1–2 hours**; descriptive tiny-cohort value, limited prediction value.
6. **Snyder/Nathanson and companion bulk:** check only incremental patients and usable baseline objects — **2 hours maximum**.

Drop open-ended Cabrita, Chen and Weber searches; drop GSE314805 admission work and standalone GSE274229 acquisition. Defer Cloughesy survival analysis. These rank below the concrete, already documented leads.
