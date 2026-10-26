# A/A.1 data acquisition: appraisal and API-first route

25 October 2026 · coordinator: Claude Opus 5.5. Three read-only investigations fed this appraisal: a code audit, a process audit, and a survey of programmatic sources. The coordinator spot-checked their key claims. Nothing in this appraisal is authorized to change a frozen spec.

## Verdict

The workstream built and reviewed infrastructure around the data instead of acquiring data. Concretely:

- **Real data.** No real sample header has been parsed. There are 0 crosswalks and 0 admission receipts. Twelve real public objects are hashed in custody, but none has been opened (`docs/validation/A_DAV_06/LANE_F_CUSTODY.md`: "Nothing was parsed").
- **The pipeline cannot accept real data.** `tools/a_dav/core.py:180` rejects any packet not classified `SYNTHETIC_ONLY`. So every stage from T04 onwards (registries, endpoints, timing, assays, admission, matrices) refuses real data by construction.
- **The only working Riaz crosswalk is outside DAV.** It is a 74-line September script, `docs/research/A_source_admission_91061/audit_metadata.py`. It reads the GEO family SOFT plus the author tables, but it is hard-coded to an `E:/` path.
- **Effort went into procedure.** The 23 packets contain 632 files: 94 receipts, 41 Sol and 19 Astra receipts, and 69 further review files. The Prat work is 11 packets and 117 files, with 0 lines of code that touch real Prat data.

## Why it stalled (evidence-based)

1. **Review loops ran until ACCEPT, and every finding reopened the packet.**
   - Small hardening issues got the same blocking weight as real gaps. Examples: a Bearer-token heuristic took 5 revisions, and chunked encoding, `RAW.tar` counting and the HTTP host field each forced rework.
   - Review counts: A-DAV-04 had 8 code rounds, A-DAV-05 had 5, and A-DAV-07 had 8 Astra reviews for 14 GET requests.
   - The frozen spec asks for *one review requirement per ticket*, not convergence.
2. **Synthetic completion was counted as progress.**
   - All 14 tickets were "accepted" on invented inputs, with the real-source tracers marked NOT_RUN.
   - Riaz is the named tracer for DAV-T02/T05/T06/T11, yet its objects were never retrieved into DAV.
3. **Prat became a gate, and requirements were added that the spec does not contain.**
   - The added requirements were: byte-continuity with the 2017 attachment, two authenticated readers, invented-case rehearsals, and archive hunts.
   - "Two-reader" appears nowhere in `specs/A_DATA_ACQUISITION_VALIDATION`. It comes from a historical, non-frozen pipeline document.
   - **Prat GSE93157 is also NanoString (GPL19965), not RNA-seq.** Whether it fits a bulk RNA-seq Paper A at all is an open question.
4. **Every step needed a new packet, a new authorization and its own hash ledger.**
   - The events log stops on 21 Oct, so the Prat work is unlogged.
   - "BLOCKED_UNKNOWN" was used whenever an authority could not be found. For a public GEO object, the user and supervisor are the natural reviewer and integrator.

## What the frozen spec actually requires for a first baseline cohort

These are the V1–V7 gates for `A_BASELINE_BIO`:

- **V1.** Study and family identity.
- **V2.** The exact object, a complete SHA-256, and the terms. When the terms are unclear, publish hashes and instructions, never bytes.
- **V3.** The unit, transform and IDs.
- **V4.** A private header → specimen → patient crosswalk.
- **V5.** The raw response kept unchanged, then mapped to ORR and bound to the episode.
- **V6.** An overlap disposition.
- **V7.** A dated receipt from a real source reviewer and the integrator.
- **Per ticket.** TDD, one review requirement, and one real-source tracer.

Nothing in the spec requires historical byte continuity, two readers, repeated review rounds, or per-packet hash ledgers.

## Data acquisition can be done by API, not by hand

All of the following was tested live using small metadata calls only.

| Source | What it gives | Access |
| --- | --- | --- |
| GEO `acc.cgi?acc=GSE…&targ=gsm&form=text&view=brief`, family SOFT/MINiML, GEOparse/GEOquery | Per-sample `characteristics_ch1`. Verified for GSE91061: 109 samples, visit Pre 51 / On 58, response PD 48 / SD 34 / PRCR 23 / UNK 4, patient ID in the title (`Pt1_Pre_…`). | REST, no key |
| NCBI E-utilities (db=gds) | Series UID, platform, sample count, PMID, GSM→title | REST |
| ENA Portal API `filereport` | Run→sample→title (Riaz PRJNA356761; Gide PRJEB23709 gives patient and timepoint but not response) | REST |
| Author repo `riazn/bms038_analysis` (GitHub API, pin a commit) | `bms038_clinical_data.csv` (BOR, cohort NAIVE/PROG, PFS, OS), `SampleTableCorrected.9.19.16.csv` | REST. There is no licence, so keep the files private and publish hashes only. |
| cBioPortal REST (iAtlas-harmonized studies) | `mel_iatlas_riaz_nivolumab_2017` (107), `hugo_ucla_2016` (27), `gide_2019` (91), `liu_2019` (122), `imvigor210_2017` (347), and others, with RESPONSE, RESPONDER, PRIOR_ICI_RX and SAMPLE_TREATMENT | REST, no key |
| CRI iAtlas GraphQL | 23 ICI datasets | GraphQL |

**MCP is not the answer by itself.** BioMCP does not cover GEO sample metadata. GEOmcp and cbioportal-mcp describe themselves as experimental, and cbioportal-mcp needs database credentials. MCP output is also not versioned, which weakens provenance. Use MCP for exploration at most, and do acquisition with roughly 100 lines of scripted REST calls whose responses are pinned and hashed.

**Harmonized resources are a cross-check, not the source of record.** cBioPortal's Riaz study has 107 samples, not 109, and only 98 RESPONSE values. Labels must be reconciled against GEO and the author table, and disagreements flagged automatically.

## Recommended route: one vertical slice, Riaz GSE91061 × A_BASELINE_BIO

1. **`geo_metadata_adapter`.** Fetch the GEO sample-brief text, or the family SOFT, through the existing allowlisted fetcher. Store it privately with a SHA-256, then parse it into specimen and patient proposal rows. It should be a port of `audit_metadata.py`, tested on a small real-format fixture, and it must reproduce 109 / 51 Pre.
2. **`author_table_adapter`.** Pin `bms038_analysis` at a commit SHA. Read the sample and clinical tables by column position, join them to GEO, keep the raw BOR, and flag conflicts automatically. The known conflicts are `Pt7_Pre`→`Pt72`, NE vs UNK, Pt3, and the four exclusions in the author code.
3. **A real-data packet class in `core.py` (`PUBLIC_REAL`/`PRIVATE_REAL`), plus one command: `dav run GSE91061 --branch A_BASELINE_BIO`.** It chains the two adapters with the FPKM header check (reusing `batchqual/adapters/riaz_fpkm.py`), feeds the T04→T09 modules, and stops at a **reviewer worksheet** that lists only the judgment items.
4. **cBioPortal cross-check.** An automatic per-patient disagreement report.

**Deliverable:** a private crosswalk, a conflict report, and a draft V7 receipt for the user and supervisor to sign. When this works, the same registry-driven pipeline repeats for Hugo, Gide and Liu by adding a field map, not a new packet.

### Human decisions that remain (and only these)

- The responder definition (CR/PR vs SD/PD; SD handling; RECIST vs irRECIST) and the NE/UNK rule.
- Whether ipilimumab-progressed patients are kept or stratified.
- Overlap between Riaz and Hugo.
- Whether NanoString cohorts such as Prat belong in Paper A.
- Whether to apply for controlled access (Liu dbGaP).
- Whether data from an unlicensed author repo may be used.
- A ruling on each automatically flagged conflict.

## Proposed operating changes

These are proposals. Items marked † would need an explicit spec amendment.

- **Review.** One independent review, plus one fix-verification. After that, Medium and Low findings go to a backlog unless they affect privacy or data integrity. Drop the separate Astra layer for software slices.
- **Authorization.** One authorization per cohort slice, not one per packet.
- **Hash ledger.** One rolling hash manifest, covering real objects only.
- **Stop:** further synthetic, legacy or environment hardening unless a real-source run reproduces a defect.
- **Stop:** two-reader rehearsals and archive hunts. Prat is deferred, with the NanoString question attached.
- **Stopping rule.** If a source's essential V4/V5 evidence (patient link, response label) cannot be obtained from its official objects within one slice, defer it and move to the next queued cohort.
- **† Reviewer.** For public, non-controlled objects, a single named human reviewer (the student or supervisor) satisfies the V7 "source reviewer".
- **† Review cap.** Cap the number of review rounds per ticket.
- **Logging.** Resume logging in `orchestration/events.jsonl`. The Prat work from 23 to 25 Oct is unlogged.
