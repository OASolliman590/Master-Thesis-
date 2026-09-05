# D reproduction and readiness

**PROPOSED / NOT IMPLEMENTATION-READY — v0.1.** There is currently nothing to reproduce as a completed D analysis. These steps define the eventual deliverable and the evidence required to reopen execution. No package has been installed or checkpoint run by this kit.

## Research gates

| Gate | Exact evidence required to pass | Current state / next action |
|---|---|---|
| G1 Native prostate ground truth | An accessible source accession plus full eligible condition/control/biological-unit manifest and source-backed modality/identity; real measured prostate treatment outcomes | **Open:** no qualifying joined dataset. Execute D-R01. |
| G2 Semantic compatibility | Full ordered native output gene IDs, preprocessing transform/version, supported structural drug/dose identity, compatible duration, valid matched controls, representative real input checks | **Open:** dimensions/config exist; features/transform/eligible exposure joins unresolved. D-R02. |
| G3 Independence | Exact checkpoint weights hash linked to training sources/splits, test sample/experiment lineage audit and all overlap categories resolved for the intended claim | **Open:** released nonprostate split is insufficient. D-R02. |
| G4 Primary baseline availability | Auditable matched training effects for every primary supported label/duration, equal-context construction and no test-row contamination | **Open:** original training response rows not established. D-R02; no substitution to weaker baseline without amendment. |
| G5 Statistical freeze | Exact eligible sets and clusters; reviewed precision assessment with delta_min/h_target; justified uncertainty design; primary/secondary preregistration frozen before test outcomes | **Open:** dataset, precision and cluster structure unknown. D-R03. |
| G6 Terms and resources | Selected code/model/data/output terms and permitted artifact policy; AIU CPU/RAM/GPU/disk/runtime inventory and allocation plan | **Open:** terms differ by asset; runtime budget unresolved. Review before data/weight acquisition. |
| G7 Software compatibility | Exact resolved environment; documented CLI smoke; candidate checkpoint load and known-label reproduction with matched controls/features and verified output field | **Not run.** Nonprostate reproduction may satisfy only this software gate. |
| G8 Programme and review release | All four kits independently reviewed; D's material decisions approved; prior-paper sequence respected; Opus findings resolved and Astra final disposition recorded | **Pending.** This draft is not an approval. |

G1–G5 are prerequisites for scientific production coding; a separately reviewed bounded feasibility adapter/reproduction ticket may establish G7 without claiming D implementation. No inference on prostate is released until all eight gates pass. Missing facts remain open rather than being converted into design assumptions. A recommendation to defer at the 15-hour feasibility cap is an agenda item for the user, not automatic goal completion.

## Reproduction workflow once released

1. Check out the exact reviewed commit, read accepted D decisions and verify source/config/checkpoint manifests. Restore permitted data through documented source routes and validate hashes; do not expect large data in Git.
2. On AIU, inspect existing host/scheduler state. Resolve and validate the environment according to SOFTWARE_CONTRACT, retaining its exact package lock and runtime/container identity. Store authentication outside the project and logs.
3. Run the bundle eligibility validator. Review its full candidate attrition, identity, controls, units, feature order, overlap and baseline availability. An eligibility rejection is an explicit stop with evidence, not a prompt to force a dataset into the model.
4. Freeze the test manifest and primary contract. Export baseline effects using only permitted training rows. Keep test outcomes inaccessible to inference/model selection.
5. Run the approved State adapter with the exact selected checkpoint, basal cells, supported labels and seed. Capture actual invocation and validated output-field extraction. Upstream CLI arguments are documented in SOFTWARE_CONTRACT, but a copy-paste scientific run command cannot be supplied until real paths/input contracts are verified; no invented `run_D` command exists.
6. Evaluate paired errors using the frozen formula, produce figures and independent numerical verification, and review claim limits. Archive failures and nulls with the same completeness as positive results.
7. Publish reviewed code/spec/allowed aggregate artifacts to the verified private repository; synchronize AIU by commit; update Notion with actual commit, tests/deferred tests, reviews and next action. The orchestrator owns publication.

## Expected artifacts and completion evidence

- Versioned all-source manifest and terms record; complete analysis-specific sample/condition/control/feature/split manifests.
- Candidate checkpoint hash and training lineage, original config/map hashes, selected package/code revision and resolved environment.
- Prior-exposure and preregistration record; accepted decisions and explicit amendments.
- Real eligible baseline/truth/prediction data in authorised storage; source retrieval instructions and hashes in Git.
- Eligibility/failure report, primary baseline effects, replicate-level paired errors, theta/constituent losses/denominators, justified uncertainty or descriptive-only limitation.
- Four figure source tables and rendered figures; secondary analyses distinguishable from primary.
- Successful actual test commands/results, independent numerical check, Opus review plus Astra resolution; AIU run IDs and restart history.
- A second clean invocation that reconstructs the declared outputs from fixed inputs, with tolerances justified for GPU/stochastic computation; identical scientific decisions and denominators are required even when exact floating-point identity is not.

## Honest status and interruption handling

Design categories: **drafted**. Independent spec review: **pending**. Data/checkpoint compatibility: **unresolved**. Environment lock: **not resolved**. Production implementation: **not started**. Real-data smoke: **not run**. Figures/results: **not generated**. GitHub issue/publication and Notion update for this kit: **orchestrator pending**.

If VPN fails, record commit/environment, requested commands, expected artifacts, last known live job ID and timestamp in the programme's pending-validation queue. Check the same remote handle when connectivity resumes. Continue documentation/review work; do not move training to another server or restart a possibly live job. A source/config file on disk does not establish an active process. Deferred tests cannot satisfy readiness.

Completing a conditional kit is not implementing D. A nonprostate reproduction or an unavailable-data disposition cannot satisfy the prostate benchmark objective unless the user explicitly accepts a change. Preserve the complete programme goal and the unresolved work.
