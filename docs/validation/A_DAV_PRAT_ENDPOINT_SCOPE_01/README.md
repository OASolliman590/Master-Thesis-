# Prat training endpoint scope: settled

The previous two-reader rehearsal left one difference in how readers labelled the endpoint question. Form v3 settles that training rule: the endpoint summary covers **native endpoint meaning and individual assessment evidence**. The proposed same-patient/same-episode match has a separate status. A missing or conflicting match still prevents completion of the full question and withholds use.

In invented case INV-C02, the summary is `UNRESOLVED`. The unsupported transfer from BETA to ALPHA stays visible as an episode conflict. Neither earlier reader pass nor its seal is changed. This is a training instruction, not an adjudicated finding about Prat.

Use [FORM_V3.json](FORM_V3.json) with the [scope decision](DECISION.md). It adds six fields to the endpoint assertion only. All seven question texts remain unchanged. Source priority, raw labels, assessment timing requirements and the same-episode requirement remain in force. This form does not change a frozen DAV schema or a runtime interface.

The [independent contract review](REVIEW.md) found one wording issue: name assessment date/day and window, or their absence, explicitly. That clarification is incorporated in the final form and decision. No new timing default was selected. This resolves the review recommendation; the review itself remains a record of the earlier draft.

## What the checks establish

[Eight invented boundary cases](TRAINING_EXAMPLES.json) exercise the local summary rule. The [results](SCOPE_CHECK_RESULTS.json) retain episode status separately. In particular, supported meaning and assessment with an unknown or conflicting episode link produce a narrow `SUPPORTED` summary while use stays false. Even the fully supported invented case grants no actual authority. The component completeness flag describes three toy states only; it is not branch eligibility.

Run `python3 docs/validation/A_DAV_PRAT_ENDPOINT_SCOPE_01/VERIFY.py` from the worktree. The checker verifies the eight cases, preserved question texts, packet hashes, local document links and the 2,280 protected prior files. [Verification record](VERIFICATION.json).

This is a document-rule check, not another independent two-reader pass, an endpoint evidence extractor or a production validator. Runtime tests were not rerun because no runtime code changed. Earlier test results retain their original scope. No source objects, network access, SSH, real data or biological analysis were used.

## What remains

The training scope decision is complete. No further synthetic rehearsal is required by this decision. The next work depends on actual authority and source evidence; this packet does not authorize it. Follow [REMAINING_STEPS.md](REMAINING_STEPS.md).

Actual custody/use approval and two reader appointments remain **not established** in the checked records. Real-source readiness remains `BLOCKED_UNKNOWN`. These are missing authority/evidence, not software defects. No new executable defect was established. [Status](STATUS.json).

Only this new packet is added. Frozen specs, runtime code and prior packets remain unchanged. No push or source admission is part of this work.
