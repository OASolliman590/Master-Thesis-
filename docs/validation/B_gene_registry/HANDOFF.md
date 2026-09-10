# B-G1 local software handoff

This is an implementer receipt for parent review. It is not parent acceptance, not AIU validation, not real annotation coverage, and not scientific readiness. No TCGA/CPC cohort, outcome, score, probe, or model was used.

## Base

- Requested base: `933f6a8`
- `git rev-parse HEAD`: `933f6a8c0c7dfa8d4c60bd7d6fb4306077b61570`
- Local interpreter used for these gates: Python 3.12.10 (stdlib-only code; AIU Python 3.11 was not run)

## Scope and boundaries

Owned paths only:

- `tools/b_gene_registry/`
- `tests/b_gene_registry/`
- `docs/validation/B_gene_registry/`

The CLI is `python -m tools.b_gene_registry build` with explicit `--registry`, `--schema`, `--annotation-manifest`, and `--output`. Tests create only tiny synthetic, patient-free annotation fixtures. Required annotation sources missing after valid registry/manifest checks emit only `INCOMPLETE.json` and exit 3. Existing output paths are refused without mutation. No network, no real cohort files, no CPC outcomes, no probe selection, no scoring, and no model fitting.

Schema files are admitted only with the Draft 2020-12 dialect URI and the v0.2 schema `$id` URI; a minimal or opened object schema is rejected before use. v0.2 registries must retain the locked alias/non-collapse rules and the exact 11 program id/layer pairs.

## Files

| Path | SHA-256 (this run) |
|---|---|
| `tools/b_gene_registry/__init__.py` | `c26a6b817a423a33844b57725a3acec127af72dc3a5f01803a8d0a12a5263962` |
| `tools/b_gene_registry/__main__.py` | `a28c5825b5c766662b240a06dafbd929c0f637ccf752804e8915eff19e19875c` |
| `tests/b_gene_registry/test_b_gene_registry.py` | `3918a287dc72a1d3581bd9e91fdc1e4ee9132c18f138ef3fa08d992bcbad8add` |

Changes remain uncommitted. Owned paths are untracked: `tools/b_gene_registry/`, `tests/b_gene_registry/`, `docs/validation/B_gene_registry/`.

## Commands and actual results

```text
python -m py_compile tools/b_gene_registry/__init__.py tools/b_gene_registry/__main__.py tests/b_gene_registry/test_b_gene_registry.py
```

Exit 0.

```text
python -m unittest discover -s tests/b_gene_registry -v
```

**15 tests, 15.665 s, `OK` (exit 0).** Prior acceptance tests remain. Added subprocess tests mutate schema identity/open objects, required aliases and the TAPBP/TAPBPL pair, v0.2 program ids/layers, and RFC 3339 `date` (including `20260910`, which `date.fromisoformat` accepts). Those cases exit 3 with no `COMPLETE.json` or output directory.

```text
python -m json.tool specs/B/gene_set_registry.proposed.json
python -m json.tool specs/B/gene_set_registry.schema.json
```

Both exit 0. Specs were not edited.

```text
git diff --check
```

Exit 0. This workspace reports dubious ownership, so the check was invoked as a one-shot `git -c safe.directory=<repo> diff --check` without writing git configuration.

## Limitations

- Parent has not independently rerun or accepted this receipt.
- AIU Python 3.11 execution was not performed and is not claimed.
- Synthetic fixtures do not measure real TCGA GENCODE v36, GSE107299, or historical v18 annotation coverage.
- The registry remains proposed and unfrozen. B-G1 does not freeze `P`, select probes, score programs, or authorize B-I5.
