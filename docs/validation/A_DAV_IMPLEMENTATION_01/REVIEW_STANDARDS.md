# Independent Standards and code-quality review

Reviewed the exact additive package in `.superpowers/implement/2026-10-23-dav-all/review-inputs.json` against base `9da3b1afaeba04aa9a8a29095c01574e8c87579c`, including 14 new modules, seven test files and integration uses of the four unchanged dependencies. This is the initial package review, before corrective edits. Static review only: no tests, network, installations, source objects, commits or subagents. Read AGENTS/CONTEXT, domain/tracker instructions, implementation plan, frozen architecture/schemas and all three worker reports. Applied the code-review Standards axis; no CODING_STANDARDS/CONTRIBUTING was supplied.

| Owner | Code-quality verdict |
|---|---|
| A | Changes required: component chronology can contradict its episode. Otherwise source preservation and explicit measurement lanes are clear. |
| B | Changes required: manifest completeness bypass and study-order-dependent admission audit. |
| C | No additional blocking finding in this review. Explicit rank ties, private/public separation, dependency checks and immutable publication are appropriate. |
| Parent | Changes required: malformed configuration escapes the public failure boundary. Connected tests exercise real stage APIs; sealed unit fixtures are not mistaken for source acceptance. |

Actionable findings (four P2; zero P0/P1/P3):

1. **P2 — Component chronology is only half bounded.** [timing.py:47](/Users/megastore/Documents/ChatGPT/MyThesis_Epigentics_Project/work/a-dav-01/tools/a_dav/timing.py:47) checks start ≥ episode start and stop ≤ episode stop, but allows start > stop or start beyond episode stop. Compare both component endpoints and their ordering. Documented rule: implementation plan line 33, “known contradictions fail.”
2. **P2 — Required manifest IDs can be labelled optional.** [prat_review.py:43](/Users/megastore/Documents/ChatGPT/MyThesis_Epigentics_Project/work/a-dav-01/tools/a_dav/prat_review.py:43) permits a missing object when `required=False`; line 53 only tests ID presence. A listed required object can therefore lack verified bytes while its assertions are accepted. Required-ID membership must control completeness and usable authority. Documented rule: independent Prat review P01, line 36, missing required objects withhold acceptance.
3. **P2 — Study audit eligibility depends on iteration order.** [admission.py:223](/Users/megastore/Documents/ChatGPT/MyThesis_Epigentics_Project/work/a-dav-01/tools/a_dav/admission.py:223) uses globally accumulated reasons inside the study loop. A later unknown study changes earlier/later supported-study audit states when rows reverse. Separate study-local reasons from aggregate status. Documented rule: SOFTWARE_ARCHITECTURE.md lines 57/78–84, deterministic ordering/provenance.
4. **P2 — Failure construction rethrows malformed configuration.** [core.py:178](/Users/megastore/Documents/ChatGPT/MyThesis_Epigentics_Project/work/a-dav-01/tools/a_dav/core.py:178) hashes rejected config again outside its fallback. Return a redacted fixed failure for noncanonical input. Documented rule: implementation plan line 24, invalid input returns fixed codes without caller text.

No heuristic smell is promoted into a mandatory refactor. Actual source/clinical/reviewer/environment/statistical acceptance remains **NOT_RUN**; synthetic readiness establishes software simulation only.

## Evidence appendix: fixed synthetic repro recipes

These are code-traced recipes, **not executed tests**. Parent owns narrow regression verification and finding dispositions.

### Finding 1

Starting from `tests/a_dav_implementation/test_group_a.py`'s invented `timing_config(packet())`, set `records['treatment_exposure'][0]['start_date_or_day']='50'` and `stop_date_or_day='10'`, then use `with_registries` and call `validate_timing`. Episode bounds remain 0..60. At timing.py:53 the only numeric comparisons are 50 >= 0 and 10 <= 60; neither checks the reversed component interval. Both endpoint strings satisfy the frozen treatment-exposure schema. An independent literal expected result is `FAIL` with `COLLECTION_CHRONOLOGY_CONFLICT`. Also exercise start='61', stop='60' and start='0', stop='-1', while preserving the legitimate delayed-component case already covered.

### Finding 2

Starting from `tests/a_dav_implementation/test_group_b_protocol.py::prat()`, retain `required_object_ids=['invented-object']`, change its manifest entry to `state='MISSING', required=False`, remove `content_hex`, and update `basis['manifest_sha256']`, both readers' identical basis and their seal hashes. This represents a newly sealed internally contradictory inventory, not stale-seal tampering. Lines 43–45 skip byte validation without setting incomplete, line 53 sees the required ID, and line 94 accepts the authority ID from `object_ids`. Expected: `BLOCKED_UNKNOWN` with `OBJECT_MANIFEST_INCOMPLETE`, regardless of per-item optional flag. Requiring an available authority object independently closes optional-missing-object assertion support.

### Finding 3

Use two schema-valid invented clinical studies and their source rows, with fixed complete config and current dependencies. Study s1 has the baseline/ORR evidence used in the passing fixture; study s2 has a source but lacks baseline/outcomes. For order [s1,s2], s1's audit eligibility is SYNTHETIC_READY, then s2 adds BRANCH_EVIDENCE_UNKNOWN. For [s2,s1], the same global reasons set already contains BRANCH_EVIDENCE_UNKNOWN when s1's eligibility is computed, so s1 is BLOCKED_UNKNOWN. Both aggregate results remain blocked, but the audit differs for canonically identical record sets and normalized input binding. Expected: identical complete results after row reversal, with stable per-study dispositions.

### Finding 4

```python
from tools.a_dav.core import SchemaStore
from tools.a_dav.registries import build_registries

store = SchemaStore()
packet = {'classification': 'SYNTHETIC_ONLY', 'branch_id': 'A_BASELINE_BIO',
          'records': {}, 'config': {'value': float('nan')},
          'schema_hashes': store.hashes, 'dependencies': {}}
result = build_registries(packet, schemas=store)
assert result['status'] == 'FAIL'
assert result['reasons'] == ['MALFORMED_INPUT']
assert result['records'] == {}
```

`check_packet` raises MALFORMED_INPUT during canonicalization; the handler invokes finish. Its input hash falls back at lines 169–172, but config hashing at line 178 raises again. Existing test_core.py:66–77 only calls `check_packet`, so it misses the public API's handler path. Also cover a non-JSON object under config and an unpaired Unicode surrogate, without echoing rejected input in the result.
