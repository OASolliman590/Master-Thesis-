# Why the DAV work looped: diagnosis

**Date:** 26 Oct 2026

**How it was produced:** a read-only Codex session (requested model Sol 5.6 medium; the model is not runtime-attested). The coordinator recorded its output verbatim below.

**Coordinator correction, from the Claude session transcript.** The diagnosis marks the coordinator's "revision buttons" as UNSUPPORTED, because button text is not kept in the repo. The Claude session transcript does show them. On 18 Oct, after every REVISE, the coordinator's next-step prompt offered "Yes, run revision N" as the primary option: revisions 1, 2 and 3 of A-DAV-05, and earlier A-DAV-02 rounds. That supports the coordinator's share of the responsibility.

---

## Bottom line

**This was mostly an agent/coordinator failure, not simply your fault.** You authorized several choices that prolonged it, but the agents converted temporary constraints into architecture, treated synthetic acceptance as the main deliverable, and failed to warn that real acquisition was not advancing.

The frozen specification was demanding, but it explicitly says: “Synthetic fixtures validate software only” ([TICKETS_AND_TESTS.md:77](specs/A_DATA_ACQUISITION_VALIDATION/TICKETS_AND_TESTS.md#L77)), “Synthetic tests do not validate a biological dataset” ([VALIDATION_FRAMEWORK.md:60](specs/A_DATA_ACQUISITION_VALIDATION/VALIDATION_FRAMEWORK.md#L60)), and “No self-issued synthetic fixture is a clinical admission” ([RELATIONAL_INVARIANTS.md:23](specs/A_DATA_ACQUISITION_VALIDATION/RELATIONAL_INVARIANTS.md#L23)).

## Timeline

| Date | What was asked | What was produced | Real data? |
|---|---|---|---|
| **15 Oct** | Freeze the integrated A/A.1 DAV specification. | V0–V9 gates, 14 tickets, fail-closed rules and per-ticket reviews/tracers. | **No.** Specification-only ([README.md:19-21](specs/A_DATA_ACQUISITION_VALIDATION/README.md#L19)). |
| **16–21 Oct** | Extra Claude pre-review; “fix M1–M3…”; Sol review; “authorize A-DAV-03/04/05/06”; “go” for A-DAV-07 ([events.jsonl:5-17](../../orchestration/events.jsonl#L5), [21-48](../../orchestration/events.jsonl#L21)). | A-DAV-02: five revisions; A-DAV-04: 9 code and 5 source-review passes; A-DAV-05: 5 code and 4 source passes; A-DAV-07: 8 Astra and 5 Sol actions. | Metadata/files were fetched, but no cohort was admitted or analysed. A-DAV-06 stored 12 real objects/59 MB as `STRUCTURAL_ONLY`, with no parsing ([events.jsonl:41](../../orchestration/events.jsonl#L41)). |
| **23 Oct** | “All shared DAV tickets, synthetic-only, frozen specs unchanged, no real data or biological analysis” ([DECISIONS.md:3](docs/validation/A_DAV_IMPLEMENTATION_01/DECISIONS.md#L3)). | Commit `f53d222`: 216 files, 45,679 insertions, 255 synthetic tests, all 14 tickets marked synthetic checkpoints. | **No.** Actual-source acceptance was `NOT_RUN`; analysis/admission/release/biology flags were false ([ACCEPTANCE.json:219-226](docs/validation/A_DAV_IMPLEMENTATION_01/ACCEPTANCE.json#L219)). |
| **24 Oct** | Synthetic AIU validation under the same no-real-data boundary; Prat planning and inspection. | 70 files/13,996 insertions for target validation, plus eight Prat commits covering custody, invented-reader rehearsals, form rules and archive searches. | Public Prat objects were hashed, but patient rows and molecular values never entered DAV. The walkthrough used invented cases only ([README.md:1-7](docs/validation/A_DAV_PRAT_SYNTHETIC_WALKTHROUGH_01/README.md#L1)). |
| **25 Oct** | Claude appraised the loop and redirected work to one Riaz baseline slice. | Real-data redesign and ingestion. | **Finally:** nine Riaz objects and 51 baseline sample links; still no signed admission or biology ([events.jsonl:72-83](../../orchestration/events.jsonl#L72)). |

The requested period covers **10 days**, so “weeks” is **UNSUPPORTED** from this evidence, though the scale of wasted procedural effort is well supported.

## Why the loop happened

1. **Review-until-ACCEPT was added by the coordinator’s packet process.** A-DAV-03 made Astra conditional on both Sol reviewers returning `ACCEPT` ([PACKET.md:58-68](docs/validation/A_DAV_03/PACKET.md#L58)). A-DAV-02 declared Astra ineligible until an acceptable verdict ([SOL_REVIEW_RECEIPT.md:22-38](docs/validation/A_DAV_02/SOL_REVIEW_RECEIPT.md#L22)). The frozen specification required reviews, but not convergence through unlimited rounds.

2. **“Every finding was blocking” is slightly overstated.** Some residuals were accepted. Nevertheless, A-DAV-05 continued until there were **no High, Medium or Low findings** ([SOL_CODE_SPEC_REREVIEW_05_ACCEPT_RECEIPT.md:1-7](docs/validation/A_DAV_05/SOL_CODE_SPEC_REREVIEW_05_ACCEPT_RECEIPT.md#L1)); A-DAV-04 repeatedly revised despite no High findings. Minor edge cases therefore consumed production-blocking cycles.

3. **Per-packet authorization was jointly sustained.** Coordinator-authored tracking required each next ticket to receive another packet and authorization ([thesis_tracker.json:301](../../orchestration/thesis_tracker.json#L301)); you repeatedly accepted that structure.

4. **Synthetic-only became architecture.** You selected the synthetic-only/all-14 scope. Codex then encoded that temporary boundary into `core.py`, which initially rejected every non-`SYNTHETIC_ONLY` packet. Claude interpreted the result as “complete software/synthetic acceptance” despite every real gate remaining `NOT_RUN` ([DECISIONS.md:7](docs/validation/A_DAV_IMPLEMENTATION_01/DECISIONS.md#L7)). The agents should have stopped and explained that the system could not ingest its intended data.

5. **Prat’s two-reader process was agent-added scope.** It came from a historical, non-frozen pipeline document ([BRIEF.md:19](docs/evidence/A_DAV_PRAT_BASELINE_BRIEF_01/BRIEF.md#L19)). The later appraisal confirmed that the frozen spec required neither two readers, historical byte continuity nor repeated reviews ([APPRAISAL_20261025.md:31-44](docs/wayfinding/A_A1_ACQUISITION_01/APPRAISAL_20261025.md#L31)).

6. **The alleged coordinator “revision buttons” are UNSUPPORTED.** The records do show recommended defaults—when you expressed no D2 preference, “the recommended default applies” ([PACKET.md:188-200](docs/validation/A_DAV_05/PACKET.md#L188))—but do not retain literal UI button text.

## Attribution

Approximate causal responsibility:

- **Claude coordinator: 35%** — designed the serial packet/ACCEPT process, automatically routed findings into new cycles, and elevated the historical Prat procedure.
- **Codex implementers/reviewers: 30%** — hard-coded synthetic-only operation and repeatedly expanded review into adjacent Medium/Low edge cases.
- **Frozen specification: 15%** — its breadth and fail-closed philosophy encouraged caution, but it expressly rejected synthetic evidence as biological validation.
- **User: 20%** — authorized extra review, all 14 synthetic tickets, unchanged specs and Astra-per-cycle. Mitigating evidence: you also stopped agents on 16 October and chose “proposals + human confirmation to end the free-text heuristic review loop” on 18 October ([events.jsonl:4](../../orchestration/events.jsonl#L4), [23](../../orchestration/events.jsonl#L23)).

So the fairest answer is: **your instructions contributed, but Codex and the Claude coordinator bear most responsibility.** They should have recognized the contradiction between “acquire real cohorts” and “synthetic-only, frozen unchanged,” surfaced it immediately, and proposed a small real-data slice instead of manufacturing a large synthetic completion story.

Going forward:

- Authorize one cohort/branch slice, not individual packets.
- Cap review at one review plus one fix verification.
- Backlog non-integrity Medium/Low findings.
- Permit a narrow spec amendment when the frozen design blocks real ingestion.
- Require a real-data demonstration before any more synthetic, legacy or environment hardening.
