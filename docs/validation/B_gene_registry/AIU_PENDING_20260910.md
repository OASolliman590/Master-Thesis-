# B-G1 AIU portability gate pending

**Attempted:** 2026-09-10T15:59:00Z

**Resolved:** VPN connectivity was restored and the later bounded run passed. See [AIU_20260910.md](AIU_20260910.md). The timeout account below is retained as immutable attempt history.

This is a connectivity/deferral receipt, not an AIU validation result and not a scientific-analysis run.

The parent attempted one bounded, non-interactive SSH preflight against the existing authenticated alias `omics` with a 10-second connection timeout. The intended read-only preflight was to report `/home/omics/miniforge3/envs/omics-py/bin/python --version` and verify that the unique proposed scratch root `/home/omics/projects/ici_thesis_pipeline/planning/2026-09-10/B_G1_aiu_6395bb4` did not exist.

Result: SSH timed out connecting to `10.55.205.205:22` before authentication. Exit was non-zero. No remote command ran, no scratch directory or process was created, and no file was transferred. Therefore B-G1 AIU/Python 3.11 portability remains **pending**. The parent-accepted local Python 3.12 synthetic checkpoint is unchanged.

No real cohort data, CPC outcome, patient/sample/value table, score, probe selection, model, network retrieval beyond this SSH connection attempt, or external application update occurred.
