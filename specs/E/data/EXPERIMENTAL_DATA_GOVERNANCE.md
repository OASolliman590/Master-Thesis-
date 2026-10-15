# Original-data boundary in the public core

No core packet requires donor consent documents, device inventory, local reagent availability, experimental generation or local prospective validation. Those are E_LAST responsibilities. The shared legacy schemas include experimental records solely for format compatibility and labelled test fixtures; their existence does not admit original data to core.

Core loaders must reject internal unpublished observations for real runs. They must not search internal storage opportunistically or read optional extension outputs while fitting public-only models. Runtime manifests declare mode `public_core`, a public-object allowlist and excluded internal paths. All role selection and caches must include mode and input hashes.

A missing E_LAST directory is a supported installation. Core deletion/mutation isolation tests must demonstrate identical public-input selection, model configuration and output hashes with internal data absent, present, changed or inaccessible. Such a production test is specified here; this revision executes only the contract-level version.

Historical proposed experimental inventory and raw biological records are deliberately not included in active core registries. The extension's own permissions/access/approval states control later use. This is a software/data-policy separation, not an exemption from institutional requirements for actual experiments.
