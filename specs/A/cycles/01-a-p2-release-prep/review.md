# A · 01 · A-P2 release preparation — combined review

On 18 November 2026 the coordinator reused the earlier preparation reviews and requested one fresh, read-only review of the new work from Astra 6.2 at high effort. Terra 6.1 made the corrections. The coordinator verified the changes. Opus was unavailable and did not review this cycle.

## Scientific disposition

A-P2 compares a four-panel ridge score with cytolytic activity (CYT) for discrimination of objective response. The paired difference in area under the receiver operating characteristic curve (AUROC) in the separately released bladder test cohort is the formal primary. The development results would describe transfer between study families. Shared patients can still contribute twice in training and in study averages, and can cross the secondary within-study splits. Differences in regimen, treatment sequence, platform and response assessment also limit interpretation. A-P2 cannot establish prostate treatment benefit or mechanism. Its features are fixed independently of A-BIO discoveries and of later B/C results.

Within development, all 21 pairs are documented: one grouped Liu–Van Allen pair, five conservative sensitivity pairs, and 15 Tier 3 pairs. All seven pairs against the protected final test are represented. Six non-bladder pairs await documented dispositions. The Rose bladder pair specifically requires verified, executed A1 evidence. The separate GSE111636 pair is outside this run. A missing required pair blocks preparation.

Signed option A1 retains the original 408 patients in main and conservative development, with six and four families respectively. The bladder sensitivity and freeze use 375 patients in six families. The exclusion rule cannot establish whether a patient received atezolizumab earlier than the recorded regimen. These counts are historical signed facts. No new clinical estimates or classifications were obtained.

## Findings and corrections

1. **Contain patient-level outputs.** The inherited directory check allowed patient-level artifacts anywhere below the scratch directory. The preparer now restricts outputs to the private runtime subtree, refuses sibling directories and symlink escapes, and requires a fresh output directory for creation.
2. **Enforce the signed representation.** A receipt that agreed with an alternate input could previously produce a real-readiness label. Real eligibility now checks the historical original-table and build-receipt digests, the exact seven cohorts, 408 original patients including 87 bladder patients, 33 exclusions, 375 retained patients and the six/four family counts. A small invented table can pass structural checks while remaining ineligible for a real release. The preparer binds the verified A1 companion for both original-table development packages. Freeze and bladder sensitivity still bind the derived representation.
3. **Bind the user's decision to a particular run.** The old decision-file digest alone could identify a generic note. The proposed decision-content convention compares the already declared release scope with the referenced decision and rejects incomplete, ambiguous or mismatched scope. The real route remains closed pending user consideration of the convention. The consumer also checks registry hashes and statuses, A1 evidence, companion representations and identity membership against the exclusions. The coordinator tested metadata and refusal paths on invented inputs. No live authorization was simulated or given.

Checking companion metadata does not establish that the actual derived bytes were copied from the correct source. That check requires separately authorized evidence. The final-test verifier would also need proof that the exact frozen equation came from the A1-derived input before any final-test release. This development-preparation cycle grants neither permission.

## Worksheet differences held for the user

The earlier proposals' existing-input/rebuild checkboxes, historical full-hash table, development signature/date line and independent overlap accept/amend/signature/date line are retained as historical items. No field removal or signature transfer was accepted. The stale claim that 90 source versus 87 built identities constituted a mismatch was replaced by the signed subset check. The previous derived-only evidence wording was corrected for the two original-table development packages, which retain their patients while binding the verified A1 companion.

The proposed change to decision content is one fenced `a-p2-release-scope-v1` JSON section in the referenced decision. It repeats the existing operation, scope, classification, input role, manifest/input/identity/registry digests, cohort list and outcome fields. A later final test would also bind its equation and existing final-test fields. Decision identity, path and digest are excluded from the projection to avoid circular hashing. The release JSON field list is unchanged. The user has not accepted the convention or any new release worksheet. No real release form was regenerated.

## Verification

The transfer hashes and source base are in TRANSFER.md. The coordinator inspected test data sources before collection and ran the applicable suite with private invented fixtures. DEVIATIONS.md describes the implementer's interrupted selection of a published reference test, its source inspection, and the coordinator's explicit exclusions. No protected final-test data or thesis outcomes entered the checks. Fresh test counts, exclusions and limitations are recorded in tasks.md.
