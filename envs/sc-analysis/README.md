# Single-cell Python environment

The h5ad analysis uses the prebuilt environment and the pins in `requirements.lock`; analysis commands do not install packages. From the worktree root, launch it with:

```sh
../../envs/sc-analysis/bin/python -m tools.sc qc --atlas prostate --results "$SC_RESULTS"
../../envs/sc-analysis/bin/python -m tools.sc embed --atlas prostate --results "$SC_RESULTS"
../../envs/sc-analysis/bin/python -m tools.sc labels --atlas prostate --results "$SC_RESULTS"
../../envs/sc-analysis/bin/python -m tools.sc compartments --atlas prostate --results "$SC_RESULTS"
../../envs/sc-analysis/bin/python -m tools.sc pseudobulk --atlas prostate --results "$SC_RESULTS"
```

Set `THESIS_RUNTIME` to the private runtime root containing the atlas stores. Set `THESIS_RESULTS` or pass `--results` to choose an output root. The default results directory is derived from the worktree location. The Python entry point creates writable matplotlib and Numba caches under the operating system temporary directory. `sc3` requires `--allow-outcomes` for a real atlas; synthetic fixtures exercise its grouping and effect rules without reading atlas outcomes.

Run the h5ad tests and combined regression with the documented interpreters:

```sh
../../envs/sc-analysis/bin/python -m pytest -q -rs tests/sc
../../envs/dav-pipeline/bin/python -m pytest -q -rs tests/sc tests/r_bridge tests/a_cohorts
```

The stdlib environment skips `tests/sc/test_pseudobulk.py` and `tests/sc/test_prostate.py` when `anndata` is unavailable. The Lin real-R integration is marked `requires_r` and runs through `tools.r_bridge.run_r`.

## Method and tool references

- Scanpy's QC, normalization, highly variable gene, PCA, neighborhood, UMAP and Leiden workflow follows the documented API; see [Wolf et al., 2018](https://doi.org/10.1186/s13059-017-1382-0) and the [Scanpy API documentation](https://scanpy.readthedocs.io/en/stable/api/index.html).
- Patient-level aggregation sums raw counts before inference, consistent with [Crowell et al., 2020](https://doi.org/10.1038/s41467-020-19894-4), [Squair et al., 2021](https://doi.org/10.1038/s41467-021-25960-2), and the [decoupler pseudobulk API](https://decoupler.readthedocs.io/en/latest/api/generated/decoupler.pp.pseudobulk.html).
- The Lin object remains in Seurat and its count layers are accessed independently using [SeuratObject's layer API](https://satijalab.github.io/seurat-object/reference/Layers.html) and [qs2](https://github.com/qsbase/qs2). Differential expression uses [DESeq2](https://bioconductor.org/packages/DESeq2/) with the signed patient-level design.
