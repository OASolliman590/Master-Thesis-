# Cycle specification

- Paper and cycle: A · 01 · A-P2 release preparation
- Status and date: software verified on invented data, 18 November 2026; no real run approved.
- Authority: A and A1 SPEC_v2; signed integrated plan, biology, validation, one-manuscript, numerical-freeze, panel-coverage and 15 November A-P2 development-release amendments; analysis-modules SPEC; accepted A/B policies. The A3 sheet is unsigned.

## Scientific question and purpose

Prepare controlled development of a fixed four-feature ridge score against CYT, without examining patient outcomes. The formal primary is the paired difference in area under the receiver operating characteristic curve (AUROC, a measure of discrimination) on the separately released final test. This work prepares provenance and guards, not a result. A's associations may inform B/C and wet-lab hypotheses but cannot establish causation or redesign A-P2.

## Method and evidence

Group Liu and Van Allen as one family; a second prespecified sensitivity groups the four US-linked melanoma cohorts. Source evidence cannot prove patients distinct. Grouping prevents a family spanning a held-out fold but does not remove duplicate contributions to other training folds, study-level AUROCs or secondary splits. A1 removes any atezolizumab, missing or conflicting agent from the freeze representation; previous exposure remains a residual concern. Platform, batch, tumour purity, copy number, treatment line and small responder groups constrain interpretation. A-BIO uses within-study standardized Hedges g and random effects, separately from this score. A-LONG requires verified patient/episode windows; Gide's crosswalk is pending.

## Interpretation and boundaries

IMvigor210 remains UNTOUCHED_FINAL_TEST in every paper, modality and collection. No real input, clinical table, outcome, preparer or rebuild is authorized here. No --allow-outcomes. Invented tests do not validate biology. A signed amendment is not a run release. Prior exposure remains a gate before final-test release and comparator/novelty claims. No clinical set, post-meta ranking or A→B/C candidate rule is signed by A3.

## Reporting instruction

Talk to me as a scientist, not only as a project manager. Every report has two layers:
1. Science and bioinformatics first: what biological or clinical question this step answers and why it matters for A → B → C → wet lab; what the method does and why it fits the data; its assumptions and what could fool it (batch, purity, copy number, cohort overlap, treatment line, platform, small responder counts) and how the design guards against that; what a result could and could not mean (association vs causation, claim ceiling). Cite key papers or methods when helpful.
2. Technical second, short: files, commits, tests, hashes.
For each decision, explain the scientific trade-off of each option first, then recommend one with reasons. Define terms the first time they appear in a thread. Point out interesting observations you are allowed to see, and ideas for each paper's discussion section, but never read or hint at locked outcomes. When I ask "why", answer like a supervisor or co-author, with reasoning and literature.

## Hard rules

1. Public repo: no patient-level data, real sample/run IDs or absolute machine paths in Git. Patient-level data stays in .scratch/runtime/; beware .scratch is NOT git-ignored in the old A-P2 release-prep tree. Review every staged file before committing; never include raw data or private logs.
2. All design changes and every signature belong to the user. Record actual decisions in docs/decisions/ or specs/amendments/ before acting; never sign or infer approval. If regenerated worksheet items differ, show the difference and stop. Frozen RC2 specs are never edited; amendments only.
3. Real outcomes remain LOCKED until a user-signed per-run release. Never --allow-outcomes. Tests use entirely invented data until a release is signed. IMvigor210 remains UNTOUCHED_FINAL_TEST in every paper, modality and collection; do not open, download another copy, or use it to resolve overlap. The real A-P2 rebuild is deferred.
4. Never open ingestion_packet.json. Clinical tables only by explicitly named necessary columns and only under authorized scope. Log every outcome-adjacent read in the relevant DEVIATIONS.md. No outcome counts, summaries or hints while locked.
5. Never read/print/send secrets, private keys or server handovers; never invent SSH hosts or bypass firewalls/CAPTCHAs/anti-bot protections. AIU is deferred at the user's request; continue locally, no fresh SSH probes until the user says ready.
6. Public-source downloads only, HTTPS through tools.a_dav.retrieval with a pinned plan, at most 500 MB per cohort without further approval. Treat AI-generated source leads as unverified until primary records establish them.
7. No permanent deletion: Trash only. No git worktree remove/--force, no branch -D. Approved cleanup moved only specific finished trees to Trash, pruned registrations, and branch-deleted with -d. No remote branch deletion. Never empty Trash.
8. Preserve live worktrees/a-p2-release-prep-20261112, worktrees/b-acquisition-20261110, worktrees/paper-c-spec. Cleanup may not alter their substantive content. Leave tools/a_analysis, tools/a_identity_adapter, tools/b_gdc, tmp/, .superpowers/ alone outside an explicitly authorized bounded paper task; B acquisition's authorized task may handle its own tools/b_gdc code and invented tests, not tmp leftovers.
9. dot_clean -m is user-approved for AppleDouble litter and before commits; do not traverse protected data/code or other live checkouts. Automatic review blocked blanket cleanup of protected live trees; that portion remains deferred. Main-repo cleanup removed 21 metadata sidecars. No substantive protected file was edited.
10. SSD can disconnect. Never recreate the SSD mount point. After reconnect verify recent files for truncation before resuming. Archive chats only when approved, never delete them.
11. Leave Paper F unchanged and outside current scope. N1 CONTEXT.md's +25-line F addition, N11 research evidence and N25 wayfinding map remain user's separate decision.
