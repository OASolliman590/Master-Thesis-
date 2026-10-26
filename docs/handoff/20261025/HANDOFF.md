# Handoff: a_dav real-source pipeline redesign, 25 Oct 2026

Paste the "Prompt for the Codex orchestrator" section below into a new Codex session. The rest of this file is supporting context. The two briefs next to this file (`BRIEF_ROUND1_BC.txt` and `BRIEF_ROUND2_ADEF.txt`) are the authoritative task specifications; this file only points to them.

**Current status:** see [the continuation report at the end](#continuation-report). Earlier statements that round 2 and the fetch have not started are historical handoff context.

**Location.** This handoff is now stored durably at `docs/handoff/20261025/` in the active checkout. The earlier temporary-directory warning no longer applies.

---

## Prompt for the Codex orchestrator

You are the **orchestrator** taking over the real-source pipeline redesign of `tools/a_dav` for an MSc thesis (Paper A, an ICI responder study). You run parallel implementer threads, verify their work yourself, and own integration. You do not commit unless the user says so.

### 1. Locations and environment

**Repo.** `work/a-dav-01` beneath the thesis project directory, branch `codex/a-dav-01`. HEAD was `5fd08d4` at handoff. The checkout holds a lot of untracked pre-existing material. Run `git status --short` before you start. Never bulk-stage, delete or overwrite anything that is not in your task.

**Python.** `../envs/dav-pipeline/bin/python`, relative to the repo. It is Python 3.12.14 with pytest 9.1.1, jsonschema 4.26.0 and mypy 1.18.2; `FREEZE.txt` sits beside it. Always set `PYTHONDONTWRITEBYTECODE=1`. Do not install anything without the user's yes.

**Read before you start.** All paths are relative to the repo.
- `docs/adr/0001-data-classification-is-origin.md`, `0002-cohorts-are-field-maps.md`, `0003-one-source-object-retrieval-module.md`
- `docs/decisions/AMENDMENT_V7_PUBLIC_REVIEWER_20261025.md`. The user approved this in chat on 25 Oct.
- The `CONTEXT.md` glossary, section "Data acquisition". Use its terms exactly.
- `docs/research/A_DAV_REAL_INGESTION_SOURCES_01.md`, which has the primary-source facts, the GSE91061 object table and the pin list.
- `docs/wayfinding/A_A1_ACQUISITION_01/APPRAISAL_20261025.md`, the diagnosis of why the work stalled.
- The architecture report `architecture-review-20261025.html`, in this folder. Candidates A to F are described there.

### 2. Current state

**Round 1, B and C, is in progress.** A Codex Luna thread is implementing it: model `gpt-6-luna`, effort high, thread `01a17462-5f79-71f1-b557-749ce695dc6e`, workspace-write sandbox, no network. Its spec is `BRIEF_ROUND1_BC.txt`.
- Tasks run in order: T1 classification policy, T2 object store and GEO SOFT adapter, T3 table and matrix-header adapters with the field-map schema and the Riaz field map, T4 the ingest command, worksheet, summary and an opt-in real tracer.
- Its last progress note said T1 was mid-way: core owns `SYNTHETIC_ONLY`/`PRIVATE_PATIENT_LEVEL` plus a separate `READY` status, and the stages were being switched over.
- **Do not start a second writer on the same files while this thread runs.** Wait for its final report, or resume it with codex `exec resume`/`--session <thread> --sandbox workspace-write`. A resume without `--sandbox workspace-write` runs read-only.
- The accepted modules `search_log.py`, `study_resolution.py` and `queue_reconciliation.py` were byte-unchanged at handoff (sha prefixes 5f1f5c37, b14a0e17, 3d7a29da). `legacy_bridge.py` must stay untouched.

**Round 2, A/D/E/F, is fully decided but not started.** Its spec is `BRIEF_ROUND2_ADEF.txt`:
- A: one retrieval module. Plans are data files, and the old fetchers are deleted after their callers migrate.
- D: admission writes a reviewer worksheet and reads the signed one.
- E: entity tables are validated once, at registries.
- F: tests that read evidence move to an opt-in suite.

**The Riaz fetch is approved and not yet run.** The user said "q2 yes" to these 9 public objects, about 28.5 MB, into the content-addressed store under `.scratch/runtime/` (gitignored):
1. `GSE91061_family.soft.gz` (GEO soft/)
2. author FPKM `GSE91061_BMS038109Sample.hg19KnownGene.fpkm.csv.gz` (GEO suppl/)
3. NCBI `GSE91061_norm_counts_TPM_GRCh38.p13_NCBI.tsv.gz` (GEO rnaseq_counts/)
4. `Human.GRCh38.p13.annot.tsv.gz`
5. github `riazn/bms038_analysis` @ `137111c38a32f8626ee6a436e14ac667bd31b1e7`: `data/SampleTableCorrected.9.19.16.csv`
6. the same commit: `data/bms038_clinical_data.csv`
7. the same commit: `rnaseq/TableS6.A.R`
8. cBioPortal datahub `mel_iatlas_riaz_nivolumab_2017`: `data_clinical_sample.txt`
9. the same study: `data_clinical_patient.txt`

Fetch rules:
- Space requests at least 0.5 s apart.
- Use allowlisted hosts only.
- Write no bytes into Git, only hashes. The author repo has no licence and cBioPortal is ODbL.
- Nothing beyond this list without a new yes from the user.
- Codex implementer sandboxes have no network, so the **orchestrator** runs the fetch itself, preferably with the round-2 retrieval CLI once it exists.

**Pending after both rounds.**
- One Astra review: `gpt-6-astra`, effort low, read-only, fresh session, over the whole diff.
- Then a **debate-review** of the working tree in the original Claude session, or with the debate-review skill if you have it.
- Then the loop diagnosis described in §5.

### 3. Multi-threaded plan

Parallelize only across disjoint file sets.

| Lane | Starts when | Files | Conflicts with |
|---|---|---|---|
| L0 Luna B+C (running) | now | core, workflow, stages, new ingest module, field_maps/, tests/a_dav_ingest | everything below until it lands |
| L1 Retrieval (A) | L0 lands | new retrieval module, fetch_plans/, the deleted fetchers, their tests | none of L2 to L4 if L1 leaves admission/matrices alone |
| L2 Admission worksheet (D) | L0 lands | admission.py, matrices.py eligibility, worksheet CLI, its tests | L3 (shares matrices/admission) |
| L3 Validate-once (E) | L2 lands | matrices, admission, overlap, exposure, timing, workflow, assays, release, core memoize | L2 |
| L4 Evidence suite (F) | L1 lands (L1 deletes tests) | tests/ only (move into tests/evidence/) | L1 |
| L5 Riaz fetch + real tracer run (orchestrator) | L1 CLI exists | .scratch/runtime store only | none |

So L1 and L2 run in parallel; L3 follows L2; L4 follows L1; L5 follows L1.

Run each lane in its own Codex thread, or in its own git worktree when lanes overlap in time. Merge after verification. Split `BRIEF_ROUND2_ADEF.txt` into per-lane briefs: keep its hard rules and gates verbatim, and give each lane only its own section.

### 4. Operating rules

These were the user's decisions, made to stop the earlier multi-week loops.

**Review cap.**
- Each lane gets one implementer pass and is verified by you.
- One Astra review covers the whole diff at the end.
- Only High findings, or findings that touch privacy or data integrity, get one fix round followed by one check.
- Medium and Low findings go to `BACKLOG.md` and do not block.
- No further rounds without the user's explicit decision.

**Ingestion.**
- Ingestion never fetches and never resolves an ambiguity itself. Every conflict becomes a worksheet item, BLOCKED_UNKNOWN, with evidence pointers.
- Cohorts are field maps, not new code. The author clinical table is the source of record for best overall response (BOR). The GEO `response` value is a corroborating label. cBioPortal and iAtlas are cross-checks only.
- Pin both expression representations, author hg19 FPKM and NCBI GRCh38 TPM, and never convert between them. Choosing the analysis representation is a later Paper A methods decision.

**Signing.** Under the approved amendment, the thesis author or the named supervisor signs the V7 reviewer worksheet for public sources.

**Do not add:**
- per-packet receipt or hash-ledger files;
- two-reader procedures;
- archive or provenance hunts;
- synthetic hardening that no real-source run has reproduced.

**Outputs.** Patient-level outputs go only under `.scratch/runtime/<cohort>/`. Git receives code, field maps, object hashes and a patient-free summary.

**Hard limits.**
- Never edit the frozen `specs/`.
- No commit, push, merge or tag unless the user asks.
- No biological analysis or scoring.
- No controlled-access acquisition.
- No AIU or remote jobs.

**Secrets.** Never read, print or copy the SSH private key under `~/.ssh` or the server handover file on the external drive, and never invent a host. Ask the user for anything remote.

**Tracker.** The orchestration tracker is at `<project>/orchestration/` (`thesis_tracker.json`, `events.jsonl`, `render_tracker.py`). It had drifted: nothing after 21 Oct was logged, apart from the A-DAV-05 closure. Log each lane's start and landing there.

### 5. Last task: diagnose the loops

The user asked: "why did Codex convert the spec into infinite validation cycles and a synthetic pipeline? It wasted weeks. Was it my fault or Codex's?"

**Answer from evidence.** Sources:
- `orchestration/events.jsonl`
- the docs/validation receipts. A-DAV-02 needed 5 revisions over a Bearer heuristic. A-DAV-04 had 8 code rounds, A-DAV-05 had 5, A-DAV-07 had 8 Astra rounds.
- the A_DAV_IMPLEMENTATION_01 ruling that synthetic acceptance counts while the real tracers are NOT_RUN
- the Prat packets (11 packets, 117 files, 0 lines of real-data code)
- the appraisal file

**Attribute fairly across three parties.**
- **The frozen spec.** It mandates strict fail-closed rules and tracers, but not loops, two readers or byte continuity.
- **The agents.** Codex added procedures, kept synthetic-only gates, and treated every finding as blocking. The Claude coordinator ran revision after revision and made "run revision N" the default button each time.
- **The user's instructions.** For example, packet-by-packet authorization, and asking for full reviews of each revision.

Cite the evidence for every claim. Do not assign blame where there is no receipt behind it.

### 6. Definition of done

Run `python -m tools.a_dav.ingest --cohort riaz_gse91061 --branch A_BASELINE_BIO` on the real store. It should produce:
- the private records;
- a reviewer worksheet listing only the real judgment items. Known ones: the `Pt7_Pre`→`Pt72` label, the duplicate `Pt109_On`, NE vs UNK, Pt3, the four exclusions in TableS6.A.R, and 109 vs 107 samples;
- a patient-free SUMMARY.

The opt-in tracer passes: 109 samples, 51 Pre, 58 On, 65 patients. All gates are green:
- `tests/a_dav_implementation`
- `tests/a_dav_ingest`
- `tests/a_dav`
- `tests/a_identity_adapter`
- the contracts suite (`tests/a_a1_spec_contract`)
- `docs/integration/20261015/verify_integration.py --git-ref HEAD`
- mypy strict on the new modules
- `git status --short -- specs docs/integration` empty

The user then signs the worksheet.

---

## Suggested skills

Use these where your harness supports them; otherwise read their SKILL.md files under `~/.claude/skills/` or `~/.agents/skills/`.

- **codex-delegate**, plus **codex-background** if Codex is the orchestrator: dispatch the lane implementers, then verify and land their work.
- **tdd**: every lane is test-first.
- **codebase-design**: keep using its vocabulary (module, interface, depth, seam, adapter) and the deletion test.
- **domain-modeling**: update the `CONTEXT.md` glossary and `docs/adr/` when a term or a hard-to-reverse decision appears.
- **code-review**, then **debate-review**: the single end-of-work review.
- **research**: only for a bounded, named source question; reuse `docs/research/A_DAV_REAL_INGESTION_SOURCES_01.md` first.
- **wait-what**: before expanding the process, explain the next action plainly to the user.

---

## Update, 25 Oct, after the handoff was written: round 1 (B+C) has LANDED

The Luna thread finished, and the coordinator re-ran the gates independently.

| Gate | Result |
| --- | --- |
| `tests/a_dav_implementation` + `tests/a_dav_ingest` | 282 passed, 1 skipped (the opt-in real tracer, no store yet) |
| `tests/a_dav` + `tests/a_identity_adapter` | 1346 passed, 40 failed |
| `specs` / `docs/integration` status | empty |

**About the 40 failures.** All of them are `test_legacy_bridge.py`, and they fail the same way at the pre-change baseline. The cause is the environment: `batchqual` from the sibling worktree cannot be imported in the new venv. The B+C changes did not cause them. Log this in BACKLOG; do not fix it inside the round-2 lanes.

**New modules:**
- `source_objects.py`
- `geo_soft.py`
- `delimited.py`
- `matrix_header.py`
- `field_maps.py`, with `field_maps/field_map.schema.json` and `field_maps/riaz_gse91061.json`
- `ingest.py`
- `INGESTION.md`
- tests in `tests/a_dav_ingest/`

**State of the Riaz inputs.** The Riaz field-map hashes are still null. The next step is the approved 9-object fetch, which round 2 now covers. So lane L0 in §3 is complete, and L1 (retrieval) and L2 (admission worksheet) can start in parallel. Luna's own report is in thread `01a17462-5f79-71f1-b557-749ce695dc6e`.


## Continuation report

25 October 2026. Luna implementers completed retrieval, reviewer worksheets, validation-once and the evidence-suite split. The orchestrator connected the landed B+C ingestion to canonical stage inputs, performed the authorized public retrieval, and independently ran the gates. The one Astra review found one High admission defect and two provenance defects. All three received one bounded fix round. Astra confirmed all three corrections and independently passed 7 targeted checks. Final verification is complete with the explicit limitations below.

### Changes and design

| Lane | Files and behavior | Verification available from the lane |
| --- | --- | --- |
| A: retrieval | Added `tools/a_dav/retrieval.py`, `fetch_plans/riaz_gse91061.json`, and `tests/a_dav/test_retrieval_round2.py`. Updated `source_objects.py` and the Riaz field map/schema. One HTTP interface now owns redirects, host policy, all-attempt spacing/counting, retries, range checks, bounds, complete hashes and atomic publication. Pure record construction remains in `object_verification.py`. | 12 focused tests passed. The parent also ran the approved nine-object retrieval and independently checked full hashes and lengths. Original RED counts were not retained, so no complete test-first audit is claimed. |
| D: reviewer worksheet | Added `worksheet.py` and `test_reviewer_worksheet.py`; changed `admission.py`, `matrices.py` and admission tests. One worksheet binds the source objects, entity records, branch, policies and questions. Public routes use the approved single named reviewer; unsigned or partial review stays blocked. V8 requires actual matrix validation. | 90 focused checks passed in the implementation pass. Astra reproduced the V7 supersession bypass; the final regression now requires explicit V7 PASS for real admission. |
| E: validate once | Changed `core.py`, registries and downstream stage modules. Registries owns entity schema validation. Receipt, configuration, entity and dependency integrity checks remain. Module hashes are memoized only within one workflow invocation. Added `test_validate_once.py`. | 236 focused checks and 2 dedicated checks passed. Subsequent runs recompute hashes. The fix round also binds `worksheet.py` in admission/workflow/freeze. |
| F: evidence suite | Added `tests/evidence/conftest.py` and seven evidence modules; moved 25 tests from their original default modules. Default metadata/raw-question tests use invented fixtures. Set `DAV_EVIDENCE=1` to run historical inventory and implementation-inspection tests. | Focused default run: 10 passed, 25 skipped. Historical receipt comparison is explicitly reported below. Original RED counts were not retained. |

The real ingestion integration now emits schema-shaped canonical records, carries source pointers, and passes successful dependencies to the next stage. The actual author sample table places its patient field at column 4; the field map was corrected using the retained header and an invented 14-column regression fixture. Clean baseline joins use the author sample and clinical tables. Generic on-treatment labels keep timing unresolved. The author clinical BOR remains the source of record; corroborating labels and missing values are preserved. The analysis script is inspected as text, never executed. Both expression measurement representations are retained separately.

Astra corrections: V7 SUPERSEDED cannot grant admission; ingestion worksheet configuration is established before stage receipts; worksheet-validator code participates in admission and workflow/freeze bindings. Luna reproduced all three failures before correcting them, then passed 81 adjacent checks and the final 3 regression checks. The two Medium findings were included because they concern dependency and admission provenance integrity. This is the agreed one fix round, not a new review cycle.

### Removed interfaces and test rationale

Removed modules: `private_retrieval.py`, `filelist_fetch.py`, `listing_fetch.py`, `filelist_plan.py`, `listing_plan.py`, and `lane_crosswalk.py`. The network part of `object_verification.py` was removed. Their replacement is the one retrieval interface and data fetch plan; preserved historical receipts were not rewritten.

Removed old test modules under `tests/a_dav/`: `test_private_retrieval.py`, `test_filelist_fetch.py`, `test_listing_fetch.py`, `test_filelist_plan.py`, `test_listing_plan.py`, `test_lane_crosswalk.py`, and `test_object_verification.py`. These exercised the removed retrieval/planning interfaces. Replacement retrieval tests check the new interface, including redirects, retries/spacing, resume ranges, full hashes and publication. The retained source-record interface is also exercised by `test_existing_seams.py`; this is a migration of coverage, not a claim of one-for-one equivalence with every old assertion.

Two old `atomic_retrieve` tests were removed from `test_existing_seams.py`: `test_injected_object_transport_resumes_and_publishes_immutable_bytes` and `test_bad_source_checksum_never_publishes_destination`. Their behaviors are covered through the new retrieval API. F moved, rather than deleted, 25 evidence tests: queue reconciliation 10, study resolution 8, workflow 2, metadata queue 2, identity adapter 1, search log 1, raw question 1. Unrelated Paper B test files were restored unchanged.

### Real source run

The authorized fetch completed: **9 source objects, 9 HTTP 200 requests, 28,667,384 bytes**. All nine complete SHA-256 values, source versions and sizes are now pinned in the field map and fetch plan. No additional object was requested. Source bytes and patient-level output stay under `.scratch/runtime/riaz_gse91061/`, which is ignored by Git.

The source set consists of GEO SOFT; author sample and clinical tables; the author analysis script at a pinned commit; author hg19 FPKM; NCBI GRCh38 TPM and annotation; and the two cBioPortal harmonized cross-check tables. The last two remain cross-checks. No representation was converted or selected for biological analysis.

Local review outputs are `ingestion/records/ingestion_packet.json`, `ingestion/worksheet.json` and the patient-free `ingestion/SUMMARY.md`, beneath that runtime directory. The observed source counts are 109 samples, 51 baseline, 58 on-treatment and 65 patient labels; 51 baseline samples link to patient records. These are metadata linkage counts, not an admitted analysis population.

There are 9 observed source questions plus 9 gate questions: 18 worksheet items. Source categories are three outcome-label disagreements, two missing author-sample matches, one duplicate patient/visit, one unresolved author-exclusion policy, one harmonized sample-count mismatch, and one unresolved on-treatment window. Individual labels and evidence pointers stay in the private worksheet.

### Worksheet format and remaining human work

The generated JSON includes `schema_version`, `worksheet_id`, `created_utc`, `context`, `context_hash`, and `items`. Keep these fields unchanged. A completed review adds a `signature` and one decision for every item. This fragment uses invented text and is not a complete or signed production worksheet:

```json
{
  "signature": {"reviewer_name": "Example Reviewer", "review_date": "2026-10-25"},
  "decisions": [
    {"item_id": "I-example", "status": "BLOCKED_UNKNOWN", "rationale": "Source meaning still needs review."},
    {"item_id": "V7", "status": "BLOCKED_UNKNOWN", "rationale": "Admission has not been approved."}
  ]
}
```

The signature is a declared name and date, not authenticated identity. For these public sources, the author or named supervisor may sign under the approved amendment. Controlled access retains the existing separate requirements.

The next work is one source review: resolve or explicitly retain the nine source questions, document endpoint/treatment/exclusion policies, and encode accepted decisions in the packet. Rebuild affected dependencies and regenerate a matching worksheet after any source, record or policy change. Then the human records the final V7 decision and signs. The signature alone cannot supply missing endpoint evidence or stage dependencies. Matrix construction and its V8 validation follow admission; biological analysis remains outside this task.

### Verification and limits

| Gate | Round-1 baseline | Final result |
| --- | --- | --- |
| Implementation + ingestion | 282 passed, 1 skipped | **294 passed, 1 skipped**; the default skip is the opt-in real tracer |
| Real Riaz tracer | Not run: store unavailable | **1 passed** against the retained nine objects |
| DAV + identity adapter | 1346 passed, 40 failed | **1175 passed, 40 failed**; the same legacy `batchqual` import limitation |
| Opt-in evidence | Not separated | **24 passed, 1 failed**; historical byte-size/hash inventory mismatch |
| Frozen A/A.1 contracts | Baseline not rerun here | **38 passed** |
| Integration verifier at HEAD | Baseline not rerun here | **PASS**: 696 manifest hashes, 697 Git objects, 94 schemas, 16 D examples, 38 entry links |
| Strict mypy | Lane-level checks | **23 source modules passed** |
| Protected files and whitespace | Round-1 spec/integration status empty | Spec/integration status empty; no tracked validation-record diff; `git diff --check` clean |

The implementation count changes because obsolete retrieval tests were removed, evidence tests moved, and behavior regressions added. The final combined run took 216.08 seconds. The final real registry dependency was independently loaded from the emitted packet and verified READY. The real run stops at endpoints with BLOCKED_UNKNOWN because the needed policy/evidence is not yet supplied; the reviewer worksheet is UNSIGNED. This is the expected review boundary, not cohort admission.

Mypy used `--strict --follow-imports=silent --ignore-missing-imports --explicit-package-bases` with all 23 relevant modules supplied explicitly, including `field_maps.py`; no `attr-defined` suppression was needed in the parent check. Missing third-party typing is not checked by those options. The contracts suite emitted existing unclosed-file ResourceWarnings but passed.

A prior evidence run also failed one workflow-freeze test. It passed in isolation (2 workflow tests) and in the final evidence suite; no separate runtime correction was made for that transient result. The only final evidence failure is the preserved historical inventory comparison.

Reproduction commands, from this checkout, with `PYTHONDONTWRITEBYTECODE=1` and `PY=../envs/dav-pipeline/bin/python`:

```sh
$PY -m pytest -q -p no:cacheprovider tests/a_dav_implementation tests/a_dav_ingest
$PY -m pytest -q -p no:cacheprovider tests/a_dav tests/a_identity_adapter
DAV_EVIDENCE=1 $PY -m pytest -q -p no:cacheprovider tests/evidence
$PY -m unittest discover tests/a_a1_spec_contract
$PY docs/integration/20261015/verify_integration.py --git-ref HEAD
$PY -m tools.a_dav.ingest --cohort riaz_gse91061 --branch A_BASELINE_BIO --store .scratch/runtime/riaz_gse91061/store --out .scratch/runtime/riaz_gse91061/ingestion
DAV_REAL_STORE=.scratch/runtime/riaz_gse91061/store $PY -m pytest -q -p no:cacheprovider tests/a_dav_ingest/test_real_riaz_tracer.py --basetemp .scratch/runtime/riaz_gse91061/tracer-check-new
```

Keep real-tracer temporary output within `.scratch/runtime/`; select a fresh basetemp for each deliberate rerun. Do not repeat retrieval: all authorized source objects are retained and pinned.

The separate environment and tooling issues are in [BACKLOG.md](../../../BACKLOG.md): 40 legacy `batchqual` import failures; the historical inventory comparison against a changed test file; and the debate-review launcher failure before either reviewer started. Debate review has not occurred. These do not justify claiming every prescribed gate is green.

No commit, push, merge, tag, installation, remote/AIU job or biological analysis was performed. Implementer lanes made no network requests; the orchestrator performed the authorized public fetch. Frozen specifications, integration files and historical validation records were preserved. Existing untracked historical material remains untouched.

The requested explanation of the earlier loops is in [LOOP_DIAGNOSIS.md](LOOP_DIAGNOSIS.md), with source links and a distinction between recorded facts and interpretation.


## Public-source review continuation, 26 October 2026

The nine Riaz questions have been reviewed by two Luna workers and accepted in one bounded Astra review. See [decisions before signing](../../research/A_DAV_RIAZ_DECISIONS_20261026.md), with links to the two primary-source evidence notes. The recommended baseline-only scope leaves on-treatment identity/replicate questions open for A.1. Three NE/UNK flags retain unevaluable source labels. The four script removals and separate paper PCA exclusion remain distinct; no final analytical population was chosen.

A Luna implementation chat added `review_prepare.py` and its synthetic tests, was reviewed, and was archived (`01a174e8-e111-75f3-9f7c-05ea872f360c`). A second Luna pass corrected a reproduced ingestion reporting defect: a conflicting same-code candidate is now surfaced without making an identity join. The 26 October real metadata run still has 51 baseline joins and nine source questions. Parent checks: 29 focused tests passed / 1 default real-tracer skip; real tracer 1 passed; strict typing 3 modules passed. Prior full-suite environment/historical limitations were not rerun or represented as fixed.

The new private run folders are `ingestion-review-20261026` and `review-prepared-20261026` under the existing Riaz runtime root. Original unsigned artifacts are preserved. The prepared worksheet is unsigned; registries are READY while endpoint, timing, assay, overlap and exposure policies remain blocked. Human decisions and remaining gate configuration are listed in the decisions note. Frozen specs/integration and historical validation documents are unchanged; no biology, commit or remote job.


## 26 October: approved baseline scope and author BOR implemented

The user approved baseline-only `A_BASELINE_BIO` and author BOR, and requested QC proposals separately. Luna implemented `tools/a_dav/baseline_policy.py`, its CLI and invented-fixture tests. The parent ran it on retained public metadata into `.scratch/runtime/riaz_gse91061/baseline-bor-20261026/`: 51 patients, 51 Pre specimens, 102 assay records, all nine source objects, and all nine source questions. Two NE records remain unevaluable with null ORR. The 49 other source categories are an upper bound before later gates, not an analytical denominator. Original inputs are unchanged and the new worksheet is unsigned.

Registries pass. Endpoint mapping policy is configured; materialization remains blocked by `ENDPOINT_EPISODE_UNKNOWN` because no legitimate reviewed treatment-response binding exists. Timing, assay policy, overlap and prior-use review remain unresolved. No binding, reviewer, signature, admission, QC exclusion or measurement choice was invented. No expression values were inspected and no biological analysis ran.

Astra found one substantive-conflict preservation issue in the NE/UNK crosswalk; Luna fixed it, and Astra confirmed closure in the single bounded follow-up. Parent checks: initial combined suite 36 passed / 1 opt-in tracer skipped; post-fix policy suite 8 passed; strict mypy four modules passed; final metadata run and unsigned context checks passed; all 1,343 frozen/historical file hashes unchanged; diff check clean. Work remains uncommitted.

Next policy choices are approval of the [QC rules](../../research/A_DAV_RIAZ_QC_PROPOSAL_20261026.md) and selection between already retained author hg19 FPKM and official NCBI GRCh38 TPM. Both full objects are downloaded and hash-pinned; numerical validation is NOT_RUN, and NCBI processing details still need support. Then implement/run approved technical checks, complete source-supported treatment/timing and overlap/prior-use review, regenerate the worksheet and obtain the actual human signature. Do not reopen baseline/BOR approval or restart custody/two-reader searches for these public objects. See the [accepted decision and full results](../../decisions/RIAZ_BASELINE_BOR_20261026.md).
