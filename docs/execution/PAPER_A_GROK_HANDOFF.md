# Manual Grok handoff — Paper A implementation

Repository: https://github.com/OASolliman590/Master-Thesis- (private; use the user's existing authenticated access, never request keys in chat).

Verified code baseline when this handoff was prepared: `7c9ad16fc612a37c30836130d7976cf5fd368280`. Later documentation commits may contain this handoff. Inspect the current commit and dirty tree; never reset user work. The A/B scientific amendment is `38e3026` and remains controlling.

## Assignment and boundaries

The user requests manual Grok implementation of Paper A. Produce executable code, tests and real-source admission evidence, not another spec-only response. Do not invoke a delegation relay or additional agents. No commits or pushes; Sol reviews and the parent owns publication. Preserve Paper B/C/D and their outputs. A's source preparation and parameterized software implementation may proceed; real model fitting requires the A-specific scientific/data freeze. The repository's one-production-paper-at-a-time rule remains applicable to production analysis, not permission to abandon this authorized source/software work.

Work from `E:\Master_Thesis\master-thesis` or a separately created checkout of this repository. If another implementer is editing the same checkout, reserve A-owned paths and avoid shared-module changes; request a separate checkout rather than modifying their files. Never run git reset/clean or overwrite uncommitted changes.

## Read the actual GitHub files before coding

1. `AGENTS.md`, `CONTEXT.md`, `docs/execution/PROGRESS.md`.
2. `docs/decisions/AB_IMMUNE_BARRIERS_20260911.md`.
3. All `specs/A/`: README, DATA, ANALYSIS, DISCOVERY, TRANSPORT, ENGINEERING, FIGURES, PREREGISTRATION, REVIEW_RESPONSE and existing tickets.
4. `specs/B/IMMUNE_BARRIER_FRAMEWORK.md` for the consumer contract only; do not alter B.
5. `docs/research/A_clinical_transfer.md`, `A_COMPASS_2026.md`, `A_source_admission_91061/REPORT.md`, `A_source_admission_176307/REPORT.md`, `A_COMBAT_ADMISSION.md`, and their small provenance manifests where available.
6. Existing workflow code may supply ideas for manifests, hashes, atomic completion and test patterns. Do not copy B's patient-random ridge-validation design into A's study-held-out classification design.

Some source cache files are intentionally excluded from Git. Their absence in a clone is expected: retrieve permitted originals from verified source URLs or record missing status. Never fabricate a cache, replace it with synthetic data, or silently update a historical hash.

## Scientific purpose and selected primary

A identifies pretreatment expression programs associated reproducibly with objective response to immune checkpoint inhibitors across independently sourced eligible cohorts. A-P2 is selected: frozen discovered score versus fixed CYT, paired independent-test AUROC difference on the same patients, with specified cancer/cohort aggregation. A-P1 response-definition sensitivity is secondary. Do not revert to a CYT-only paper.

ORR: documented CR/PR positive; SD/PD negative. Preserve original assessment system/timing. Binary labels qualify only after original definitions are verified. Disease control includes SD and is not equivalent to duration-qualified benefit. PSA decline, survival and unspecified clinical benefit are separate endpoints.

The A-to-B/C product is a frozen discovery signature plus response-association/stability and immune-function annotations. It informs prostate molecular characterization and candidate biology. It is not a validated prostate ICI-response classifier, causal treatment-effect estimate, or guarantee of epigenetic reversibility.

## Source inventory: retrieve originals, audit every candidate

Source list below is the agreed source architecture and current candidate list, NOT a claim that each source is usable. Registry fields must distinguish verified metadata, downloaded objects, admitted cohort, blocked access and proposed discovery resource. Do not hard-code promotional resource totals as sample counts.

| Source | Role | Known issue / required action |
|---|---|---|
| NCBI GEO + linked original publications/supplements | Primary accessions, expression and clinical provenance | Retrieve exact objects; preserve raw labels, identifiers, versions, hashes, access and redistribution terms |
| GSE91061 (Riaz melanoma) | Candidate ICI development/test; label-definition analysis | 51 baseline patient candidates, at most 49 category-labelled in prior audit; prior ipilimumab strata are one originating cohort. Two source columns called Response must not overwrite each other. Verify source exclusions, timing, full FPKM universe and patient linkage |
| GSE176307 (Rose urothelial) | Candidate different-cancer ICI cohort | At most 88 labelled patient codes; repeat sequencing BACI165, two unmapped current matrix columns, pretreatment/adjudication questions. Resolve or report explicitly |
| GSE78220 (Hugo melanoma) | Candidate objective-response discovery/test | At most 26 baseline patient candidates; on-treatment sample and multiple baseline sites. No deposited SD; source irRECIST/category rules need reconciliation. Do not infer independent validation of signatures developed on these patients |
| GSE126044 | Candidate binary-response cohort | 16 records in prior audit; establish equivalence to declared ORR and baseline timing before primary admission |
| GSE135222 | Candidate separate PFS/duration analysis | Inspected metadata contain PFS/event information, not sufficient categorical ORR. Do not manufacture response labels |
| ICBatlas | Expand original-study inventory; possible permitted harmonized data | Publication DOI 10.1158/2326-6066.CIR-22-0249. Audit underlying accession/trial/patient overlap; resource copies are not independent cohorts |
| TIGER | Additional ICI cohort/source catalogue | Verify current official publication/site, export availability and source-level provenance before use |
| IOhub | Additional bulk/single-cell ICI source catalogue | Verify current official publication/site, original studies and source terms; do not merge bulk and single-cell observations as independent patients |
| Cancer-Immu | Additional multi-omic ICI source catalogue | Candidate catalogue pending official documentation/access verification; not an already-admitted cohort or mandatory dependency |
| ArrayExpress/BioStudies and dbGaP | Original hosting routes if identified by a candidate study | Record access tier; controlled access remains blocked without authorization. No alternate mirror to bypass restrictions |
| GDC/TCGA-PRAD; qualified TCGA-LUAD | Untreated molecular characterization / lineage comparison | No ICI labels; no false clinical validation or pooling away tissue effects. Use verified GDC API docs and annotation/measurement contracts |
| PCaDB and original prostate cohorts | Independent prostate molecular characterization | Verify current official source/access, original cohort identities, processing units and overlaps with TCGA/CPC. Array expression is not TPM |
| GSE229555 / COMBAT | Separate prostate regimen-specific exploration | 15 paired subjects in inspected public workbook; published subset differs. TPM-scale issue and clinical linkage unresolved. PSA50/radiographic flags do not supply ORR/DCR categories; combination/sequential treatment cannot isolate ICI benefit |
| Guan 2022 Nature, DOI 10.1038/s41586-022-04522-6 | Candidate prostate clinical context | Complete reusable expression/label package not secured; reported PSA-related endpoint is not ORR |
| Existing AIU old-run inventory | Discovery aid and exposure/overlap audit | Do not assume 1,300 eligible patients/22 independent cohorts. Consult existing approved inventory reports; do not inspect unrelated server directories or expose credentials |

GEO accession URL template: `https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE91061` (replace only with a listed/verified accession). Retrieve actual download URLs from source metadata; do not invent FTP filenames. GDC docs: `https://docs.gdc.cancer.gov/`. Search official sources for unpinned catalogue URLs; record the actual documentation consulted and retrieval date.

Published comparator/novelty sources: Ayers GEP (`https://www.jci.org/articles/view/91190`), CYT/Rooney DOI 10.1016/j.cell.2014.12.033, COMPASS final DOI 10.1038/s41591-026-04502-7 and repo audit above. Generic cross-cancer learning is not itself novel. A COMPASS/TIDE/TIS comparator requires source-correct implementation, availability, feature compatibility and training-overlap checks; never substitute a homemade score with the same name. Database coverage and comparator implementation are different requirements.

LINCS, DepMap/CCLE, DrugBank, ChEMBL, Perturb-CITE-seq and TISMO belong to Paper C's preserved source architecture, not Paper A's clinical training set. MethylCIBERSORT belongs primarily to B's separately specified composition sensitivity; do not add it as an assumed input to RNA-only ICI cohorts.

## Connected implementation stages

Use A-prefixed stage/module identifiers to avoid confusing B's W stages. Proposed ownership: `tools/a_workflow/`, `tools/a_sources/`, `tools/a_cohort/`, `tools/a_prediction/`, `tools/a_report/`, `tests/a_*/`, `specs/A/configs/`, `specs/A/synthetic/`, `docs/validation/A_pipeline/`. Shared-code edits require a narrow justified diff and regression evidence; never refactor B during this assignment.

1. **A1 real-source audit/acquisition:** executable inventory, originals/terms/checksums and candidate admission table. Start with real public metadata and permitted files, not only synthetic fixtures. No clinical scores/models yet.
2. **A2 patient/label/assay preparation:** raw-to-canonical records; originating study and trial identifiers; baseline/replicate rules; source-specific units and transforms; original-to-canonical labels and exclusions. Separate development, final-test and prostate branch manifests. Do not assign final test based on measured performance or call previously examined data untouched.
3. **A3 discovery development:** implement DISCOVERY.md's elastic-net logistic model with whole-cohort nested splits and all preprocessing inside training partitions. Emit paired held-out predictions, convergence evidence and frozen model/features/scalers/coefficients.
4. **A4 locked independent test:** exact artifact and exposure lock; no refit/calibration/feature changes; paired A-P2 AUROC contrast against CYT and specified uncertainty. Source failure leaves the declared aggregate incomplete, never silently reweighted.
5. **A5 secondary robustness:** fixed-score paired ORR/DCR comparison on the same eligible patients, category decomposition and source-correct frozen comparator panel. Do not invent SD for binary cohorts or duration for censored cases.
6. **A6 prostate characterization and A-to-B/C handoff:** assay/scale-qualified molecular characterization; independent clinical prostate analysis only for its actual supported regimen/endpoint. Export all frozen coefficients and provenance before final-test inspection, plus descriptive stability and separately sourced immune annotation. No truncated score pretending to be the original model.
7. **A7 report:** four figures in the amended A FIGURES.md order, underlying plotted tables, actual counts/exclusions/uncertainty and plain-language explanations beside each graph. Explicitly separate synthetic demonstration, real-source evidence and real biological results.

Target interface to deliver (currently proposed, not existing commands):

```text
python -m tools.a_workflow audit --config specs/A/configs/sources.json --output AUDIT_DIR
python -m tools.a_workflow run --mode synthetic --config specs/A/configs/synthetic.json --output RUN_DIR --through A7
python -m tools.a_workflow resume --output RUN_DIR
```

First reviewable checkpoint: real public-source audit plus connected A1-A2 executable preparation with fixtures and source-backed adverse cases. Then continue connected A3-A7; do not mark the full assignment complete at the first helper or CYT tracer. No simulated processing stages or placeholder scientific payloads. Parameterized coding can proceed while an unresolved real contract is blocked; the block must identify the exact branch and required evidence.

## ML contract and leakage requirements

Use the exact proposed learner in DISCOVERY.md as explicit versioned configuration, not undocumented defaults. Proposed values include log2(1+TPM), training-only TPM/variance filtering, at most 5,000 training-variable genes, elastic-net logistic SAGA, C {0.01,0.1,1,10}, l1_ratio {0.1,0.5,0.9}, specified cohort/cancer sample weights, convergence rules and tie handling. Verify the installed scikit-learn API against its official versioned docs before implementing. These values remain proposed for the real analysis until frozen; fixtures do not freeze science.

At least three eligible independent development cohorts plus separately reserved final-test data are needed for the proposed structure. Require both classes and estimable inner folds. This is structural feasibility, not adequate power. Never replace study-held-out validation with patient-random folds to force success. Leave-cancer-out is additional and only where estimable. Map duplicates before splitting and retain prior ICI, biopsy/treatment timing and disease context.

Test that changing held-out expression cannot change training filters/scalers; held-out labels cannot change tuning outside their assigned role or the frozen handoff; final-test mutation cannot change model/genes; study/patient overlap fails; unknown labels/missing features are not imputed; paired AUROC matches hand calculations and ties; all required test cohorts contribute or the aggregate fails; no convergence warning is silently treated as a pass. Report negative/null results unchanged.

## Runtime, evidence and delivery

Local candidate interpreter: `E:\Master_Thesis\.venvs\paper-b-20260911\Scripts\python.exe`. Inspect available packages; do not mutate B's shared tested environment. If A requires new dependencies, create a separate A environment with a recorded lock. AIU candidate interpreter: `/home/omics/miniforge3/envs/omics-py/bin/python`. Use approved existing SSH access, isolated project paths and bounded jobs; do not assume VPN/server availability or alter shared environments. No GPU is required by the proposed model.

Create a strict A test runner that fails on skipped/zero-discovered tests. Run focused A checks and meaningful integration/leakage tests. Run B regressions only if a shared implementation/dependency changed. Source/version/config/code hashes and atomic completion/resume records are mandatory. Do not include API keys, sessions, patient matrices or restricted records in Git/Notion/report text.

Write `docs/validation/A_pipeline/GROK_IMPLEMENTATION_REPORT.md` and, on this machine, `E:\Master_Thesis\planning\grok_local_repair\GROK_A_IMPLEMENTATION_REPORT.md`. Include code baseline, files changed, actual commands/exit codes/test counts, real-source admission table, current eligible patient counts with reasons, output paths, train/test exposure/split feasibility, reproducibility evidence, actual AIU results or pending state, completed stages and exact remaining blockers. Sol reviews the code before parent publication. No commit/push/delegation.
