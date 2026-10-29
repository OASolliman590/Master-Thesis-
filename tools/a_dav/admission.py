"""Branch eligibility and evidence-backed admission drafts."""
from __future__ import annotations
from typing import Any
from .exposure import patient_exposure_state
from .core import BRANCHES, SchemaStore, dependency, digest, finish, require, stage_boundary
from .worksheet import GATE_QUESTIONS, validate_signed_worksheet

REASON_CODES = frozenset({"ADMISSION_POLICY_UNKNOWN", "REQUIRED_SOURCE_MISSING", "REQUIRED_SOURCE_INCOMPLETE", "BRANCH_CRITERION_FAILED", "BRANCH_EVIDENCE_UNKNOWN", "ACTUAL_REVIEW_NOT_RUN", "ADMISSION_DRAFT_COLLISION", "WORKSHEET_CONTEXT_MISMATCH", "WORKSHEET_UNSIGNED", "WORKSHEET_PARTIAL", "WORKSHEET_CONTRADICTION", "CONTROLLED_REVIEWERS_REQUIRED", "WORKSHEET_STUDY_AMBIGUOUS", "WORKSHEET_INPUT_INVALID"})
DEPENDENCIES = ("registries", "endpoints", "timing", "assays", "overlap", "exposure")
BRANCH_REQUIREMENTS: dict[str, tuple[str, ...]] = {
 "A_BASELINE_BIO": ("baseline", "endpoint"),
 "A_P2_DEVELOPMENT": ("baseline", "endpoint", "assay_compatibility", "class_representation", "development_freeze"),
 "A_P2_OUTER_VALIDATION": ("baseline", "endpoint", "originating_study_holdout", "lineage_no_training"),
 "A_P2_FINAL_TEST": ("baseline", "endpoint", "untouched_policy", "feature_coverage", "prospective_freeze"),
 "A_P1_ENDPOINT_SENSITIVITY": ("category_recovery", "mapping_freeze"),
 "A1_ON_R_NR": ("baseline", "endpoint", "on_window", "no_treatment_change"),
 "A1_POST_R_NR": ("baseline", "post_window", "progression_distinction"),
 "A1_RESPONSE_TIME_INTERACTION": ("repeated_observations", "response_groups", "time_model", "missing_followup_audit"),
 "A1_PROGRESSION": ("baseline", "progression_pair", "progression_timing", "intervening_treatment"),
 "A1_ARM_TIME_INTERACTION": ("comparative_arms", "arm_assignment", "serial_sampling"),
 "PAIRED_MULTIOMICS": ("patient_link", "same_time_specimen", "modality_gates"),
 "PROSTATE_TRANSPORT": ("prostate_eligibility", "transport_assay", "transport_specimen", "claim_ceiling"),
 "A1_PAIRED_CHANGE": ("baseline", "paired_change", "window_policy", "missing_followup_audit"),
 "A1_SYNTHESIS": ("independent_families", "compatible_contrasts", "synthesis_policy"),
 "A1_MODERATOR": ("independent_families", "moderator_policy", "compatible_contrasts"),
 "A_TO_BC": ("development_only_selection", "full_effect_export", "handoff_policy"),
}


POLICY_FIELDS: dict[str, tuple[str, ...]] = {
 "assay_compatibility": ("allowed_units", "allowed_platforms"),
 "class_representation": ("minimum_per_class",),
 "development_freeze": ("role", "locked_order", "feature_selection_order"),
 "originating_study_holdout": ("held_out_study_ids", "training_study_ids"),
 "lineage_no_training": ("analysis_lineage_id",),
 "untouched_policy": ("analysis_lineage_id", "metadata_only_permitted"),
 "feature_coverage": ("required_features",),
 "prospective_freeze": ("locked_order", "evaluation_order"),
 "mapping_freeze": ("mapping_version",),
 "on_window": ("baseline_specimen_uid", "followup_specimen_uid", "window_id"),
 "post_window": ("baseline_specimen_uid", "followup_specimen_uid", "window_id"),
 "no_treatment_change": ("specimen_uids",),
 "progression_distinction": ("followup_specimen_uid", "declared_category"),
 "repeated_observations": ("specimen_uids",),
 "response_groups": ("endpoint_id", "group_definition"),
 "time_model": ("model_id", "variables"),
 "missing_followup_audit": ("candidate_specimen_uids", "dispositions"),
 "progression_pair": ("baseline_specimen_uid", "followup_specimen_uid"),
 "progression_timing": ("followup_specimen_uid", "timing_policy_version"),
 "intervening_treatment": ("episode_ids", "disposition"),
 "comparative_arms": ("arm_ids", "episode_to_arm"),
 "arm_assignment": ("episode_to_arm",),
 "serial_sampling": ("specimen_uids", "sampling_policy_version"),
 "patient_link": ("specimen_uids",),
 "same_time_specimen": ("specimen_uids", "same_time", "same_specimen"),
 "modality_gates": ("modalities", "assay_uids"),
 "transport_assay": ("allowed_units", "allowed_platforms"),
 "transport_specimen": ("allowed_compartments",),
 "claim_ceiling": ("claim",),
 "paired_change": ("baseline_specimen_uid", "followup_specimen_uid", "contrast_id"),
 "window_policy": ("window_id", "timing_policy_version"),
 "independent_families": ("publication_family_ids", "minimum_families"),
 "compatible_contrasts": ("contrast_ids", "effect_scale"),
 "synthesis_policy": ("model_id", "effect_scale"),
 "moderator_policy": ("moderator", "prespecified_version"),
 "development_only_selection": ("development_study_ids", "selection_version"),
 "full_effect_export": ("effect_fields", "export_policy_version"),
 "handoff_policy": ("handoff_version", "claim_ceiling"),
}


def _criterion(name: str, evidence: dict[str, Any], records: dict[str, Any], study: dict[str, Any],
               deps: dict[str, Any], config: dict[str, Any]) -> str:
    """Evidence is structured selectors/versions, never a caller PASS flag."""
    if not isinstance(evidence, dict):
        return "CONTRADICTED"
    patient_ids = {r["patient_uid"] for r in records.get("patient_registry", []) if r["study_id"] == study["study_id"]}
    # Validate supplied references before asking for absent policy assertions.
    refs = evidence.get("record_refs", [])
    if not isinstance(refs, list):
        return "CONTRADICTED"
    for ref in refs:
        if not isinstance(ref, dict):
            return "CONTRADICTED"
        table, key, value = ref.get("table"), ref.get("key"), ref.get("value")
        if not isinstance(table, str) or not isinstance(key, str):
            return "CONTRADICTED"
        matching = [r for r in records.get(table, []) if r.get(key) == value]
        if not matching:
            return "CONTRADICTED"
        for row in matching:
            if "study_id" in row and row["study_id"] != study["study_id"]:
                return "CONTRADICTED"
            if "patient_uid" in row and row["patient_uid"] not in patient_ids:
                return "CONTRADICTED"
            if 'specimen_uid' in row and not any(sp['specimen_uid'] == row['specimen_uid'] and
                    sp['patient_uid'] in patient_ids for sp in records.get('specimen_registry', [])):
                return 'CONTRADICTED' 
    if not evidence.get("policy_version") or not evidence.get("source_locators"):
        return "UNKNOWN"
    if name == "baseline":
        rows = [r for r in records.get("specimen_registry", []) if r["patient_uid"] in patient_ids]
        return "SUPPORTED" if any(r["canonical_timing_category"] == "PRE_INDEX_BASELINE" and r["baseline_candidate_status"] == "YES" and r["biological_compartment"] == "TUMOUR" for r in rows) else "UNKNOWN"
    if name == "endpoint":
        rows = [r for r in records.get("clinical_outcome", []) if r["patient_uid"] in patient_ids]
        endpoint = evidence.get("endpoint_class")
        if endpoint not in {"ORR", "SOURCE_BINARY"}:
            return "CONTRADICTED" if endpoint is not None else "UNKNOWN"
        if endpoint == "SOURCE_BINARY" and not evidence.get("source_binary_definition"):
            return "UNKNOWN"
        views = [r for r in records.get("endpoint", []) if r["patient_uid"] in patient_ids]
        if endpoint == "ORR" and any(r["endpoint_class"] == "ORR" and r["evaluability"] == "EVALUABLE" for r in views):
            return "SUPPORTED"
        return "SUPPORTED" if any(r["endpoint_class"] == endpoint and r.get("evaluability") == "EVALUABLE" and r["mapping_confidence"] == "VERIFIED" for r in rows) else "UNKNOWN"
    if name == "category_recovery":
        rows = [r for r in records.get("clinical_outcome", []) if r["patient_uid"] in patient_ids]
        return "SUPPORTED" if rows and all(r["canonical_category"] in {"CR", "PR", "SD", "PD"} for r in rows) else "UNKNOWN"
    if name == "prostate_eligibility":
        return "SUPPORTED" if "prostat" in study["cancer_type"].lower() else "CONTRADICTED"
    required_fields = POLICY_FIELDS.get(name, ())
    if not required_fields or not all(field in evidence and evidence[field] is not None for field in required_fields):
        return "UNKNOWN"
    if name == "class_representation":
        minimum = evidence["minimum_per_class"]
        if type(minimum) is not int or minimum < 1:
            return "CONTRADICTED"
        rows = [r for r in records.get("clinical_outcome", []) if r["patient_uid"] in patient_ids and r.get("evaluability") == "EVALUABLE"]
        counts = [len({r["patient_uid"] for r in rows if r.get("orr_mapping") is flag}) for flag in (False, True)]
        return "SUPPORTED" if min(counts) >= minimum else "CONTRADICTED"
    if name in {"development_freeze", "prospective_freeze"}:
        end = evidence.get("feature_selection_order" if name == "development_freeze" else "evaluation_order")
        locked = evidence["locked_order"]
        if type(locked) is not int or type(end) is not int or locked >= end:
            return "CONTRADICTED"
        if name == "development_freeze" and evidence["role"] != "DEVELOPMENT":
            return "CONTRADICTED"
    if name in {"assay_compatibility", "transport_assay"}:
        compatible_assays = [r for r in records.get("assay_registry", []) if any(sp["specimen_uid"] == r["specimen_uid"] and sp["patient_uid"] in patient_ids for sp in records.get("specimen_registry", []))]
        if not compatible_assays:
            return "UNKNOWN"
        if any(r["measurement_unit"] not in evidence["allowed_units"] or r["platform"] not in evidence["allowed_platforms"] for r in compatible_assays):
            return "CONTRADICTED"
    if name == "originating_study_holdout":
        if study["study_id"] not in evidence["held_out_study_ids"] or set(evidence["held_out_study_ids"]) & set(evidence["training_study_ids"]):
            return "CONTRADICTED"
    if name == "claim_ceiling" and evidence["claim"] != "MOLECULAR_TRANSPORT_ONLY":
        return "CONTRADICTED"
    if name == "independent_families":
        minimum = evidence["minimum_families"]
        families = evidence["publication_family_ids"]
        if type(minimum) is not int or minimum < 2 or len(set(families)) < minimum:
            return "CONTRADICTED"
    if "specimen_uids" in evidence:
        specimens = {r["specimen_uid"]: r for r in records.get("specimen_registry", []) if r["patient_uid"] in patient_ids}
        if not isinstance(evidence["specimen_uids"], list) or not evidence["specimen_uids"]:
            return "UNKNOWN"
        if any(uid not in specimens for uid in evidence["specimen_uids"]):
            return "CONTRADICTED"
    if "baseline_specimen_uid" in evidence and "followup_specimen_uid" in evidence:
        specimens = {r["specimen_uid"]: r for r in records.get("specimen_registry", []) if r["patient_uid"] in patient_ids}
        baseline, follow = specimens.get(evidence["baseline_specimen_uid"]), specimens.get(evidence["followup_specimen_uid"])
        if baseline is None or follow is None or baseline["patient_uid"] != follow["patient_uid"] or baseline["specimen_uid"] == follow["specimen_uid"]:
            return "CONTRADICTED"
        baseline_times = {a['treatment_episode_id']: a for a in deps['timing']['audit']
                          if a.get('check') == 'TIMING_ASSERTION' and a.get('specimen_uid') == baseline['specimen_uid']}
        follow_times = {a['treatment_episode_id']: a for a in deps['timing']['audit']
                        if a.get('check') == 'TIMING_ASSERTION' and a.get('specimen_uid') == follow['specimen_uid']}
        contexts = set(baseline_times) & set(follow_times)
        requested = evidence.get('treatment_episode_id')
        if requested is not None:
            if requested not in contexts: return 'CONTRADICTED'
            contexts = {requested}
        if not contexts: return 'CONTRADICTED' if baseline_times and follow_times else 'UNKNOWN'
        if len(contexts) != 1: return 'UNKNOWN'
        context = next(iter(contexts))
        before, after = baseline_times[context], follow_times[context]
        if before['canonical_category'] != 'PRE_INDEX_BASELINE': return 'CONTRADICTED'
        categories = {'on_window': {'EARLY_ON_TREATMENT', 'LATE_ON_TREATMENT'},
                      'post_window': {'POST_TREATMENT', 'POST_DISCONTINUATION'}, 'progression_pair': {'PROGRESSION'}}
        if name in categories and after['canonical_category'] not in categories[name]: return 'CONTRADICTED'
        if 'window_id' in evidence and after.get('window_id') != evidence['window_id']: return 'CONTRADICTED'
        if before.get('relative_day') is not None and after.get('relative_day') is not None and before['relative_day'] >= after['relative_day']:
            return 'CONTRADICTED'
    specimens = {r['specimen_uid']: r for r in records.get('specimen_registry', [])
                 if r['patient_uid'] in patient_ids}
    assays = {r['assay_uid']: r for r in records.get('assay_registry', [])
              if r['specimen_uid'] in specimens}
    # Every selector is scoped before the policy can support a relationship.
    if 'assay_uids' in evidence and (not isinstance(evidence['assay_uids'], list) or
            not evidence['assay_uids'] or any(uid not in assays for uid in evidence['assay_uids'])):
        return 'CONTRADICTED'
    checked = {'class_representation', 'development_freeze', 'prospective_freeze',
               'assay_compatibility', 'transport_assay', 'originating_study_holdout', 'claim_ceiling'}
    if name in {'lineage_no_training', 'untouched_policy'}:
        lineage = evidence['analysis_lineage_id']
        if lineage != config.get('exposure', {}).get('analysis_lineage_id'):
            return 'CONTRADICTED'
        states = [patient_exposure_state(records, deps['exposure']['audit'], p, None if name == 'untouched_policy' else lineage)
                  for p in records.get('patient_registry', []) if p['patient_uid'] in patient_ids]
        if 'RESPONSE_ASSOCIATED' in states:
            return 'CONTRADICTED'
        if not states or 'UNKNOWN' in states:
            return 'UNKNOWN'
        if name == 'untouched_policy' and (evidence['metadata_only_permitted'] is not True or
                                           any(state != 'METADATA_ONLY' for state in states)):
            return 'CONTRADICTED'
        checked.add(name)
    if name in {'patient_link', 'same_time_specimen', 'repeated_observations', 'serial_sampling', 'no_treatment_change'}:
        selected = [specimens[uid] for uid in evidence['specimen_uids']]
        if len(selected) < 2 or len({r['patient_uid'] for r in selected}) != 1:
            return 'CONTRADICTED'
        if name == 'patient_link':
            if any(p.get('patient_identity_confidence') != 'VERIFIED' for p in records.get('patient_registry', [])
                   if p['patient_uid'] == selected[0]['patient_uid']):
                return 'UNKNOWN'
            checked.add(name)
        if name == 'same_time_specimen':
            if type(evidence['same_time']) is not bool or type(evidence['same_specimen']) is not bool:
                return 'CONTRADICTED'
            if evidence['same_specimen'] != (len({r['specimen_uid'] for r in selected}) == 1):
                return 'CONTRADICTED'
            specimen_contexts = [[a for a in deps['timing']['audit'] if a.get('check') == 'TIMING_ASSERTION'
                         and a.get('specimen_uid') == r['specimen_uid']] for r in selected]
            common = set.intersection(*[{a['treatment_episode_id'] for a in rows} for rows in specimen_contexts])
            episode = evidence.get('treatment_episode_id')
            if episode is not None:
                if episode not in common: return 'CONTRADICTED'
                common = {episode}
            if len(common) != 1: return 'UNKNOWN'
            episode = next(iter(common))
            timing = [next(a for a in rows if a['treatment_episode_id'] == episode) for rows in specimen_contexts]
            if any(a['precision'] != 'EXACT' or a.get('relative_day') is None for a in timing):
                return 'UNKNOWN'
            same = len({a['relative_day'] for a in timing}) == 1
            if evidence['same_time'] != same: return 'CONTRADICTED'
            if evidence['same_specimen'] and not same: return 'CONTRADICTED'
            checked.add(name)
        if name == 'no_treatment_change' and any(r['canonical_timing_category'] == 'AFTER_REGIMEN_CHANGE' for r in selected):
            return 'CONTRADICTED'
    if name == 'modality_gates':
        selected_assays = [assays[uid] for uid in evidence['assay_uids']]
        if not isinstance(evidence['modalities'], list) or len(set(evidence['modalities'])) < 2:
            return 'CONTRADICTED'
        if set(evidence['modalities']) != {r['modality'] for r in selected_assays}:
            return 'CONTRADICTED'
        modality_families = {'RNA' if r['modality'] in {'RNA', 'RNA_SEQ', 'BULK_RNA',
                             'TRANSCRIPTOMICS', 'MICROARRAY', 'TARGETED_RNA'} else
                             'METHYLATION' if r['modality'] in {'METHYLATION', 'DNA_METHYLATION'} else
                             r['modality'] for r in selected_assays}
        if len(modality_families) < 2: return 'CONTRADICTED'
        relationship = config.get('admission', {}).get('branch_policies', {}).get('PAIRED_MULTIOMICS', {})
        for criterion in ('patient_link', 'same_time_specimen'):
            declared = relationship.get(criterion, {}).get('specimen_uids')
            if declared is None: return 'UNKNOWN'
            if set(declared) != {r['specimen_uid'] for r in selected_assays}: return 'CONTRADICTED'
        for assay in selected_assays:
            coverage = [r for r in deps['assays']['records'].get('coverage', []) if r['assay_uid'] == assay['assay_uid']]
            if assay['qc_status'] == 'FAIL' or any(r['measurement_suitability'] == 'FAIL' for r in coverage):
                return 'CONTRADICTED'
            if assay['qc_status'] != 'PASS' or len(coverage) != 1 or coverage[0]['measurement_suitability'] != 'PASS':
                return 'UNKNOWN'
        checked.add(name)
    if name == 'transport_specimen':
        if any(r['biological_compartment'] not in evidence['allowed_compartments'] for r in specimens.values()):
            return 'CONTRADICTED'
        if not specimens: return 'UNKNOWN'
        checked.add(name)
    if name == 'mapping_freeze':
        versions = {r['mapping_version'] for r in records.get('endpoint', []) if r['patient_uid'] in patient_ids}
        if versions and versions != {evidence['mapping_version']}: return 'CONTRADICTED'
        if not versions: return 'UNKNOWN'
        checked.add(name)
    if name == 'feature_coverage':
        coverage = [r for r in deps['assays']['records'].get('coverage', []) if r['study_id'] == study['study_id']]
        if any(not set(evidence['required_features']) <= set(r['present_genes']) or
               r['final_test_suitability'] == 'FAIL' for r in coverage): return 'CONTRADICTED'
        if not coverage or any(r['final_test_suitability'] != 'PASS' for r in coverage): return 'UNKNOWN'
        checked.add(name)
    if name == 'progression_distinction':
        follow = specimens.get(evidence['followup_specimen_uid'])
        if follow is None or follow['canonical_timing_category'] != evidence['declared_category']:
            return 'CONTRADICTED'
    if name == 'independent_families':
        available = {r['publication_family_id'] for r in records.get('study_registry', [])}
        if not set(evidence['publication_family_ids']) <= available: return 'CONTRADICTED'
        for component in deps['overlap']['audit']:
            families = {n['node_id'] for n in component.get('nodes', []) if n['node_type'] == 'PUBLICATION_FAMILY'}
            if len(families & set(evidence['publication_family_ids'])) > 1: return 'CONTRADICTED'
    episodes = {r['treatment_episode_id']: r for r in records.get('treatment_episode', []) if r['patient_uid'] in patient_ids}
    for field in ('baseline_specimen_uid', 'followup_specimen_uid'):
        if field in evidence and evidence[field] not in specimens: return 'CONTRADICTED'
    for field, available_ids in (('candidate_specimen_uids', set(specimens)), ('episode_ids', set(episodes))):
        if field in evidence and (not isinstance(evidence[field], list) or not set(evidence[field]) <= available_ids):
            return 'CONTRADICTED'
    if 'endpoint_id' in evidence and not any(r['patient_uid'] in patient_ids and
            r['endpoint_id'] == evidence['endpoint_id'] for r in records.get('endpoint', [])):
        return 'CONTRADICTED'
    if 'timing_policy_version' in evidence:
        times = [r for r in deps['timing']['audit'] if r.get('check') == 'TIMING_ASSERTION' and
                 r.get('specimen_uid') in specimens]
        if any(r.get('mapping_version') != evidence['timing_policy_version'] for r in times): return 'CONTRADICTED'
    if 'episode_to_arm' in evidence:
        assignments = evidence['episode_to_arm']
        if not isinstance(assignments, dict) or not set(assignments) <= set(episodes): return 'CONTRADICTED'
        if any(episodes[ep].get('arm_id') is not None and episodes[ep]['arm_id'] != arm for ep, arm in assignments.items()):
            return 'CONTRADICTED'
        if 'arm_ids' in evidence and (len(set(evidence['arm_ids'])) < 2 or set(assignments.values()) != set(evidence['arm_ids'])):
            return 'CONTRADICTED'
    if name == 'development_only_selection':
        if study['study_id'] not in evidence['development_study_ids']: return 'CONTRADICTED'
        if any(r['patient_uid'] in patient_ids and r['permanent_role'] != 'DEVELOPMENT'
               for r in config.get('split', {}).get('assignments', [])): return 'CONTRADICTED'
    # External model/contrast/clinical policies are not certified by an arbitrary
    # existing reference. Their unresolved evidence remains UNKNOWN.
    refs = evidence.get('record_refs')
    if name not in checked or not isinstance(refs, list) or not refs or not evidence.get('rule'):
        return 'UNKNOWN'
    return 'SUPPORTED'



@stage_boundary("admission")
def evaluate_admission(packet: dict[str, Any], *, schemas: SchemaStore | None = None,
                       reviewer_worksheet: dict[str, Any] | None = None,
                       worksheet_context_packet: dict[str, Any] | None = None) -> dict[str, Any]:
    store = schemas or SchemaStore()
    for stage in DEPENDENCIES:
        dependency(packet, stage, store)
    records, config = packet["records"], packet["config"].get("admission", {})
    worksheet = reviewer_worksheet if reviewer_worksheet is not None else config.get("reviewer_worksheet")
    signature: dict[str, Any] | None = None
    if worksheet is not None:
        signature = validate_signed_worksheet(worksheet_context_packet or packet, worksheet)
    require(set(BRANCH_REQUIREMENTS) == set(BRANCHES), "ADMISSION_POLICY_UNKNOWN")
    studies = records.get("study_registry", [])
    require(bool(studies), "BRANCH_EVIDENCE_UNKNOWN", blocked=True)
    sources = {r["source_object_id"]: r for r in records.get("source_record", [])}
    required = config.get("required_source_object_ids", [])
    reasons: set[str] = set()
    source_reasons: dict[str, set[str]] = {}
    for source in sources.values():
        if source.get("validation_status") == "FAIL":
            source_reasons.setdefault(source["study_id"], set()).add("BRANCH_CRITERION_FAILED")
    failed = bool(source_reasons)
    if failed:
        reasons.add("BRANCH_CRITERION_FAILED")
    if not isinstance(required, list) or not required:
        reasons.add("ADMISSION_POLICY_UNKNOWN")
        required = []
    for source_id in required:
        if source_id not in sources:
            reasons.add("REQUIRED_SOURCE_MISSING")
        else:
            source = sources[source_id]
            if source.get("retrieval_status") != "RETRIEVED" or source.get("hash_scope") != "FULL_OBJECT" or not source.get("sha256") or not (source.get("validation_status") == "PASS" or
                    source.get("validation_status") == "STRUCTURAL_ONLY" and
                    any(c.get("source_object_id") == source_id and c.get("measurement_suitability") == "PASS"
                        for c in packet["dependencies"]["assays"]["records"].get("coverage", []))):
                reasons.add("REQUIRED_SOURCE_INCOMPLETE")
                source_reasons.setdefault(source["study_id"], set()).add("REQUIRED_SOURCE_INCOMPLETE")
    branch = packet["branch_id"]
    policy = config.get("branch_policies", {}).get(branch, {})
    audit: list[dict[str, Any]] = []
    drafts: list[dict[str, Any]] = []
    for study in studies:
        scoped = [r for r in sources.values() if r["study_id"] == study["study_id"]]
        study_reasons = set(source_reasons.get(study["study_id"], set()))
        if "ADMISSION_POLICY_UNKNOWN" in reasons:
            study_reasons.add("ADMISSION_POLICY_UNKNOWN")
        study_failed = "BRANCH_CRITERION_FAILED" in study_reasons
        criteria: dict[str, str] = {}
        if branch.startswith("A_P2") or branch == "A_BASELINE_BIO":
            study_class = study.get("study_class")
            criteria["clinical_ici"] = (
                "UNKNOWN" if study_class is None else
                "SUPPORTED" if study_class == "CLINICAL_ICI" else "CONTRADICTED"
            )
        for name in BRANCH_REQUIREMENTS[branch]:
            criteria[name] = _criterion(name, policy.get(name, {}), records, study, packet["dependencies"], packet["config"])
        if "CONTRADICTED" in criteria.values():
            study_failed = True
            study_reasons.add("BRANCH_CRITERION_FAILED")
        if "UNKNOWN" in criteria.values():
            study_reasons.add("BRANCH_EVIDENCE_UNKNOWN")
        if not scoped:
            study_reasons.add("REQUIRED_SOURCE_MISSING")
        worksheet_statuses: dict[str, str] = {}
        if signature is not None:
            worksheet_statuses = signature["decisions"]
            admission_decisions = {item_id: status for item_id, status in worksheet_statuses.items()
                                   if item_id != "V8"}
            if "FAIL" in admission_decisions.values():
                study_failed = True
                study_reasons.add("BRANCH_CRITERION_FAILED")
            if "BLOCKED_UNKNOWN" in admission_decisions.values():
                study_reasons.add("BRANCH_EVIDENCE_UNKNOWN")
            if worksheet_statuses.get("V7") == "NOT_APPLICABLE":
                study_failed = True
                study_reasons.add("BRANCH_CRITERION_FAILED")
            elif packet.get("classification") != "SYNTHETIC_ONLY" and worksheet_statuses.get("V7") != "PASS":
                study_reasons.add("BRANCH_EVIDENCE_UNKNOWN")
            if worksheet_statuses.get("V8") == "PASS":
                matching_matrices = [row for row in records.get("matrix_build_receipt", [])
                                     if row.get("branch_id") == branch]
                if not matching_matrices or any(row.get("test_status") != "PASS" or
                                                 row.get("validation_status") != "PASS"
                                                 for row in matching_matrices):
                    study_failed = True
                    study_reasons.add("BRANCH_CRITERION_FAILED")
            if worksheet_statuses.get("V7") == "PASS" and (
                    "CONTRADICTED" in criteria.values() or
                    study_reasons - {"BRANCH_EVIDENCE_UNKNOWN"} or study_failed):
                study_failed = True
                study_reasons.add("BRANCH_CRITERION_FAILED")
        elif packet.get("classification") != "SYNTHETIC_ONLY" and not study_failed:
            study_reasons.add("ACTUAL_REVIEW_NOT_RUN")
        eligibility = "FAIL" if study_failed else "BLOCKED_UNKNOWN" if study_reasons else "READY"
        failed |= study_failed
        reasons.update(study_reasons)
        audit.append({"kind": "admission_eligibility", "study_id": study["study_id"], "branch_id": branch,
                      "eligibility": eligibility, "criteria": criteria,
                      "reviewer_name": signature["reviewer_name"] if signature else None,
                      "review_date": signature["review_date"] if signature else None})
        if scoped:
            gate_results = []
            for gate in GATE_QUESTIONS:
                decision = worksheet_statuses.get(gate, "BLOCKED_UNKNOWN")
                gate_results.append({"gate": gate, "status": decision,
                                     "reason": "V7_PASS_REQUIRED" if gate == "V7" and decision != "PASS"
                                     else None if decision in {"PASS", "NOT_APPLICABLE", "SUPERSEDED"}
                                     else "MATRIX_BUILD_PENDING" if gate == "V8" and decision == "BLOCKED_UNKNOWN"
                                     else "REVIEW_UNRESOLVED"})
            draft = {"admission_receipt_id": "dav-draft-" + digest([study["study_id"], branch, config,
                                                                     worksheet if signature is not None else None])[:20],
                     "study_id": study["study_id"], "publication_family_id": study["publication_family_id"],
                     "branch_id": branch, "admission_version": str(config.get("admission_version", "dav-draft-v1")),
                     "source_object_ids": sorted(r["source_object_id"] for r in scoped),
                     "source_object_hashes": sorted(r["sha256"] for r in scoped if r.get("sha256")),
                     "gate_results": gate_results,
                     "admission_status": "EXCLUDED" if study_failed else
                     "ADMITTED" if signature is not None and packet.get("classification") != "SYNTHETIC_ONLY"
                     and eligibility == "READY" else "BLOCKED_UNKNOWN",
                     "approved_branches": [branch] if signature is not None
                     and packet.get("classification") != "SYNTHETIC_ONLY" and eligibility == "READY" else [],
                     "blocked_branches": [] if signature is not None
                     and packet.get("classification") != "SYNTHETIC_ONLY" and eligibility == "READY" else [branch],
                     "validator": "SOFTWARE_ONLY", "reviewer": signature["reviewer_name"] if signature else "UNSIGNED",
                     "code_version": "dav-admission-v2", "config_hash": digest(packet["config"]),
                     "created_utc": worksheet.get("created_utc", "UNSIGNED_WORKSHEET") if isinstance(worksheet, dict)
                     else "UNSIGNED_WORKSHEET",
                     "unresolved_limitations": sorted(study_reasons)}
            store.validate("cohort_admission_receipt", draft)
            drafts.append(draft)
        else:
            audit.append({"kind": "admission_draft_unavailable", "study_id": study["study_id"], "reason": "REQUIRED_SOURCE_MISSING"})
    output = dict(records)
    existing = records.get("cohort_admission_receipt", [])
    for draft in drafts:
        prior = [r for r in existing if r.get("admission_receipt_id") == draft["admission_receipt_id"]]
        require(not prior or len(prior) == 1 and prior[0] == draft, "ADMISSION_DRAFT_COLLISION")
    output["cohort_admission_receipt"] = existing + [draft for draft in drafts if not any(r.get("admission_receipt_id") == draft["admission_receipt_id"] for r in existing)]
    return finish("admission", packet, output, status="FAIL" if failed else "BLOCKED_UNKNOWN" if reasons else "READY",
                  reasons=reasons, audit=audit, schemas=store)
