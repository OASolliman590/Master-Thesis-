# Batch-1 review decisions (28 Oct 2026)

The user decided these in chat on 28 Oct 2026.

1. **Expression column rules approved** for GSE248014, GSE168204 and Hugo GSE78220, as proposed in their field maps (`expression_column_map`):
   - **GSE248014:** the header `<patient>_<visit>` matches the title "patient <patient> at time point <visit>".
   - **GSE168204:** header and title match after `-`→`_` normalization and removal of a trailing `_bam`.
   - **Hugo:** the header `PtN.baseline` matches the title `PtN`.

   All three were checked to be one to one.
2. **Hugo Pt27.** This patient has two pre-treatment biopsies: lesion A (right upper arm) and lesion B (right upper back). The baseline table uses lesion **A**, chosen by a fixed rule set in advance that ignores outcome: the lowest lesion letter. Lesion B stays linked as an extra measurement and is not used in the baseline table.
3. **Hugo Pt16.** Only an on-treatment biopsy exists, so Pt16 is NOT_APPLICABLE for A_BASELINE_BIO. It is kept for A.1.

These decisions do not sign any worksheet. Each cohort's worksheet is signed separately, once its context is final.
