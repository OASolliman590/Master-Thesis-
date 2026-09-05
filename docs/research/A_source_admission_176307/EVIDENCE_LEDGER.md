# GSE176307 grilling ledger — 2026-09-06

All proposed decisions remain unapproved. `REPORT.md` contains direct source links; local source receipts are in `PROVENANCE.json`.

| Question | Factual answer / boundary | Status | Exact source/field and verification | Spec impact |
|---|---|---|---|---|
| How many independent units? | 90 GSM records, 89 patient codes, one duplicate patient; at most88 labelled codes | Locally verified metadata; eligible N unknown | SOFT `Series_overall_design`, `Sample_title`, `io.response`; official key; `audit_metadata.py` | Correct ceilings; choose duplicate representation before scores |
| Does every matrix column identify a patient? | Current TPM92 RS columns; official key maps90, leaves2 unmatched | Verified header-only | `salmon_tpm...` first line and `Sample ID`/`Omniseq_RS_ID (RNAseq)` key fields | Do not invent identities or admit unmatched columns |
| Is this a baseline cohort? | Archival tissue verified; per-specimen pre-ICI timing not established | Unknown for admission | Original article Methods, cached GEO sample fields lack collection/ICI interval | Timing gate remains open for both primaries |
| Are all PD labels RECIST radiographic PD? | Original response definition has non-imaged clinical nonresponse exceptions | Source-reported; individual flag unknown | Original article Methods → Clinical annotation | Preserve mixed ascertainment; do not call strict RECIST-only |
| Does SD mean durable benefit? | GEO has SD labels; original clinical benefit has a duration condition | Categories verified; individual duration eligibility unknown | `io.response`; original Clinical annotation | A-P1 proposed recoding distinct from reported clinical benefit |
| Are all files TPM? | Only the current Salmon file is explicitly declared TPM; transformed CSV is different; RSEM field unspecified | Source-reported units plus observed format | GEO `data_processing`, current directory, complete TSV headers/partial CSV header | Separate adapters/unit contracts; no reverse transform assumption |
| Are both CYT genes covered? | Present in partial transformed CSV header; current TPM gene coverage uninspected | Verified narrow fact; main-input coverage unknown | Prefix/header artifacts | Do not close CYT/TPM feature gate |
| Does an atlas add another independent study? | UNC-108 is the GSE176307 source alias | Source-reported reuse; broader patient overlap unverified | 2025 meta-analysis Data availability | Originating-study deduplication; independent split gate |
| Is one primary now approved? | Neither A-P1 nor A-P2 chosen; source audit cannot choose | Proposed planning boundary | Parent task and A source/discovery contracts | Preserve alternatives and unapproved cohort-role assignment |

No scores, models, treatment effects or full expression-matrix calculations were performed. This ledger distinguishes source facts from proposed admission rules rather than treating a successful download as scientific readiness.
