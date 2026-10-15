# Implementation and source-state reconciliation

This revision edits the delivered 13 October Markdown/schema package in a new local directory. It does not modify the original ZIP, a repository checkout, remote branch or A–D production code.

The live GitHub branch list was re-read on 15 October 2026. Main remained `a8278c776da7c6b096cc14139d729979db286b50`; the list also contained the A acquisition review branch (`293130281db0a827cda0e975aec3b823403df68f`) and a Paper C review branch pointing to the main snapshot. AGENTS, CONTEXT and a progress excerpt were re-read. No live uncommitted work can be inferred from GitHub. A full A–D regression or AIU environment inspection was not performed.

The live AGENTS rule says agents do not commit/push; the orchestrator owns integration, and only one paper's production implementation is active. This bundle respects that boundary. Draft integration text is supplied; no write-access failure or lack of GitHub account permission is claimed as a substitute for that policy.

## Reuse versus new scope

| Existing item | Reuse | Required caution |
|---|---|---|
| v1 source/observation/event/parameter schemas | Retained version 1.0.0 where unchanged | They validate syntax, not external-only admission |
| v1 contract-checking helper/tests | Retained and rerun locally | Historical receipt removed; fresh results have software-only meaning |
| Source curation/unit/digitisation contracts | Retained with v2 operating boundary | Source availability not reverified for every inherited route |
| PK/observation scaffolding | Retained/adapted | No claim of an already executable calibrated model |
| v1 primary local HLA endpoint | Removed from core, retained conditionally in E_LAST | Cannot block core completion |
| v1 original experimental inventory | Moved out of active core dependence | Not proof of received reagents or generated data |
| v1 packet order | Replaced E0–E7; X0–X5 separate | E6 never waits for local experimental validation |

A future integrator must compare actual target paths and latest branch state before applying the kit. Do not run historical acquisition scripts or commit an additive patch blindly; their network/privacy assumptions may differ.
