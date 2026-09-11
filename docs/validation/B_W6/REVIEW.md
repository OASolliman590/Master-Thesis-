# Paper B W6 independent review and correction

Date: 11 September 2026. Review fixed point: `0e0fd89a7b150c3b9186f3da1218a8d0de0ee7a2`. Scope: synthetic W6 frozen external evaluation only.

## Disposition

W6 is accepted as a local synthetic software checkpoint after correction. It is not a real CPC-GENE evaluation, AIU acceptance, evidence of biological validity or completion of the broader Paper B immune-barrier study.

The two-axis review found no breach of `AGENTS.md` and no scope creep into MethylCIBERSORT, barrier scores or clinical-response claims. It found four specification defects in the initial candidate:

1. the evaluation lock was constructed after the external metrics, making the validation tautological;
2. W5 bundle validation did not completely cross-link `contract.json`, the embedded contract, code identity, final state, training-patient hashes and the enclosing W5 publication;
3. an evaluation with fewer than two patients reported `n` rather than all configured bootstrap resamples as undefined;
4. the Y/predictor mutation tests exercised the feature provider but did not rerun W6 or inspect its predictions and metrics.

All four are corrected. The fixture-only lock is written before external transformation; no failed run receives `COMPLETE.json`. The dedicated W5 loader and stage validator verify exact payloads and every relevant contract/code/state/patient/upstream link. The one-patient oracle reports 2,000 undefined resamples. Metamorphic tests rerun W6 and prove that changing finite external Y changes evaluation statistics but not predictions, while changing an external promoter predictor can change the extended prediction and neither mutation changes W5 bytes.

## Verification

- Focused corrected W6 suite: 10 tests passed.
- Integrated W6/W7 workflow regression: 22 tests passed.
- Final post-review strict Paper B acceptance: 133 tests passed, zero skipped, in 219.248 seconds using `E:\Master_Thesis\.venvs\paper-b-20260911\Scripts\python.exe`.
- Original fixed-table B-P1 `develop` and `evaluate` interfaces remain covered by their existing regression suite.

The maintainability review noted duplicated command/lock validation and a large W6 orchestration function as judgement-call design debt. Those observations do not change the scientific or integrity disposition and can be refactored only with unchanged behavior and regression coverage.

AIU W6 validation remains pending. The prior W5 AIU record remains 115/116 because excluded server fixtures could not be reattached after SSH timeouts; this review does not upgrade that gate.
