# Split, independence and prior-exposure validation

## Split roles

Allowed roles:

- `DEVELOPMENT`;
- `INNER_VALIDATION`;
- `OUTER_HELD_OUT_STUDY`;
- `UNTOUCHED_FINAL_TEST`;
- `PREVIOUSLY_INSPECTED_EXTERNAL_VALIDATION`;
- `LONGITUDINAL_ONLY`;
- `PROSTATE_TRANSPORT`;
- `EXCLUDED`.

“External” alone is not a valid role.

## Prior-exposure states

- none documented;
- metadata only;
- expression inspected;
- outcomes inspected;
- used for feature selection;
- used for tuning;
- used for model development;
- used for prior validation;
- unknown.

The ledger records actor/date, source/object/patient set, fields accessed, purpose, model/signature version, reserved role and contamination disposition.

## Untouched final-test standard

`UNTOUCHED_FINAL_TEST` requires no documented or suspected use of its outcomes, expression, outcome-associated features or model performance for current feature selection, threshold selection, tuning or model development. Metadata-only inspection is recorded and may be permitted if the freeze protocol allows it.

A study is not untouched because it moved repositories, changed filenames or received a new local copy.

## Independence checks

Validate and report:

- patient disjointness;
- specimen disjointness;
- originating-study disjointness;
- trial disjointness;
- publication-family overlap;
- repository/atlas derivation;
- prior feature-selection exposure;
- prior model evaluation;
- same cancer/regimen requirements;
- required final-test feature coverage;
- required source contribution.

Unknown material overlap blocks untouched claims.

## Freeze procedure

1. select candidate roles using metadata and prespecified scientific criteria;
2. complete overlap/exposure audit;
3. freeze split version before model performance or outcome-associated feature screening;
4. hash patient membership privately and publish aggregate receipt;
5. prohibit reassignment after performance unless a new exploratory release is declared;
6. retain previously inspected cohorts under their honest role.

## Leakage failures

```text
PATIENT_SPLIT_OVERLAP
SPECIMEN_SPLIT_OVERLAP
TRIAL_ALIAS_OVERLAP
PUBLICATION_FAMILY_OVERLAP
ATLAS_DERIVED_FEATURE_EXPOSURE
OUTCOME_INSPECTION_BEFORE_FREEZE
PRIOR_MODEL_EXPOSURE
FINAL_TEST_SELECTED_AFTER_PERFORMANCE
REQUIRED_FEATURE_MISSING
UNKNOWN_EXPOSURE_FOR_UNTOUCHED_CLAIM
```

## Previously exposed studies

Previously exposed studies can remain valuable for development, sensitivity analysis or transparently labelled external validation. Exposure changes the claim, not necessarily the usefulness of the data.
