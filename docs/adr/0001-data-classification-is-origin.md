# Data classification records data origin, not whether checks passed

The DAV stages originally used one value, `SYNTHETIC_ONLY` / `SYNTHETIC_READY`, written into about 13 modules. That value meant both "this data is invented" and "the checks passed", and as a result the pipeline rejected every real source by construction.

Decided on 25 Oct 2026:
- `data_classification` holds only the data's origin. The allowed values are owned by `core` and use the frozen schema enums: `SYNTHETIC_ONLY` for tests and `PRIVATE_PATIENT_LEVEL` for real cohorts.
- A separate status field records the result of the checks.
- Stages copy the incoming packet's classification and never write it themselves.
- Synthetic data is kept as the test classification and is not deleted.
