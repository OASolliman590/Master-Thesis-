# NMRbox ICI Canary Harness

This folder contains the NMRbox reproducibility canary for the ICI RNA-seq thesis pipeline.

The canary is intentionally small. It packages source code plus lightweight reviewed outputs, submits a modest HTCondor job, rebuilds the report when possible, fingerprints key scientific tables, and writes an internal audit markdown.

It does not run the full pipeline and does not transfer raw sequencing or large expression data by default.

## Local Bundle
```bash
bash scripts/nmrbox_ici_canary/prepare_bundle.sh
```

## Remote Submit
```bash
ssh beryllium.nmrbox.org
cd ~/ici_thesis_pipeline_canary
tar -xzf ici_thesis_pipeline_canary.tar.gz
cd ici_thesis_pipeline_canary
mkdir -p condor_logs
condor_submit scripts/nmrbox_ici_canary/condor_ici_canary.sub
condor_q osoliman -nobatch
```

## Pull Audit Outputs
```bash
REMOTE_DIR="~/ici_thesis_pipeline_canary/ici_thesis_pipeline_canary" bash scripts/nmrbox_ici_canary/pull_results.sh
```

Review `nmrbox_scientific_audit.md` before planning any full NMRbox rerun.

## If NMRbox Python Packages Are Broken
The canary may fail before report building if the system Python has a broken `numpy`/`pandas` stack. Build an isolated environment in the extracted bundle:

```bash
cd ~/ici_thesis_pipeline_canary/ici_thesis_pipeline_canary
bash scripts/nmrbox_ici_canary/bootstrap_python_env.sh
PYTHON_BIN="$HOME/ici_thesis_pipeline_pyenv/bin/python" bash scripts/nmrbox_ici_canary/run_ici_canary.sh
```

For Condor, submit again after adding `PYTHON_BIN=$HOME/ici_thesis_pipeline_pyenv/bin/python` to the job environment or wrapping the executable.
