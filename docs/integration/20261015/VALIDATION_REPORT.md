# Fresh integration verification — 15 October 2026

Specification/schema/reference tests pass after two packaging compatibility fixes. The standard applicable B regression is **not fully passing**: its real-format fixture is absent. No cohort, fitted biological model, AIU environment or execution/result release is validated here.

| Command/suite | Fresh result | Scope |
|---|---|---|
| `python -m unittest discover -s tests/a_a1_spec_contract -v` | 38 passed | Current A/A.1/DAV schemas, false-readiness, UNKNOWN, episode binding and synthetic estimand checks |
| `python -m unittest discover -s tests/a_data_acquisition_validation -v` | Initial 1 failure + 1 error; after correction 10 passed | Preserved standalone predecessor version, including original internal payload hashes |
| `python -m unittest discover -s specs/C/revision_20261015/tests -v` | Initial 1 failure + 2 errors; after path correction 10 passed | C framework, matched-query contract, schema examples and links |
| E qa / qa_v2 / E_LAST qa, separate PYTHONPATH | 50 / 42 / 42 passed | Synthetic declared-contract reference checks; no PBPK/QSP biology |
| Local recovered A `python -m pytest tests/a_intake -q -p no:cacheprovider` | 23 passed, 4.97 seconds | Existing sibling checkout synthetic intake, commit d574f8ae; code unmodified |
| Initial local A unittest discovery | 0 tests, exit 5 | Wrong discovery mechanism; not counted as pass; subsequently pytest used |
| `python tools/check_paper_b.py` | 147 tests in 181.062 s: 145 passed, 1 failure, 1 error, zero skips | Standard strict existing B regression; no code changed |
| B acquisition subset rerun with localhost permitted | 7 passed | Resolves sandbox socket bind limitation only; does not erase full-suite failure |
| Freeze verifier adversarial suite | 3 passed | Missing/empty manifest and content mutation reject release |
| `python docs/integration/20261015/verify_integration.py` | 94 schema definitions, 16 D examples; final links/hash receipt separately logged | Read-only integrated document checks |

B remaining fixture failure: `tests/b_formats/test_bf1_cli.py::test_real_fixtures_all_formats` cannot read `docs/research/B_readiness/tcga_a4980c9c-6c37-46da-8db3-c60a1c29081f.tsv`. Other real-format fixtures in that test were not reached and are not thereby verified. Fixture bytes and source contracts require separate recovery; fabricated replacements are forbidden. Initial acquisition error was `PermissionError` binding 127.0.0.1; the unchanged acquisition suite passed outside the network sandbox. The complete strict suite was not rerun after this environment-only subset check, so do not report 147/147.

Packaging fixes preserve scientific intent: C test now references the actual supplied docs/plans path; predecessor DAV tests target the preserved predecessor tree instead of asserting its old manifest shape against integrated v1.1. Current v1.1 has its own 38-test suite. Original imported source bytes remain in the import commit/archive provenance. Imported historical logs were not relabelled as fresh. Initial diff whitespace check reported 334 source trailing-whitespace/CRLF warnings; these are recorded, not silently normalized.

Archive checks: four supplied scientific ZIPs match expected external hashes; A decision handoff is a different package; master handoff hash is computed-only. Original C/D/E checksum payloads: 39/111/233 match, zero mismatches. Original DAV: 75 match after explicit absent-wrapper mapping, self-checksum fails. A recovered DAV overlap exactly reproduces 65 equal, 2 changed, 15 added, zero standalone-only. Historical NMRbox source manifest is recomputed in RECOVERY_FINGERPRINTS.json; live server/private fixture state remains UNKNOWN. Corrected integration hashes exclude their own manifests.

Environment: isolated temporary venv, Python 3.12.14. Exact installed package versions are in logs/environment.lock.txt. No shared environment modified. JSON Schema 4.26.0, referencing 0.37.0, pytest 9.1.1; scientific numeric dependencies were installed solely for existing synthetic B tests. Temporary synthetic B outputs under tmp/ are excluded from publication. Logs are sanitized for local absolute paths, retaining actual error types and assertions.

No production data, fitting, GPU work, remote scientific job or full historical pipeline rebuild occurred. Current tests do not certify cross-record episode semantics in an unimplemented adapter, numerical scorer parity, clinical linkage or biological validity. Those remain explicit next-packet gates. Legacy risks are historical/static unless a pinned original function has a fresh adversarial reproduction; no such new defect claim is made here.
