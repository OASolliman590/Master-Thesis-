# A/A.1 integrated specification decision — 15 October 2026

## Authority and limits

The user supplied the Paper_A_A1_Decision_Handoff_20261015 package and instructed this thread to continue and finalize the Spec Kit. This record applies that architectural direction. It is not an institutional amendment, external preregistration, source-admission signature, statistical release, or evidence that a model has run. The earlier appraisal and September decision records remain historical evidence.

## Resolved architecture

1. Paper A is one baseline clinical-reference manuscript. A-BIO estimates response-associated biological effects; A-PRED is a separately frozen predictive product. A-BIO is not conditional on favourable prediction.
2. A-P2 remains the selected primary: the paired independent-test AUROC of the frozen learned score minus fixed CYT. Preserve equal cancer weights and equal originating-study weights within cancer. Admission, actual roster, numerical weights, measurement contract, prior exposure, grouped-development feasibility and precision remain release gates.
3. A-P1 remains secondary and CYT-led. Its principal fixed-score contrast is AUROC(DCR) minus AUROC(ORR), using identical eligible patients. The single frozen learned score is an additional prespecified secondary, independent of its construction; no endpoint-specific retraining.
4. A.1 is an active, fully specified longitudinal workstream. Thesis inclusion is the default; a separate manuscript is conditional. Separate pairing, estimation, synthesis, moderator and publication gates. Use 'planned for prespecification/preregistration', not 'preregistered'.
5. Absence of a lineage-clean final test blocks the specified independent A-P2 evaluation, not unrelated branches with their own releases. Internal–external validation is never relabelled untouched confirmation. All related assays/specimens of reserved patients remain protected across A, A.1, B and C.
6. Prepare a source-faithful protocol crosswalk and proposed amendments. Do not contact supervisors, submit forms or presume institutional approval. Manuscript placement alone is not established here as requiring an institutional amendment.
7. The canonical acquisition authority is specs/A_DATA_ACQUISITION_VALIDATION, inherited from commit 58ac943acbe8c981c7c8c269103c602b4425bd50 and draft PR #9. A and A1 consume it; they do not create competing identity stores. The older e477c680 snapshot is no longer the live acquisition head.
8. Replace the historical two-low-yield-pages search shortcut with actual query/export/pagination coverage and explicit unresolved limits. Do not retroactively label scheduled searches executed.

## Supersession and preservation

The complete pre-revision A tree is preserved byte-for-byte at reference/specs_A_before_20261015 (tree d6136db3bd0f70000e8eb0770799f36f5ae9baec). New A documents control current work. Historical numeric defaults, command names and test counts do not become released merely by inheritance. Draft PR #6 remains a proposal: retain its biological/longitudinal intent, replace its coarse intake and contrast semantics with the shared contracts, and do not adopt clinical NMA or a second manuscript by implication. PR #9 is incorporated by ancestry, not merged or closed by this action. Issues #1 and #7 remain open.

## Unresolved by design

No source roster or eligible N is approved here; no model hyperparameters, confidence precision target, source-specific time windows, comparator implementation bundle, cell-deconvolution reference, raw-reprocessing lane or controlled-access application is released. Each is tracked with an owner, evidence and blocked stage in specs/A/NUMERICAL_FREEZE_REGISTER.tsv and UNRESOLVED_QUESTIONS.md. Null, negative, contradictory and nonestimable results remain valid outputs.
