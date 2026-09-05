# AIU execution capability audit

Checked 5 September 2026 through the existing authenticated SSH alias. Primary thesis root remains `/home/omics/projects/ici_thesis_pipeline`; old code/results were not changed. A separate `master-thesis` checkout beneath that root was absent at inspection.

Live executable checks succeeded for system Python 3.10.12, Git 2.34.1, `/home/omics/miniforge3/envs/omics-py/bin/python` 3.11.16 and `/home/omics/miniforge3/envs/omics-r/bin/Rscript` 4.5.3. Micromamba is at `/home/omics/.local/bin/micromamba`. Registered environments include omics-py, omics-r, omics-tools, omics-md and md-analysis. A compact existing omics-py package inventory is recorded in aiu_python_inventory.json; it is an observation, not a project lockfile or proof of compatible imports.

The inspected `/home/omics/bin/omq` is a small per-GPU queue wrapper, not a cluster resource scheduler. Its submit command selects CUDA_VISIBLE_DEVICES and starts a lane runner; it does not impose CPU/memory quotas. No sbatch/qsub command was found on the checked login PATH. Do not infer that queuing grants unlimited resources. No job was submitted, cancelled or relaunched.

Next: synchronize the reviewed repository into a separate checkout, verify its commit, then inspect/import only dependencies required by the agreed pilot. Choose a dedicated environment or explicitly reused environment from actual compatibility checks. Avoid modifying shared environments to satisfy guessed requirements.

During VPN interruption record the commit, exact unrun command and last known job handle in pending_validation.json. Inspect remote job state before retrying; a disconnected client does not prove a job stopped.
