# Usable data repository first — 31 October 2026

User instruction: “turn these data into one data repo that is usable without overengineering and overcomplications”. Follow-up: “after we have a data repo we can make it better”. This records the requested work, not a scientific sign-off or a signature.

Use the existing checkout and the accepted [simple-mode amendment](../../specs/amendments/2026-10-31-simple-mode/AMENDMENT.md). Provide one cohort list, one local build command, and a SQLite/TSV catalogue linking to separate cohort expression and clinical tables. Keep source representations and original labels; record unresolved facts plainly. Preserve existing admissions and never equate a built table with approval for analysis.

The supplied ICBatlas parse can supply a study index. Its study and processing tables contain metadata, not patient matrices. Import those columns only and hash the provided files. The publication is verified as [Yang et al., Cancer Immunology Research, 2022](https://doi.org/10.1158/2326-6066.CIR-22-0249); the provided parse's byte-for-byte provenance to publisher supplements remains unverified. Its entries remain leads until checked against each primary record. Do not import computed response summaries, drug scores, API reconstructions, or the ICBcomb/ICBcDrug website extracts.

All discussed sources stay visible in the cohort registry or resource inventory, including pending and rejected leads. Paper B and single-cell entries are catalogue references only; their production work and unsigned decisions remain separate. IMvigor210 remains UNTOUCHED_FINAL_TEST, including copies in collections. No analysis, new scientific choices, signatures, commits or remote actions are authorized by this record.

Rebuild local table exports from the already pinned sources, preserving any older exports in private runtime archives. Give one review to the completed implementation, run the main tests, and report table dimensions and specific blockers. Future improvements can follow after the first usable repository exists.

## Delivered first version

Nine local expression/clinical table pairs passed source/output hashing and patient-column alignment checks: four admitted exports and five exports pending batch review. The catalogue contains 44 cohort rows, 107 resource entries (including four existing recount3 run representations), and 50 unjoined ICBatlas metadata records. Gide and Kim patient tables remain blocked by unverified identity; missing clinical evidence is listed in [the cohort report](../cohorts/STATUS_20261031.md).

Terra implemented the loader; Luna audited the supplied index and performed the single finished-piece review. The review noted inconsistent raw ICBatlas study keys; they remain explicitly unjoined. A real-build check exposed the admitted receipt's combined expression/patient hash convention; a regression test preceded the correction. The parent reran the real build and final main suite: **646 passed, 3 skipped** across `tests/a_dav_ingest`, `tests/a_dav_implementation`, `tests/a_discovery`, and `tests/a_cohorts`. The focused loader/catalogue suite also passed **21 tests** after the final catalogue label correction. No second review loop was run.

These checks do not turn source uncertainty into biological validation or clear the previously recorded unrelated historical-suite failures. No response comparisons, scoring, model fitting, downloads, Paper B changes, commits or pushes were performed. No user signatures were inferred. Earlier private exports remain recoverable.
