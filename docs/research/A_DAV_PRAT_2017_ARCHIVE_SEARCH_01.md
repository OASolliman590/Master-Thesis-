# Prat Table S1: bounded search of publisher archive history

**Checked:** 24 October 2026. **Scope:** public archive indexes and replay of publisher records for the Table S1 supplement associated with Prat et al., DOI [10.1158/0008-5472.CAN-16-3556](https://doi.org/10.1158/0008-5472.CAN-16-3556). This is a locator/history search only. No spreadsheet cells, rows, identifiers, clinical fields, or molecular values were opened or interpreted. It does not change the frozen specifications, establish project custody or source admission, or authorize biology.

## Finding

An archived publisher article page from 6 July 2017 is directly retrievable from the Internet Archive. Its supplementary-material footnote says that supplementary data were available at “Cancer Research Online” and points only to the publisher homepage. The archived page contains no file-level Table S1 hyperlink, filename, attachment ID, or downloadable attachment route. It establishes a 2017 publisher-page snapshot and a generic supplement reference, but it does not identify or preserve the original attachment. [2017 archived AACR article page](https://web.archive.org/web/20170706123733id_/http://cancerres.aacrjournals.org/content/77/13/3540)

The [Wayback CDX index](https://web.archive.org/cdx/search/cdx?url=http%3A%2F%2Fcancerres.aacrjournals.org%2Fcontent%2F77%2F13%2F3540&output=json&fl=timestamp%2Coriginal%2Cstatuscode%2Cmimetype%2Cdigest%2Clength&filter=statuscode%3A200) returned six successful records for the exact issue-page URL, including the 6 July 2017 HTML capture. A prefix query for that page route returned the page and alternate article representations such as `.full`, `.abstract`, and `.short`; it did not return a supplement object. A separate exact query for `/content/77/13/3540/suppl/DC1` returned an empty CDX result. These index results describe the queried URL keys and filters; they do not establish that no differently named attachment URL or publisher history exists.

Several plausible legacy paths were submitted as separate CDX prefix queries: `/content/suppl/2017/05/05/0008-5472.CAN-16-3556.DC1`, that route with `.xls`, `/content/77/13/3540/suppl`, `/content/early/2017/05/09/0008-5472.CAN-16-3556/suppl`, `/content/77/13/3540/DC1`, and `/content/canres/77/13/3540/DC1/embed/inline-supplementary-material-1.pdf`. The AACR-hosted modern supplement route `/cancerres/article-supplement/77/13/3540/619915/` was also checked. These queries did not complete with usable CDX responses: the public index returned read timeouts or HTTP 503. A broad DOI-token wildcard CDX query returned HTTP 503, and the Wayback availability endpoint for the canonical `/suppl/DC1` route returned HTTP 429. Those are service/query failures, not empty archive findings.

As one alternate public-index check, the Common Crawl collection list returned HTTP 200 and included the 2017 collections `CC-MAIN-2017-26`, `-30`, and `-34`. Queries for the article-page prefix against those 2017 indexes returned HTTP 504, 404, and 504 respectively. The 2023-06 index query returned HTTP 504. These responses do not establish whether those collections contain or omit the publisher route; no Common Crawl page body or attachment bytes were retrieved.

## Locator and evidence status

| Question | Result | Evidence grade |
|---|---|---|
| Is an original-era publisher record archived? | Yes. A 2017 AACR article-page replay is retrievable and says only that supplementary data were available at the publisher site. | **Verified publisher-page snapshot.** |
| Does that page identify the original attachment URL or bytes? | No file-level hyperlink, filename, or attachment is present in the retrieved page. | **No locator identified in this snapshot.** |
| Did the bounded route search find an archived attachment? | No attachment snapshot was identified. The `/suppl/DC1` exact query was empty; several additional index requests failed before a usable result. | **Unresolved archive coverage.** Empty results apply only to completed exact/prefix queries; failed requests are not negative findings. |
| Does the current AACR Figshare object prove 2017 identity or continuity? | No. The existing history record documents current item/version/file metadata dated 2023; no original 2017 bytes or publisher-side file history has been found for comparison. | **Current repository metadata only; byte continuity unproven.** |

The relevant current object remains AACR Figshare item `22415270`, version 1, file `39861317`, first posted in 2023 according to its official record ([item page](https://aacr.figshare.com/articles/dataset/Table_S1_from_Immune-Related_Gene_Expression_Profiling_After_PD-1_Blockade_in_Non_Small_Cell_Lung_Carcinoma_Head_and_Neck_Squamous_Cell_Carcinoma_and_Melanoma/22415270), [official metadata API](https://api.figshare.com/v2/articles/22415270)). That association is not an original 2017 attachment locator and does not show byte continuity. The retained copy and hash comparison are documented in the patient-free [retrieval notes](../evidence/A_DAV_PRAT_PUBLIC_INVENTORY_01/RETRIEVAL_NOTES.md); that copy is not represented here as historically original.

## Closure

This search identified an actual 2017 archived publisher page, but it did not identify the original Table S1 attachment URL or retrieve original attachment bytes. The article snapshot supports the publication-era generic supplement statement only. Archive-index errors, rate limiting, and untested or differently named routes leave archive coverage incomplete; therefore this search does not establish that no original attachment snapshot exists. The original locator and byte continuity remain unresolved, and the current 2023 Figshare object must not be treated as the original 2017 file without an independent attachment snapshot or publisher history record.

## Sources

- AACR, [archived publisher article page captured 6 July 2017](https://web.archive.org/web/20170706123733id_/http://cancerres.aacrjournals.org/content/77/13/3540).
- Internet Archive, [Wayback CDX exact-URL query for the issue page](https://web.archive.org/cdx/search/cdx?url=http%3A%2F%2Fcancerres.aacrjournals.org%2Fcontent%2F77%2F13%2F3540&output=json&fl=timestamp%2Coriginal%2Cstatuscode%2Cmimetype%2Cdigest%2Clength&filter=statuscode%3A200) and [CDX search documentation](https://github.com/internetarchive/wayback/blob/master/wayback-cdx-server/README.md).
- Common Crawl, [public collection index list](https://index.commoncrawl.org/collinfo.json); index query outcomes are retained only in restricted temporary scratch because they are operational search logs.
- AACR Figshare, [Table S1 item page](https://aacr.figshare.com/articles/dataset/Table_S1_from_Immune-Related_Gene_Expression_Profiling_After_PD-1_Blockade_in_Non_Small_Cell_Lung_Carcinoma_Head_and_Neck_Squamous_Cell_Carcinoma_and_Melanoma/22415270) and [official item metadata API](https://api.figshare.com/v2/articles/22415270).
- Project's prior [Table S1 public version-history assessment](A_DAV_PRAT_TABLE_S1_HISTORY_01.md) and [patient-free retrieval notes](../evidence/A_DAV_PRAT_PUBLIC_INVENTORY_01/RETRIEVAL_NOTES.md).
