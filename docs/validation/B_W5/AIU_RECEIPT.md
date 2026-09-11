# Paper B corrected W5 AIU validation receipt

Date: 2026-09-11  
Host: existing authenticated SSH alias `omics`  
Isolation root: `/home/omics/projects/ici_thesis_pipeline/planning/2026-09-11/B_W5_aiu_sol_02`  
Canonical server checkout: not read, changed, or used  
Shared environment: not changed

## Transfer boundary and fidelity

Only Paper B code, tests, required specifications, synthetic fixtures, and two B-F1 expected-fixture metadata files were included. The archive excluded Git metadata, `tmp`, `SOURCE_MANIFEST.json`, `docs/research/B_readiness`, real/patient source objects, audit caches, secrets, and credentials.

- Local archive: `E:\Master_Thesis\planning\grok_local_repair\W5_aiu_20260911_sol_02.tar.gz`
- Bytes: 446,857
- Entries: 167 archive entries / 135 extracted files
- Local SHA-256: `bc9d8a47fe7bbe570d51bbfc3927c30ef57dd90b8622d757b2b00db7e4484b41`
- Remote SHA-256: `bc9d8a47fe7bbe570d51bbfc3927c30ef57dd90b8622d757b2b00db7e4484b41`

## Environment

- Python 3.11.16
- NumPy 2.4.6
- SciPy 1.17.1
- scikit-learn 1.9.0
- threadpoolctl 3.6.0
- `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `NUMEXPR_NUM_THREADS=1`, `VECLIB_MAXIMUM_THREADS=1`

## Portability correction discovered

The first isolated attempt (`B_W5_aiu_sol_01`, archive SHA-256 `982be3782562d31ff3a61add05fb1bde95e844ff6616f8c45348d44ceb0dc2ac`) failed because W3 writes `manifest.json` while `FoldFeatureProvider` attempted to read `MANIFEST.json`. Windows' case-insensitive filesystem masked this defect. Production and test fixtures were corrected to use the exact lowercase W3 filename. Local focused post-fix tests passed 15/15 before the second transfer.

## Strict suite result

Command: `/home/omics/miniforge3/envs/omics-py/bin/python tools/check_paper_b.py`

Result: **exit 1; 116 tests run in 41.235 seconds; 115 passed, 1 failed, 0 skipped.**

The sole failure was `test_real_fixtures_all_formats`, which requires retained files under `docs/research/B_readiness/`, beginning with `tcga_a4980c9c-6c37-46da-8db3-c60a1c29081f.tsv`. Those real-source readiness fixtures were intentionally absent under the parent's explicit no-patient-source/no-raw-audit-cache transfer boundary. The test was not weakened, skipped, or misreported as passing.

Therefore: the **full strict AIU gate is blocked by an explicit transfer-scope conflict**, not passed. Either a later authorization must permit the already-approved bounded B-F1 fixtures, or the strict gate must be split into a patient-free portability gate and a separately controlled real-fixture gate. This receipt does neither unilaterally.

## Connected synthetic W5 result

Fresh command in the isolated copied repository:

`python -m tools.b_workflow run --mode synthetic --config specs/B/workflow.synthetic.json --output <isolated-root>/w5_fresh --through W5`

Result: **exit 0**; executed W1-W5; `pipeline_complete=false`; no stderr.

Resume command:

`python -m tools.b_workflow resume --output <isolated-root>/w5_fresh --through W5`

Result: **exit 0**; `executed=[]`; skipped W1-W5; `pipeline_complete=false`; no stderr.

Remote identities/hashes:

- Code identity: `f972087c857ef0ddc14b0c92477af2286f77dea5aa81af3567bb10b6991dc195` (matches the local post-fix code identity)
- Config SHA-256: `77d7e7c7683cd4c88a5ed3cc996e6728de38dc0f02f8ce4b2470937ac6ff4c53`
- W5 bundle checksum-manifest SHA-256: `f135ee0b4fbf1613f50017a7d6e78d2aa42d81918bbe609c0ee27e3f027c9365`
- W5 bundle completion SHA-256: `aadc3093d3e2b0fcaaeb14fbd3b05f7d924b9a20e4a9f58f3db8beba2462dacb`
- W5 stage completion SHA-256: `c380867f98115cb21d2b735c94633552cd8710db5e8fd908a3e6794ace4e7285`

## Disposition

Corrected W5 passes the isolated AIU Python/POSIX connected synthetic run and resume checks. It also exposed and fixed one genuine POSIX filename defect. The complete strict suite cannot be called passed under the simultaneous prohibition on transferring the real B-F1 fixtures it requires.

This is software portability evidence only. It is not a real cohort run, biological result, scientific release, W6 implementation, commit, or push.

## Existing-server fixture closure attempt

A later closure attempt was authorized to use, without any new egress, the four B-F1 fixtures previously copied to AIU under:

`/home/omics/projects/ici_thesis_pipeline/planning/2026-09-07/B_F1_aiu_run_002/repo/docs/research/B_readiness`

The intended action was read-only SHA-256 verification against `docs/validation/B_formats/fixture_manifest.json`, followed—only if all four hashes matched—by an AIU-internal copy into the isolated W5 root and an unchanged strict-suite rerun.

No fixture was read or copied because both SSH attempts failed before authentication:

1. `ConnectTimeout=20`: `connect to host 10.55.205.205 port 22: Connection timed out`.
2. `ConnectTimeout=30`: `banner exchange: Connection to UNKNOWN port -1: Connection timed out`.

No server state changed during these attempts. The 115/116 strict result therefore remains the latest full-suite evidence, while the fresh W1-W5 and resume passes remain valid. Fixture-backed strict-suite closure is deferred until the VPN/SSH route is reachable again.
