# W8 local synthetic software acceptance

Date: 12 September 2026. Review baseline: `bde4c05`. Paper A source archive and handoff are preserved.

## Implementation and scope

`tools/b_secondary` is connected to W8 and the strict Paper B test runner. It consumes W3/W5/W6/W7 publications, verifies exact declared payloads, checksums, manifests, COMPLETE markers and linked code/config/plan/frozen-bundle identities, and checks the pinned proposed registry. W8's actual dependencies participate in invalidation; changed plan input hashes invalidate resumable work.

One explicitly fictional signed-expression contract executes on synthetic TCGA-like W3 rows. Membership, signs, weights, units, input columns, missingness and output semantics are pinned in `specs/B/workflow.synthetic.json`. Named Ayers, full IFNG Hallmark and HOPE contracts are blocked. M0-M6 emit raw-symbol fixture coverage/context only. Regulatory-target evidence has a header-only table and an explicit blocked reason. MethylCIBERSORT and LUAD remain blocked.

The separate fictional C handoff calculates a predeclared TCGA-only mean-minus-fixed-reference contrast, preserving negative/zero/undefined effects, finite/missing counts, undefined confidence limits and alternative explanations. Its available-finite-per-gene rule is explicit. It is not a methylation-association result or biological nomination. The implementation rejects external/CPC/outcome-selected contract provenance; changing CPC expression values does not change the handoff calculation.

Successful completion is scoped `synthetic-software-w1-w8`, with `biological_validation=false`. This closes the synthetic software path, not the named secondary predictive models, broader immune-barrier study, real-cohort execution, AIU acceptance or MSc scientific deliverables. W7 remains a traceable partial APM report and points to the run status for downstream W8 status.

## Parent review and corrections

The parent inspected the new module and all integration/configuration changes against the W8 brief and current B contracts. Corrections before final acceptance:

- Modelled the documented W3 null self-checksum placeholder and W3/W5/W6 manifest checksum entries exactly, without allowing arbitrary missing hashes.
- Made W8 depend on all consumed W3/W5/W6/W7 stages and checked cross-stage identity links.
- Added an explicit handoff missingness rule and overflow rejection.
- Made missing COMPLETE return a clean incomplete result; reject false biological-completion metadata.
- Removed stale W7 statements that W8 code does not exist, while retaining partial APM scope.
- Corrected a test oracle: TCGA-0004 lacks unrelated GENE_E, so fictional A-minus-B remains defined.
- Removed unrelated newline churn from existing files.

No scientific source was invented or qualified by these software changes. No remote run was performed.

## Verification

Interpreter: `E:\Master_Thesis\.venvs\paper-b-20260911\Scripts\python.exe`.

Implementer focused command: `python -m unittest discover -s tests/b_secondary -v` — 14 passed, zero skips, 52.785 seconds (implementer report).

Parent strict command: `python tools/check_paper_b.py` — **147 passed, zero skips, 353.029 seconds**, exit 0. Complete log: `STRICT_LOCAL.log`. This independently reruns the W8 tests alongside all earlier component suites.

Standalone fresh and resume commands:

```text
python -m tools.b_workflow run --mode synthetic --config specs/B/workflow.synthetic.json --output tmp/paper_b_checks/w8_fresh_reviewed_20260912
python -m tools.b_workflow resume --output tmp/paper_b_checks/w8_fresh_reviewed_20260912
```

Fresh/resume receipts and identity summary are adjacent. Artifact values are synthetic and must not be reused as paper findings.

## Remaining work

AIU W6-W8 validation remains pending. Qualify and freeze named secondary, composition and broader scientific contracts from authoritative source artifacts. Verify E1-E4/E6 and external-evaluation release before any real-cohort analysis. Any real TCGA-only C nomination needs its own scientific contract and review.

Parent standalone acceptance: fresh executed W1-W8; resume executed none and skipped W1-W8. All eight publications verified locally, and current code/config hashes match the receipts. Exact hashes and payload index: `ACCEPTANCE.json`.
