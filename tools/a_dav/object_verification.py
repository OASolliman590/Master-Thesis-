"""Pure source-object record validation; network retrieval lives in retrieval.py."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, NoReturn
from urllib.parse import urlsplit

from tools.a_dav.search_log import _scan_text, _validate_fact_locator

HOST_ALLOWLIST = frozenset({"ftp.ncbi.nlm.nih.gov", "www.ncbi.nlm.nih.gov", "eutils.ncbi.nlm.nih.gov", "zenodo.org", "raw.githubusercontent.com", "media.githubusercontent.com", "api.github.com", "github.com", "ega-archive.org", "www.ebi.ac.uk", "ftp.ebi.ac.uk"})

class VerificationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message); self.code = code

def _fail(code: str, message: str) -> NoReturn: raise VerificationError(code, message)

def validate_url(url: str, allowed_hosts: frozenset[str] = HOST_ALLOWLIST) -> str:
    try:
        p = urlsplit(url)
        if "@" in p.netloc: _fail("SECRET_LOCATOR", "URL user information is not allowed")
        _validate_fact_locator("URL", url)
    except Exception as exc:
        code = getattr(exc, "code", "MALFORMED_URL")
        raise VerificationError(code, str(exc)) from exc
    if p.hostname not in allowed_hosts: _fail("HOST_NOT_ALLOWED", f"host is not allowlisted: {p.hostname}")
    if p.scheme != "https": _fail("HTTPS_REQUIRED", "only HTTPS URLs are permitted")
    return p.hostname

def _scan_obj(value: Any) -> None:
    if isinstance(value, dict):
        for k,v in value.items(): _scan_text(str(k)); _scan_obj(v)
    elif isinstance(value, (list,tuple)):
        for x in value: _scan_obj(x)
    elif isinstance(value,str): _scan_text(value)

def classify_access_route(url: str | None, controlled: bool = False, author_request: bool = False, unavailable: bool = False) -> str:
    if author_request: return "AUTHOR_REQUEST"
    if unavailable: return "UNAVAILABLE"
    if not url: return "CONTROLLED" if controlled else "UNKNOWN"
    p=urlsplit(url)
    path=p.path.rstrip("/") or "/"
    if p.hostname not in HOST_ALLOWLIST: return "UNKNOWN"
    if p.hostname=="ega-archive.org" and (path.startswith("/"+"studies"+"/") or path.startswith("/"+"datasets"+"/")): return "CONTROLLED"
    if p.hostname=="www.ncbi.nlm.nih.gov" and path.startswith("/"+"projects"+"/"+"gap"+"/"+"cgi-bin"+"/"+"study.cgi"): return "CONTROLLED"
    if p.hostname=="www.ebi.ac.uk" and path.startswith("/"+"ena"+"/"+"browser"+"/"+"view"+"/"): return "PUBLIC_LANDING"
    if p.hostname in ("www.ncbi.nlm.nih.gov","eutils.ncbi.nlm.nih.gov") and "geo/query/acc.cgi" in path: return "PUBLIC_LANDING"
    if p.hostname=="zenodo.org" and (re.search(r"/"+"api/records/[0-9]+$",path) or re.search(r"/"+"records/[0-9]+$",path)): return "PUBLIC_LANDING"
    return "PUBLIC_DIRECT"

def build_source_record(data: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data,dict): _fail("MALFORMED_INPUT","record input must be an object")
    _scan_obj(data)
    out={}
    props=schema.get("properties",{})
    for key, spec in props.items():
        if key in data: out[key]=data[key]
        elif key == "schema_version": out[key]=spec.get("default","1.0.0")
        elif key == "access_route": out[key]=classify_access_route(data.get("object_url") or data.get("landing_page_url"), controlled=data.get("controlled",False))
        elif key == "object_url": out[key]=None
        elif key == "sha256": out[key]=None
        elif key == "hash_scope": out[key]="NOT_RETRIEVED"
        elif key == "retrieval_status": out[key]="NOT_ATTEMPTED"
        elif key == "validation_status": out[key]="STRUCTURAL_ONLY"
        elif key == "patient_sample_crosswalk": out[key]="UNKNOWN"
        elif key == "redistribution_status": out[key]="UNKNOWN"
        elif key in ("license_terms",): out[key]="UNKNOWN"
        elif spec.get("type")==["string","null"] or spec.get("type")=="null": out[key]=None
    if data.get("landing_page_url") and not data.get("object_url"):
        out["object_url"]=None
        if not data.get("exact_file_name"): out["exact_file_name"]=""
    if "source_locators" not in out and data.get("landing_page_url"):
        out["source_locators"]=[{"kind":"URL","value":data["landing_page_url"],"page_or_section":None,"accessed_utc":None}]
    if out.get("access_route") not in schema["properties"]["access_route"]["enum"]: _fail("MALFORMED_INPUT","invalid access route")
    locator_url=out.get("object_url") or data.get("landing_page_url")
    if locator_url and out.get("access_route") != classify_access_route(locator_url,controlled=data.get("controlled",False)):
        _fail("ACCESS_ROUTE_MISMATCH","access route does not match the URL classification")
    validate_source_record(out,schema)
    return out

def validate_source_record(record: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(record,dict): _fail("MALFORMED_INPUT","record must be an object")
    _scan_obj(record)
    try:
        from jsonschema import Draft202012Validator
        errors=list(Draft202012Validator(schema).iter_errors(record))
    except ImportError:
        _fail("SCHEMA_VALIDATOR_UNAVAILABLE","frozen-schema validation requires jsonschema")
    if errors: _fail("SCHEMA_INVALID", errors[0].message)
    if not record.get("license_terms") or not record.get("redistribution_status"): _fail("TERMS_REQUIRED","license terms and redistribution status are required")
    if record.get("validation_status") not in ("NOT_VALIDATED","STRUCTURAL_ONLY","BLOCKED_UNKNOWN"): _fail("VALIDATION_TOO_STRONG","source-object construction cannot claim validation beyond STRUCTURAL_ONLY")
    locator_urls=[x.get("value") for x in record.get("source_locators",[]) if x.get("kind")=="URL"]
    locator_urls.extend([record.get("object_url"),record.get("landing_page_url")])
    # An object's listing page is provenance, not the object's access route.
    route_urls=[record["object_url"]] if record.get("object_url") else locator_urls
    locator_routes={classify_access_route(u) for u in route_urls if u}
    if len(locator_routes)>1 or (locator_routes and record.get("access_route") not in locator_routes): _fail("ACCESS_ROUTE_MISMATCH","access route conflicts with one or more repository URL classifications")
    if record.get("object_url") and classify_access_route(record["object_url"])!="PUBLIC_DIRECT":
        _fail("LANDING_IS_NOT_OBJECT","repository landing URLs cannot identify a source object")
    if record.get("sha256") is not None:
        if not re.fullmatch(r"[a-f0-9]{64}",str(record.get("sha256"))): _fail("HASH_STATE_INVALID","sha256 must be lowercase hexadecimal")
        if record.get("hash_scope") != "FULL_OBJECT" or record.get("retrieval_status") != "RETRIEVED" or record.get("byte_size") is None or record.get("retrieval_utc") is None:
            _fail("HASH_STATE_INVALID","full hash requires a retrieved object with byte size and retrieval time")
    elif record.get("hash_scope") == "FULL_OBJECT": _fail("HASH_STATE_INVALID","FULL_OBJECT hash scope requires a verified digest")
    if record.get("hash_scope") in ("COMPRESSED_PREFIX","HEADER_ONLY") and record.get("sha256") is not None: _fail("HASH_STATE_INVALID","prefix/header digest cannot populate full sha256")
    if record.get("object_url"): validate_url(record["object_url"])
    for loc in record.get("source_locators",[]):
        if loc.get("kind")=="URL": validate_url(loc["value"])
        else:
            try: _validate_fact_locator(loc.get("kind"),loc.get("value"))
            except Exception as exc: raise VerificationError(getattr(exc,"code","MALFORMED_LOCATOR"),str(exc)) from exc
    if not record.get("exact_file_name") or (not record.get("object_url") and not record.get("access_route")):
        if record.get("object_url") or record.get("retrieval_status") in ("LOCATED","RETRIEVED"): _fail("OBJECT_IDENTITY_INCOMPLETE","an object requires exact filename and object URL/access route")
    return record

def validate_unique_ids(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen=set()
    for row in records:
        if not isinstance(row,dict): _fail("MALFORMED_INPUT","records must be objects")
        ident=row.get("source_object_id")
        if not ident: _fail("MALFORMED_INPUT","record has no source_object_id")
        if ident in seen: _fail("DUPLICATE_ID",f"duplicate source_object_id: {ident}")
        seen.add(ident)
    return records

def _etag_from_notes(notes: Any) -> str | None:
    matches=re.findall(r"(?:^|; )repository_etag=([^;]+)",str(notes or ""))
    return matches[-1] if matches else None

def version_record(prior: dict[str, Any], changes: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    fields=("byte_size","etag","last_modified","object_url")
    drift=[k for k in fields if k in changes and changes[k] != (_etag_from_notes(prior.get("notes")) if k=="etag" else prior.get(k))]
    if not drift: return dict(prior),dict(prior),[]
    updated=dict(prior)
    for key,value in changes.items():
        if key!="etag" and key in updated: updated[key]=value
    if "etag" in changes:
        prior_tag=_etag_from_notes(prior.get("notes"))
        updated["notes"]=(str(prior.get("notes") or "")+"; repository_etag="+str(changes["etag"])).strip("; ")
    seed=json.dumps([prior.get("source_object_id"), sorted((k,changes[k]) for k in drift)],sort_keys=True,separators=(",",":"))
    updated["source_object_id"]=str(prior["source_object_id"])+"-v"+hashlib.sha256(seed.encode()).hexdigest()[:10]
    updated["source_version"]=changes.get("source_version") or updated["source_object_id"].rsplit("-v",1)[-1]
    updated.update({"sha256":None,"hash_scope":"NOT_RETRIEVED","retrieval_status":"LOCATED","retrieval_utc":None})
    return updated,dict(prior),drift
