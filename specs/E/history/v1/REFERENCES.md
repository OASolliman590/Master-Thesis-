# References, source identities and inspection limits

Review date: 2026-10-13. Source inspection is not numerical-data admission. Browser/connector text was inspected; original article/supplement bytes were not retained here. Their byte counts/hashes are UNKNOWN. Package hashes identify newly authored package files, not original source objects. No private protocol originals are redistributed.

## Primary evidence

| ID | Identity / official source | Inspected role and boundary |
|---|---|---|
| S001 | Vorinostat PBPK/PD, DOI `10.1007/s00280-017-3447-x`; PMID `28988277`; PMCID `PMC6056765`. https://pubmed.ncbi.nlm.nih.gov/28988277/ ; https://pmc.ncbi.nlm.nih.gov/articles/PMC6056765/ | Systemic PBPK, HDAC-activity/platelet PD; candidate reconstruction, not prostate-priming validation. Table 2 bounded seeds inspected. Full asset/source audit pending. A recheck returned a browser challenge; no endless retry. |
| S002 | Wang et al., HER2-negative breast epigenetic–ICI virtual-trial QSP, DOI `10.3389/fbioe.2020.00141`; PMCID `PMC7051945`. https://www.frontiersin.org/journals/bioengineering-and-biotechnology/articles/10.3389/fbioe.2020.00141/full | Public article describes MATLAB/SimBiology. Scripts offered by request, not anonymous required asset. Supplements/numerical calibration overlap still need audit. |
| S003 | Prostate immunotherapy QSP, DOI `10.1038/s41598-020-65590-0`. https://www.nature.com/articles/s41598-020-65590-0 | Context-specific prostate precedent, not a ready human prostate parameter set. Asset/licence/parity pending. |
| S004 | Rodems et al., *Reversible epigenetic alterations regulate class I HLA loss in prostate cancer*, DOI `10.1038/s42003-022-03843-6`. https://www.nature.com/articles/s42003-022-03843-6 | Relevant HLA/recognition experimental precedent, not local cell/assay qualification or new recovery data. |
| S005 | Guo et al., *Cell*, DOI `10.1016/j.cell.2023.05.028`. https://doi.org/10.1016/j.cell.2023.05.028 | Mechanistic counterexample cited by project; primary-object extraction pending; no numeric rate imported. |
| S006 | Allen et al., virtual-population methodology, DOI `10.1002/psp4.12063`. https://doi.org/10.1002/psp4.12063 | Methodological lead resolved from precedent references; not reproduced or selected as an opaque weighting algorithm. |
| S007 | HDAC kinetics lead, DOI `10.1074/jbc.M113.490706`. https://doi.org/10.1074/jbc.M113.490706 | Follow-up target/assay/kinetics audit, no constants imported. |

Regulatory route resolved from S001: `https://www.accessdata.fda.gov/drugsatfda_docs/nda/2006/021991s000_Zolinza_ClinPharmR.pdf`. It is a retrieval target, not a retained/extracted PK dataset. The linked S001 supplement `NIHMS980542-supplement-1.docx` was not downloaded; model availability is not inferred from its filename.

## Official documentation / acquisition routes

| ID | Official documentation | Boundary |
|---|---|---|
| O01 | https://europepmc.org/RestfulWebService | Article search, identity and full-text discovery; access per object. |
| O02 | https://open.fda.gov/apis/drug/drugsfda/ | Regulatory application/document metadata, not a complete PK observation database. |
| O03 | https://open.fda.gov/apis/drug/label/ ; https://dailymed.nlm.nih.gov/dailymed/ | Product/formulation/PK summaries; avoid counting duplicate studies as independent. |
| O04 | https://clinicaltrials.gov/data-api/api | API v2 trials/results/documents; metadata ≠ individual PK. |
| O05 | https://www.ebi.ac.uk/chembl/api/data/docs | Compound/assay identities; original potency context required. |
| O06 | https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest | Chemical identifiers/properties, parent/salt and method distinctions. |
| O07 | https://pk-db.com/ | Exact usable PK object/API unresolved; optional until verified. |
| O08 | https://www.open-systems-pharmacology.org/OSP-PBPK-Model-Library/ | No exact vorinostat asset claimed found. |
| O09 | https://www.open-systems-pharmacology.org/OSPSuite-R/ | Pin release/native runtime and verify OS-specific execution before use. |
| O10 | https://docs.open-systems-pharmacology.org/ | PK-Sim/MoBi structures, exports and editing contracts. |
| O11 | https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html | New open ODE candidate; solver/event parity still untested. |
| O12 | https://www.ncbi.nlm.nih.gov/books/NBK25501/ | E-utilities; obey current service rate/identity rules. |
| O13 | https://www.ncbi.nlm.nih.gov/geo/info/download.html | GEO object access; actual processed objects must be identified. |
| O14 | https://www.ebi.ac.uk/biostudies/ | Open study/supplement discovery; no E object admitted. |
| O15 | https://www.ebi.ac.uk/biomodels/ | Public model discovery, not proven compatible asset. |

## Private/project sources and live repository

| ID | Source identity | Status |
|---|---|---|
| INT01 | Eight-page proposal, Library `file_00000000a82881f48525a50cb40ddbdc`, title beginning *Epigenetic Priming for Enhanced Immunotherapy...* | Submitted scientific scope inspected. Institutional administrative approval not established. |
| INT02 | `Epigenetic_Priming_WetLab_Protocol_v2.md`, Library `file_0000000098d471f4a67f11635af17db8`, 13 July 2026 | Research-design proposal, not completed experiments. |
| INT03 | `Wet_Lab_Protocol_Epigenetic_Priming_PRAD.pdf`, Library `file_00000000813c7243b1f76b389664f95c` | Older seven-page plan with superseded/contested design elements. |
| INT04 | `Product (2).docx`, Library `file_0000000097988210896de84254dee843` | Procurement alternatives, not verified received inventory. |
| USER01 | Current E request, 2026-10-13 | Architecture/data-policy approval; biological decisions explicitly unresolved. |
| REP01 | https://github.com/OASolliman590/Master-Thesis- ; main `a8278c776da7c6b096cc14139d729979db286b50` | AGENTS, CONTEXT, progress, A–D entry contracts, branches/PRs/issues and selected acquisition code inspected; not exhaustive application audit. |
| REP02 | `review/evidence-expansion-20260912`, `48373c5eae2c6e22dc9a53b54f6cfc84bf969d54`, draft PR 6 | Shared acquisition/A.1 proposal, not merged main. |
| REP03 | `review/paper-b-scientific-revision-20260928`, `4fbd5e27c3097f010b419ddffe28ad95e42b5d82`, draft PR 8 | B additive revision proposal, not automatically adopted. |
| REP04 | https://github.com/OASolliman590/epigenetic-ici-priming-thesis ; main `96c16794bafc8946ae9f0bdcef81d5f3a599542b` | Historical branch identity inspected; exhaustive legacy audit incomplete. |

Current Project/conversation Files listing returned no files; relevant earlier documents were recovered through Library search. A zero-result PBPK code search does not prove absence of local E work. GitHub cannot inspect uncommitted work. No AIU job or fresh A–D regression was run.
