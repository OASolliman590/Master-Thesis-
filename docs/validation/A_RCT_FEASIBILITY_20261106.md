# A-RCT feasibility audit, Stage 1 (6 Nov 2026)

Source: Braun 2020 workbook, SHA-256 `a1f8683676d416b255291dcaa007aa0fa48c736c23e6a7a566664ba528bf205b`. Aggregate counts only. No feature was joined to any outcome. Exposure is logged in `specs/amendments/2026-11-05-prostate-state-and-causal-evidence/DEVIATIONS.md`.

| Check | Result | Status |
| --- | --- | --- |
| 1. S4A holds everolimus expression | 130 everolimus and 120 nivolumab CheckMate 025 patients; all 311 S4A columns match S1 | Pass |
| 2. Trial IDs and arm | `Cohort` = CM-025 and `Arm` are present. Whether `Arm` means assigned or received is not documented | Pass, one point open |
| 3. Specimen timing, one per patient | No patient has two RNA rows. All 155 known timings are positive, read as collected before trial therapy; 95 are missing. Median 727.5 days (everolimus) and 567 days (nivolumab); 15 patients within 90 days | Pass as an archival marker |
| 4. Path to RNA | 130 of 397 everolimus (33%), 120 of 406 nivolumab (30%). Tissue selection rules are not in the workbook | Open |
| 5. Batches | The workbook S1 has no batch field. ComBat was fitted across both arms | Open |
| 6. Precision for ORR | 5 everolimus responders | **Fail** |

## Arms in the RNA subset

| Measure | Everolimus, all | Everolimus, RNA | Nivolumab, all | Nivolumab, RNA |
| --- | ---: | ---: | ---: | ---: |
| Patients | 397 | 130 | 406 | 120 |
| Two or more prior therapies | 147 (37%) | 54 (42%) | 131 (32%) | 35 (29%) |
| MSKCC favourable | 141 (36%) | 48 (37%) | 136 (33%) | 36 (30%) |
| Female | 104 (26%) | 38 (29%) | 94 (23%) | 26 (22%) |

## ORR classes

| Class | Everolimus, all | Everolimus, RNA | Nivolumab, all | Nivolumab, RNA |
| --- | ---: | ---: | ---: | ---: |
| CR/PR | 17 | 5 | 94 | 25 |
| SD | 224 | 67 | 140 | 45 |
| PD | 106 | 37 | 142 | 41 |
| Not evaluable | 50 | 21 | 30 | 9 |

The response rate in the RNA subset is close to the full trial in both arms. Not-evaluable patients are more common with everolimus (16% against 8% in the RNA subset), so dropping them is a post-randomisation selection that differs by arm.

## Conclusion

A-RCT is feasible as a data source. The signed ORR interaction is not: five responders in one arm cannot support it. Any change of endpoint needs the user's decision and a signed change, before any score is joined to an outcome.
