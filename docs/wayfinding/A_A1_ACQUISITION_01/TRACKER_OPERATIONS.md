# Wayfinding operations for this map

Canonical tracker: [A/A.1 acquisition: one source from retrieval to review](https://github.com/OASolliman590/Master-Thesis-/issues/20). The local files mirror the questions and supporting research. Decision detail belongs in each issue's resolution comment; the map indexes closed decisions only.

GitHub native sub-issues express parenthood. Native issue dependencies express blocking. The issue assignee is the claim. Only `wayfinder:` labels are used; these are decisions, not implementation tickets.

## Find the next decision

Read the map once. List its native children, then their states, assignees and `dependencies/blocked_by` records. The frontier consists of open, unassigned children whose blockers are all closed. Preserve child order when selecting the next decision. `FRONTIER.json` is a dated local snapshot; refresh it from GitHub before claiming work.

The native API routes used and checked for this map are:

```text
GET  /repos/OASolliman590/Master-Thesis-/issues/20/sub_issues
GET  /repos/OASolliman590/Master-Thesis-/issues/{issue_number}
GET  /repos/OASolliman590/Master-Thesis-/issues/{issue_number}/dependencies/blocked_by
POST /repos/OASolliman590/Master-Thesis-/issues/20/sub_issues
     body: {"sub_issue_id": <numeric GitHub issue database ID>}
POST /repos/OASolliman590/Master-Thesis-/issues/{issue_number}/dependencies/blocked_by
     body: {"issue_id": <numeric blocker issue database ID>}
```

The relationship bodies require database IDs, not display issue numbers. Existing native links must be inspected before changing them; this map does not replace its links with body-only conventions.

## Claim and resolve

Assign the chosen issue to the authenticated developer before working. Read its actual label and question. A research ticket may resolve through checked primary evidence. A `wayfinder:grilling` ticket requires live user answers; an agent cannot choose the source or approve the handoff on the user's behalf.

Post a resolution comment from an exact saved body file, close that decision issue, and add one named link/gist to the map's Decisions-so-far. Preserve the full resolution in its ticket. Do not close scientific parent issues, grant data admission, or claim that a research recommendation is a user selection.

Research assets remain local and reviewed on the current branch under the standing no-push restriction. Issue updates synchronize the decision map; they do not publish patient-level evidence or source bytes. No archive search, data retrieval or biological analysis is needed merely to refresh this map.
