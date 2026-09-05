# D proposed software and environment contract

**PROPOSED / NOT IMPLEMENTATION-READY — v0.1.** No project adapter or benchmark workflow exists. Module names below describe intended interfaces, not installed commands. Upstream helpers must pass the scientific contract before use.

## Architecture and seams

One high-level acceptance seam: a **sealed benchmark bundle** is either rejected with typed reasons or evaluated to traceable paired-error outputs. Internally: source resolver → metadata/identity validator → eligibility/overlap report → frozen input builder → independent model/baseline prediction workers → sealed-outcome evaluator → figure/provenance exporter. The model worker cannot read held-out treated expression. The evaluator cannot choose checkpoint, features or baseline. Keep that information boundary enforceable through explicit inputs and filesystem permissions where available.

Workflow DAG: source/terms review → metadata join → eligibility and checkpoint compatibility → precision and split freeze → environment reproduction → approved inference → paired evaluation → reviewed manuscript artifacts. Compatibility development may use the released nonprostate split; it is labelled `software_reproduction` and has a distinct manifest/run type. The production DAG remains closed until all gates pass.

## Input schemas

All contracts require `schema_version`, source provenance and checksum. Missing is an explicit null with a reason, never a fabricated zero.

| Entity | Required fields / types | Invariants |
|---|---|---|
| Source file | `source_id`, `origin_study_id`, `release`, `url/access_route`, `relative_path`, `sha256`, `bytes`, `modality`, `terms_url`, `redistribution_status`, `verified_at` | A retrieved object cannot change silently at an unchanged version key. No credentials/signed access tokens. |
| Biological sample | `sample_id`, `source_sample_id`, `origin_study_id`, `experiment_id`, `biological_unit_id`, `plate_id`, `context_id`, `species`, `tissue`, `role`, `control_group_id`, `time_value/unit`, `identity_status`, `qc_status` | Unique source mapping. Independent-unit evidence required, not derived from barcode count. Roles train/development/test_control/test_treated cannot overlap. |
| Condition | `condition_id`, `drug_id`, `structure_id`, `parent_salt_policy`, `dose_value/unit`, `time_value/unit`, `context_id`, `checkpoint_label`, `mapping_evidence` | Exact supported label and semantic identity; no nearest-dose mapping. |
| Cell observation | `cell_id`, `sample_id`, `biological_unit_id`, `condition_id`, `is_control`, quality annotations | A cell belongs to one sample; technical re-exports deduplicate by source lineage. |
| Feature map | `feature_index`, `model_gene_id`, `source_gene_id`, `id_namespace/version`, `measurement_status`, `transform_id` | Full ordered primary output space; no duplicate/ambiguous map or inferred test feature. |
| Checkpoint | `repository`, `revision`, `checkpoint_path/hash`, config/map hashes, code commit, output-feature hash, `training_manifest_hash`, `overlap_status` | Config, weights and saved maps from the declared run; unknown overlap not unseen. |
| Split | `unit_id`, `role`, `source_ids`, `assignment_reason`, `seal_timestamp/hash` | All related condition cells/replicates remain together; source-control links explicit. |

AnnData is the intended native input container. `obs` holds stable sample/context/condition keys; `var`/a separate immutable feature table supplies identifiers and order; `obsm['X_hvg']` is used only if verified identical to the checkpoint's expected representation. `X` must not be assumed to hold predictions after upstream inference: extract and verify the documented output field for the pinned model and CLI. Neither L1000 z-scores nor expanded bulk rows satisfy this schema merely by being saved as `.h5ad`.

## Output schemas

| Artifact | Required content |
|---|---|
| `eligibility_report` | Every candidate condition, pass/pending/fail, typed reasons, counts at source/sample/biological-unit/condition/drug levels, feature coverage and overlap status. |
| `run_manifest` | Run type; spec/code/environment/input/checkpoint hashes; seed; host resources; timestamps; scheduler/session handle; phase status; logs; artifact hashes. |
| `predictions` | `model_id`, `condition_id`, `biological_unit_id/control_input_set_id`, feature IDs, predicted treated mean and basal mean, status; no truth column. |
| `paired_errors` | Observed delta, State delta, baseline delta; losses/gain; drug/condition/replicate/gene weights; provenance join keys. |
| `primary_result` | Theta, constituent losses, all denominators, interval method/validity or explicit unavailable reason; frozen analysis hash; no pass/fail based solely on sign. |
| `reproduction_bundle` | Permitted aggregate outputs, source retrieval manifests, environment lock, command transcript, failures/deferred checks, figure source tables and reviews. |

## Pinning and compatibility

The inspected upstream commit is `9bbfe78a434a55205e4de834e1ea99f85f7a3add`; its `pyproject.toml` declares **arc-state 0.11.3** and Python **>=3.11,<3.13**. This is a verified source pin, not an executed lock. The candidate checkpoint is separately pinned by repository revision and path. [Pinned package](https://github.com/ArcInstitute/state/blob/9bbfe78a434a55205e4de834e1ea99f85f7a3add/pyproject.toml).

`environment.contract.json` records upstream minimum dependencies and unresolved environment fields. Minimum constraints are not resolved transitive pins. Before any accepted run, resolve the environment on AIU without disrupting existing jobs, record exact Python/Torch/CUDA/driver/dependencies, run import/CLI/model loading checks, and export a reproducible lock plus a built container digest if container execution is selected. Container base, package resolver version and memory/runtime remain unknown; do not invent digests or claim a GPU allocation from a model card. Validate whether the 2026 package commit loads the separately released checkpoint; coinciding version dates do not prove compatibility.

The inspected CLI source documents `state tx infer` arguments `--model-dir`, `--checkpoint`, `--adata`, `--embed-key`, `--pert-col`, `--celltype-col`, `--batch-col`, `--control-pert`, `--seed`, and `--output`. The run directory expects config, dimensions and saved mappings. This interface is documented, not executed here. [Pinned CLI](https://github.com/ArcInstitute/state/blob/9bbfe78a434a55205e4de834e1ea99f85f7a3add/src/state/_cli/_tx/_infer.py).

Unknown-label fallback, unmatched control fallback, unchanged rows and output placement require explicit adapter assertions. A process exit of zero cannot bypass them. Upstream metadata/code licences and model/output licences are reviewed independently. No untrusted pickle execution is needed for the current documentation audit; any eventual checkpoint loader uses verified source and content with a reviewed loading policy.

## Resources and restart

AIU is principal execution host. Begin with metadata checks and an explicitly capped reproduction job only after host inspection; the feasibility allocation is 15 researcher-hours, not permission for unbounded training. CPU threads, RAM, GPU/VRAM, wall time, disk quota and scratch paths are mandatory run-manifest fields to discover before allocation. No new model training is included.

Resume by immutable stage keys `(spec, code, environment, input, checkpoint, seed)` and verified output hashes. Write to temporary outputs then atomically publish complete stage artifacts. Changed keys invalidate dependent stages. On VPN loss, preserve job handle and mark local observation `unknown`; inspect the same remote job before retrying. Queue exact deferred commands and expected artifacts. A partial run must never produce a completed benchmark status.
