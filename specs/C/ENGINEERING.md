# Paper C engineering and reproduction contract

Version 0.1, 5 September2026. **Proposed interfaces; no production implementation exists.** Read README, DATA, ANALYSIS and VALIDATION_AND_FIGURES together. References to future commands, schemas and tests are acceptance requirements, not claims of completed code or validated results.

## Module boundary and execution order

Proposed public interface: `python -m thesis.paper_c audit --config <config.json> --out <run_dir>` and `python -m thesis.paper_c run --config <frozen_config.json> --out <run_dir>`. Audit mode reads metadata and definitions only; it must not read perturbation effect values or tune a query. Production mode admits only a reviewed B handoff, a frozen C analysis configuration, hash-pinned data and a validated scorer. Neither command is implemented yet.

Use these explicit stages: source registry → canonical identity and instance graph → condition coverage → B query/feature-universe admission → pinned matrix extraction → raw WTCS → compound/condition descriptive aggregation → separate context/validation/PK adapters → source-data tables and figures. An unavailable contextual source emits a typed status and reason. It does not silently erase that arm or make the primary calculation fail unless the frozen specification names it as required for the relevant claim.

Keep source parsing behind narrow adapters. The scoring module accepts numeric vectors and a frozen ordered feature universe, never a database name or an implicit query-direction convention. The integration module joins annotated evidence with source and context labels; it must not convert unlike species, interventions and outcomes into an unexplained weighted confidence score. Paper D predictions cannot enter C's measured-validation field.

## Required data contracts

Use versioned UTF-8 TSV or JSON metadata, explicit types and units, and immutable originating-study IDs. Identifiers remain strings. Missing numeric values are null, never zero; legitimate identifier strings are not subject to a parser's default NA vocabulary. Matrix format/scale and separate row/column identity manifests are mandatory.

| Artifact | Primary key and required fields | Fail-closed invariant |
|---|---|---|
| source_registry | source_id, origin_study_id, release, original_url, checked_at, retrieved_at, bytes, sha256, access_status, license, redistribution_status, assay, scale, locator | Unknown hashes remain null; failed HTTP is not biological absence; no signed/session URLs |
| compound_identity | source_id+source_compound_id; original_name, aliases, canonical_parent_id, full_InChIKey, structure_source, salt/batch, mechanism, mechanism_reference, curation_status | No fuzzy-name-only merge; parent/structure decisions reviewed; raw MOA preserved beside corrected annotation |
| model_identity | source_id+source_model_id; cell_iname, Cellosaurus/ACH/COSMIC when available, species, tissue, model_type, origin_study_id | Identity match does not imply assay coverage; ambiguous models remain unresolved |
| signature_metadata | release+sig_id; pert_id, cell_iname, exact pert_dose/unit, pert_time/unit, rounded label, project_code, nsample, qc_pass, is_hiq, tas, distil_ids, collapse_weights | Exact dose distinct from rounded label; input metadata must match matrix column; replicate count agrees with instance list or emits discrepancy |
| instance_membership | release+sig_id+instance_id; plate, well, original profile ID, origin_study_id, experiment_id when supported | Cross-release alias/instance overlap is explicit; missing biological experiment identity is not inferred from well count |
| query_handoff | query_id+gene_id; disease_axis, disease_direction, expression_effect, methylation_effect, association_model, B_discovery_split, gene/probe/build versions, selection_rule, provenance | B validation or C effects cannot choose genes; UP and DOWN both nonempty, disjoint; whole bundle has immutable hash |
| feature_universe | universe_id+ordered_gene_id; original row ID, gene_symbol, landmark/best_inferred/inferred/absent, mapping_version | Order, duplicates and full-universe ranks fixed; absent features cannot be padded as observed zeros |
| coverage | source×compound/target×model×exposure×assay; state, n_observations, independent_unit, n_independent, reason, source hash | `catalogued`, `measured`, `qc_pass`, `usable`, `not_screened`, `access_blocked`, `unknown` remain distinct |
| signature_score | query_id+sig_id+scorer_commit; ES_up, ES_down, WTCS, reversal=-WTCS, universe_hash, QC, project, status/reason | Finite[-1,1]; invalid query/vector is an error, not successful zero; WTCS never called tau |
| compound_condition | canonical_compound+query+cell+exact exposure; eligible signature IDs, n_signature, n_instance, n_experiment_known, mean_reversal, aggregation_rule | Explicit finite-release descriptive mean; no unjustified biological CI or treatment-superiority p-value |
| context_evidence | source+original contrast+target/compound+model; intervention, control, species, condition, endpoint, effect/scale, unit, replication, mapping, independent_of_discovery | Genetic knockout, drug inhibition, cytokine reference and patient association remain different interventions |
| PK_annotation | molecule+source_document+regimen; formulation, route, time, total/free concentration, unit, protein binding method, active metabolite, uncertainty, source locator | Unknown free medium/tumour exposure stays unknown; no dose recommendation or universal Cmax threshold |
| run_manifest | run_id; commit, spec/config/input/output hashes, environment digest, RNG/seed, stage statuses, timestamps, job handle, logs, pending_validation | Complete only after required outputs/checks; interrupted runs cannot be relabelled passed |

Schema names above are proposed. Ticket C01 implements their machine-readable forms and validators after scientific review; this kit does not fabricate JSON schemas that appear tested.

## Scorer reference and numerical semantics

Reference: [official cmapM](https://github.com/cmap/cmapM/tree/8f0e7bc4c38efbdf3f96f5ac72ee26792907a99c), inspected commit `8f0e7bc4c38efbdf3f96f5ac72ee26792907a99c`, README version2.0.0. Call path: `runCmapQuery → computeCmapScore → cmapScoreCore → fastESCore → getCombinedES(...,false)`. Use the inspected query implementation, not the similarly named standalone `fastWTCSCore` file. Local source evidence/hashes: `docs/research/C_lincs2020_readiness/{methods_manifest,core_methods_manifest,artifact_checksums}.json`.

The combiner computes half the ES difference and zeroes it when `sign(ES_up)==sign(ES_down)`. Thus one exact-zero ES and one nonzero ES retain half the difference. No across-query rescaling is applied. The fast ES implementation compares pre-hit versus post-hit absolute values with strict `<`, preserving post-hit on equality, then uses the first absolute maximum. The upstream rank-generation convention for tied z values still needs direct numerical verification; it must not be guessed from the displayed WTCS formula.

Official [QueryL1k options](https://github.com/cmap/cmapM/blob/8f0e7bc4c38efbdf3f96f5ac72ee26792907a99c/sig_tools/resources/mortar.sigtools.SigQueryl1k.arg): `--metric wtcs`, `--es_tail both`, `--up`, `--down`, `--score`, `--rank`, `--sig_meta`, `--ncs_group`, `--max_col`. Whole-universe ranks must accompany scores; extracting only query rows and reranking them changes the statistic. `sig_id` must be adapted to the documented first metadata column. Empty/full-universe queries, all-zero hit weights, nonfinite values and overlapping signed sets are rejected by our contract even where upstream helpers provide permissive fallbacks.

Raw WTCS is the primary numerical layer. QueryL1k normalized scores depend on a frozen reference set and grouping; FDR depends on null signatures. Global normalization is the documented default; missing reference flags may fall back to all signatures and normalization NaNs may become zero. An adapter must block these states. If secondary NCS/FDR are implemented, first validate complete reference strata and control compatibility. Historical tau additionally needs its reference query-score distribution and is not promised by this kit. [Official outputs](https://github.com/cmap/cmapM/blob/8f0e7bc4c38efbdf3f96f5ac72ee26792907a99c/docs/SigToolDemo.md).

## Environment and resource contract

`environment.contract.json` deliberately has `lock_status=pending` and null lock/container digests. Existing AIU Python3.11.16 is verified for metadata work; this does not establish the scoring runtime. No MATLAB/Octave executable was found on the inspected PATH. Docker is present but daemon permissions, compiled-tool availability, image digest and runtime numerical equivalence remain untested. The [official Docker demo](https://cmap.github.io/cmap-sig-tools/docker_demo/) documents `cmap/sigtool-runtime`; no mutable `latest` reference can serve as the final lock. cmapPy is an I/O option, not a verified scoring engine; its original repository reports discontinued active maintenance.

Choose an isolated environment after a small reference smoke. Freeze exact interpreter/package/build hashes, scorer source and compiled/container digest, OS/architecture and recreation instructions. Do not alter shared AIU environments. Any Python reimplementation is conditional on numerical parity with pinned reference fixtures. Proposed parity tolerance is absolute1e-7, a reviewable engineering choice to be justified against output precision; an unexplained larger discrepancy blocks scoring. Pin workflow/testing/plotting packages only after API verification; no invented package versions belong in a lockfile.

Start CPU-only with one worker/thread and a tiny compatible matrix slice. Measure memory/runtime before increasing chunk size. Full L1000 matrices require a separately reviewed acquisition/storage plan, exact original object URL and matrix/metadata concordance; the completed465MB metadata stream does not authorize guessing a Level5 matrix filename. A bounded range/subset route must preserve gene-universe and signature IDs. No GPU is needed for WTCS.

## Acceptance tests

1. Direction oracle: a constructed disease-copy profile is concordant and a constructed inversion gives the reversal extreme; also verify sign of the final negative-WTCS output. These fixtures test code, not drug biology.
2. Numerical parity: independently generated finite profiles against pinned reference, including exact-zero ES, equal absolute extremes, z ties, same-sign ES and one-direction-only invalid queries. Assert no accidental rescaling or normalization.
3. Identity/coverage: E-7438 resolves to the audited tazemetostat identity; BIX-01294 raw DNMT label is flagged; azacitidine source IDs do not automatically become independent compounds. Dictionary intersections never become measured observations.
4. Metadata: exact doses1.11 and1.11111 remain distinct until a reviewed exposure rule says otherwise; column order/ID mismatch and unit mismatch block that artifact. Missing/non-HIQ data cannot become not-screened.
5. Leakage/independence: changing C effects or B validation outcomes cannot alter the frozen query, mapping or eligibility.2017/2020 repeated instances cannot enter opposite independent-validation sets. Shared instances and partial overlap trigger the declared resolution policy.
6. Aggregation/uncertainty: reproduce hand-calculated equal-signature means with unequal signatures per compound; a single experiment emits no biological CI. No gene/cell/well bootstrap silently expands biological N.
7. Context adapters: Frangieh original/scPerturb retain one origin; knockout effects cannot masquerade as drug effects; mouse orthologue ambiguity remains missing. Primary PRISM viability and secondary AUC are not pooled on one scale.
8. Resume: intentional interruption leaves partial state; changed config/input/scorer hash cannot resume into old results; matching restart reuses only verified completed stages. Failure does not yield a finished manuscript artifact.

Real-data smoke must retrieve an approved small LINCS slice containing the exact primary signatures and full selected gene universe, validate matrix IDs/features, run the pinned numerical route, and reproduce output hashes or a documented floating-point tolerance. It has no required biological score direction. The complete analysis and independent-context checks remain separate acceptance steps.

## AIU, VPN interruption and review

Main checkout: `/home/omics/projects/ici_thesis_pipeline/master-thesis`. Existing completed metadata evidence lives under `/home/omics/projects/ici_thesis_pipeline/planning/2026-09-05/C_lincs2020_readiness`; it is evidence, not a production output directory. Use a fresh run ID and separate approved data cache. Verify the existing scheduler/wrapper before long jobs and record the real job/process handle; a wrapper's name does not prove resource enforcement.

If VPN/SSH fails, retain logs, last verified stage hashes and an explicit `pending_validation.json`. Continue local specification/review tasks. Before restart, inspect the remote job to avoid duplicate jobs; resume only a matching commit/config/input/environment bundle. Retrieve checksums before promoting temporary output to complete. Tests deferred by connection loss remain unrun and are not replaced by synthetic success.

Review checklist: source roles intact; B bidirectional-query gate enforced; primary anchor and descriptive weighting approved; no canonical-gene success gate; actual measured/inferred coverage; no accidental class/project causal claim; scorer zero/tie behavior verified; reference/holdout leakage excluded; every scientific statement linked to primary evidence; licensing and credentials handled per source; figure tables reproduce every plotted value; negative and unavailable results retained. Opus consultation and Astra final review assess a concrete diff and evidence bundle. Implementer tickets never commit/push; the orchestrator integrates reviewed milestones and updates GitHub/Notion with genuine statuses.
