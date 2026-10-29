# Evidence taken from the object itself (28 Oct 2026)

The user decided in chat on 28 Oct 2026 that the pipeline may use evidence taken from the object itself when both GEO text and the cited paper are silent. Each such fact is recorded as `DERIVED_FROM_OBJECT`, together with the exact rule that produced it. A fact that remains ambiguous stays BLOCKED.

The allowed rules are:
- **Feature-ID type, from the identifier format.** All IDs match `^ENSG\d{11}(\.\d+)?$` → Ensembl gene. All IDs are numeric → Entrez Gene. All IDs are HGNC-like symbols → gene symbol. If the IDs are mixed or ambiguous → BLOCKED.
- **Raw counts.** If every retained value is a whole, non-negative number, the unit is raw counts and the transform is NONE. RSEM expected counts that are not whole numbers are recorded as the unit "RSEM expected counts", transform NONE, but only when GEO or the paper names RSEM.
- **Unit from the file name plus the paper.** A file name that states the unit (for example `…FPKM…`) counts as evidence only when the paper's methods do not contradict it. Both sources are cited.

In addition, the GSE168204 table has 44 empty cells. They stay missing and are never filled with zero. Any gene with an empty cell is left out of that cohort's signature scores, and the number of genes dropped is reported.
