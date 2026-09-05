# B-F1 initial implementation review

6 September 2026, Cairo. Base release: M1 `43efda19bff062a2e9e140fadd84ab32c88cee71`. This is an intermediate review of uncommitted Spark work, not acceptance. No biological analysis ran.

## Actual run and diagnosis

The first `codex-delegate` run used Codex CLI0.153.1, model `gpt-5.3-codex-spark`, workspace-write, session `01a07375-3554-7cd0-bf07-ff0f5c684769`. The orchestrator stopped its identified process tree after the test suite stalled; the relay reports failed, exit4294967295, with no final report. A successful model dispatch is not a passed ticket.

The stalled child was the synthetic CPC methylation CLI, with its output in the default Windows temporary directory. An independent identical-format call with output under the authorized workspace completed immediately. A one-test reproduction exposed `PermissionError [WinError5]` during Python TemporaryDirectory cleanup in the default directory. This explains the observed cleanup failures; it does not identify the precise internal cause of the long-running child. No shared OS permission or global environment setting was changed.

The orchestrator then ran the existing suite using Python3.12 with `tempfile.tempdir` set only for that test process to a workspace folder. Ten tests finished in5.594seconds: eight passed, two failed. The full real-format test stopped at the first STAR fixture, so it did not establish success of all four real formats.

1. Real STAR inspection rejected row3 `tpm_unstranded` as nonnumeric. Direct source inspection verified that all four N_ summary records have empty gene_name/gene_type and empty normalized-expression fields, with populated count fields. Their structural absence needs a separate schema/count classification; it must not authorize empty numeric fields in actual gene rows.
2. The alleged swapped-column test actually supplied correctly paired headers and a short data row. The observed error was wrong width. The regression fixture must genuinely swap a detection-column label while retaining full row width.

## Additional code/spec findings sent for rework

- Protect input/output identity, including aliases, and define atomic existing-output behavior that prevents stale success attribution.
- Check all seven CPC annotation fields, nonempty unique identifiers/sample columns and unique methylation assay pairs. Repeated patient codes across distinct assays remain valid and are not independent patients.
- Restrict missing-header repair to the documented source pattern; reject empty/header-only inputs and malformed blank rows.
- Check SHA argument syntax, gzip bytes regardless of filename, and distinguish output I/O failures from schema failures.
- Report methylation beta and detection-P finite/missing counts separately.
- Bound test subprocess duration and document a portable writable temporary-directory option. Do not suppress failures or call the default-temp run passed.

The same Spark session was resumed with these exact constraints and the original disjoint ownership. Root publication/issue/queue changes shown in the relay's whole-tree status are orchestrator edits, not implementer changes. Final local checks, AIU checks, Opus code review and Astra release remain pending. A recent AIU SSH timeout is recorded; no remote analysis job was started.
