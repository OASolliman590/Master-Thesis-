# Master thesis — single-goal execution prompt

## One goal

Develop a scientifically defensible, evidence-grounded specification kit for every paper in my agreed four-paper MSc programme, then implement each feasible paper sequentially through reviewed, reproducible coding milestones, using AIU as the principal execution server, the verified private thesis GitHub repository as the versioned record, and Notion as the continuously maintained project record. Continue until each paper has a reviewed specification and an honestly evidenced implementation status; unresolved scientific or infrastructure requirements must remain explicit rather than be replaced by invented answers, fabricated results or unverified completion claims.

## Preserve my programme and decisions

Read the original submitted protocol, both wet-lab plans, the existing spec kits, the supplied Claude conversation and the latest corrections before designing work. Workspace: E:\Master_Thesis. Server handover: E:\HANDOVER\_servers.md. Read connection details privately; never copy credentials into prompts, logs, GitHub or Notion.

Use stable labels and retain the historical numbering in a crosswalk:

- A: immune-signature robustness, clinical endpoint definitions and transferability.
- B: prostate methylation-associated immune regulation; the central computational thesis biology.
- C: epigenetic-drug prioritisation with functional, immune-context and pharmacological corroboration; the third current paper and Claude's original Paper 4.
- D: virtual-cell perturbation benchmarking; conditional on a valid independent benchmark.

Preserve the registered wet-lab component and its computational interfaces. Neither code nor virtual-cell predictions replace required experiments. Original six-paper ideas outside A–D remain in an ideas register unless I explicitly reactivate them. Four months at five hours daily is the planning constraint; publication acceptance is not a controllable completion criterion.

Read planning/feasibility/C_SOURCE_SCOPE_RESTORED.md before assessing C. Its agreed sources include TCGA/PRAD/LUAD, LINCS/CMap, CCLE, DepMap, PRISM/GDSC, DrugBank, ChEMBL, Perturb-CITE-seq/Frangieh/SCP1064, TISMO and the proposed LJP4 interferon-reference arm. Verify the last arm's actual coverage. GSE199800/GSE216053 add measured prostate corroboration; they do not replace the agreed architecture. Keep source roles and independent evidence distinct. Do not silently demote or delete an agreed source because an easier dataset exists.

The previous A/C endpoint revisions and narrow/combine/defer recommendations are proposals to examine, not a licence to overwrite my programme. Reconcile them during documented grilling. Old code and historical runs are optional reusable assets; repairing them is not a prerequisite for scientific design. Audit only the components selected for reuse.

## Install and use the real skills

Inspect existing skills first. Install missing relevant skills from https://www.aihero.dev/skills and its linked official repository https://github.com/mattpocock/skills. Use the applicable skill-installer and current documented installation method; resolve actual paths, dependencies and references rather than guessing them. Record upstream commit/release, installation location and local modifications. Avoid duplicate installations or overwriting working skills without reviewing differences.

Explicitly use setup-matt-pocock-skills, grill-with-docs, its grilling/domain-modeling dependencies, research where appropriate, to-spec, to-tickets, implement, code-review and diagnosing-bugs as applicable. Read the actual SKILL.md files and required references before using them. If a host lacks a named invocation mechanism, use the documented compatible mechanism and report any unsupported capability. Do not pretend that an invocation succeeded.

Inspect/install the relevant skills from https://github.com/amElnagdy/delegate-skills, including delegate-setup and the available codex-, grok-, claude- and agy-delegate skills. Configure this thesis project using the current schema; preserve unrelated global settings. Follow applicable approval requirements using the authorization already present in this conversation. Where approval of the final concrete fleet configuration is still required, first show the discovered capabilities, lane table and complete configuration, then explain the exact requirement. Do not repeatedly ask permission for actions I have already authorized.

## Grilling must produce evidence, not plausible answers

Conduct grill-with-docs for each paper before to-spec. Research questions from primary scientific papers, original dataset records, official tool/API documentation and inspected data. Agent opinions and agreement between models are not factual evidence.

For every grilling question record: question ID; proposed answer; whether it is a verified fact, inference, design choice or unresolved unknown; supporting DOI/URL and exact section or dataset field; source/release date; verification command or inspected artifact where applicable; uncertainty/contradictions; effect on the spec; and decision status. Check that each citation actually supports the attached claim.

Resolve answerable factual questions autonomously, with bounded consultation from Claude Opus or Grok when useful. If evidence is missing, record unknown and investigate the best available route. Never manufacture a factual answer merely to finish the interview. Ask me only for information, preferences, institutional decisions or material tradeoffs that cannot be established from the records. Proposed statistical thresholds and modelling choices must be justified and labelled as choices, not presented as facts from a citation.

Challenge novelty, eligible sample size, power/precision, response definitions, timing, repeated patients, cohort overlap, cell composition, tissue lineage, species transfer, biological replication, exposure, directionality, leakage, multiplicity and external validation. Compare with the closest published studies and current relevant preprints, identifying preprints correctly. Record why the paper adds knowledge beyond its closest precedent; using more databases alone is not novelty.

For each resource, verify accession/release, access conditions, modality, identifiers, actual eligible patients/independent experiments, controls, model/treatment/time/dose coverage, missingness, licence and redistribution conditions. Distinguish catalogue size from usable sample size. Audit overlap among CCLE/DepMap/PRISM releases and reused clinical atlases. A metadata inspection is not a matrix-level validation.

Use small real-data checks before accepting critical tool/data assumptions. Consult the documented version of each algorithm and executable interface. Synthetic fixtures are allowed for software invariants and must be labelled synthetic; they cannot stand in for biological validation. Preserve null results and uncertainty. Do not turn a missing expected biological signal into an automatic technical failure.

## Produce a complete spec kit for every paper

Create and independently review all four design packages before production implementation. Existing kits are inputs to reconcile, not proof that designs or tests are correct. Each package must contain:

1. Scope, thesis/protocol mapping, novelty comparison, hypotheses, claim limits and proceed/narrow/combine/defer criteria.
2. Source-by-question coverage matrix, versioned data manifest, access/redistribution notes, identifier mappings and representative real-data verification artifacts.
3. One primary endpoint, exact estimand/formula, experimental unit, inclusion/exclusion rules, covariates, missing-data policy, multiplicity, precision assessment and secondary/exploratory analyses.
4. Validation strategy, development/test boundaries, patient/experiment grouping, feature-selection and preprocessing boundaries, and pretraining-overlap checks where relevant.
5. A four-figure evidence outline with each panel tied to a question, dataset, analysis, uncertainty display and claim.
6. Preregistration draft, decision log/ADRs, evidence ledger, glossary, citation library and explicit unresolved questions. Preserve prior exposure to data; a Git tag alone is not external preregistration.
7. Software architecture, documented tool versions, environment lock/container specification, input/output schemas, provenance/checksum strategy, workflow graph, resources and AIU run instructions.
8. Bounded implementation tickets with dependencies, owned files, acceptance criteria, meaningful tests, real-data smoke checks, restart behaviour and review requirements.
9. Test plan for substantive risks: sign reversal, label/timing mistakes, duplicate patients, leakage, identifiers, missing/inferred genes, replicate handling and statistical calculations. Tests must challenge behaviour, not merely mirror implementation.
10. Reproduction guide, expected artifacts and a spec-readiness checklist with no hidden blockers.

Do not label a blocked or conditional package implementation-ready. D must have a complete conditional design even if its benchmark remains unavailable; document the exact evidence needed to reopen it. A combine/defer recommendation remains reviewable and must not silently cancel a paper. Finish unaffected design work while investigating blockers.

## Delegated work and independent review

Use one accountable orchestrator and a bounded fleet. Preferred roles are Astra for planning/integration/final review, consulting Claude Opus; Opus may lead planning with Astra consulting when that is the active arrangement. Use Grok as an additional bounded technical/scientific challenger where useful.

Heavy coding may use Codex Spark, Grok, Claude Code and Antigravity with the requested Gemini model. Opus handles independent code review and difficult debugging; Astra performs final milestone review. Treat these as requested roles, not verified capabilities. Discover actual installed/authenticated CLIs and exact supported model IDs. In particular, verify what the user's names "Codex Spark" and "Gemini 3.8" resolve to; never invent a model ID or silently substitute a different model under the requested name. If unavailable, disclose it and use another already-authorized suitable fleet member where possible. Record any unmet mandatory final-review role.

Read each implementer's delegation skill before dispatch. Each brief must include the scientific contract, citations/documented APIs, allowed files, exact acceptance criteria, data fixtures, execution host, constraints and required output. Use isolated branches/worktrees or disjoint ownership; avoid simultaneous edits to shared files. Bound concurrency to actual server resources and available tool limits. Implementation within the active paper may be parallelized, but only one paper's production implementation is active at a time.

Inspect every returned diff and resolve reviewer findings with evidence. The orchestrator verifies applicable gates and owns integration, commits and pushes. A successful agent exit, approval message or multi-agent consensus does not replace tests or scientific validation. Do not buy credits, change subscriptions or start open-ended paid compute without authorization.

## Sequential implementation and AIU execution

After all design packages have been reviewed and each ready spec committed/pushed, freeze a dependency-aware implementation order. Default: minimal shared interfaces, then B, C, A and finally D if its feasibility conditions are met. Revise the order only for a documented dependency or my instruction. B's fixed literature program permits it to start independently of A; freeze any discovery-derived B handoff before C uses it. Do not implement a blocked analysis simply to preserve this order.

Use AIU as the principal working/execution server through the existing handover configuration. Inspect available environments, storage, scheduler/resource limits and existing project state before provisioning work. Reuse viable environments without disrupting other jobs. Keep local development/checkpoints portable and synchronize through reviewed commits and manifests. Do not move the main workload to another server or initiate large training jobs merely to bypass a temporary VPN outage.

If VPN/SSH times out, record the last known job state and exact unrun tests, preserve code and logs, and continue useful documentation, review or lightweight local checks. Remote jobs may continue after disconnection: inspect their status before relaunching. Maintain a pending-validation queue containing commit, environment, commands, expected artifacts and dependency blockers. Resume AIU tests when connectivity returns during active work. Do not busy-loop, kill unknown remote jobs or mark deferred tests passed. Push interrupted milestones only as clearly labelled work-in-progress; do not tag them validated or build dependent scientific conclusions on unrun checks.

For each implementation milestone: read ticket/spec → delegate bounded work → inspect diff → run feasible tests → Opus review/debug → resolve findings → Astra final review → commit/push → update Notion. A paper is implemented only when its required workflow and validation gates have actually run and its outputs/provenance are reproducible; scaffolding alone is not implementation.

## GitHub, Notion and durable progress

Resolve the exact private thesis repository from existing authenticated GitHub information/remotes. I have referred to it as master thesis, master-thesis and master thesis protocol: do not guess that these are separate repositories or invent an owner/name. Inspect existing content/branches before cloning or publishing; ask only if the destination remains genuinely ambiguous. My request authorizes reviewed milestone pushes to that verified private repository. Preserve its visibility and existing work; use ordinary reviewed branches/PRs consistent with its workflow, without force-pushing or deleting unrelated history.

Push each completed spec and every implementation milestone with clear scope, review evidence and validation status. Record the commit SHA and verify push success. Keep credentials, restricted patient-level data and unlicensed redistributions out of GitHub, Notion and delegated prompts. Use manifests/retrieval instructions for data that cannot be committed; large data belong in appropriate authorized storage.

Maintain the existing Notion project at https://app.notion.com/p/3d24763e55d28144bcdefd15d74d45c4 and its plan/blueprints. Read current content before targeted updates. After each substantive milestone record the evidence-backed decision, artifact/commit links, tests run or deferred, reviewer/model roles, blockers and exact next action. Git holds executable/versioned work; Notion holds readable decisions and progress. A Notion summary alone is not a backup of code or research data.

Maintain a local progress ledger, pending-validation queue and handover with the last verified state so interruptions and context compaction do not restart the project or lose scope corrections. When GitHub or Notion is unavailable, queue exact unsynchronized updates and reconcile them later. Never claim a push, backup, review, installation or test happened without checking the result.

## Completion and persistence

Progress autonomously through authorized work, giving concise updates on evidence, decisions and blockers. Do not repeatedly return plans instead of producing artifacts. Do not convert every scientific question into a user questionnaire when source research can answer it. Respect genuine institutional decisions and unresolved mandatory requirements.

Maintain one goal throughout. Completion requires a reviewed spec package for every agreed paper, actual implementation/validation of each feasible approved package, published milestone records in the verified private GitHub repository, synchronized Notion documentation and a reproducible handover. Any paper still blocked or deferred must be reported as such; it is not implemented and must not be counted as a completed execution requirement unless I explicitly accept that disposition. The goal does not promise journal acceptance, new biological discoveries or degree approval.

When this prompt is activated, begin by reconciling the current documents and restoring the full agreed scope, verifying skills/repository/server/fleet access, then conducting evidence-grounded grilling for all four spec kits. Do not start by repairing the historical codebase.

## Workflow references verified when drafting

- AIHero skills and installation: https://www.aihero.dev/skills
- Official skills repository: https://github.com/mattpocock/skills
- grill-with-docs and its dependencies: https://github.com/mattpocock/skills/blob/main/skills/engineering/grill-with-docs/SKILL.md
- to-spec workflow: https://www.aihero.dev/skills-to-spec
- Delegation package: https://github.com/amElnagdy/delegate-skills

Drafted 5 September 2026. This file is the execution prompt; its existence does not certify skill installation, fleet configuration, a GitHub push or an analysis run.
