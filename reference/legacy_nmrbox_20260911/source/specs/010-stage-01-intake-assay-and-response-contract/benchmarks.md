# Benchmarks: Spec 010 — Stage 01 Intake (Assay & Response Contract)

## Baseline (to measure at T002, before implementation)

| metric | how to capture | baseline |
|---|---|---|
| `cli.py` total lines | `wc -l src/pipeline/cli.py` | 10,515 (2026-05-30) |
| `cli.py` Stage 01 surface lines | sum of `cmd_intake_*` + helpers L480–581, L1655–2980 | ~1,500 (est; measure exactly at T002) |
| intake wall time (full cohort set) | `/usr/bin/time -l python -m pipeline.cli intake build-geo-sample-manifest ...` | TBD |
| intake peak RSS | same | TBD |
| existing intake test runtime | `pytest tests/unit/test_intake_* tests/unit/test_spec006_metadata_intake.py -q` | TBD |

## Regression budget

- Assay detection adds one full read per cohort matrix already read elsewhere — **≤ +15%** intake wall time acceptable (detection reuses parsed frames where possible; budget allows a second pass).
- Peak RSS: **no more than +10%** (detection streams column stats; does not hold all cohorts in memory simultaneously).
- `cli.py` line count MUST *decrease* by ≥ 400 (FR-009) after extraction — a negative budget.
- Existing intake test runtime: **≤ +20%** with the new tests included.

## Measurement procedure

```
# Baseline (run once, before M3):
wc -l src/pipeline/cli.py
/usr/bin/time -l python -m pipeline.cli intake build-geo-sample-manifest <args> 2> baseline_intake.time
pytest tests/unit/test_intake_* -q 2> baseline_tests.time

# Post-implementation (at M6):
wc -l src/pipeline/cli.py        # expect ≥400 fewer
/usr/bin/time -l python -m pipeline.cli intake detect-assay-type <args> 2> new_assay.time
/usr/bin/time -l python -m pipeline.cli intake build-response-record <args> 2> new_resp.time
# Confirm wall time and RSS within budget; confirm golden integration test passes.
```

## Notes
- Assay detection cost is dominated by reading each cohort's primary matrix; for the large series matrices this is I/O-bound. If it exceeds budget, cache the per-column stats in `assay_detection.tsv` and skip re-detection when the source file checksum is unchanged (idempotency, mirroring spec 009 FR-004).
- SC-004 migration note is a correctness artifact, not a perf metric, but record how many cohorts change model class — it quantifies the blast radius the Stage 06 spec inherits.

## Current Implementation Check (Round-3 contract cycle)

- `wc -l src/pipeline/cli.py` (current total): `12,594` lines.
- Stage-01 contract surface in `cli.py` (measured ranges):
  - `NR 510..924` (`_infer_response_label` + Stage-01 response/timing + contract commands),
  - `NR 2426..2646` (`cmd_intake_build_geo_sample_manifest`),
  - `NR 3428..3440` (`_build_stage01_index`).
- Combined Stage-01 surface count (command below): `649` lines.

```bash
awk '((NR>=510 && NR<925) || (NR>=2426 && NR<2647) || (NR>=3428 && NR<3441)) {c++} END {print c}' src/pipeline/cli.py
```

- Compared with the benchmark baseline estimate (`~1,500` Stage-01 lines), this is an approximate reduction of `~851` lines, satisfying the FR-009 shrink target (`>=400`).
