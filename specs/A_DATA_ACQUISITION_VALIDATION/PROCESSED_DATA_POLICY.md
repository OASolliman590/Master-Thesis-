# Processed-data policy

## Default

Use the most interpretable source-deposited processed object that preserves the variables required by the branch and has traceable provenance. Processed-first is a scientific and operational default, not permission to accept undocumented matrices.

## Potentially eligible representations

- raw integer counts;
- supported estimated counts with quantifier/import metadata;
- complete gene-level TPM;
- complete gene-level FPKM/RPKM, with appropriate downstream method and no conversion to counts;
- normalized log expression with documented transform;
- microarray expression with platform and preprocessing metadata;
- methylation beta or M values with platform/QC provenance;
- protein abundance with assay and normalization provenance;
- processed single-cell or spatial objects with original counts/metadata where required;
- study-level summary effects when patient-level data are unavailable, assigned only to a compatible summary-evidence branch.

## Prohibited transformations and assumptions

- rounding TPM/FPKM into counts;
- treating FPKM as raw counts;
- fabricating TPM from an incomplete feature universe;
- converting missing genes to zero;
- reversing an undocumented transform;
- treating integrated embeddings as expression counts;
- inferring patients or endpoints from group totals;
- joining samples because names look similar;
- transferring a unit or normalization description from an older file to a replacement file without verification.

## Object selection hierarchy

For each study and modality:

1. original-author processed object tied to the publication;
2. official repository object with version/history;
3. author repository or institutional archive with pinned revision;
4. curated resource object only after original-study reconciliation;
5. raw reprocessing only through amendment.

Multiple representations may be retained for audit, but one named branch representation must be frozen before analysis.

## Raw-data amendment

FASTQ, BAM/CRAM, IDAT, raw mass-spectrometry or image reprocessing requires a versioned amendment containing:

- blocked branch and why processed routes fail;
- expected information gain;
- source terms and access authority;
- compute/storage estimate;
- validated pipeline and reference versions;
- source-specific sample sheet and identity strategy;
- QC and failure criteria;
- reviewer and user approval;
- plan for comparing the raw-derived object with available processed data.

Raw availability alone is not sufficient justification.

## Retrieval receipt

A complete object retrieval records:

```text
source_object_id
exact URL/access route
repository/accession
filename and source version
retrieval UTC
HTTP/repository metadata where available
byte size
complete SHA-256
compression and content type
license/terms/redistribution status
retrieval code/config versions
partial/full status
validation status
```

A prefix or header hash must be labelled as such and cannot populate the complete-file hash field.

## Version drift

When a repository replaces an object:

- preserve the prior object record;
- create a new source object ID/version;
- record replacement date and repository evidence;
- rerun header, identity, scale and coverage validation;
- do not silently rebuild a frozen matrix from the new bytes.
