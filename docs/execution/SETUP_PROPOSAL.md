# Concrete project setup proposal

Status: approved by the user with AGENTS.md on 5 September 2026; applied. The proposal below is retained as the approval record. Discovery notes at the end are historical; see PROGRESS.md for corrected CLI availability.

The existing private destination is `OASolliman590/Master-Thesis-`; it was empty when inspected. Local checkout: `E:\Master_Thesis\master-thesis`. AIU is reachable through the existing SSH alias and the designated thesis root exists. No production analysis has started.

## Engineering skill setup

Use GitHub Issues in this private repository as the canonical spec/ticket tracker, with local markdown mirrors for durable work during outages. Use one root `CONTEXT.md` glossary and `docs/adr/` for consequential decisions. Create root `AGENTS.md`; neither it nor `CLAUDE.md` currently exists. The triage skill is not installed, so its label-vocabulary interview is inapplicable.

Proposed complete `AGENTS.md`:

```markdown
# Thesis project instructions

Read CONTEXT.md, docs/execution/PROGRESS.md, the applicable paper evidence ledger and accepted decisions before editing. The latest user scope corrections take precedence over historical proposals.

Preserve A/B/C/D labels and the full restored Paper C source architecture. Do not turn unresolved questions into facts or claim synthetic fixtures validate biology. Cite primary scientific sources and official tool documentation. All four spec packages require review before production implementation; only one paper's production implementation is active at a time.

AIU is the principal execution server. Record deferred remote tests and live job handles; never report them as passed. Keep credentials and restricted data out of this repository and delegation briefs. Agents do not commit or push; the orchestrator reviews and owns integration.

## Agent skills

### Issue tracker

Specs and tickets live in this private repository's GitHub Issues, with local markdown mirrors. See docs/agents/issue-tracker.md.

### Domain docs

Single-context glossary and decision layout. See docs/agents/domain.md.
```

Proposed complete `docs/agents/issue-tracker.md`:

```markdown
# Issue tracker: GitHub

Canonical tracker: GitHub Issues in OASolliman590/Master-Thesis-. Use gh with the verified repository. Store exact multiline issue/spec bodies locally and send with --body-file. Keep local paper spec and ticket mirrors under specs/ for offline continuity. Record issue URLs and synchronization status.

Publishing a spec means creating/updating its parent GitHub issue after scientific review; it does not authorize an agent to implement the whole parent issue. Only bounded unblocked child tickets are dispatchable. Do not label incomplete scientific designs ready-for-agent. Apply that label only to reviewed actionable items and distinguish parent specs from coding tickets.

Read issue bodies/comments before updates. Link dependencies explicitly. PRs as a request surface: no. No notification messages to other people are authorized.
```

Proposed complete `docs/agents/domain.md`:

```markdown
# Domain docs

Read the root CONTEXT.md glossary and relevant accepted docs/adr/ decisions before designing or editing. This is a single scientific programme context with stable A/B/C/D paper labels. Use precise terms from the glossary and surface conflicts rather than silently changing meaning. Missing domain documents are not a blocker; create them lazily when concepts or consequential decisions are resolved. Keep implementation details out of the glossary.
```

## Available fleet proposal

| Lane | Implementer | Verified model ID | Basis |
|---|---|---|---|
| research | codex | gpt-6-astra | User requested Astra scientific planning; discovery reports model and authenticated CLI |
| heavy | codex | gpt-5.3-codex-spark | User requested Spark coding; discovery reports model and authenticated CLI |
| final-review | codex | gpt-6-astra | User requested Astra final review; read-only |

No reasoning-effort override is added. Existing unrelated global lanes remain untouched and must not be used accidentally for thesis dispatches. Project `heavy` overrides the old global Aider lane only in this repository.

Proposed complete project configuration:

```json
{
  "version": "delegate-fleet.v1",
  "lanes": {
    "research": {"implementer": "codex", "model": "gpt-6-astra", "readOnly": true},
    "heavy": {"implementer": "codex", "model": "gpt-5.3-codex-spark"},
    "final-review": {"implementer": "codex", "model": "gpt-6-astra", "readOnly": true}
  }
}
```

Local discovery: Codex authenticated; Grok 1.0.13 reports grok-4.6 but is not authenticated; Claude and Antigravity were not found on Windows PATH or AIU login-shell PATH. WSL is not installed. Exact Gemini 3.8 availability is unverified. These are current discovery limits, not a claim that the user has no access elsewhere.

Opus review/debug and Grok/Antigravity coding remain requested roles to activate when their usable authenticated location is identified. Astra research is allowed to proceed; it is not recorded as an Opus review. No unavailable CLI/model is assigned an active lane.

This draft does not write or trust .delegate/config.json and does not create an agent instruction file until the setup choice is confirmed.
