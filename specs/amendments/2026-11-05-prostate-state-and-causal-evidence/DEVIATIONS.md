# Deviation and exposure log: 5 Nov 2026 amendment

Dated record. Add to it; do not rewrite entries.

## 6 Nov 2026: outcome-related column loaded during the A-RCT source audit

- **What happened:** the first audit script blocked outcome columns by name, but its pattern missed `Tumor_Shrinkage`. That column was loaded into memory for CheckMate 025 patients with RNA.
- **What was seen:** one line giving the number of distinct arm and value pairs (187). No value, summary or link to any score was printed.
- **Effect:** none on results. The values were not used.
- **Action:** later audit steps name the columns they read, rather than blocking by pattern.

## 6 Nov 2026: class counts read for the A-RCT audit (level 2 exposure, allowed)

- `ORR` categories were counted by arm, for all CheckMate 025 patients and for those with RNA. Counts are in `docs/validation/A_RCT_FEASIBILITY_20261106.md`.
- No expression value, score or other feature was joined to these counts.
