"""In-memory, synthetic-only bridge from legacy metadata into DAV proposals.

This module checks reconstruction and structure. It never admits sources or
releases analysis, and deliberately has no matrix or file-writing interface.
"""
from __future__ import annotations

import hashlib
import json
import copy
import math
import sys
from pathlib import Path
from typing import Any, Literal, TypedDict

MetadataScalar = str | int | float | bool | None


class LegacyMetadata(TypedDict):
    classification: Literal["SYNTHETIC_ONLY"]
    tables: dict[str, list[dict[str, MetadataScalar]]]
    producer_hashes: dict[str, str]
    auditor_hashes: dict[str, str]
    source_code_hashes: dict[str, str]


class LegacyLink(TypedDict):
    legacy_table: str
    legacy_key: str
    canonical_table: str
    canonical_key: str
    evidence_refs: list[str]


class CanonicalSupplement(TypedDict):
    classification: Literal["SYNTHETIC_ONLY"]
    legacy_metadata_sha256: str
    records: dict[str, list[dict[str, Any]]]
    links: list[LegacyLink]
    unresolved: list[str]
    schema_hashes: dict[str, str]


class LineageRow(TypedDict):
    legacy_table: str
    legacy_key: str
    canonical_table: str | None
    canonical_key: str | None
    raw_fields: dict[str, MetadataScalar]
    evidence_refs: list[str]


class MigrationResult(TypedDict):
    status: Literal["STRUCTURAL_CANDIDATE", "BLOCKED_UNKNOWN", "FAIL"]
    records: dict[str, list[dict[str, Any]]]
    lineage: list[LineageRow]
    dispositions: list[dict[str, Any]]
    reason_counts: dict[str, int]
    bindings: dict[str, str]
    analysis_ready: bool
    source_admission: bool
    statistical_release: bool
    biological_analysis_executed: bool


_CODES = {"contract.py", "schema.py", "builder.py", "auditor.py"}
_TABLES = ("study_registry", "publication_family", "source_record", "patient_registry",
           "specimen_registry", "assay_registry", "treatment_episode", "treatment_exposure",
           "clinical_outcome", "episode_binding")
_FALSE = dict(analysis_ready=False, source_admission=False, statistical_release=False,
              biological_analysis_executed=False)


def _canon(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _bad(code: str) -> MigrationResult:
    return MigrationResult(status="FAIL", records={t: [] for t in _TABLES}, lineage=[],
                           dispositions=[], reason_counts={code: 1}, bindings={}, **_FALSE)


def _metadata_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, bool)) or (
        isinstance(value, float) and math.isfinite(value))


def _legacy_modules() -> tuple[Any, Any]:
    root = Path(__file__).resolve().parents[2].parent / "paper-a-batch-pipeline"
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from batchqual.patient import schema as schema
    from batchqual.patient import contract as contract
    return schema, contract


def _key(table: str, row: dict[str, Any], schema: Any) -> str:
    pk = schema.PRIMARY.get(table)
    if pk:
        value = row.get(pk)
        return value if isinstance(value, str) else ""
    return schema.digest([table, [row.get(c) for c in schema.COLUMNS[table]]])


def build_legacy_candidate(legacy_metadata: LegacyMetadata, supplement: CanonicalSupplement,
                           *, schema_root: Path) -> MigrationResult:
    try:
        if not isinstance(legacy_metadata, dict) or not isinstance(supplement, dict):
            return _bad("MALFORMED_INPUT")
        if legacy_metadata.get("classification") != "SYNTHETIC_ONLY" or supplement.get("classification") != "SYNTHETIC_ONLY":
            return _bad("SYNTHETIC_ONLY_REQUIRED")
        S, contract = _legacy_modules()
        allowed = set(S.COLUMNS) - {"assay_value", "feature", "gate_status"}
        tables = legacy_metadata["tables"]
        if set(tables) != allowed:
            return _bad("UNSUPPORTED_INPUT_TABLE")
        for table, rows in tables.items():
            if not isinstance(rows, list) or any(not isinstance(row, dict) or set(row) != set(S.COLUMNS[table]) or any(not _metadata_scalar(v) for v in row.values()) for row in rows):
                return _bad("MALFORMED_INPUT")
        for t,pk in S.PRIMARY.items():
            if t in allowed and len([r.get(pk) for r in tables[t]])!=len(set(r.get(pk) for r in tables[t])):
                return _bad("MALFORMED_INPUT")
        hashes = {}
        for t in allowed:
            raw = S.canonical_table(tables, t)
            value = _sha(raw)
            if legacy_metadata["producer_hashes"].get(t) != value or legacy_metadata["auditor_hashes"].get(t) != value:
                return _bad("METADATA_HASH_MISMATCH" if legacy_metadata["producer_hashes"].get(t) != legacy_metadata["auditor_hashes"].get(t) else "LEGACY_AUDIT_MISMATCH")
            hashes["legacy:" + t] = value
        legacy_root = Path(S.__file__).resolve().parent
        for name in _CODES:
            p = legacy_root / name
            actual = _sha(p.read_bytes())
            if legacy_metadata["source_code_hashes"].get(name) != actual:
                return _bad("CODE_BINDING_MISMATCH")
            hashes["code:" + name] = actual
        expected_metadata=S.digest({"classification":"SYNTHETIC_ONLY",
            "table_hashes":{t:hashes["legacy:"+t] for t in sorted(allowed)},
            "source_code_hashes":{n:hashes["code:"+n] for n in sorted(_CODES)}})
        if supplement.get("legacy_metadata_sha256") != expected_metadata:
            return _bad("METADATA_HASH_MISMATCH")
        hashes["bridge_module"] = _sha(Path(__file__).read_bytes())
        if set(supplement["records"]) != set(_TABLES) or any(not isinstance(supplement["records"][t], list) for t in _TABLES):
            return _bad("MALFORMED_INPUT")
        input_records=copy.deepcopy(supplement["records"])
        records=copy.deepcopy(input_records)
        unresolved=supplement["unresolved"]
        if not isinstance(unresolved,list) or any(x not in {"E%02d"%i for i in range(1,11)} for x in unresolved):
            return _bad("MALFORMED_INPUT")
        for t in _TABLES:
            p = Path(schema_root) / (t + ".schema.json")
            raw = p.read_bytes()
            actual = _sha(raw)
            if supplement["schema_hashes"].get(t) != actual:
                return _bad("SCHEMA_BINDING_MISMATCH")
            hashes["schema:" + t] = actual
        import jsonschema
        missing_canonical=False
        missing_canonical_keys={t:set() for t in _TABLES}
        missing_unkeyed={t:0 for t in _TABLES}
        missing_episode_binding_refs=[]
        for t in _TABLES:
            schema_doc = json.loads((Path(schema_root) / (t + ".schema.json")).read_bytes())
            valid=[]
            for rec in records[t]:
                if t=="patient_registry" and rec.get("inclusion_state")=="INCLUDED": return _bad("ADMISSION_STATE_NOT_ALLOWED")
                errors=list(jsonschema.Draft202012Validator(schema_doc).iter_errors(rec))
                if not errors:
                    valid.append(rec)
                    continue
                def derived_from_missing_discriminator(exc):
                    path=list(exc.schema_path)
                    if len(path)<3 or path[0]!="allOf" or not isinstance(path[1],int) or path[2]!="then":
                        return False
                    clauses=schema_doc.get("allOf",[])
                    if path[1]>=len(clauses): return False
                    condition=clauses[path[1]].get("if",{}).get("properties",{})
                    return any(field not in rec for field in condition)
                if any(exc.validator!="required" and not derived_from_missing_discriminator(exc) for exc in errors):
                    return _bad("CANONICAL_SCHEMA_INVALID")
                missing_canonical=True
                key=_canonical_key(t,rec)
                if key: missing_canonical_keys[t].add(key)
                else: missing_unkeyed[t]+=1
                if t=="episode_binding":
                    missing_episode_binding_refs.append(tuple(rec.get(k) if isinstance(rec.get(k),str) and rec.get(k) else None for k in ("patient_uid","treatment_episode_id","subject_type","subject_id")))
            records[t]=valid
        keys: dict[str, dict[str, dict[str, Any]]] = {}
        for t in _TABLES:
            keys[t] = {}
            for rec in records[t]:
                k = _canonical_key(t, rec)
                if not k or k in keys[t]:
                    return _bad("CANONICAL_SCHEMA_INVALID")
                keys[t][k] = rec
        idsets={t:set(rows) for t,rows in keys.items()}
        fams={(r["publication_family_id"],r["study_id"]) for r in records["publication_family"]}
        missing_canonical_link_aliases={t:set() for t in _TABLES}
        raw_links=supplement.get("links")
        if isinstance(raw_links,list):
            for t in _TABLES:
                unresolved=[x.get("canonical_key") for x in raw_links if isinstance(x,dict) and x.get("canonical_table")==t and isinstance(x.get("canonical_key"),str) and x.get("canonical_key") not in keys[t]]
                if missing_unkeyed[t]==1 and len(unresolved)==1:
                    missing_canonical_link_aliases[t].add(unresolved[0])
        def missing_ref(table,key):
            return (bool(key) and (key in missing_canonical_keys[table] or key in missing_canonical_link_aliases[table])) or (not key and missing_unkeyed[table]==1)
        def missing_family(family_id,study_id):
            return any(f.get("publication_family_id")==family_id and f.get("study_id")==study_id and missing_ref("publication_family",_canonical_key("publication_family",f)) for f in input_records["publication_family"])
        if any((r.get("publication_family_id"),r.get("study_id")) not in fams and not missing_family(r.get("publication_family_id"),r.get("study_id")) for r in records["study_registry"]): return _bad("FOREIGN_KEY_UNRESOLVED")
        if any((r.get("study_id") not in idsets["study_registry"] and not missing_ref("study_registry",r.get("study_id"))) or ((r.get("publication_family_id"),r.get("study_id")) not in fams and not missing_family(r.get("publication_family_id"),r.get("study_id"))) for r in records["source_record"]): return _bad("FOREIGN_KEY_UNRESOLVED")
        if any(r.get("study_id") not in idsets["study_registry"] and not missing_ref("study_registry",r.get("study_id")) for r in records["patient_registry"]): return _bad("FOREIGN_KEY_UNRESOLVED")
        if any(r.get("patient_uid") not in idsets["patient_registry"] and not missing_ref("patient_registry",r.get("patient_uid")) for r in records["specimen_registry"]): return _bad("FOREIGN_KEY_UNRESOLVED")
        if any((r.get("specimen_uid") not in idsets["specimen_registry"] and not missing_ref("specimen_registry",r.get("specimen_uid"))) or (r.get("source_object_id") not in idsets["source_record"] and not missing_ref("source_record",r.get("source_object_id"))) for r in records["assay_registry"]): return _bad("FOREIGN_KEY_UNRESOLVED")
        if any((r.get("patient_uid") not in idsets["patient_registry"] and not missing_ref("patient_registry",r.get("patient_uid"))) or (r.get("study_id") not in idsets["study_registry"] and not missing_ref("study_registry",r.get("study_id"))) for r in records["treatment_episode"]): return _bad("FOREIGN_KEY_UNRESOLVED")
        if any(r.get("patient_uid") not in idsets["patient_registry"] and not missing_ref("patient_registry",r.get("patient_uid")) for t in ("treatment_exposure","clinical_outcome") for r in records[t]): return _bad("FOREIGN_KEY_UNRESOLVED")
        for r in records["episode_binding"]:
            ep=next((x for x in records["treatment_episode"] if x["treatment_episode_id"]==r.get("treatment_episode_id")),None)
            if ep is None:
                if missing_ref("treatment_episode",r.get("treatment_episode_id")): continue
                return _bad("FOREIGN_KEY_UNRESOLVED")
            if r.get("patient_uid")!=ep.get("patient_uid"): return _bad("EPISODE_PATIENT_MISMATCH")
            subtab={"SPECIMEN":"specimen_registry","TREATMENT_EXPOSURE":"treatment_exposure","CLINICAL_OUTCOME":"clinical_outcome"}.get(r.get("subject_type"))
            if subtab is None: return _bad("FOREIGN_KEY_UNRESOLVED")
            subject=next((x for x in records[subtab] if _canonical_key(subtab,x)==r.get("subject_id")),None)
            if subject is None:
                if missing_ref(subtab,r.get("subject_id")): continue
                return _bad("FOREIGN_KEY_UNRESOLVED")
            if subject.get("patient_uid")!=r.get("patient_uid"): return _bad("EPISODE_PATIENT_MISMATCH")
        exposure_by_id={r["treatment_exposure_id"]:r for r in records["treatment_exposure"]}
        bound_exposure_ids={b.get("subject_id") for b in records["episode_binding"] if b.get("subject_type")=="TREATMENT_EXPOSURE"}
        def missing_binding_match(expected):
            compatible=[ref for ref in missing_episode_binding_refs if sum(value is not None for value in ref)>=3 and all(value is None or value==expected[i] for i,value in enumerate(ref))]
            return len(compatible)==1
        for exposure_id,exposure in exposure_by_id.items():
            if exposure_id not in bound_exposure_ids and not any(missing_binding_match((ep.get("patient_uid"),ep.get("treatment_episode_id"),"TREATMENT_EXPOSURE",exposure_id)) for ep in records["treatment_episode"] if exposure_id in ep.get("component_exposure_ids",[])):
                return _bad("FOREIGN_KEY_UNRESOLVED")
        for ep in records["treatment_episode"]:
            for exposure_id in ep.get("component_exposure_ids",[]):
                exposure=exposure_by_id.get(exposure_id)
                bound=any(b.get("subject_type")=="TREATMENT_EXPOSURE" and b.get("subject_id")==exposure_id and b.get("treatment_episode_id")==ep["treatment_episode_id"] for b in records["episode_binding"])
                if exposure is None:
                    if missing_ref("treatment_exposure",exposure_id): continue
                    return _bad("FOREIGN_KEY_UNRESOLVED")
                if not bound and not missing_binding_match((ep.get("patient_uid"),ep.get("treatment_episode_id"),"TREATMENT_EXPOSURE",exposure_id)):
                    return _bad("FOREIGN_KEY_UNRESOLVED")
                if exposure.get("patient_uid")!=ep.get("patient_uid"): return _bad("EPISODE_PATIENT_MISMATCH")
        links = supplement["links"]
        if not isinstance(links, list): return _bad("MALFORMED_INPUT")
        linkidx: dict[tuple[str, str], list[LegacyLink]] = {}
        extant={(t,_key(t,r,S)) for t in allowed for r in tables[t] if t in S.PRIMARY}
        link_targets={"study":"study_registry", "source_object":"source_record", "person":"patient_registry",
                      "specimen":"specimen_registry", "assay":"assay_registry", "treatment_episode":"treatment_episode",
                      "endpoint_obs":"clinical_outcome"}
        for link in links:
            if not isinstance(link,dict) or not isinstance(link.get("evidence_refs"),list) or not link["evidence_refs"] or any(not isinstance(e,str) or not e for e in link["evidence_refs"]): return _bad("MALFORMED_INPUT")
            if link["legacy_table"] not in allowed or link["canonical_table"] not in _TABLES:
                return _bad("MALFORMED_INPUT")
            if (link["legacy_table"],link["legacy_key"]) not in extant: return _bad("MALFORMED_INPUT")
            if link["legacy_table"] in link_targets and link_targets[link["legacy_table"]]!=link["canonical_table"]: return _bad("AMBIGUOUS_IDENTITY")
            if link["canonical_key"] not in keys[link["canonical_table"]]:
                if missing_ref(link["canonical_table"],link["canonical_key"]):
                    continue
                unresolved_table_links=sum(1 for candidate in links if isinstance(candidate,dict) and candidate.get("canonical_table")==link["canonical_table"])
                if missing_unkeyed[link["canonical_table"]]==1 and unresolved_table_links==1:
                    continue
                return _bad("FOREIGN_KEY_UNRESOLVED")
            linkidx.setdefault((link["legacy_table"], link["legacy_key"]), []).append(link)
        if any(len(v)!=1 for v in linkidx.values()): return _bad("AMBIGUOUS_IDENTITY")
        patient_targets={}
        for (lt,lk),ll in linkidx.items():
            if lt=="person" and len(ll)==1:
                target=ll[0]["canonical_key"]
                if target in patient_targets and patient_targets[target]!=lk: return _bad("AMBIGUOUS_IDENTITY")
                patient_targets[target]=lk
        legacy_studies={r["study_id"] for r in tables["study"]}
        if any(r.get("study_id") not in legacy_studies for r in tables["source_object"]): return _bad("FOREIGN_KEY_UNRESOLVED")
        source_object_ids={r.get("object_id") for r in tables["source_object"]}
        legacy_person_ids={r.get("person_key") for r in tables["person"]}
        legacy_episode_ids={r.get("episode_id") for r in tables["treatment_episode"]}
        legacy_specimen_ids={r.get("specimen_id") for r in tables["specimen"]}
        legacy_assay_ids={r.get("assay_id") for r in tables["assay"]}
        if any(r.get("person_key") not in legacy_person_ids for r in tables["specimen"]): return _bad("FOREIGN_KEY_UNRESOLVED")
        if any(r.get("person_key") not in legacy_person_ids for r in tables["treatment_episode"]): return _bad("FOREIGN_KEY_UNRESOLVED")
        if any(r.get("episode_id") not in legacy_episode_ids for r in tables["endpoint_obs"]): return _bad("FOREIGN_KEY_UNRESOLVED")
        if any(r.get("source_object_id") not in source_object_ids for r in tables["assay"]): return _bad("FOREIGN_KEY_UNRESOLVED")
        if any(r.get("assay_id") not in legacy_assay_ids or r.get("specimen_id") not in legacy_specimen_ids for r in tables["assay_specimen"]): return _bad("FOREIGN_KEY_UNRESOLVED")
        if any(r.get("specimen_id") not in legacy_specimen_ids or r.get("episode_id") not in legacy_episode_ids for r in tables["specimen_episode"]): return _bad("FOREIGN_KEY_UNRESOLVED")
        cohort_study={r["cohort_id"]:r["study_id"] for r in tables["cohort"]}
        if any(r.get("study_id") not in legacy_studies for r in tables["cohort"]): return _bad("FOREIGN_KEY_UNRESOLVED")
        scoped_labels={}
        scope_missing_targets=set()
        for row in tables["person"]:
            link=linkidx.get(("person",_key("person",row,S)))
            cohort_id=row.get("cohort_id")
            scoped_study=cohort_study.get(cohort_id)
            study_link=linkidx.get(("study",scoped_study)) if scoped_study else None
            if not scoped_study or scoped_study not in legacy_studies:
                return _bad("FOREIGN_KEY_UNRESOLVED")
            if not link: continue
            scope=(scoped_study,row.get("source_label"))
            prior=scoped_labels.setdefault(scope,link[0]["canonical_key"])
            if prior!=link[0]["canonical_key"]: return _bad("AMBIGUOUS_IDENTITY")
            patient=keys[link[0]["canonical_table"]].get(link[0]["canonical_key"])
            if patient is not None and study_link and patient.get("study_id")!=study_link[0]["canonical_key"]: return _bad("FOREIGN_KEY_UNRESOLVED")
            if not study_link:
                scope_missing_targets.add(("patient_registry",link[0]["canonical_key"]))
        dispositions=[]; lineage=[]; reasons={}
        mapping = {"study":"study_registry", "source_object":"source_record", "person":"patient_registry",
                   "specimen":"specimen_registry", "assay":"assay_registry", "treatment_episode":"treatment_episode",
                   "endpoint_obs":"clinical_outcome"}
        entities=set(mapping)
        relationship_missing=set(scope_missing_targets)
        relationship_blockers=[]
        for table in allowed:
            for row in tables[table]:
                key = _key(table,row,S)
                links_for = linkidx.get((table,key), [])
                state="SUPPORT_ONLY"; ct=None; ck=None; why=[]
                parent_key={"specimen":("person",row.get("person_key")),
                            "treatment_episode":("person",row.get("person_key")),
                            "endpoint_obs":("treatment_episode",row.get("episode_id")),
                            "assay":("source_object",row.get("source_object_id"))}.get(table)
                if parent_key and not linkidx.get(parent_key):
                    state="WITHHELD"; why=["FOREIGN_KEY_UNRESOLVED"]
                if table=="assay" and any(x.get("assay_id")==key for x in tables["assay_specimen"]):
                    rel=[x for x in tables["assay_specimen"] if x.get("assay_id")==key]
                    if any(not linkidx.get(("specimen",x.get("specimen_id"))) for x in rel):
                        state="WITHHELD"; why=["FOREIGN_KEY_UNRESOLVED"]
                if table in entities:
                    if state=="WITHHELD":
                        pass
                    elif len(links_for) != 1:
                        state="WITHHELD"; why=["MISSING_CANONICAL_ASSERTION"]
                    elif links_for[0]["canonical_key"] in missing_canonical_keys[links_for[0]["canonical_table"]]:
                        state="WITHHELD"; why=["MISSING_CANONICAL_ASSERTION"]
                    else:
                        l=links_for[0]; ct,ck=l["canonical_table"],l["canonical_key"]; state="MAPPED"
                        rec=keys[ct][ck]
                        if (ct,ck) in relationship_missing:
                            state="WITHHELD"; why=["MISSING_CANONICAL_ASSERTION"]; ct=None; ck=None
                        checks={"person":("source_label","source_patient_id"),"assay":("native_label","source_sample_id"),"endpoint_obs":("native_value","raw_endpoint_label")}
                        if table in checks:
                            a,b=checks[table]
                            if (table=="endpoint_obs" or row.get(a) is not None) and rec.get(b)!=row.get(a): return _bad("RAW_VALUE_CONFLICT")
                        if table=="specimen" and row.get("source_label") not in rec.get("raw_sample_aliases",[]): return _bad("RAW_VALUE_CONFLICT")
                        if table=="assay" and ((row.get("native_unit") is not None and rec.get("measurement_unit")!=row.get("native_unit")) or (row.get("declared_transform") is not None and rec.get("transform")!=row.get("declared_transform"))): return _bad("RAW_VALUE_CONFLICT")
                target=mapping.get(table)
                if state=="MAPPED" and target!=ct: return _bad("AMBIGUOUS_IDENTITY")
                dispositions.append(dict(legacy_table=table,legacy_key=key,state=state,reason_codes=why))
                lineage.append(dict(legacy_table=table,legacy_key=key,canonical_table=ct,canonical_key=ck,
                                    raw_fields=dict(row),evidence_refs=list(links_for[0]["evidence_refs"]) if links_for else []))
        mapped_links={(lt,lk):ll[0] for (lt,lk),ll in linkidx.items() if len(ll)==1}
        person_targets={k:keys[mapped_links[("person",k)]["canonical_table"]][mapped_links[("person",k)]["canonical_key"]]
                        for k in {_key("person",r,S) for r in tables["person"]} if ("person",k) in mapped_links}
        for row in tables["specimen"]:
            link=mapped_links.get(("specimen",_key("specimen",row,S))); owner=person_targets.get(row.get("person_key"))
            target=keys[link["canonical_table"]][link["canonical_key"]] if link else None
            if target is not None and owner is not None and target.get("patient_uid")!=owner.get("patient_uid"): return _bad("AMBIGUOUS_IDENTITY")
        for row in tables["treatment_episode"]:
            link=mapped_links.get(("treatment_episode",_key("treatment_episode",row,S))); owner=person_targets.get(row.get("person_key"))
            target=keys[link["canonical_table"]][link["canonical_key"]] if link else None
            if target is not None and owner is not None and target.get("patient_uid")!=owner.get("patient_uid"): return _bad("EPISODE_PATIENT_MISMATCH")
        for row in tables["endpoint_obs"]:
            link=mapped_links.get(("endpoint_obs",_key("endpoint_obs",row,S)))
            ep_link=mapped_links.get(("treatment_episode",row.get("episode_id")))
            target=keys[link["canonical_table"]][link["canonical_key"]] if link else None
            episode=keys[ep_link["canonical_table"]][ep_link["canonical_key"]] if ep_link else None
            if target is not None and episode is not None and target.get("patient_uid")!=episode.get("patient_uid"): return _bad("EPISODE_PATIENT_MISMATCH")
            if link:
                expected_episode=ep_link["canonical_key"] if ep_link else None
                subject_bindings=[b for b in records["episode_binding"] if b.get("subject_type")=="CLINICAL_OUTCOME" and b.get("subject_id")==link["canonical_key"]]
                if expected_episode is None:
                    relationship_missing.add(("clinical_outcome",link["canonical_key"]))
                    relationship_blockers.append("E03")
                elif subject_bindings and not any(b.get("treatment_episode_id")==expected_episode for b in subject_bindings):
                    return _bad("EPISODE_PATIENT_MISMATCH")
                elif not any(b.get("treatment_episode_id")==expected_episode for b in subject_bindings):
                    relationship_missing.add(("clinical_outcome",link["canonical_key"]))
                    relationship_blockers.append("E03")
        expected_outcome_episode={}
        for row in tables["endpoint_obs"]:
            ol=mapped_links.get(("endpoint_obs",_key("endpoint_obs",row,S)))
            el=mapped_links.get(("treatment_episode",row.get("episode_id")))
            if ol and el:
                prior=expected_outcome_episode.setdefault(ol["canonical_key"],el["canonical_key"])
                if prior!=el["canonical_key"]: return _bad("EPISODE_PATIENT_MISMATCH")
        for binding in records["episode_binding"]:
            if binding.get("subject_type")=="CLINICAL_OUTCOME" and binding.get("subject_id") in expected_outcome_episode and binding.get("treatment_episode_id")!=expected_outcome_episode[binding["subject_id"]]: return _bad("EPISODE_PATIENT_MISMATCH")
        for row in tables["source_object"]:
            obj=mapped_links.get(("source_object",_key("source_object",row,S)))
            study=mapped_links.get(("study",row.get("study_id")))
            if obj:
                cr=keys[obj["canonical_table"]][obj["canonical_key"]]
                if row.get("sha256") is not None and cr.get("sha256") is not None and row["sha256"]!=cr["sha256"]: return _bad("RAW_VALUE_CONFLICT")
                if study:
                    if cr.get("study_id")!=study["canonical_key"]: return _bad("FOREIGN_KEY_UNRESOLVED")
                else:
                    relationship_missing.add(("source_record",obj["canonical_key"]))
                    relationship_blockers.append("E03")
        for row in tables["assay"]:
            assay_link=mapped_links.get(("assay",_key("assay",row,S)))
            object_link=mapped_links.get(("source_object",row.get("source_object_id")))
            if assay_link and object_link:
                canonical_assay=keys["assay_registry"].get(assay_link["canonical_key"])
                if canonical_assay is not None and canonical_assay.get("source_object_id")!=object_link["canonical_key"]:
                    return _bad("FOREIGN_KEY_UNRESOLVED")
        for row in tables["assay_specimen"]:
            al=mapped_links.get(("assay",row.get("assay_id"))); sl=mapped_links.get(("specimen",row.get("specimen_id")))
            if al and sl:
                assay=keys[al["canonical_table"]][al["canonical_key"]]
                specimen=keys[sl["canonical_table"]][sl["canonical_key"]]
                if assay.get("specimen_uid")!=specimen.get("specimen_uid"): return _bad("FOREIGN_KEY_UNRESOLVED")
        specimen_episode_pairs=set()
        for row in tables["specimen_episode"]:
            specimen_link=mapped_links.get(("specimen",row.get("specimen_id")))
            episode_link=mapped_links.get(("treatment_episode",row.get("episode_id")))
            if not specimen_link or not episode_link:
                if specimen_link:
                    relationship_missing.add(("specimen_registry",specimen_link["canonical_key"]))
                    relationship_blockers.append("E03")
                continue
            specimen_id=specimen_link["canonical_key"]; episode_id=episode_link["canonical_key"]
            specimen_episode_pairs.add((specimen_id,episode_id))
            specimen=keys["specimen_registry"].get(specimen_id)
            episode=keys["treatment_episode"].get(episode_id)
            if specimen is not None and episode is not None and specimen.get("patient_uid")!=episode.get("patient_uid"):
                return _bad("EPISODE_PATIENT_MISMATCH")
        bound_specimen_pairs={(b.get("subject_id"),b.get("treatment_episode_id")) for b in records["episode_binding"] if b.get("subject_type")=="SPECIMEN"}
        expected_by_specimen={}
        for specimen_id,episode_id in specimen_episode_pairs:
            expected_by_specimen.setdefault(specimen_id,set()).add(episode_id)
        for specimen_id,expected_episodes in expected_by_specimen.items():
            supplied_episodes={episode_id for sid,episode_id in bound_specimen_pairs if sid==specimen_id}
            if supplied_episodes and expected_episodes.isdisjoint(supplied_episodes):
                return _bad("EPISODE_PATIENT_MISMATCH")
        for specimen_id,episode_id in specimen_episode_pairs:
            if (specimen_id,episode_id) not in bound_specimen_pairs:
                relationship_missing.add(("specimen_registry",specimen_id)); relationship_blockers.append("E03")
        for d in dispositions:
            l=next(r for r in lineage if r["legacy_table"]==d["legacy_table"] and r["legacy_key"]==d["legacy_key"])
            if d["state"]=="MAPPED" and (l["canonical_table"],l["canonical_key"]) in relationship_missing:
                d["state"]="WITHHELD"; d["reason_codes"]=["MISSING_CANONICAL_ASSERTION"]
                l["canonical_table"]=None; l["canonical_key"]=None
        # Suppress canonical entities whose corresponding legacy entity was withheld.
        mapped={(r["canonical_table"],r["canonical_key"]) for r in lineage if r["canonical_table"] is not None}
        dropped_canonical=False
        for ct in mapping.values():
            kept=[r for r in records[ct] if (ct,_canonical_key(ct,r)) in mapped]
            dropped_canonical |= len(kept)!=len(records[ct])
            records[ct]=kept
        # Dependency closure after withholding absent canonical assertions.
        changed=True
        while changed:
            changed=False
            keep={t:set(_canonical_key(t,r) for r in records[t]) for t in _TABLES}
            refs={
                "study_registry":lambda r:any(f.get("publication_family_id")==r.get("publication_family_id") and f.get("study_id")==r.get("study_id") for f in records["publication_family"]),
                "publication_family":lambda r:r.get("study_id") in keep["study_registry"],
                "source_record":lambda r:r.get("study_id") in keep["study_registry"] and any(f["publication_family_id"]==r.get("publication_family_id") and f["study_id"]==r.get("study_id") for f in records["publication_family"]),
                "patient_registry":lambda r:r.get("study_id") in keep["study_registry"],
                "specimen_registry":lambda r:r.get("patient_uid") in keep["patient_registry"] and all(epid in keep["treatment_episode"] and any(b.get("subject_type")=="SPECIMEN" and b.get("subject_id")==r.get("specimen_uid") and b.get("treatment_episode_id")==epid for b in records["episode_binding"]) for epid in expected_by_specimen.get(r.get("specimen_uid"),set())),
                "assay_registry":lambda r:r.get("specimen_uid") in keep["specimen_registry"] and r.get("source_object_id") in keep["source_record"],
                "treatment_episode":lambda r:r.get("patient_uid") in keep["patient_registry"] and r.get("study_id") in keep["study_registry"] and all(x in keep["treatment_exposure"] and any(b.get("subject_type")=="TREATMENT_EXPOSURE" and b.get("subject_id")==x and b.get("treatment_episode_id")==r.get("treatment_episode_id") for b in records["episode_binding"]) for x in r.get("component_exposure_ids",[])),
                "treatment_exposure":lambda r:r.get("patient_uid") in keep["patient_registry"] and any(b.get("subject_type")=="TREATMENT_EXPOSURE" and b.get("subject_id")==r.get("treatment_exposure_id") and b.get("treatment_episode_id") in keep["treatment_episode"] for b in records["episode_binding"]),
                "clinical_outcome":lambda r:r.get("patient_uid") in keep["patient_registry"] and (r.get("outcome_id") not in expected_outcome_episode or (expected_outcome_episode[r.get("outcome_id")] in keep["treatment_episode"] and any(b.get("subject_type")=="CLINICAL_OUTCOME" and b.get("subject_id")==r.get("outcome_id") and b.get("treatment_episode_id")==expected_outcome_episode[r.get("outcome_id")] for b in records["episode_binding"]))),
                "episode_binding":lambda r:r.get("patient_uid") in keep["patient_registry"] and r.get("treatment_episode_id") in keep["treatment_episode"]
            }
            refs["episode_binding"] = lambda r: r.get("patient_uid") in keep["patient_registry"] and r.get("treatment_episode_id") in keep["treatment_episode"] and ((r.get("subject_type")=="SPECIMEN" and r.get("subject_id") in keep["specimen_registry"]) or (r.get("subject_type")=="TREATMENT_EXPOSURE" and r.get("subject_id") in keep["treatment_exposure"]) or (r.get("subject_type")=="CLINICAL_OUTCOME" and r.get("subject_id") in keep["clinical_outcome"]))
            for t,pred in refs.items():
                kept=[r for r in records[t] if pred(r)]
                if len(kept)!=len(records[t]): dropped_canonical=True; records[t]=kept; changed=True
        final_keys={t:{_canonical_key(t,r) for r in records[t]} for t in _TABLES}
        lineage_by_key={(r["legacy_table"],r["legacy_key"]):r for r in lineage}
        for d in dispositions:
            l=lineage_by_key[(d["legacy_table"],d["legacy_key"])]
            if d["state"]=="MAPPED" and l["canonical_key"] not in final_keys.get(l["canonical_table"],set()):
                d["state"]="WITHHELD"; d["reason_codes"]=["MISSING_CANONICAL_ASSERTION"]
                l["canonical_table"]=None; l["canonical_key"]=None
        blockers=list(supplement["unresolved"])+relationship_blockers
        if not any(d["state"]=="MAPPED" for d in dispositions): reasons["MISSING_CANONICAL_ASSERTION"]=reasons.get("MISSING_CANONICAL_ASSERTION",0)+1
        if missing_canonical:
            reasons["MISSING_CANONICAL_ASSERTION"]=reasons.get("MISSING_CANONICAL_ASSERTION",0)+1
        if dropped_canonical:
            reasons["MISSING_CANONICAL_ASSERTION"]=reasons.get("MISSING_CANONICAL_ASSERTION",0)+1
        for code in blockers: reasons["SOURCE_EVIDENCE_REQUIRED"]=reasons.get("SOURCE_EVIDENCE_REQUIRED",0)+1
        status="BLOCKED_UNKNOWN" if blockers or missing_canonical or dropped_canonical or not any(d["state"]=="MAPPED" for d in dispositions) or any(d["state"]=="WITHHELD" for d in dispositions) else "STRUCTURAL_CANDIDATE"
        for d in dispositions:
            if d["state"] == "WITHHELD":
                for code in d["reason_codes"] or ["MISSING_CANONICAL_ASSERTION"]:
                    reasons[code] = reasons.get(code,0)+1
        stable_meta={"classification":legacy_metadata["classification"],"tables":{
            t:sorted(tables[t],key=lambda row:_canon([row.get(c) for c in S.COLUMNS[t]])) for t in sorted(allowed)},
            "producer_hashes":dict(sorted(legacy_metadata["producer_hashes"].items())),
            "auditor_hashes":dict(sorted(legacy_metadata["auditor_hashes"].items())),
            "source_code_hashes":dict(sorted(legacy_metadata["source_code_hashes"].items()))}
        stable_supp={"classification":supplement["classification"],"legacy_metadata_sha256":supplement["legacy_metadata_sha256"],"records":{
            t:sorted(input_records[t],key=lambda row:(_canonical_key(t,row),_canon(row))) for t in sorted(_TABLES)},
            "links":sorted(links,key=lambda x:_canon(x)),"unresolved":sorted(supplement["unresolved"]),
            "schema_hashes":dict(sorted(supplement["schema_hashes"].items()))}
        hashes.update({"supplement":_sha(_canon(stable_supp)),"legacy_metadata":expected_metadata})
        return MigrationResult(status=status, records={t:sorted((dict(r) for r in records[t]),key=lambda row:_canonical_key(t,row)) for t in _TABLES},
             lineage=sorted(lineage,key=lambda r:(r["legacy_table"],r["legacy_key"])),
             dispositions=sorted(dispositions,key=lambda r:(r["legacy_table"],r["legacy_key"])),
             reason_counts=reasons,bindings=hashes,**_FALSE)
    except Exception:
        return _bad("MALFORMED_INPUT")


def _canonical_key(table: str, record: dict[str, Any]) -> str:
    fields={"study_registry":"study_id","publication_family":None,"source_record":"source_object_id",
            "patient_registry":"patient_uid","specimen_registry":"specimen_uid","assay_registry":"assay_uid",
            "treatment_episode":"treatment_episode_id","treatment_exposure":"treatment_exposure_id",
            "clinical_outcome":"outcome_id","episode_binding":"binding_id"}
    if table=="publication_family": return _canon([record.get("publication_family_id"),record.get("publication_id")]).decode()
    value=record.get(fields[table])
    return value if isinstance(value,str) else ""


def public_summary(result: MigrationResult) -> dict[str, object]:
    return {"status":result["status"],"counts":{"records":sum(map(len,result["records"].values())),
            "lineage":len(result["lineage"]),"dispositions":len(result["dispositions"])},
            "reason_counts":dict(result["reason_counts"]),"bindings":dict(result["bindings"]),**_FALSE}
