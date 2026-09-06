# TCGA ABSOLUTE source and candidate linkage audit

6 September 2026 (retrieved 5 September 23:31 UTC). Source-field and identifier audit only; no new molecular matrix, score, regression, calibration or biological result.

The original [GDC PanCan Cell-of-Origin publication page](https://gdc.cancer.gov/about-data/publications/PanCan-CellOfOrigin), linked to [Hoadley et al. 2018](https://doi.org/10.1016/j.cell.2018.03.022), provides the small public ABSOLUTE purity/ploidy table. Retrieved complete object: `TCGA_mastercalls.abs_tables_JSedit.fixed.txt`, UUID `4f277128-f793-4354-a13d-30cc7fe9f6b5`, 901,812 bytes, SHA256 `f430a975433d82e0098d7405619d4f12a0c765fcd97e7d63cc9b1de7f2d763cd`. No authentication or controlled-access route was used. The source object stays outside Git; retrieval instructions and aggregate audit are retained. Public availability is not a general redistribution licence.

## Fields and counts

The actual header contains distinct `purity`, `ploidy` and `Cancer DNA fraction` columns alongside `sample` and `call status`. Use the source-defined `purity` field for an ABSOLUTE cellularity candidate. The DNA-fraction column is not an interchangeable alias; see the separately reviewed original-method comparison. No cross-method conversion is performed.

The table has10,786 rows. The existing paired-candidate metadata has497 TCGA-PRAD cases and501 shared sample-vial identifiers. Its file inventory is exclusively the inspected open STAR-Counts expression and SeSAMe/450K beta workflows, but it remains a before-QC candidate manifest.

| Join level | Rows | Distinct cases | Meaning |
|---|---:|---:|---|
| Case prefix only |486|485|Includes one metastatic sample from a case also represented by a primary sample.|
| Exact shared sample-vial prefix |485|485|All primary-tumour type01.|
| Shared sample-vial, literal status `called` |469|469|Finite purity0.16–1.00 and ploidy1.79–4.39.|
| Shared sample-vial, blank status |16|16|Purity/ploidy/DNA fraction blank; no imputation or failure-cause assignment.|

Twelve of497 candidate cases have no table row;28 have no called row. Of501 candidate sample-vials,32 have no called matching row. These are coverage counts, **not final eligible N**. Numeric field existence does not establish valid specimen linkage or a defensible cross-cohort covariate.

## Barcode boundary

[GDC barcode documentation](https://docs.gdc.cancer.gov/Encyclopedia/pages/TCGA_Barcode/) distinguishes participant, sample, vial, portion, analyte and aliquot. The existing16-character keys include the vial. A matching16-character prefix supports that hierarchy level; it cannot prove a shared portion or exact DNA/RNA aliquot. The original ABSOLUTE table's full aliquot IDs permit a later explicit portion/analyte join against the selected molecular files. That join was not done here. Clinical/pathology completeness and any accepted specimen policy also remain open.

Some pan-cancer source `sample` entries are not full TCGA aliquot barcodes. The audit validates the full barcode pattern before reporting hierarchical whole-table counts; all486 case-linked PRAD rows have valid full barcodes. It does not interpret arbitrary source identifiers by blindly slicing them into TCGA sample types.

## Contract consequences and reproducibility

B-E4 has a concrete TCGA source/field and469 called sample-vial candidates. This closes an availability subquestion, not the full purity gate. No choice between B-P and B-R is made. Valid-call policy, specimen granularity, missingness/precision and Qpure/ABSOLUTE measurement comparability remain required. Retain the excluded portal WGS-agreement field prohibition.

`retrieve.py` retrieves at most3MB from the exact public URL, saves the complete object and a hash receipt. `audit.py` reads that object and the canonical `docs/research/B_paired_prostate/summary.json`; it writes only aggregate `summary.json`. Their current paths assume the original E:\Master_Thesis audit layout; they are source-audit helpers, not portable production commands. No AIU runtime test or biological validation is implied. The original source table and candidate metadata hashes are recorded in the summary.
