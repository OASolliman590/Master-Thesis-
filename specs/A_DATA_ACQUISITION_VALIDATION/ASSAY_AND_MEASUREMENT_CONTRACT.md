# Assay and measurement validation contract

## Purpose

Determine whether an exact assay object is interpretable and structurally compatible with a named branch. This layer validates measurement provenance and structure; it does not select the final biological model.

## Required assay fields

```text
assay_uid
specimen_uid
source sample ID
source object ID
modality/platform/version
genome build and annotation
feature identifier system
measurement unit and transform
normalization/batch processing
matrix column/header
processing history
QC and replicate status
feature coverage and missingness
branch suitability and reason
```

## Universal matrix checks

- exact source object and complete hash;
- dimensions and delimiter/encoding;
- row and column identifiers;
- duplicate rows/columns;
- sample-header and patient/specimen mapping;
- finite/missing/negative values;
- integer-likeness as a consistency check;
- source-documented unit, transform and normalization;
- feature universe and annotation version;
- repeated/identical/suspicious profiles;
- compatibility with the intended branch.

Magnitude heuristics can flag anomalies but cannot override source documentation. If the scale remains unknown, fail closed.

## Count-model eligibility

Require:

- nonnegative counts or a supported estimated-count structure;
- integer or quantifier-compatible representation;
- appropriate library properties;
- feature annotation;
- no incompatible prior normalization;
- no missing-to-zero conversion.

## TPM/FPKM eligibility

Validate:

- complete source feature universe;
- gene versus transcript level;
- quantifier and annotation;
- sum/scale behavior where informative;
- truncation or filtering;
- log transformation state;
- no conversion to integer counts.

FPKM may be used with a compatible continuous-expression method; it is never relabelled TPM without a fully justified conversion based on a complete gene-length universe.

## Microarray eligibility

Validate platform, annotation release, preprocessing, probe-level versus gene-level representation, probe-to-gene policy, batch/source structure and duplicate probes. Probe collapse belongs to a frozen analysis contract, not an undocumented intake default.

## Methylation eligibility

Validate platform, probe IDs, beta/M scale, detection-P provenance, probe filtering, genome build, SNP/cross-reactive/sex-chromosome policy and specimen linkage. Low-quality detection P means high P values under the source method; do not remove low P values by mistake.

## Single-cell/spatial eligibility

Validate object class/version, raw/normalized layers, cell/spot identifiers, patient/specimen linkage, cell-type annotation provenance, batch integration history and availability of donor-aware aggregation. Integrated embeddings are not counts.

## Branch suitability

Allowed suitability labels:

```text
BASELINE_DE
BASELINE_SCORING
PREDICTION_DEVELOPMENT
OUTER_VALIDATION
FINAL_TEST
LONGITUDINAL
METHYLATION
PROTEIN
SINGLE_CELL
SPATIAL
UNSUPPORTED
```

Suitability is evidence-based and branch-specific. No unsupported assay is sent to a default model route.

## Receipt

The assay validation receipt records checks, observed values, status, warnings, blocked branches, code/config versions and object hash. Passing structure does not admit a cohort.
