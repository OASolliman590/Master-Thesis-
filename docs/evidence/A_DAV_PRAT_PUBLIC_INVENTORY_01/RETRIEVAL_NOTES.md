# Bounded public source retrieval notes

## Scope and status

This packet records a bounded public-source retrieval for GEO series **GSE93157** and platform **GPL19965**. The inspection used their official NCBI GEO accession pages and official `ftp.ncbi.nlm.nih.gov` HTTPS directory listings. It followed only links within these two accessions and retained public landing pages, directory listings, family metadata representations, the series matrix, the listed raw supplementary object, and platform family metadata.

The collection-time public HTTPS requests succeeded for the accession pages, discovered directory paths, and the listed object URLs below. This establishes retrieval accessibility at that time only. It does not establish approved institutional custody, authorized readers, redistribution rights, or complete source-family coverage. Object-level terms remain **NOT ESTABLISHED**. This is not a substantive source review, patient-data review, biological analysis, or evidence of institutional authorization.

Detailed byte-level inventory, retrieval timestamps, response metadata, capture mapping, sizes, and full SHA-256 digests are held only in the temporary restricted inspection scratch. They are deliberately excluded from this repository under the existing Prat review-export boundary. Raw source bytes are not included here.

## Official retrieval entry points

- Series record: <https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE93157>
- Series directory: <https://ftp.ncbi.nlm.nih.gov/geo/series/GSE93nnn/GSE93157/>
- Platform record: <https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GPL19965>
- Platform directory: <https://ftp.ncbi.nlm.nih.gov/geo/platforms/GPL19nnn/GPL19965/>

The accession directory listings exposed the following official representations for retrieval:

- GSE93157 matrix: <https://ftp.ncbi.nlm.nih.gov/geo/series/GSE93nnn/GSE93157/matrix/GSE93157_series_matrix.txt.gz>
- GSE93157 family MINiML: <https://ftp.ncbi.nlm.nih.gov/geo/series/GSE93nnn/GSE93157/miniml/GSE93157_family.xml.tgz>
- GSE93157 family SOFT: <https://ftp.ncbi.nlm.nih.gov/geo/series/GSE93nnn/GSE93157/soft/GSE93157_family.soft.gz>
- GSE93157 listed supplementary object: <https://ftp.ncbi.nlm.nih.gov/geo/series/GSE93nnn/GSE93157/suppl/GSE93157_raw_data_values.txt.gz>
- GPL19965 family MINiML: <https://ftp.ncbi.nlm.nih.gov/geo/platforms/GPL19nnn/GPL19965/miniml/GPL19965_family.xml.tgz>
- GPL19965 family SOFT: <https://ftp.ncbi.nlm.nih.gov/geo/platforms/GPL19nnn/GPL19965/soft/GPL19965_family.soft.gz>

These are retrieval routes, not a claim that the selected set satisfies any source-review requirement. The series landing page and directory listings were used to discover these paths. No unrelated study directories were crawled.

## Limits and follow-up

- Per-object and total retrieval caps were enforced; only objects within those caps were retained. No access-control, CAPTCHA, or paywall bypass was attempted.
- Retained compressed objects passed full-stream gzip integrity checks; the two `.tgz` family containers also passed container-structure checks. Full retained-byte hashes and sizes were recomputed after retrieval.
- Source content was not opened for clinical identifiers, sample rows, molecular headers, or values. No patient parsing, canonical mapping, statistics, or biological interpretation was performed.
- A successful public request does not establish redistribution permission. Confirm terms and approved custody/retention authority before any later authorized review or onward transfer.
- Search was limited to the two named GEO accessions and their official linked directories. It does not establish that the accession family is complete or that no corrections, publications, reanalyses, or other relevant source objects exist.
- Retrieval failure or a missing object would apply only to that request and route; it would not establish global absence.

The frozen specifications remain unchanged. Any later source review requires its own authorized custody, scope and terms assessment, and must retain object/member identity and inspection scope as required by the existing source-object checklist.

## Publisher supplement follow-up

The worker subsequently located and retained the public Table S1 attachment from [AACR's Figshare record](https://aacr.figshare.com/articles/dataset/Table_S1_from_Immune-Related_Gene_Expression_Profiling_After_PD-1_Blockade_in_Non_Small_Cell_Lung_Carcinoma_Head_and_Neck_Squamous_Cell_Carcinoma_and_Melanoma/22415270). Its [official API metadata](https://api.figshare.com/v2/articles/22415270) identifies version 1 and links the supplement to article DOI `10.1158/0008-5472.CAN-16-3556`. The item is dated 31 March 2023. That establishes the current repository association, not byte continuity with the original 2017 supplement or a correction history. The public [download endpoint](https://ndownloader.figshare.com/files/39861317) is a retrieval instruction, not an exported file.

The item displays **CC BY 4.0**, linked to the [license](https://creativecommons.org/licenses/by/4.0/). This observed item-level license is distinct from the article's copyright and from the still-unverified terms of other objects. It does not establish institutional custody, actual reader authority or source-review acceptance. No raw supplement bytes are redistributed here.

The full retained file passed size/hash recomputation and the OLE spreadsheet signature check. The orchestrator independently repeated those checks against the retained file and checked the article DOI association in the captured API metadata. No workbook rows, clinical records or molecular values were opened. Detailed capture records remain outside Git; temporary capture is not the sealed common basis or approved retention location. Storage redirect query parameters were not exported. Current item discovery resolves the direct-download locator gap; historical version continuity and substantive source evidence remain unresolved.
