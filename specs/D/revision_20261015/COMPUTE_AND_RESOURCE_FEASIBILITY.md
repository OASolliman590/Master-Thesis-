# Compute and resource feasibility

## Known historical AIU observations

A prior repository audit observed Python 3.11.16 in an `omics-py` environment and a per-GPU queue wrapper rather than a standard SLURM/PBS scheduler. That inventory is historical, not a current resource guarantee or resolved D lock.

## First operations

- CPU-only metadata and checksum inspection;
- JSON/TSV validation;
- small source tracers;
- arithmetic/baseline tests;
- official small upstream reproduction after approval.

## Required before GPU/model execution

Current CPU, RAM, GPU model/VRAM, driver/CUDA, storage/quota, active jobs, scheduler/queue behaviour, environment/container, checkpoint size, expected runtime, and licence.

## Prohibited without separate approval

Large model training, Tahoe-x1-3B or equivalent training/fine-tuning, large atlas downloads, paid/requester-pays transfer, controlled access, and open-ended GPU sweeps.

Prefer released checkpoints, smaller models, parameter-efficient adapters only when justified, and surrogate/sensitivity designs that respect compute limits.
