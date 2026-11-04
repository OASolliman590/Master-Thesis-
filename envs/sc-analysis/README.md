# Single-cell analysis

The prostate h5ad workflow uses the prebuilt Python environment and pins in `requirements.lock`. The commands below do not install packages. From the worktree root, set `THESIS_RUNTIME` to the private runtime root and choose an output directory with `--results` or `THESIS_RESULTS`:

```sh
../../envs/sc-analysis/bin/python -m tools.sc qc --atlas prostate --results "$SC_RESULTS"
../../envs/sc-analysis/bin/python -m tools.sc embed --atlas prostate --results "$SC_RESULTS"
../../envs/sc-analysis/bin/python -m tools.sc labels --atlas prostate --results "$SC_RESULTS"
../../envs/sc-analysis/bin/python -m tools.sc compartments --atlas prostate --results "$SC_RESULTS"
../../envs/sc-analysis/bin/python -m tools.sc pseudobulk --atlas prostate --results "$SC_RESULTS"
```

The Lin workflow runs through `tools.r_bridge.run_r` and keeps the Seurat object in R. Pseudobulk outputs use `<results>/<A|B>/sc_<atlas>/pseudobulk/<compartment>/` with `expression.tsv`, `clinical.tsv`, and a hash-checked `manifest.json`. SC-3 is outcome analysis; real atlases require the explicit `--allow-outcomes` flag, and the synthetic fixtures do not validate biology.

The prostate map assigns basal epithelial cells to `basal epithelial`; Club, Luminal, Luminal_like, and Club_IFN labels to `luminal/malignant epithelial`; T cells to `T/NK`; B cells and plasma cells to `B/plasma`; myeloid cells to `myeloid`; CAFs and smooth muscle cells to `fibroblast/stromal`; and endothelial cells to `endothelial`. Ciliated and NE cells were moved out of the luminal/malignant compartment and remain unassessed pending a cited mapping rationale. The Lin source-label mappings are in `tools/sc/lin_compartment_map.tsv`.

TNBC_Shiao has non-integer stored values, so it is ineligible for count-based pseudobulk; its audit reports the fractional-entry count and at most 20 fractional values, preserves stored values, and never rounds them.

Run the h5ad tests and combined regression using the documented interpreters; keep pytest staging and runtime caches under the ignored worktree `results/` directory:

```sh
../../envs/sc-analysis/bin/python -m pytest -q -rs --basetemp=results/sc-test-tmp tests/sc
../../envs/dav-pipeline/bin/python -m pytest -q -rs --basetemp=results/dav-test-tmp tests/sc tests/a_meta tests/r_bridge tests/a_cohorts
```

The standard-library environment skips the h5ad-specific tests when `anndata` is unavailable. The Lin real-R integration is marked `requires_r` and must run through `tools.r_bridge.run_r`.

## Method and tool references

- Scanpy QC, normalization, highly variable genes, PCA, neighborhood graph, UMAP, and Leiden steps follow the documented APIs; see [Wolf et al., 2018](https://doi.org/10.1186/s13059-017-1382-0) and the [Scanpy API documentation](https://scanpy.readthedocs.io/en/stable/api/index.html).
- Patient-level aggregation sums raw counts before inference, consistent with [Crowell et al., 2020](https://doi.org/10.1038/s41467-020-19894-4), [Squair et al., 2021](https://doi.org/10.1038/s41467-021-25960-2), and the [decoupler pseudobulk API](https://decoupler.readthedocs.io/en/latest/api/generated/decoupler.pp.pseudobulk.html).
- The Lin object remains in Seurat and its count layers are accessed independently using [SeuratObject's layer API](https://satijalab.github.io/seurat-object/reference/Layers.html) and [qs2](https://github.com/qsbase/qs2). Differential expression uses [DESeq2](https://bioconductor.org/packages/DESeq2/) with the signed patient-level design.
