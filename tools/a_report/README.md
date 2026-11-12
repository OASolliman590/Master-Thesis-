# Paper A report shells

Build static manuscript layout examples from fixed invented values. The
command does not open cohort runtimes, product results, or source data. It
writes 18 single-page figures as SVG and PDF, seven TSV shells, and a
provenance manifest.

Use the existing `sc-analysis` Python environment for figure rendering. The
`dav-pipeline` Python environment supports CLI help, output-path validation,
and preservation checks, but it does not include Matplotlib or NumPy.

```sh
MPLCONFIGDIR=<writable-private-cache> python -m tools.a_report --output-dir <absolute-private-output-directory>
```

Run that command with the `sc-analysis` Python interpreter. The output
directory must be outside the repository and either new or empty. Choose a
fresh directory for each run; a nonempty directory is refused without
opening or changing its contents. Generated figures and tables repeat the
INVENTED DATA — MANUSCRIPT SHELL label. No gate, biological result, or outcome
release is implied.

The manifest records the fixed fixture hash, code hash, classification,
output hashes, and the fact that external inputs were not opened. Rendering
tests use `sc-analysis` Python; the focused suite can also run in
`dav-pipeline` Python, where only the plotting-dependent test is expected to
skip.

The SC-1 shell shows invented custom composite panels only. Its value is the
per-study median donor `log2(CPM+1)` (`median_log2_cpm_plus1`); each study gets
its own nonnegative color scale from assessed values, with a visible 0–1
fallback when all assessed values are zero or unavailable. Dots stay fixed in
size. Individual M5/M6 gene dots are not plotted here; their product size field
is `median_percent_cells_detected`, the median donor percent with counts above
zero, not coverage.

SC-3 keeps RECIST, pathology, and T-cell expansion in separate metric-family
panels. T-cell expansion is a nonclinical metric, not clinical response. The
heatmap displays Hedges `g`; DE `log2FoldChange` remains a separate field and
scale.

The A-LONG shells use the supplied W8 field inventory as a layout guide; this
report does not assert compatibility with a corrected W8 candidate. Figure 8
combines invented aggregate pairing/selection structure,
exact-day versus interval timing, and the central `R_minus_NR_change` estimate
with separate ANCOVA sensitivity. S3 counts independent study families in its
invented source flow; patient, specimen, and assay N remain UNKNOWN separately.
S4 shows separate within-group `DELTA_R` and `DELTA_NR` intervals. S5 compares
invented independent family/cancer directions, with patient units for the
within-study effects, and marks influence output unavailable. S6 shows matched
primary, same-lesion, exact-day, and tighter-timing sensitivity examples. S7–S10
identify gated moderator-design (independent studies plus paired-patient
support), released heterogeneity (independent families), orthogonal context
(patients with nested cells/spots), and NMA/handoff (studies/programmes)
questions without estimates.

Real source/release status and real patient N remain unavailable; specimen and
assay counts remain separate. All displayed values are invented, and no pair,
patient, or source rows are included. Readiness records the verification
history, user decisions, and future command templates; no outcome command was
executed.
