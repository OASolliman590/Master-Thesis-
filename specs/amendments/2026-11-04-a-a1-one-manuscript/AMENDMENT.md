# Papers A and A.1: one manuscript (4 Nov 2026)

**Status: DRAFT, NOT SIGNED.** It takes effect only when the user signs it. Until then the v2.1 specs stand as written. The user said on 4 Nov 2026 that A and A.1 will be in the same manuscript; this note works out what that changes. All of it was decided before any response result existed.

## Decision

Paper A and Paper A.1 are published as one manuscript. A.1 stops being a possible separate paper and becomes a named product of Paper A: **A-LONG**, the on-treatment change analysis. "A.1" stays as the name of its spec folder and tools.

The manuscript asks one question in two parts: what immune biology before treatment goes with response to ICI, and how does that biology change during treatment?

## What changes

1. **Publication gate removed.** The separate-manuscript conditions no longer apply: `specs/A1/INTERFACES.md` (last paragraph), `specs/A1/README.md` (status line), `specs/A1/READINESS.md` row L6 and the "Publication gate" section of `specs/A1/VALIDATION_AND_FIGURES.md`. These files get a pointer to this note.
2. **Product order in Paper A.** A-LONG joins the list in `specs/A/SPEC_v2.md` section 1 as a secondary product, after A-BIO, A-P2 and A-P1, and alongside A-COMP. A-P2 stays the single formal primary.
3. **Figures.** One new main figure joins the Paper A plan in the analysis-modules spec, as Figure 8. It combines verified pair structure (1B) and the direct response-by-time estimates (2B). A.1 panels 1A, 2A, 2C and 3C go to the supplement. Panels 3A, 3B, 4A and 4B are shown only if their gates pass, and in the supplement.
4. **Overlap.** Baseline samples in A-LONG are also in A-BIO. The manuscript reports this once and presents them as the same patients, never as independent support for A-BIO.
5. **Budget.** The hours stay as they are: about 60 for A.1, on top of Paper A's. No saving is assumed until the writing starts.

## What does not change

- **A.1's design:** the central estimand, pairing rules, windows, ANCOVA sensitivity and claim limits in `specs/A1/SPEC_v2.md`.
- **Separate statistics:** A-LONG keeps its own tests and FDR families. It adds nothing to A-BIO's families or to A-P2.
- **One-way flow:** A-LONG never selects or changes A-P2 features, A-BIO results or the frozen predictor. `longitudinal_support.tsv` stays corroboration only.
- **Scientific gates:** the pairing, window and roster gates in `specs/A1/SPEC_v2.md` section 9 still apply. One study still cannot be called cross-study replication.
- **Protected data:** IMvigor210 stays out, at every timepoint.

## If the data are thin

A-LONG is reported whatever it finds, with the pairs it has. If too few pairs pass the gates, Figure 8 shows the pair structure and per-study estimates, and the manuscript says the question could not be answered well. Paper A's main results do not depend on it.

## Sign-off

- [ ] Signed by the user, date: ________
