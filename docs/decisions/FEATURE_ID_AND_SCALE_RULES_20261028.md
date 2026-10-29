# Feature identifiers and FPKM scale taken from the object (28 Oct 2026)

The user approved these rules in chat on 28 Oct 2026. They extend `OBJECT_DERIVED_EVIDENCE_20261028.md` and apply when GEO text and the cited paper are silent. Each fact is recorded as `DERIVED_FROM_OBJECT` with the rule name.

1. **GENE_SYMBOL_MAJORITY.** If at least 99% of row identifiers match the HGNC symbol pattern (`[A-Z0-9][A-Za-z0-9.-]*`), the feature identifier system is recorded as gene symbol.
2. **NONSTANDARD_ROWS_EXCLUDED.** The remaining rows are listed in the worksheet with their reason and excluded from scoring. Examples: merged names (`APOBEC3A_B`), suffixed duplicates (`C4B_2`), transcript IDs (`TCONS_…`), names that look date-mangled (`SEP15`, `DEC1`), and duplicate symbols. Nothing is renamed, remapped or guessed.
3. **LINEAR_FPKM_BY_RANGE.** For a source labelled FPKM, if the maximum finite value is above 50 and every value is non-negative, the transform is recorded as NONE (linear, not log). Otherwise the transform stays BLOCKED.

These rules are representation facts only. They do not authorize scoring or real-response analysis.
