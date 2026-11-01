# Batch 2 (cBioPortal cohorts): decisions, 30 Oct 2026

The user decided in chat on 30 Oct 2026.

1. **Final test: IMvigor210 is UNTOUCHED_FINAL_TEST** for A-P2 (the urothelial cancer study, atezolizumab, `blca_iatlas_imvigor210_2017`). The protection covers the whole study family in every paper (A-BIO, A-PRED, A.1, B, C):
   - curators may reconstruct headers and endpoints;
   - nobody inspects its expression–response relationships, DEG tables or predictions until the authorized final evaluation.
   - Prior ICI for a final-test cohort may not be UNKNOWN. It must be documented, for example from the trial eligibility criteria; otherwise A-P2's test is nonestimable.
2. **Liu 2019 and Gide 2019 are DEVELOPMENT.** prior_ici_policy UNKNOWN_ALLOWED_DEVELOPMENT applies where prior ICI is undocumented.
3. **Exposure: METADATA_ONLY** for all three. Neither the user nor the earlier project examined their expression or scores against response.
4. **Routine answers accepted:**
   - the composite row `THRA1/BTR` is excluded under NONSTANDARD_ROWS_EXCLUDED (FEATURE_ID_AND_SCALE_RULES_20261028.md): listed, never renamed;
   - unlabelled responses stay UNKNOWN, never non-response;
   - patient–sample joins come from the source PATIENT_ID/SAMPLE_ID fields;
   - Liu: the iAtlas TPM is primary, with the DFCI TPM pinned as a sensitivity; iAtlas is the source of record for the 2 differing response labels, and the DFCI labels are kept, never overwritten;
   - melanoma overlap (Liu, Gide, Riaz, Hugo, GSE168204) is flagged and independence is not certified.
5. **Still open:**
   - V3 processing facts (iAtlas TPM pipeline; Gide's log2 upper-quartile normalization);
   - IMvigor210 prior-ICI eligibility evidence;
   - the IMvigor210 author package (HTTP only, not retrieved);
   - the Gide author cross-check.

## Follow-up decisions (user, 30 Oct 2026), after the processing-evidence search
Evidence: `docs/research/cohort_sources/BATCH2_PROCESSING_EVIDENCE_20261030.md`.
- **Liu: the authors' DFCI TPM (`mel_dfci_2019`) is now primary**; the iAtlas TPM becomes the sensitivity. This replaces item 4's Liu line. The DFCI TPM is documented: STAR + RSEM, gene-level, linear TPM, with snoRNAs removed and the rest re-summed. iAtlas's pipeline is undocumented. Response labels follow the authors (DFCI `BR`), and iAtlas `RESPONSE` is kept alongside, never overwritten. Prior ICI comes per patient from DFCI `PRIOR_CTLA4`.
- **Gide: the user will supply the methods text** (RNA-seq processing) from the paywalled paper (Cancer Cell 2019, PMID 30753825). Gide stays unsigned until then.
- **IMvigor210 author package:** retrieved once over plain HTTP into an isolated staging folder under `.scratch/runtime/imvigor210/`:
  - `IMvigor210CoreBiologies_1.0.1.tar.gz`, 73,683,703 bytes, SHA-256 `890b80da68a837db6edbc1d348c53de4c7c8c7e9eddf3000bf26df5ef2b4668a`, Last-Modified 14 Dec 2023;
  - it is not extracted or installed, and its R code is never run;
  - its data files (for example `data/cds.RData`) are read only at the authorized final evaluation, or for curation-only header/endpoint checks.
- **IMvigor210 prior ICI:** NONE at study level, by trial eligibility (NCT02108652 excludes prior anti-CTLA-4, anti-PD-1 and anti-PD-L1).

## Gide decisions (user, 30 Oct 2026)
- **Admitted with a declared limitation, DEVELOPMENT only.** The deposited `mel_iatlas_gide_2019` profile (log2 upper-quartile normalized counts) was produced downstream of the authors, by an UNDOCUMENTED pipeline (see `docs/research/cohort_sources/gide2019_SOURCES.md`). It passes V3 under a written exception, with four conditions:
  - Gide is analysed only on its own deposited scale (per-study models), never merged into a common cross-study representation;
  - every pooled result is also reported without Gide;
  - Gide can never be a final-test or confirmation cohort;
  - the limitation is stated wherever Gide contributes.
- **Author clinical tables retrieved** (publisher supplementary files, public), in an isolated staging folder under `.scratch/runtime/gide2019/`:
  - `mmc2.xlsx` = Table S1, anti-PD-1 monotherapy, SHA-256 `6153cd8606c17a43f2a1dd36967a5680b42693007f428daffc4bb80feefe2c15`;
  - `mmc3.xlsx` = Table S2, anti-PD-1 + anti-CTLA-4, SHA-256 `83c5efac77e6566fb4af3569afe8f814325d03394c05e21d7f6952e9f9c44ac5`.
  - Per patient they give: treatment, best RECIST response, PFS and OS (days), biopsy sites and EDT timing, and RNA-seq availability.
  - They have no prior-ICI column, so prior ICI stays UNKNOWN under the DEVELOPMENT policy.
- **Endpoints:**
  - ORR from the per-patient best RECIST response;
  - separately, the authors' clinical benefit (CR, PR, or SD > 6 months without progression; non-responders PD or SD ≤ 6 months), derived from Table S1/S2 response + PFS, as a SOURCE_BINARY endpoint;
  - the two are never merged.

## Liu V3 (user, 30 Oct 2026)
Liu's DFCI TPM is accepted for DEVELOPMENT. Sourced facts: linear gene-level TPM; STAR + RSEM; snoRNA removal with Ensembl GRCh38.p10 biotypes; Illumina HiSeq 2000 v3 / 2500, 76 bp paired-end; exome-captured cDNA from FFPE (`liu2019_SOURCES.md`). The alignment reference build and GTF, and the tool versions, are recorded as UNKNOWN. This is a lighter limitation than Gide's: no own-scale-only restriction, but the unknowns are stated wherever Liu contributes. The Pre-Ipi samples are still open.
- **Liu Pre-Ipi samples (user, 30 Oct 2026):** the 14 samples labelled `Pre-Ipi` (taken before earlier ipilimumab, not at the start of anti-PD-1) are excluded from the main A_BASELINE_BIO baseline. They are kept for a prior-ICI sensitivity analysis. If the same patients also have a later pre-PD-1 biopsy, the pairs feed a descriptive A.1 note only.

## Liu signature and Gide join rule (user, 30 Oct 2026)
- **Liu 2019 signed** in chat: "I sign the Liu 2019 A_BASELINE_BIO worksheet as omar soliman with the suggested answers. Admit it for DEVELOPMENT." Signed with the suggested answers in `.scratch/runtime/liu2019/final-unsigned-20261030c/`. Gates V0–V7 PASS, V8 BLOCKED_UNKNOWN until the matrix is validated.
- **Gide join rule, verify-then-use.** The proposed rule is cBioPortal `PD<n>` = author Table S1 patient n, and `iP<n>` = Table S2 patient n.
  - It is used only if **every** pair agrees on sex, age, drug, best RECIST response and PFS (author days against cBioPortal months, within rounding).
  - Any disagreement, any unmatched row, or any ambiguity means the rule is not adopted and the author tables stay unlinked. The disagreements are reported in aggregate, without patient IDs.

## Gide link and Liu feature scope (user, 30 Oct 2026)
- **Gide link adopted, corrected rule.** The round-19 check matched 75 cBioPortal patients, and all 75 pairs agreed on sex, age, drug, best RECIST response and PFS (0 disagreements). 30 author rows had no match. The authors' Tables S1/S2 list every trial patient (105); 31 of them have no RNA-seq ("-"). The rule, as approved:
  - link the 75 agreeing pairs (PD<n> = Table S1 n, iP<n> = Table S2 n);
  - check that every unmatched author row is a patient without RNA-seq;
  - report any exception in aggregate (the counts suggest one).
  - If an unmatched row does have RNA-seq, or a matched row has none, report it and leave that patient's author fields unlinked.
- **Liu feature scope.** Add the assay-policy category COMPLETE_WITH_DOCUMENTED_EXCLUSIONS. It is allowed only when the source documents the excluded feature class (Liu: 380 snoRNA genes removed using Ensembl GRCh38.p10 biotypes). Liu is admitted under it.
- **Raw route on the cluster: ON HOLD.** The user's research on harmonized ICB collections may change the source strategy; see `specs/amendments/2026-10-30-source-strategy/DECISION_PENDING.md`.

## Liu transfer and Gide signature (user, 30 Oct 2026)
- **Liu:** the signature is transferred although the already-answered FEATURE_ROWS_EXCLUDED item no longer appears in the signed-admission context. The 10 duplicate-symbol rows stay excluded under NONSTANDARD_ROWS_EXCLUDED. All other items must be identical. This is the same kind of approved drop as GSE168204's.
- **Gide signed** in chat: "I sign the Gide 2019 A_BASELINE_BIO worksheet as omar soliman with the suggested answers; admit for DEVELOPMENT." Its scope is DEVELOPMENT only, under the documented-processing exception, with ORR and the authors' clinical benefit kept as separate endpoints.
