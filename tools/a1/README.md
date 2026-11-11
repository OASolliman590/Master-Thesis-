# A-LONG

A-LONG has an outcome-free, source-specific pair builder and separate products for feature joining, two-timepoint change, ANCOVA sensitivity, repeated windows, randomized arms, and study-first synthesis. Its invented demonstrations and tests check software behavior only; they do not validate biology.

Run invented demonstrations with the project Python environment:

```sh
python -m tools.a1 demo --out .scratch/a1-demo
python -m tools.a1 demo-analysis --out .scratch/a1-analysis-demo
```

The pair product retains candidates, rejected combinations and reasons, selected pairs, missing-follow-up receipts, timing precision, source locators and confidence, assay comparability, admission receipts, technical-replicate counts, and longitudinal support. It does not read endpoint, response, survival, or benefit fields. Endpoint-evaluable counts remain unavailable before a separate outcome release.

`missing_followups.tsv` contains one private receipt for each selected eligible baseline patient/episode/exposure and every approved follow-up window without a selected pair. Its columns are `study_id`, `patient_id`, `index_episode`, `exposure`, `window_id`, `reason`, and `candidate_reasons`; an early-window pair does not suppress a missing later-window receipt. `pair_candidates.tsv` and `pairing_exclusions.tsv` retain selected/rejected assay identities, raw timing precision, source locators/confidence, episode/exposure, endpoint and admission provenance for adjudication.

Scoring uses the fixed four A-P2 panels, CYT, eleven strict-coverage custom panels, and 21 M5/M6 genes. A-P2 panels use log2(TPM + 1) only on the qualified linear RNA-seq TPM route. CYT stays on its TPM geometric-mean scale. Custom panels and individual M5/M6 genes retain the declared source scale. The fixed aliases and memberships come through the existing A-META/A-scoring APIs; production calls cannot inject replacement memberships. Raw counts are refused because no voom/dream route is offered.

## Future real-input command shapes

These commands require new, exact user-approved records under the relevant scope and the explicit outcome opt-in shown below. The CLI and every released Python API default to refusing N13 outcome access; the flag or `allow_outcomes=True` is necessary but never sufficient without the checked record and exact hashes. No valid release record is supplied by this implementation. The commands are future templates, not authorization:

```sh
python -m tools.a1 pair --study-id '<study>' --classification real \
  --input '<named outcome-free table>' --columns-json '<source-column-map.json>' \
  --policy-json '<N12-policy.json>' --input-manifest '<N12-input-manifest.json>' \
  --release-record '<N12-user-release.json>' --out results/a_long/pairing

python -m tools.a1 pair-to-analysis --allow-outcomes --input-manifest '<N13-feature-input-manifest.json>' \
  --release-record '<N13-feature-user-release.json>' --policy-json '<feature-policy.json>' \
  --out results/a_long/feature-join --retention-dir results/a_long/retention-feature

python -m tools.a1 two-timepoint --allow-outcomes --input-manifest '<N13-model-input-manifest.json>' \
  --release-record '<N13-two-timepoint-user-release.json>' --policy-json '<N13-policy.json>' \
  --out results/a_long/two-timepoint --retention-dir results/a_long/retention-two-timepoint
python -m tools.a1 ancova --allow-outcomes --input-manifest '<N13-model-input-manifest.json>' \
  --release-record '<N13-two-timepoint-user-release.json>' --policy-json '<N13-policy.json>' \
  --out results/a_long/ancova --retention-dir results/a_long/retention-ancova
python -m tools.a1 repeated --allow-outcomes --input-manifest '<N13-repeated-input-manifest.json>' \
  --release-record '<N13-repeated-user-release.json>' --policy-json '<N13-repeated-policy.json>' \
  --out results/a_long/repeated --retention-dir results/a_long/retention-repeated
python -m tools.a1 randomized-arm --allow-outcomes --input-manifest '<N13-randomized-input-manifest.json>' \
  --release-record '<N13-randomized-user-release.json>' --policy-json '<N13-randomized-policy.json>' \
  --out results/a_long/randomized-arm --retention-dir results/a_long/retention-randomized
python -m tools.a1 synthesize --allow-outcomes --input-manifest '<N13-synthesis-input-manifest.json>' \
  --release-record '<N13-synthesis-user-release.json>' --policy-json '<N13-synthesis-policy.json>' \
  --out results/a_long/synthesis --retention-dir results/a_long/retention-synthesis
```

The N12 user-release record binds the exact source-column map and source-specific window policy. N13 scopes bind their exact feature membership, representation, method and covariate contracts, repeated selection and window set, randomization admission, or synthesis multiplicity and source-overlap contract. Every record also binds its operation, policy hash, input-manifest hash, source-file hashes, cohort set, permitted named fields, and a decision identity/path/hash under `docs/decisions/`. `APPROVED`, `ACCEPTED`, or a non-empty record reference by itself is not enough. Gide crosswalk activation additionally requires its own N12 crosswalk record and explicit command option.

The outcome-free N12 pair command does not use `--allow-outcomes`. Pairing remains available only under its source/window policy record, and its endpoint-evaluable counts remain unavailable. The N13 flag is future-use CLI syntax documented for users; no command with that flag was run in this code-only work.

The following are documentation-only templates. `DRAFT_UNSIGNED` and every placeholder are deliberately rejected by the reader. A user decision must supply a real decision file and its exact SHA256; do not convert these snippets into release records by changing a status string.

```json
{
  "record_type": "a_long_user_release_v1",
  "record_status": "DRAFT_UNSIGNED",
  "data_classification": "PRIVATE_PATIENT_LEVEL",
  "release_scope": "N12_PAIRING",
  "operation": "pair",
  "decision": {
    "identity": "<approved-N12-decision-identity>",
    "path": "docs/decisions/<approved-N12-decision-file>.md",
    "sha256": "<sha256-of-exact-decision-file>"
  },
  "policy_sha256": "<canonical-N12-policy-sha256>",
  "input_manifest_sha256": "<exact-input-manifest-sha256>",
  "source_sha256": {"specimens": "<exact-specimen-table-sha256>"},
  "cohorts": ["<one-exact-study-id>"],
  "permitted_fields": ["specimens:<named-source-column>"],
  "source_column_map_sha256": "<canonical-column-map-sha256>",
  "window_policy_sha256": "<canonical-window-policy-sha256>"
}
```

For N13, keep the common fields above and set the exact scope/operation pair. Bind these additional fields: `N13_FEATURE_JOIN` uses `feature_membership_sha256`, `pair_manifest_sha256`, and `representation_sha256`; `N13_TWO_TIMEPOINT` uses `ancova_method_id`, `covariate_contract_sha256`, and `delta_method_id`; `N13_REPEATED` uses `repeated_method_id`, `selection_mode`, and `window_set_sha256`; `N13_RANDOMIZED_ARM` uses `comparative_estimand_id`, `randomization_receipt_sha256`, and `randomized_method_id`; `N13_SYNTHESIS` uses `meta_method_id`, `multiplicity_contract_sha256`, and `source_overlap_contract_sha256`. The Gide crosswalk scope binds `crosswalk_sha256` and `crosswalk_source_manifest_sha256`. Each source role and permitted column must also appear in that scope's input manifest.

## Private products

Real patient-level outputs belong under `results/` or `.scratch/` and each command refuses an existing non-empty output directory. Pairing writes `pair_candidates.tsv`, `pairing_exclusions.tsv`, `missing_followups.tsv`, `pairing_summary.tsv`, `longitudinal_support.tsv`, and a private pairing manifest. Feature joining writes `analysis_rows.tsv`, `feature_coverage.tsv`, `longitudinal_support.tsv`, a released-input receipt in retention, and a private feature-join manifest. Model products write `a_long_effects.tsv`, `within_group_deltas.tsv`, `model_support.tsv`, `longitudinal_support.tsv`, and the R bridge manifest. Repeated model rows use a distinct `baseline_to_<window>` identity for each contrast, including nonestimable rows. `model_support.tsv` and `longitudinal_support.tsv` retain contrast-specific unique-patient and observation support separately from total fitted observations; nonestimable rows keep their status and reason. Model `longitudinal_support.tsv` contains input pair counts and one row per effect/sensitivity with patient/observation support, status, and role; it contains no patient identifiers. Synthesis retains `synthesis_input.tsv`, `synthesis_groups.tsv`, `overlap_receipts.tsv`, `a_long_synthesis.tsv`, `synthesis_support.tsv`, and the R bridge manifest. These are private patient-level or source-family products. No public patient-level tables or response-coloured plots are produced.

The primary two-timepoint model is d = on − pre, fit as d ~ response + prespecified covariates. ANCOVA is a separate conditional-on-baseline sensitivity. Same-lesion, exact-day, and tighter-timing rows appear only when selected in the bound N13 policy; tighter timing needs an explicit source-specific cutoff and unknown days never qualify. Repeated-window fitting reports its declared missing-window selection mode, patient and observation denominators, rank, convergence, singularity, and support. Randomized-arm effects retain arm counts and require a separate admission. Synthesis uses REML with modified Knapp–Hartung, requires pairwise source-overlap receipts for multi-study families, retains k=1, labels k=2–3 tentative, and suppresses prediction intervals below the declared minimum k. Holm and exploratory BH use predeclared denominators; unestimable p-values stay missing.

Inference precision checks use machine precision relative to the observed response scale and observation count. A change of measurement units therefore does not impose an absolute minimum standard error; exact or numerically perfect fits remain nonestimable with their uncertainty and p-value missing.

The N12/N13 note remains PROPOSED and unsigned in [PROPOSED_A_LONG_N12_N13_20261107.md](../../docs/decisions/PROPOSED_A_LONG_N12_N13_20261107.md). Real source admission, outcome release, real fitting, and real synthesis remain locked. The A-P2 rebuild remains deferred. CIBERSORTx was not run.
