# Swarm batch 1 and the Riaz split role: decisions (27 Oct 2026)

The user made these decisions in chat on 27 Oct 2026.

1. **Riaz split role.** All 51 baseline patients of `riaz_gse91061` × A_BASELINE_BIO get the permanent role **DEVELOPMENT**. The role was prespecified from metadata, and no model performance was observed. Riaz will not be used as an untouched final test. The final-test cohort will be chosen later, from cohorts that nobody in this project has analysed, and it will be locked before anyone looks at it.
2. **Batch 1 cohorts.** Hugo GSE78220, plus the GEO cohorts whose objects A-DAV-05 already located: GSE115821, GSE176307, GSE168204, GSE126044 and GSE248014. Public data only.
3. **Downloads.** The coordinator may download public objects for batch 1 without asking per cohort, within these limits:
   - at most 500 MB per cohort and 3 GB in total;
   - only from GEO, ENA, GitHub at a pinned commit, and cBioPortal;
   - no controlled access.
   The coordinator reports the file list after each fetch.
4. **Models and lanes.**
   - **Cohort lanes:** free OpenCode models. They see only public metadata and code, never the private store. Each lane writes only its cohort's field map, fetch plan and sources note.
   - **Shared code:** `gpt-6.1-terra` at high effort is the only writer of `tools/a_dav/*.py`. It also does one review per batch.
   - **Cross-check:** a second free model checks each field map against its sources.
   - **Sign-off:** the user signs one batch worksheet.
5. **Process.** The lean rule applies. Data checks decide. There is one review per batch, and only High findings or findings that affect privacy or integrity are fixed.
