# Paper C: immune-context resource access handover

Checked: 2026-09-05. Scope: bibliographic and data-access evidence for Perturb-CITE-seq/SCP1064, TISMO, and the proposed LINCS LJP4 reference. This is not a complete coverage audit, analysis specification, or experimental protocol. No expression matrices were downloaded or analysed.

## Access and coverage evidence

| Resource | Authoritative location | What was established | What remains unverified |
|---|---|---|---|
| Frangieh Perturb-CITE-seq | [Primary article](https://www.nature.com/articles/s41588-021-00779-1); [SCP1064](https://singlecell.broadinstitute.org/single_cell/study/SCP1064/multi-modal-pooled-perturb-cite-seq-screens-in-patient-models-define-novel-mechanisms-of-cancer-immune-evasion) | The live portal reports **218,331 cells and 23,712 genes**. Its download navigation requires sign-in. These are portal-reported totals, not a locally counted eligible matrix. | Authenticated original file manifest, available sample/replicate metadata, and eligible independent units. |
| Frangieh harmonised release | [scPerturb primary resource paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC12220817/); [Zenodo record 10044268](https://zenodo.org/records/10044268); [record API](https://zenodo.org/api/records/10044268) | Locally inspected record JSON lists `FrangiehIzar2021_RNA.h5ad` (**1,458,928,348 bytes**) and `FrangiehIzar2021_protein.h5ad` (**24,714,445 bytes**). | Neither matrix was downloaded. Internal observation fields, processing compatibility, replicate identifiers and actual eligible counts remain unverified. The harmonised release and SCP1064 are versions of the same study, not independent datasets. |
| TISMO | [Primary resource paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC8728303/); [original address](https://tismo.cistrome.org/); [current redirected website](https://tismo.pku-genomics.org/); [author code repository](https://github.com/zexian/TISMO_data) | The original address redirects to the current website. Small public website files were retrieved. The paper reports **605 in-vitro RNA-seq samples**, including **195 cytokine-treated**, and **1,518 in-vivo samples**, including **832 from ICB studies**. These describe the publication release. | No current sample metadata or expression download manifest was retrieved. Current release size, model-specific coverage, study overlap, sample timing and independent-animal counts are unknown. |
| LINCS LJP4 / L1000CDS2 ligand reference | [Primary L1000CDS2 paper](https://www.nature.com/articles/npjsba201615); [official help](https://maayanlab.cloud/L1000CDS2/help/); [live ligand metadata endpoint](https://maayanlab.cloud/L1000CDS2/ligands) | Locally downloaded JSON contains **22 entries**, including **IFNG** with identifier `55d38ec50bdc501eb68f1472`, and a separate **IFNA** entry. The paper associates the ligand references with LJP4 and describes the experiment context as **six breast cell lines**. | The IFNG signature payload, exact constituent samples, cell-line identifiers, exposure metadata, controls and replicate counts were not fetched. The public consensus listing alone does not establish a prostate IFNG reference or a complete release manifest. |

The Frangieh article describes a genetic perturbation resource with RNA and protein measurements; its reported conditions include control, IFN-gamma and co-culture. The paper reports 57,627, 87,590 and 73,114 cells in those conditions, respectively. These are source-reported cell counts, not independent patient or biological-replicate counts. The original article identifies SCP1064 for processed data and a separate DUOS route for raw data. [Article, accessible through the permitted BioC service](https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json/PMC8376399/unicode).

The TISMO paper states that sample metadata and expression data are provided through its download interface; it distinguishes in-vitro cytokine data from in-vivo ICB studies. Its historical totals must not be promoted to current locally verified analysis coverage. [Resource paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC8728303/).

The official L1000CDS2 help identifies the displayed ligand references as consensus signatures using landmark genes. The live JavaScript confirms that selecting a ligand requests `ligand?id=<identifier>`. Thus the observed IFNG identifier gives the candidate payload URL below; the payload itself has **not** been retrieved. [Official help](https://maayanlab.cloud/L1000CDS2/help/), [official application script](https://maayanlab.cloud/L1000CDS2/dist/main.min.js).

## Established download paths

- RNA file listed by the inspected Zenodo record: <https://zenodo.org/api/records/10044268/files/FrangiehIzar2021_RNA.h5ad/content>.
- Protein file listed by that record: <https://zenodo.org/api/records/10044268/files/FrangiehIzar2021_protein.h5ad/content>.
- SCP1064 original processed data: use its authenticated download interface; an original-file manifest has not been recovered.
- TISMO current interface: <https://tismo.pku-genomics.org/#/datadownload>. This route is present in the downloaded application script; exact downloadable data-object URLs remain unresolved.
- IFNG candidate payload, derived from the observed application route and ligand identifier: <https://maayanlab.cloud/L1000CDS2/ligand?id=55d38ec50bdc501eb68f1472>. **Derived route, not a successful payload retrieval.**

## Files actually inspected

Files reside in `docs/research/C_immune_context/`. `retrieval_manifest.json` records requested URLs, retrieved byte sizes and SHA-256 hashes, or retrieval errors.

| Local artifact | Size (bytes) | Inspection performed |
|---|---:|---|
| `scp1064_public_summary.json` | 419 | Sanitised extraction of public cell/gene totals and sign-in requirement. Original HTML was removed because it contained session-specific embedded data. |
| `scperturb_zenodo.json` | 18,926 | Parsed file names, sizes and download links for the two Frangieh matrices. |
| `frangieh_bioc.json` | 100,405 | Article metadata, accession statements and reported dataset totals. |
| `l1000cds2_ligands.json` | 1,070 | Parsed all 22 entries; verified IFNG and IFNA as distinct records. |
| `l1000cds2.html` | 4,065 | Identified official application-script location. |
| `l1000cds2_main.js` | 22,397 | Inspected ligand metadata and signature-request routes. |
| `tismo.html` | 1,598 | Identified current public application assets. |
| `tismo_config.js` | 72 | Public site configuration only. |
| `tismo_app.js` | 96,954 | Located data-download interface route. No sample table parsed. |
| `tismo_manifest.js` | 2,051 | Retrieved application asset manifest; no downstream data chunk fetched. |

Initial default-network requests failed with connection-refused errors. Repeating the same bounded public requests with approved network access succeeded for the files above. A request to the Frangieh author's repository tree using `master` returned HTTP 404; that does **not** establish repository absence because the default branch was not resolved. No credentials are retained in these artifacts.

## Grilling evidence handover

| Question | Answer and classification | Evidence inspected | Consequence for the specification |
|---|---|---|---|
| Does an IFNG reference actually appear in the proposed ligand resource? | **Fact:** yes, in the current official 22-entry ligand list. | `l1000cds2_ligands.json`, `term=IFNG`, `_id=55d38ec50bdc501eb68f1472`; [endpoint](https://maayanlab.cloud/L1000CDS2/ligands). | Retain the arm; freeze the actual payload and provenance before scoring. |
| Is that reference a verified prostate profile? | **Unknown:** no prostate payload manifest was inspected. The source paper describes six breast cell lines. | [L1000CDS2 paper](https://www.nature.com/articles/npjsba201615). | Do not label it prostate-specific. |
| Can the original SCP1064 data be downloaded anonymously from the inspected portal? | **Observed access limitation:** its download navigation requests sign-in. | Sanitised `scp1064_public_summary.json`; [portal](https://singlecell.broadinstitute.org/single_cell/study/SCP1064/multi-modal-pooled-perturb-cite-seq-screens-in-patient-models-define-novel-mechanisms-of-cancer-immune-evasion). | Separate authenticated-original access from the public harmonised-file route. |
| Do the Frangieh totals establish statistical replication? | **No; interpretation constraint:** totals count cells. A replicate-level manifest was not examined. | Portal summary and [article](https://www.nature.com/articles/s41588-021-00779-1). | Require experiment/sample identifiers before specifying independent units. |
| Is the harmonised release an independent validation study? | **No; provenance inference:** it republishes the Frangieh dataset. | [scPerturb paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC12220817/), inspected Zenodo filenames. | Track a common originating-study identifier. |
| Have current TISMO eligibility and download objects been verified? | **Unknown:** only historical publication coverage and the current site route were established. | [Paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC8728303/), local application files. | Leave eligible sample counts unset until metadata retrieval and joins succeed. |

## Outstanding access questions

1. Obtain and checksum the permitted original SCP1064 file manifest, or explicitly select and document the public harmonised release; resolve sample and replicate fields.
2. Retrieve current TISMO sample metadata and exact object paths; reconcile its release with the publication and originating accessions.
3. Retrieve the identified IFNG signature payload and trace its constituent profile metadata. A confirmed ligand label is insufficient to establish condition-level coverage.

This handover preserves the restored source scope. It neither removes an agreed resource nor claims complete data coverage.
