"""Offline source-object verification core and explicitly bounded urllib fetch driver."""
from __future__ import annotations

import argparse
import csv
import hashlib
import http.client
import html.parser
import json
import os
import posixpath
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

from tools.a_dav.search_log import _scan_text, _validate_fact_locator

HOST_ALLOWLIST = frozenset({"ftp.ncbi.nlm.nih.gov", "www.ncbi.nlm.nih.gov", "eutils.ncbi.nlm.nih.gov", "zenodo.org", "raw.githubusercontent.com", "api.github.com", "github.com", "ega-archive.org", "www.ebi.ac.uk", "ftp.ebi.ac.uk"})
KNOWN_DUPLICATE_TRACER_DEVIATION = ("552093f5277d7d94", "efae8375d440881e", "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE198nnn/GSE198052/suppl/filelist.txt", "GET")
REQUEST_CAP = 200
MIN_SPACING_SECONDS = .5
RECEIPT_FIELDS = ("source_object_id", "exact_url_or_access_route", "repository_or_accession", "filename_and_source_version", "retrieval_utc", "http_repository_metadata", "byte_size", "complete_sha256", "compression_and_content_type", "license_terms_and_redistribution_status", "retrieval_code_config_versions", "partial_full_status", "validation_status")
PRIORITY_ROWS = ("ICB-BULK-001", "ICB-BULK-002", "ICB-BULK-003", "ICB-BULK-009", "ICB-BULK-014", "ICB-BULK-019", "ICB-BULK-024", "ICB-BULK-025", "ICB-BULK-026", "ICB-BULK-027", "ICB-BULK-033", "ICB-BULK-038", "ICB-BULK-042", "PROST-BULK-003", "PROST-BULK-005", "PROST-BULK-010", "S01", "S02", "S03", "S05", "S07", "S24")
KNOWN_C1_STALE_HOST_REQUEST_IDS=frozenset("5937e0898c970116 c372c8715dd941d5 1a9aa8518c52e9e6 b25c12656cb90541 a7d294dc6ee3ad43 9d632a56a61d8292 c7d092db0f2cea69 81910811c3ce6767 ad32af5ae77c5a8b fc97cf7dbe663b33 ae017f12eb67e1f9 2053f7e83e31a8d2 b131ca931522f80c ad6eddee3f104693 7b739a18f238858c d127dca5f7e39755 d467ab07be6f9ef7 8567d2cab7eed197 95c24ba9defe16cc a927267292dd29fa 853d11b3012143ce 6aad599f8c712feb 2fdc2b985f32fac3 b4435d33441cf599 03bead25354542f3 552093f5277d7d94 9097be6800b9439f 0403fa69963e2b00 d1076ae8afd8d77f 5f460f6b3b103ed8 8e6589b76defddb1 343da11acdd0a221".split())

class VerificationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message); self.code = code

def _fail(code, message): raise VerificationError(code, message)

def validate_url(url: str, allowed_hosts=HOST_ALLOWLIST):
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

def _scan_obj(value):
    if isinstance(value, dict):
        for k,v in value.items(): _scan_text(str(k)); _scan_obj(v)
    elif isinstance(value, (list,tuple)):
        for x in value: _scan_obj(x)
    elif isinstance(value,str): _scan_text(value)

def classify_access_route(url, controlled=False, author_request=False, unavailable=False):
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

def build_source_record(data, schema):
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

def validate_source_record(record, schema):
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

def validate_unique_ids(records):
    seen=set()
    for row in records:
        if not isinstance(row,dict): _fail("MALFORMED_INPUT","records must be objects")
        ident=row.get("source_object_id")
        if not ident: _fail("MALFORMED_INPUT","record has no source_object_id")
        if ident in seen: _fail("DUPLICATE_ID",f"duplicate source_object_id: {ident}")
        seen.add(ident)
    return records

def _etag_from_notes(notes):
    matches=re.findall(r"(?:^|; )repository_etag=([^;]+)",str(notes or ""))
    return matches[-1] if matches else None

def version_record(prior, changes):
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

def validate_retrieval_receipt(receipt):
    if not isinstance(receipt,dict) or any(not receipt.get(k) for k in RECEIPT_FIELDS): _fail("RECEIPT_INCOMPLETE","retrieval receipt is missing a required policy field")
    nested={"http_repository_metadata":("status","headers","final_url"),"compression_and_content_type":("compression","content_type"),"license_terms_and_redistribution_status":("license_terms","redistribution_status"),"retrieval_code_config_versions":("code","config")}
    for parent,children in nested.items():
        value=receipt.get(parent)
        if not isinstance(value,dict) or any(value.get(k) in (None,"") for k in children): _fail("RECEIPT_INCOMPLETE",f"retrieval receipt has empty nested field in {parent}")
    if isinstance(receipt.get("http_repository_metadata"),dict):
        headers=receipt["http_repository_metadata"].get("headers")
        if not isinstance(headers,dict) or any(not k or v in (None,"") for k,v in headers.items()): _fail("RECEIPT_INCOMPLETE","repository headers must contain non-empty values")
    if receipt.get("byte_size") is None or receipt.get("byte_size")=="": _fail("RECEIPT_INCOMPLETE","receipt byte_size is required")
    if receipt["partial_full_status"]!="FULL_VERIFIED": _fail("RECEIPT_INCOMPLETE","complete receipt must describe a full verified object")
    if not re.fullmatch(r"[a-f0-9]{64}",str(receipt["complete_sha256"])): _fail("RECEIPT_INCOMPLETE","receipt requires complete SHA-256")
    if receipt.get("validation_status") not in ("NOT_VALIDATED","STRUCTURAL_ONLY","BLOCKED_UNKNOWN"):
        _fail("VALIDATION_TOO_STRONG","retrieval receipts cannot claim validation beyond STRUCTURAL_ONLY")
    metadata=receipt["http_repository_metadata"]
    requested=receipt["exact_url_or_access_route"]; final=metadata["final_url"]
    validate_url(requested); validate_url(final)
    chain=metadata.get("redirect_chain",[])
    if not isinstance(chain,list): _fail("RECEIPT_INCOMPLETE","receipt redirect chain must be a list")
    hops=[hop.get("url") if isinstance(hop,dict) else hop for hop in chain]
    for hop in hops: validate_url(hop)
    if (hops and (hops[0]!=requested or hops[-1]!=final)) or (final!=requested and len(hops)<2):
        _fail("TRACER_PROVENANCE_MISMATCH","receipt redirect chain is not bound to its requested and final URL")
    return receipt

def _normalized_headers(headers):
    if not isinstance(headers,dict): _fail("TRACER_PROVENANCE_MISMATCH","HTTP headers must be an object")
    normalized={}
    for name,value in headers.items():
        if not isinstance(name,str) or not name or name.lower() in normalized:
            _fail("TRACER_PROVENANCE_MISMATCH","HTTP header names must be unambiguous")
        normalized[name.lower()]=value
    return normalized

def _utc(clock):
    value=clock()
    if isinstance(value,(int,float)): return datetime.fromtimestamp(value,timezone.utc).isoformat().replace("+00:00","Z")
    return str(value)
def _clock_seconds(clock):
    value=clock()
    if isinstance(value,(int,float)): return float(value)
    try: return datetime.fromisoformat(str(value).replace("Z","+00:00")).timestamp()
    except Exception: return time.time()

def _urllib_transport(url, headers):
    req=urllib.request.Request(url,headers=headers,method="GET")
    redirect_handler=_AllowlistRedirectHandler()
    opener=urllib.request.build_opener(redirect_handler)
    try: response=opener.open(req,timeout=60)
    except urllib.error.HTTPError as e: response=e
    with response:
        try: data=response.read(); interrupted=False
        except http.client.IncompleteRead as exc: data=exc.partial; interrupted=True
        final=response.geturl()
        chain=[url,*redirect_handler.hops]
        if chain[-1]!=final: chain.append(final)
        return {"status":response.status,"headers":dict(response.headers.items()),"body":data,"final_url":final,"redirect_chain":chain,"interrupted":interrupted}

class _AllowlistRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self):
        super().__init__(); self.hops=[]
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        self.hops.append(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def _atomic_retrieve_impl(url,dest,source_object_id,transport,clock,expected_sha256=None,repository="UNKNOWN",accession=None,filename=None,source_version=None,license_terms="UNKNOWN",redistribution_status="UNKNOWN",code_version="A-DAV-05-step1",config_version="1",max_bytes=None,expected_size=None):
    validate_url(url); dest=Path(dest)
    if dest.exists(): _fail("DESTINATION_EXISTS","atomic retrieval will not replace an existing destination; choose a new version path")
    part=Path(str(dest)+".part"); meta=Path(str(part)+".json"); dest.parent.mkdir(parents=True,exist_ok=True)
    headers={}; offset=0; prior_meta=None
    if part.exists() and meta.exists():
        try: prior_meta=json.loads(meta.read_text()); prefix=part.read_bytes(); digest=hashlib.sha256(prefix).hexdigest()
        except Exception: prefix=b""; digest=""
        if prefix and digest==prior_meta.get("prefix_sha256") and prior_meta.get("etag") and prior_meta.get("total"):
            offset=len(prefix); headers={"Range":f"bytes={offset}-","If-Range":prior_meta["etag"]}
        else:
            part.unlink(missing_ok=True); meta.unlink(missing_ok=True); offset=0
    response=transport(url,headers)
    if response.get("final_url"): validate_url(response["final_url"])
    status=int(response.get("status",0)); rh={str(k).lower():str(v) for k,v in response.get("headers",{}).items()}; body=response.get("body",b"")
    if isinstance(body,str): body=body.encode()
    if status not in ((200,206) if offset else (200,)): _fail("HTTP_STATUS_INVALID",f"unexpected HTTP status {status}")
    if not response.get("interrupted") and rh.get("content-length","").isdigit() and len(body)!=int(rh["content-length"]): _fail("BYTE_COUNT_MISMATCH","response body length differs from declared Content-Length")
    if expected_size is not None and not offset and rh.get("content-length","").isdigit() and int(rh["content-length"])!=int(expected_size): _fail("BYTE_COUNT_MISMATCH","expected_size differs from declared Content-Length")
    if offset:
        cr=rh.get("content-range","")
        range_match=re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)",cr)
        valid=bool(range_match and status==206 and int(range_match.group(1))==offset and int(range_match.group(3))==int(prior_meta["total"]) and (expected_size is None or int(range_match.group(3))==int(expected_size)) and int(range_match.group(2))-int(range_match.group(1))+1==len(body) and rh.get("etag")==prior_meta.get("etag"))
        if not valid:
            part.unlink(missing_ok=True); meta.unlink(missing_ok=True); _fail("RESUME_RESTART_REQUIRED","range response failed validation; driver must account for a fresh request")
        mode="ab"; total=int(prior_meta["total"])
    else:
        mode="wb"; total=int(rh["content-length"]) if rh.get("content-length"," ").isdigit() else (int(expected_size) if expected_size is not None else None)
    with open(part,mode) as f:
        f.write(body); f.flush(); os.fsync(f.fileno())
    full=part.read_bytes(); observed=len(full)
    if max_bytes is not None and observed>max_bytes:
        part.unlink(missing_ok=True); meta.unlink(missing_ok=True); _fail("OBJECT_TOO_LARGE","object exceeds configured full-retrieval size limit")
    if response.get("interrupted"):
        if total is not None and rh.get("etag"):
            meta.write_text(json.dumps({"total":total,"etag":rh["etag"],"prefix_sha256":hashlib.sha256(full).hexdigest()},sort_keys=True))
        _fail("INTERRUPTED","download incomplete; partial retained for validated resume")
    if total is not None and observed<total and status==206:
        if total is not None and rh.get("etag"):
            meta.write_text(json.dumps({"total":total,"etag":rh["etag"],"prefix_sha256":hashlib.sha256(full).hexdigest()},sort_keys=True))
        _fail("INTERRUPTED","download incomplete; partial retained for validated resume")
    if expected_size is not None and observed!=int(expected_size): _fail("BYTE_COUNT_MISMATCH",f"expected {expected_size} bytes, got {observed}")
    if total is not None and observed!=total: _fail("BYTE_COUNT_MISMATCH",f"expected {total} bytes, got {observed}")
    if total is None and not expected_sha256: _fail("TOTAL_SIZE_UNKNOWN","complete retrieval requires Content-Length, expected_size, or expected_sha256")
    digest=hashlib.sha256(full).hexdigest()
    if expected_sha256 and digest!=expected_sha256: _fail("HASH_MISMATCH","retrieved bytes do not match expected SHA-256")
    utc=_utc(clock)
    receipt={"source_object_id":source_object_id,"exact_url_or_access_route":url,"repository_or_accession":accession or repository,"filename_and_source_version":(filename or dest.name)+";"+(source_version or "UNKNOWN"),"retrieval_utc":utc,"http_repository_metadata":{"status":status,"headers":{k:rh[k] for k in ("content-length","etag","last-modified","content-type") if k in rh},"final_url":response.get("final_url",url),"redirect_chain":response.get("redirect_chain",[])},"byte_size":observed,"complete_sha256":digest,"sha256":digest,"compression_and_content_type":{"compression":"UNKNOWN","content_type":rh.get("content-type","UNKNOWN")},"license_terms_and_redistribution_status":{"license_terms":license_terms,"redistribution_status":redistribution_status},"retrieval_code_config_versions":{"code":code_version,"config":config_version},"partial_full_status":"FULL_VERIFIED","validation_status":"STRUCTURAL_ONLY","http_status":status}
    validate_retrieval_receipt(receipt)
    try: os.link(part,dest)
    except FileExistsError: _fail("DESTINATION_EXISTS","destination appeared during retrieval; refusing to overwrite")
    cleanup_warning=None
    try: part.unlink()
    except OSError as exc:
        cleanup_warning=f"verified destination published; partial cleanup failed: {type(exc).__name__}"
        try: part.unlink(missing_ok=True)
        except OSError: pass
    meta.unlink(missing_ok=True)
    if cleanup_warning: receipt["cleanup_warning"]=cleanup_warning
    return receipt

def atomic_retrieve(url,dest,source_object_id,transport,clock,expected_sha256=None,repository="UNKNOWN",accession=None,filename=None,source_version=None,license_terms="UNKNOWN",redistribution_status="UNKNOWN",code_version="A-DAV-05-step1",config_version="1",max_bytes=None,expected_size=None):
    dest=Path(dest); part=Path(str(dest)+".part"); meta=Path(str(part)+".json")
    try:
        return _atomic_retrieve_impl(url,dest,source_object_id,transport,clock,expected_sha256,repository,accession,filename,source_version,license_terms,redistribution_status,code_version,config_version,max_bytes,expected_size)
    except Exception as exc:
        if getattr(exc,"code",None)!="INTERRUPTED":
            part.unlink(missing_ok=True); meta.unlink(missing_ok=True)
        raise

def _label_gses(cluster):
    values=set()
    for label in cluster.get("source_families",[]):
        values.update(re.findall(r"\bGSE\d+\b",str(label)))
    return sorted(values)

def _request(method,url,kind,rows,study_id,identifier="",provenance=("direct",),stage=1,tracer=False):
    return {"request_id":hashlib.sha256(f"{method} {url}".encode()).hexdigest()[:16],"method":method,"url":url,"host":urlsplit(url).hostname,"kind":kind,"study_id":study_id,"priority_rows":sorted(rows),"identifier":identifier,"identifier_provenance":sorted(set(provenance)),"stage":stage,**({"access_route":"CONTROLLED"} if kind.startswith("ega_") or kind=="dbgap_study_landing" else {}),**({"tracer":True} if tracer else {})}

def build_stage1_plan(reconciliation, historical_receipts=None, verified_links=None):
    """Build a deterministic plan from direct identifiers and explicitly verified repository aliases."""
    clusters={r:c for c in reconciliation.get("clusters",[]) for r in c.get("row_ids",[]) if r in PRIORITY_ROWS}
    verified_by_study={}
    for alias in (verified_links or {}).get("verified_aliases",[]):
        if alias.get("evidence_type")!="REPOSITORY_LINK" or alias.get("alias_type")!="GEO_SERIES": continue
        val=alias.get("identifier") or alias.get("alias_value")
        if re.fullmatch(r"GSE\d+",str(val)): verified_by_study.setdefault(alias.get("study_id"),set()).add(val)

    coverage=[]; request_specs={}
    for row in PRIORITY_ROWS:
        cluster=clusters.get(row,{})
        sid=cluster.get("study_id","UNKNOWN")
        direct=[x for x in cluster.get("identifiers",[]) if not x.get("derived_only")]
        identifiers=[{"kind":x.get("kind"),"value":x.get("fold"),"provenance":"direct"} for x in direct]
        for gse in sorted(verified_by_study.get(sid,set())):
            if not any(i["kind"]=="GSE" and i["value"]==gse for i in identifiers):
                identifiers.append({"kind":"GSE","value":gse,"provenance":["VERIFIED"]})
            else:
                next(i for i in identifiers if i["kind"]=="GSE" and i["value"]==gse)["provenance"]=["direct","VERIFIED"]
        repo_ids=[i for i in identifiers if i["kind"] in {"GSE","EGAS","EGAD","PRJNA","ZENODO","GH_RELEASE","GITHUB_RELEASE","GITHUB_RAW"}]
        labels=[]
        if not repo_ids:
            labels=_label_gses(cluster)
        row_requests=[]
        for ident in repo_ids:
            kind,val,prov=ident["kind"],ident["value"],ident["provenance"]
            provs=prov if isinstance(prov,list) else [prov]
            specs=[]
            if kind=="GSE" and re.fullmatch(r"GSE\d+",str(val)):
                digits=val[3:]; base=f"https://ftp.ncbi.nlm.nih.gov/geo/series/GSE{digits[:-3] or '000'}nnn/{val}/"+"suppl"+"/"
                specs=[("GET",base,"geo_listing"),("GET",base+"filelist.txt","geo_filelist")]
            elif kind=="EGAS" and "direct" in provs:
                specs=[("GET",f"https://ega-archive.org/studies/{val}","ega_study_landing")]
            elif kind=="EGAD" and "direct" in provs:
                specs=[("GET",f"https://ega-archive.org/datasets/{val}","ega_dataset_landing")]
            elif kind=="PRJNA":
                specs=[("GET",f"https://www.ebi.ac.uk/ena/browser/view/{val}","ena_study_landing")]
            elif kind=="ZENODO":
                specs=[("GET",f"https://zenodo.org/api/records/{val}","zenodo_record")]
            for method,url,reqkind in specs:
                key=(method,url)
                spec=request_specs.setdefault(key,{"method":method,"url":url,"kind":reqkind,"study_id":sid,"rows":set(),"identifier":val,"provenance":set()})
                spec["rows"].add(row); spec["provenance"].update(provs)
        if not repo_ids:
            for ident in identifiers:
                if ident["kind"]=="PHS":
                    val=ident["value"]
                    url=f"https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id={val}"
                    key=("GET",url)
                    spec=request_specs.setdefault(key,{"method":"GET","url":url,"kind":"dbgap_study_landing","study_id":sid,"rows":set(),"identifier":val,"provenance":set()})
                    spec["rows"].add(row); spec["provenance"].add("direct")
        coverage.append({"row_id":row,"study_id":sid,"identifiers":sorted(identifiers,key=lambda i:(i["kind"] or "",i["value"] or "")),"excluded_identifiers":[{"value":x,"provenance":"label"} for x in labels if not any(i["kind"]=="GSE" and i["value"]==x for i in identifiers)],"requests":row_requests})

    req=[]
    for spec in sorted(request_specs.values(),key=lambda s:(s["url"],s["method"])):
        item=_request(spec["method"],spec["url"],spec["kind"],spec["rows"],spec["study_id"],spec["identifier"],spec["provenance"])
        req.append(item)
        for row in item["priority_rows"]:
            next(x for x in coverage if x["row_id"]==row)["requests"].append(item["request_id"])
    tracer_candidates=[r for r in req if r["kind"]=="geo_filelist"]
    if tracer_candidates:
        tracer_candidates[0]["tracer"]=True
        tracer_candidates[0]["max_bytes"]=1_000_000
    unresolved=sorted(r["row_id"] for r in coverage if not r["requests"])
    for row in coverage:
        if not row["requests"]:
            row["reason"]=("no repository object identifier; GEO accession appears only in source_family label (POSSIBLE)" if row["excluded_identifiers"] else "no repository object identifier")
    counts={}
    for item in req: counts[item["host"]]=counts.get(item["host"],0)+1
    if len(req)>199: _fail("PLAN_CAP_EXCEEDED","stage-1 plan must leave at least one request for stage 2")
    return {"plan_version":"1","request_cap":REQUEST_CAP,"stage":1,"priority_rows":list(PRIORITY_ROWS),"coverage":coverage,"unresolved_rows":unresolved,"host_allowlist":sorted(HOST_ALLOWLIST),"request_count":len(req),"request_counts_by_host":dict(sorted(counts.items())),"remaining_stage2_budget":REQUEST_CAP-len(req),"requests":req}

class _HrefParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.hrefs=[]
    def handle_starttag(self,tag,attrs):
        if tag.lower()=="a":
            href=dict(attrs).get("href")
            if href is not None: self.hrefs.append(href)

def parse_geo_directory_listing(body,base_url):
    """Return only direct plain filenames linked inside a GEO suppl/ directory."""
    validate_url(base_url)
    base=urlsplit(base_url)
    if not base.path.endswith("/") or base.query or base.fragment: _fail("LISTING_BASE_INVALID","GEO listing URL must be a clean directory URL")
    raw=body.decode("utf-8-sig","replace") if isinstance(body,bytes) else str(body)
    parser=_HrefParser()
    try: parser.feed(raw); parser.close()
    except Exception as exc: _fail("LISTING_HTML_INVALID",f"could not parse GEO directory HTML: {exc}")
    names=set()
    for href in parser.hrefs:
        absolute=urljoin(base_url,href)
        try: validate_url(absolute)
        except VerificationError: continue
        candidate=urlsplit(absolute)
        if candidate.scheme!=base.scheme or candidate.netloc!=base.netloc or candidate.query or candidate.fragment: continue
        if posixpath.dirname(candidate.path)!=base.path.rstrip("/"): continue
        encoded_name=posixpath.basename(candidate.path)
        name=_canonical_listing_name(encoded_name)
        if not name: continue
        names.add(name)
    return sorted(names)

def _canonical_listing_name(value):
    current=str(value)
    for _ in range(8):
        if current in ("",".","..") or ".." in current or any(c in current for c in ("?","#","/","\\")) or any(ord(c)<32 for c in current): return None
        decoded=unquote(current)
        if decoded==current: return current
        current=decoded
    return None

def parse_geo_filelist(body):
    """Summarize GEO's tab-separated archive-member metadata without yielding object URLs."""
    raw=body.decode("utf-8-sig","replace") if isinstance(body,bytes) else str(body)
    try:
        reader=csv.DictReader(raw.splitlines(),delimiter="\t")
        headers=reader.fieldnames or []
        file_column=next((h for h in headers if h and h.strip().lower() in ("#archive/file","supplementary_file","file")),None)
        if not file_column or not any(h and h.strip().lower()=="size" for h in headers):
            _fail("FILELIST_TSV_INVALID","GEO filelist requires a file and size column")
        size_column=next(h for h in headers if h and h.strip().lower()=="size")
        type_column=next((h for h in headers if h and h.strip().lower()=="type"),None)
        groups={}; member_count=0
        for row in reader:
            value=(row.get(file_column) or "").strip()
            if not value: continue
            parts=value.split("/")
            archive=_canonical_listing_name(parts[0])
            if not archive: _fail("FILELIST_NAME_INVALID","archive name has non-canonical or unsafe encoding")
            if any(not _canonical_listing_name(part) for part in parts[1:]): _fail("FILELIST_NAME_INVALID","archive member name has non-canonical or unsafe encoding")
            group=groups.setdefault(archive,{"archive_name":archive,"member_count":0,"declared_member_bytes":0,"types":{}})
            group["member_count"]+=1; member_count+=1
            size=(row.get(size_column) or "").strip()
            if size.isdigit(): group["declared_member_bytes"]+=int(size)
            kind=(row.get(type_column) or "").strip().upper() if type_column else "UNKNOWN"
            group["types"][kind]=group["types"].get(kind,0)+1
    except VerificationError: raise
    except Exception as exc: _fail("FILELIST_TSV_INVALID",f"could not parse GEO filelist TSV: {exc}")
    return {"header":headers,"member_count":member_count,"archive_summaries":[groups[x] for x in sorted(groups)]}

def build_stage2_plan(stage1_saved,remaining_budget):
    if remaining_budget<0: _fail("CAP_EXCEEDED","no remaining request budget")
    requests=[]
    for item in stage1_saved.get("listings",[]):
        base=item.get("base_url","")
        for name in parse_geo_directory_listing(item.get("body",b""),base):
            url=base+name
            try: validate_url(url)
            except VerificationError: continue
            request=_request("HEAD",url,"object_headers",item.get("priority_rows",[]),item.get("study_id","UNKNOWN"),name,("geo_directory_listing",),2)
            request["source_listing_request_id"]=item.get("request_id")
            requests.append(request)
    unique={}
    for r in sorted(requests,key=lambda x:(x["url"],x["method"])): unique.setdefault((r["method"],r["url"]),r)
    ordered=list(unique.values())
    tracer=stage1_saved.get("tracer")
    if tracer: ordered.append(tracer)
    pending=ordered[:remaining_budget]; deferred=ordered[remaining_budget:]
    return {"stage":2,"request_cap":REQUEST_CAP,"request_count":len(pending),"remaining_budget_before_stage2":remaining_budget,"remaining_budget_after_plan":remaining_budget-len(pending),"requests":pending,"left_unrequested":deferred,"left_unrequested_count":len(deferred),"filelist_metadata":stage1_saved.get("filelist_metadata",[]),"filelist_results":stage1_saved.get("filelist_results",[])}


def build_stage2_from_manifest(stage1_plan,manifest,out_dir,coordinator_reported_statuses=None):
    root=Path(out_dir); logs={x.get("request_id"):x for x in manifest.get("requests",[])}
    listings=[]; filelist_metadata=[]; filelist_results=[]; tracer_candidates=[]
    coordinator_reported_statuses=coordinator_reported_statuses or {}
    for req in stage1_plan.get("requests",[]):
        if req.get("kind") not in ("geo_listing","geo_filelist"): continue
        log=logs.get(req["request_id"])
        if not log:
            if req.get("kind")=="geo_filelist": filelist_results.append({"request_id":req["request_id"],"url":req["url"],"http_status":None,"status":"NOT_REQUESTED"})
            continue
        status=log.get("http_status"); error=log.get("error")
        if req.get("kind")=="geo_listing":
            if status!=200 or not log.get("body_file"): continue
            body=(root/log["body_file"]).read_bytes()
            if len(body)!=log.get("byte_count") or hashlib.sha256(body).hexdigest()!=log.get("sha256"): _fail("RESPONSE_HASH_MISMATCH","directory listing body does not match manifest")
            listings.append({"base_url":req["url"],"body":body,"study_id":req.get("study_id"),"priority_rows":req.get("priority_rows",[]),"request_id":req["request_id"]})
            continue
        result={"request_id":req["request_id"],"url":req["url"],"http_status":status,"error":error}
        if error=="HTTP_STATUS_INVALID":
            result["status"]="HTTP_STATUS_INVALID"
            if req["request_id"] in coordinator_reported_statuses:
                result["coordinator_reported_http_status"]=int(coordinator_reported_statuses[req["request_id"]])
        elif status==404:
            result["status"]="NO_RAW_TAR_FILELIST"
        elif status==200 and log.get("body_file"):
            body=(root/log["body_file"]).read_bytes()
            if len(body)!=log.get("byte_count") or hashlib.sha256(body).hexdigest()!=log.get("sha256"): _fail("RESPONSE_HASH_MISMATCH","filelist body does not match manifest")
            summary=parse_geo_filelist(body)
            result["status"]="FILELIST_METADATA_AVAILABLE"
            result["byte_count"]=len(body)
            result["header"]=summary["header"]
            result["member_count"]=summary["member_count"]
            filelist_metadata.append({"request_id":req["request_id"],"study_id":req.get("study_id"),"priority_rows":req.get("priority_rows",[]),**summary})
            tracer_candidates.append((len(body),req,log))
        else:
            result["status"]="UNAVAILABLE"
        filelist_results.append(result)
    if tracer_candidates:
        size,original,log=min(tracer_candidates,key=lambda x:(x[0],x[1]["url"]))
        tracer=_request("GET",original["url"],"geo_filelist",original.get("priority_rows",[]),original.get("study_id","UNKNOWN"),original.get("identifier",""),("stage2_tracer_retry",),2,tracer=True)
        tracer["request_id"]=hashlib.sha256((tracer["request_id"]+"\0stage2-tracer-retry").encode()).hexdigest()[:16]
        tracer["retry_of_request_id"]=original["request_id"]
        tracer["selected_stage1_byte_count"]=size
        tracer["max_bytes"]=1_000_000
    else: tracer=None
    completed_count=len(manifest.get("requests",[]))+sum(1 for x in manifest.get("requests",[]) if x.get("resume_fallback_attempt"))
    before=max(0,int(manifest.get("request_cap",REQUEST_CAP))-completed_count)
    return build_stage2_plan({"listings":listings,"tracer":tracer,"filelist_metadata":filelist_metadata,"filelist_results":filelist_results},before)

def _http_transport(method,url,headers):
    req=urllib.request.Request(url,headers=headers,method=method)
    redirect_handler=_AllowlistRedirectHandler()
    opener=urllib.request.build_opener(redirect_handler)
    try: resp=opener.open(req,timeout=60)
    except urllib.error.HTTPError as e: resp=e
    with resp:
        body=b"" if method=="HEAD" else resp.read()
        final=resp.geturl(); chain=[url,*redirect_handler.hops]
        if chain[-1]!=final: chain.append(final)
        return {"status":resp.status,"headers":dict(resp.headers.items()),"body":body,"final_url":final,"redirect_chain":chain}

def run_fetch_plan(plan,out_dir,transport=None,clock=None,stage=None,sleeper=None):
    if not isinstance(plan,dict) or not isinstance(plan.get("requests"),list): _fail("MALFORMED_PLAN","plan must contain requests")
    transport=transport or (lambda method,url,headers:_http_transport(method,url,headers)); clock=clock or time.time; sleeper=sleeper or time.sleep
    cap=min(int(plan.get("request_cap",REQUEST_CAP)),REQUEST_CAP); out=Path(out_dir)
    manifest_path=out/"MANIFEST.json"
    previous=json.loads(manifest_path.read_text()) if manifest_path.exists() else {"requests":[],"request_count":0}
    prior=previous.get("requests",[]); prior_count=len(prior)+sum(1 for x in prior if x.get("resume_fallback_attempt"))
    seen={(x.get("method"),x.get("requested_url",x.get("url"))) for x in prior}
    selected=[r for r in plan["requests"] if stage is None or int(r.get("stage",plan.get("stage",1)))==int(stage)]
    private_root=Path(".scratch/runtime/A_DAV_05").resolve()
    if any(r.get("kind")=="geo_filelist" and r.get("method")=="GET" for r in selected) and not out.resolve().is_relative_to(private_root):
        _fail("PRIVATE_OUTPUT_REQUIRED","GEO filelists must be saved under .scratch/runtime/A_DAV_05")
    out.mkdir(parents=True,exist_ok=True)
    keys=[(r.get("method"),r.get("url")) for r in selected]
    if len(keys)!=len(set(keys)): _fail("DUPLICATE_REQUEST","duplicate URL+method request in plan")
    prior_by_id={x.get("request_id"):x for x in prior}
    for r,key in zip(selected,keys):
        if key not in seen: continue
        source=prior_by_id.get(r.get("retry_of_request_id"))
        pair=(r.get("retry_of_request_id"),r.get("request_id"),r.get("url"),r.get("method"))
        retry_ok=(pair==KNOWN_DUPLICATE_TRACER_DEVIATION and bool(r.get("tracer")) and r.get("kind")=="geo_filelist" and int(r.get("stage",stage or plan.get("stage",1)))==2 and source is not None and source.get("requested_url")==r.get("url") and source.get("method")=="GET" and source.get("kind")=="geo_filelist" and source.get("http_status")==200 and not any(x.get("retry_of_request_id")==r.get("retry_of_request_id") or x.get("request_id")==r.get("request_id") for x in prior))
        if not retry_ok: _fail("DUPLICATE_REQUEST","duplicate URL+method request in plan or manifest")
    if sum(1 for r in prior if r.get("tracer_receipt") and r["tracer_receipt"].get("partial_full_status")=="FULL_VERIFIED")+sum(bool(r.get("tracer")) for r in selected)>1:
        _fail("TRACER_COUNT_INVALID","at most one tracer is permitted across all stages")
    for r in selected:
        if r.get("method") not in ("GET","HEAD"): _fail("METHOD_NOT_ALLOWED","only GET and HEAD are permitted")
        host=validate_url(r.get("url"))
        if r["method"]=="GET" and r.get("kind") not in ("geo_listing","geo_filelist","zenodo_record","controlled_landing","ega_study_landing","ega_dataset_landing","dbgap_study_landing","ena_study_landing","metadata_api","tracer"):
            _fail("BODY_READ_NOT_ALLOWED","GET bodies are restricted to repository listings, metadata, and the tracer")
        if r.get("tracer") and not (r["method"]=="GET" and r.get("kind")=="geo_filelist"): _fail("TRACER_INVALID","only a GEO series filelist tracer is allowed")
    output=[]; last_start=None; left=list(plan.get("left_unrequested",[])); extra_attempts=0
    for idx,r in enumerate(selected):
        if prior_count+len(output)+extra_attempts>=cap:
            left.extend(x["request_id"] for x in selected[idx:]); break
        host=urlsplit(r["url"]).hostname
        nowsec=_clock_seconds(clock)
        if last_start is not None and nowsec-last_start<MIN_SPACING_SECONDS:
            sleeper(MIN_SPACING_SECONDS-(nowsec-last_start))
            nowsec=_clock_seconds(clock)
            if nowsec-last_start<MIN_SPACING_SECONDS: _fail("REQUEST_SPACING","injected clock did not advance after required wait")
        start=_utc(clock); last_start=nowsec
        retry_attempt=None
        try:
            if r.get("tracer"):
                dest=out/(r["request_id"]+".body")
                try:
                    receipt=atomic_retrieve(r["url"],dest,r["request_id"],lambda u,h:transport("GET",u,h),clock,repository="GEO",filename="filelist.txt",max_bytes=r.get("max_bytes",1_000_000))
                except VerificationError as exc:
                    if exc.code!="RESUME_RESTART_REQUIRED": raise
                    if prior_count+len(output)+extra_attempts+1>=cap: raise VerificationError("CAP_EXCEEDED","resume fallback would exceed the request cap")
                    nowsec=_clock_seconds(clock)
                    if nowsec-last_start<MIN_SPACING_SECONDS:
                        sleeper(MIN_SPACING_SECONDS-(nowsec-last_start)); nowsec=_clock_seconds(clock)
                    if nowsec-last_start<MIN_SPACING_SECONDS: _fail("REQUEST_SPACING","injected clock did not advance before resume fallback")
                    retry_start=_utc(clock); last_start=nowsec; extra_attempts+=1
                    retry_attempt={"start_utc":retry_start,"end_utc":None,"reason":"resume response failed range validation; fresh full GET accounted separately","request_id":r["request_id"]}
                    try:
                        receipt=atomic_retrieve(r["url"],dest,r["request_id"],lambda u,h:transport("GET",u,h),clock,repository="GEO",filename="filelist.txt",max_bytes=r.get("max_bytes",1_000_000))
                    except VerificationError as retry_error:
                        retry_attempt.update({"end_utc":_utc(clock),"error":retry_error.code}); raise
                    retry_attempt.update({"end_utc":_utc(clock),"http_status":receipt["http_status"]})
                else: retry_attempt=None
                raw=dest.read_bytes(); status=receipt["http_status"]; headers=receipt["http_repository_metadata"]["headers"]; final=receipt["http_repository_metadata"]["final_url"]; redirect_chain=receipt["http_repository_metadata"].get("redirect_chain",[]); digest=receipt["complete_sha256"]
            else:
                response=transport(r["method"],r["url"],{}); status=int(response.get("status",0)); headers={str(k):str(v) for k,v in response.get("headers",{}).items()}; final=response.get("final_url",r["url"]); redirect_chain=response.get("redirect_chain",[]); validate_url(final)
                raw=response.get("body",b"") if r["method"]=="GET" else b""
                if isinstance(raw,str): raw=raw.encode()
                dest=out/(r["request_id"]+".body")
                if r["method"]=="GET": dest.write_bytes(raw)
                digest=hashlib.sha256(raw).hexdigest() if r["method"]=="GET" else None
            end=_utc(clock)
            hlow={k.lower():v for k,v in headers.items()}
            sample_accessions=bool(re.search(rb"(?<![A-Za-z0-9])GSM\d+",raw)) if r["method"]=="GET" else False
            output.append({"request_id":r["request_id"],"method":r["method"],"requested_url":r["url"],"host":host,"kind":r.get("kind"),"study_id":r.get("study_id"),"priority_rows":r.get("priority_rows",[]),"stage":r.get("stage",stage or plan.get("stage",1)),"retry_of_request_id":r.get("retry_of_request_id"),"start_utc":start,"end_utc":end,"http_status":status,"final_url":final,"redirect_chain":redirect_chain,"headers":{k:hlow[k] for k in ("content-length","etag","last-modified","content-type") if k in hlow},"byte_count":len(raw) if r["method"]=="GET" else 0,"sha256":digest,"body_file":dest.name if r["method"]=="GET" else None,"privacy_status":"PRIVATE_ONLY" if r["method"]=="GET" else None,"sample_accessions_detected":sample_accessions,"tracer_receipt":receipt if r.get("tracer") else None,"resume_fallback_attempt":retry_attempt if r.get("tracer") else None})
        except VerificationError as exc:
            output.append({"request_id":r["request_id"],"method":r["method"],"requested_url":r["url"],"host":urlsplit(r["url"]).hostname,"kind":r.get("kind"),"study_id":r.get("study_id"),"priority_rows":r.get("priority_rows",[]),"stage":r.get("stage",stage or plan.get("stage",1)),"retry_of_request_id":r.get("retry_of_request_id"),"start_utc":start,"end_utc":_utc(clock),"http_status":None,"final_url":r["url"],"headers":{},"byte_count":0,"sha256":None,"body_file":None,"error":exc.code,"error_detail":str(exc),"resume_fallback_attempt":retry_attempt,"transport_attempt_count":1+(1 if retry_attempt else 0)})
        except urllib.error.URLError as exc:
            if retry_attempt is not None:
                retry_attempt.update({"end_utc":_utc(clock),"error":"TRANSPORT_ERROR","error_detail":str(exc)})
            output.append({"request_id":r["request_id"],"method":r["method"],"requested_url":r["url"],"host":urlsplit(r["url"]).hostname,"kind":r.get("kind"),"study_id":r.get("study_id"),"priority_rows":r.get("priority_rows",[]),"stage":r.get("stage",stage or 1),"retry_of_request_id":r.get("retry_of_request_id"),"start_utc":start,"end_utc":_utc(clock),"http_status":None,"final_url":r["url"],"headers":{},"byte_count":0,"sha256":None,"body_file":None,"error":"TRANSPORT_ERROR","resume_fallback_attempt":retry_attempt,"transport_attempt_count":1+(1 if retry_attempt else 0)})
        except Exception as exc:
            if retry_attempt is not None:
                retry_attempt.update({"end_utc":_utc(clock),"error":"TRANSPORT_ERROR","error_detail":type(exc).__name__})
            output.append({"request_id":r["request_id"],"method":r["method"],"requested_url":r["url"],"host":urlsplit(r["url"]).hostname,"kind":r.get("kind"),"study_id":r.get("study_id"),"priority_rows":r.get("priority_rows",[]),"stage":r.get("stage",stage or 1),"retry_of_request_id":r.get("retry_of_request_id"),"start_utc":start,"end_utc":_utc(clock),"http_status":None,"final_url":r["url"],"headers":{},"byte_count":0,"sha256":None,"body_file":None,"error":"TRANSPORT_ERROR","resume_fallback_attempt":retry_attempt,"transport_attempt_count":1+(1 if retry_attempt else 0)})
    manifest={"manifest_version":"1","request_cap":cap,"request_count":prior_count+len(output)+extra_attempts,"requests":prior+output,"left_unrequested":left,"host_allowlist":sorted(HOST_ALLOWLIST)}
    tmp=manifest_path.with_suffix(".json.part"); tmp.write_text(json.dumps(manifest,sort_keys=True,indent=2)+"\n"); os.replace(tmp,manifest_path)
    return manifest

def build_records(plan,manifest,response_files,schema,historical_receipts=None,reconciliation=None,disclosed_deviations=()):
    requests,logs=_validate_manifest_bindings(plan.get("requests",[]),manifest,disclosed_deviations); records=[]; conflicts=[]
    for rid,log in sorted(logs.items()):
        req=requests.get(rid)
        if not req or log.get("http_status")!=200: continue
        if req.get("kind") in ("controlled_landing","ega_study_landing","ega_dataset_landing","dbgap_study_landing"):
            accession=urlsplit(req["url"]).path.rstrip("/").rsplit("/",1)[-1]
            repository="dbGaP" if req.get("kind")=="dbgap_study_landing" else "EGA"
            if req.get("kind")=="dbgap_study_landing":
                accession=urlsplit(req["url"]).query.split("study_id=",1)[-1]
            records.append(build_source_record({"source_object_id":"CONTROLLED:"+accession,"study_id":req["study_id"],"publication_family_id":"UNKNOWN","repository":repository,"accession":accession,"object_url":None,"access_route":"CONTROLLED","object_type":"public study landing metadata; controlled object not accessed","exact_file_name":"","retrieval_status":"CONTROLLED_PENDING","validation_status":"STRUCTURAL_ONLY","source_locators":[{"kind":"URL","value":req["url"],"page_or_section":"public landing page; no controlled content requested"}],"license_terms":"UNKNOWN","redistribution_status":"CONTROLLED"},schema))
            continue
        if req.get("method")=="HEAD":
            filename=urlsplit(req["url"]).path.rstrip("/").rsplit("/",1)[-1]
            headers={str(k).lower():v for k,v in log.get("headers",{}).items()}
            record={"source_object_id":"OBJ-"+hashlib.sha256((str(req.get("study_id"))+"\0"+req["url"]).encode()).hexdigest()[:20],"study_id":req.get("study_id","UNKNOWN"),"publication_family_id":"UNKNOWN","repository":"GitHub" if "github" in urlsplit(req["url"]).hostname else "UNKNOWN","accession":None,"object_url":req["url"],"access_route":"PUBLIC_DIRECT","object_type":"repository object","exact_file_name":filename,"source_version":None,"last_modified":headers.get("last-modified"),"byte_size":int(headers["content-length"]) if str(headers.get("content-length","")).isdigit() else None,"sha256":None,"hash_scope":"NOT_RETRIEVED","retrieval_status":"LOCATED","validation_status":"STRUCTURAL_ONLY","source_locators":[{"kind":"URL","value":req["url"],"page_or_section":"HEAD response metadata"}],"license_terms":"UNKNOWN","redistribution_status":"UNKNOWN","patient_sample_crosswalk":"UNKNOWN"}
            records.append(build_source_record(record,schema)); continue
        if rid not in response_files: continue
        path=Path(response_files[rid]); body=path.read_bytes()
        if log.get("sha256") and hashlib.sha256(body).hexdigest()!=log["sha256"]: _fail("RESPONSE_HASH_MISMATCH","saved response differs from manifest hash")
        if len(body)!=log.get("byte_count",len(body)): _fail("RESPONSE_SIZE_MISMATCH","saved response differs from manifest byte count")
        text=body.decode("utf-8","replace")
        _scan_text(text)
        if req.get("kind")=="geo_listing":
            for name in parse_geo_directory_listing(body,req["url"]):
                url=req["url"]+name; validate_url(url)
                rec={"source_object_id":"OBJ-"+hashlib.sha256((str(req.get("study_id"))+"\0"+url).encode()).hexdigest()[:20],"study_id":req["study_id"],"publication_family_id":"UNKNOWN","repository":"GEO","accession":None,"object_url":url,"access_route":"PUBLIC_DIRECT","object_type":"GEO series-level supplementary object","exact_file_name":name,"retrieval_status":"LOCATED","validation_status":"STRUCTURAL_ONLY","hash_scope":"NOT_RETRIEVED","sha256":None,"source_locators":[{"kind":"URL","value":req["url"],"page_or_section":f"directory listing href {name}"}],"license_terms":"UNKNOWN","redistribution_status":"UNKNOWN","patient_sample_crosswalk":"UNKNOWN"}
                records.append(build_source_record(rec,schema))
        if req.get("kind")=="zenodo_record":
            data=json.loads(text)
            for f in data.get("files",[]):
                url=f.get("links",{}).get("self")
                if not url: continue
                if f.get("key") not in text or url not in text: _fail("LOCATOR_NOT_CONTAINED","file name or object URL is absent from the cited saved response")
                validate_url(url)
                ridx={"source_object_id":f"{req['study_id']}:{f['key']}","study_id":req["study_id"],"publication_family_id":req["study_id"],"repository":"Zenodo","accession":str(data.get("id")) if data.get("id") is not None else None,"object_url":url,"access_route":"PUBLIC_DIRECT","object_type":"repository object","exact_file_name":f["key"],"retrieval_status":"LOCATED","validation_status":"STRUCTURAL_ONLY","hash_scope":"NOT_RETRIEVED","sha256":None,"byte_size":f.get("size"),"last_modified":None,"source_locators":[{"kind":"URL","value":req["url"],"page_or_section":"files"}],"license_terms":(data.get("metadata",{}).get("license",{}).get("id") if isinstance(data.get("metadata",{}).get("license"),dict) else data.get("metadata",{}).get("license")) or "UNKNOWN","redistribution_status":"UNKNOWN","patient_sample_crosswalk":"UNKNOWN"}
                records.append(build_source_record(ridx,schema))
    if reconciliation:
        dispositions=reconciliation.get("dispositioned_rows",[])
        if dispositions:
            included={r["row_id"] for r in dispositions if r.get("disposition")=="INCLUDED_AS_LEAD" and r.get("row_id")}
        else:
            included={row for c in reconciliation.get("clusters",[]) for row in c.get("row_ids",[])}
        not_attempted=[{"row_id":r,"retrieval_status":"NOT_ATTEMPTED","reason":"included lead outside the 22-row A-DAV-05 priority subset"} for r in sorted(included-set(PRIORITY_ROWS))]
    else: not_attempted=[]
    if historical_receipts:
        known={(r.get("object_url"),r.get("exact_file_name")):r for r in records}
        for hist in historical_receipts:
            for rec in records:
                if rec.get("exact_file_name")==hist.get("filename") and hist.get("url") and rec.get("object_url")!=hist.get("url"):
                    conflicts.append({"source_object_id":rec["source_object_id"],"kind":"historical_url_disagreement","historical_url":hist.get("url"),"current_url":rec.get("object_url"),"evidence":"historical receipt only; not verified"})
    validate_unique_ids(records)
    tsv=render_source_tsv(records)
    return {"records":sorted(records,key=lambda r:r["source_object_id"]),"tsv":tsv,"conflicts":conflicts,"not_attempted":not_attempted,"counts":{"records":len(records),"retrieval_status":{s:sum(r["retrieval_status"]==s for r in records) for s in sorted({r["retrieval_status"] for r in records})}}}

def render_source_tsv(records):
    schema_path=Path(__file__).resolve().parents[2]/"specs/A_DATA_ACQUISITION_VALIDATION/templates/source_object_registry.tsv"
    header=schema_path.read_text(encoding="utf-8").splitlines()[0].split("\t")
    from io import StringIO
    buf=StringIO(); writer=csv.DictWriter(buf,fieldnames=header,delimiter="\t",lineterminator="\n",extrasaction="ignore"); writer.writeheader()
    for r in sorted(records,key=lambda x:x["source_object_id"]):
        row=dict(r); row["source_locators"]=json.dumps(row.get("source_locators",[]),sort_keys=True,separators=(",",":")); writer.writerow({k:"" if row.get(k) is None else row.get(k) for k in header})
    return buf.getvalue()

def _response_body(manifest_row, response_dir):
    name=manifest_row.get("body_file")
    if not name: return None
    path=Path(name)
    if path.name!=str(name): _fail("MALFORMED_MANIFEST","body_file must be a basename")
    body=Path(response_dir).joinpath(path).read_bytes()
    if len(body)!=manifest_row.get("byte_count",len(body)): _fail("RESPONSE_SIZE_MISMATCH","saved body differs from manifest byte count")
    if manifest_row.get("sha256") and hashlib.sha256(body).hexdigest()!=manifest_row["sha256"]: _fail("RESPONSE_HASH_MISMATCH","saved body differs from manifest digest")
    return body

def _validate_manifest_bindings(plan_requests, manifest, disclosed_deviations=()):
    plan_rows=validate_unique_request_ids(plan_requests)
    logs=manifest.get("requests",[])
    ids=[x.get("request_id") for x in logs]
    if len(ids)!=len(set(ids)): _fail("DUPLICATE_REQUEST","duplicate request_id in saved manifest")
    by_id={x["request_id"]:x for x in plan_rows}
    seen={}; deviation_consumed=False
    log_by_id={x.get("request_id"):x for x in logs}
    req_by_id={x.get("request_id"):x for x in plan_rows}
    fixed_old,fixed_new,fixed_url,fixed_method=KNOWN_DUPLICATE_TRACER_DEVIATION
    fixed_ids={fixed_old,fixed_new}
    fixed_logs=[log_by_id.get(x) for x in fixed_ids]
    fixed_reqs=[req_by_id.get(x) for x in fixed_ids]
    if all(fixed_logs) and all(fixed_reqs):
        old=log_by_id[fixed_old]; new=log_by_id[fixed_new]
        old_req=req_by_id[fixed_old]; new_req=req_by_id[fixed_new]
        semantic=(old.get("stage")==1 and new.get("stage")==2
            and old_req.get("stage",1)==1 and new_req.get("stage",2)==2
            and new_req.get("tracer") is True
            and new_req.get("retry_of_request_id")==fixed_old
            and old.get("method")==new.get("method")==fixed_method
            and old.get("requested_url")==new.get("requested_url")==fixed_url
            and old.get("http_status")==new.get("http_status")==200
            and old.get("byte_count")==new.get("byte_count")
            and old.get("sha256") and old.get("sha256")==new.get("sha256"))
        if not semantic: _fail("DUPLICATE_REQUEST","pinned tracer duplicate does not match its historical stage, status, size, digest, and URL semantics")
    elif any(fixed_logs) or any(fixed_reqs):
        _fail("DUPLICATE_REQUEST","pinned tracer deviation requires both historical plan and manifest rows")
    for log in logs:
        rid=log.get("request_id"); req=by_id.get(rid)
        if req is None: _fail("MANIFEST_PLAN_MISMATCH",f"manifest request {rid} has no plan row")
        requested=log.get("requested_url") or log.get("url")
        if log.get("method")!=req.get("method") or requested!=req.get("url"):
            _fail("MANIFEST_PLAN_MISMATCH",f"manifest request {rid} differs from plan method or URL")
        expected_host=urlsplit(req["url"]).hostname
        if log.get("host")!=expected_host: _fail("MANIFEST_PLAN_MISMATCH",f"manifest request {rid} host differs from its requested URL")
        final=log.get("final_url") or requested
        try: validate_url(final)
        except VerificationError: _fail("MANIFEST_PLAN_MISMATCH",f"manifest request {rid} final URL is not allowlisted")
        chain=log.get("redirect_chain")
        hops=[x.get("url") if isinstance(x,dict) else x for x in chain] if isinstance(chain,list) else []
        try:
            for hop in hops: validate_url(hop)
        except VerificationError: _fail("MANIFEST_PLAN_MISMATCH",f"manifest request {rid} redirect chain contains a non-allowlisted URL")
        if hops and (hops[0]!=requested or hops[-1]!=final):
            _fail("MANIFEST_PLAN_MISMATCH",f"manifest request {rid} redirect chain is not bound to requested and final URLs")
        if final!=requested:
            if len(hops)<2 or hops[0]!=requested or hops[-1]!=final:
                _fail("MANIFEST_PLAN_MISMATCH",f"manifest request {rid} final URL lacks a bound redirect chain")
        key=(log.get("method"),requested)
        if key in seen:
            old=seen[key]; pair=(old.get("request_id"),rid,requested,log.get("method"))
            valid=(set(pair[:2])==fixed_ids and pair[2:]==(fixed_url,fixed_method) and req_by_id[fixed_new].get("tracer") is True and all(req_by_id[x].get("kind")=="geo_filelist" for x in fixed_ids) and not deviation_consumed)
            if not valid: _fail("DUPLICATE_REQUEST","duplicate method and URL in saved evidence")
            deviation_consumed=True
        else: seen[key]=dict(log,tracer=req.get("tracer",False),kind=req.get("kind"))
    full_tracers=[x for x in logs if x.get("tracer_receipt") and x["tracer_receipt"].get("partial_full_status")=="FULL_VERIFIED"]
    if len(full_tracers)>1: _fail("TRACER_COUNT_INVALID","saved evidence contains more than one complete tracer")
    return by_id,{x["request_id"]:x for x in logs}

def validate_unique_request_ids(requests):
    if not isinstance(requests,list): _fail("MALFORMED_PLAN","requests must be a list")
    ids=[x.get("request_id") for x in requests if isinstance(x,dict)]
    if len(ids)!=len(requests) or any(not x for x in ids): _fail("MALFORMED_PLAN","request row is malformed")
    if len(ids)!=len(set(ids)): _fail("DUPLICATE_REQUEST","duplicate request_id in plan")
    return requests

def _historical_evidence(root):
    """Read historical receipts as unverified comparison evidence; never promote their hashes."""
    root=Path(root)
    if not root.exists(): return []
    found=[]
    def walk(value,receipt,inherited_url=None):
        if isinstance(value,dict):
            lower={str(k).lower():v for k,v in value.items()}
            url=next((lower[k] for k in ("url","object_url","download_url","exact_url","resolved_url") if isinstance(lower.get(k),str)),inherited_url)
            filename=next((lower[k] for k in ("filename","file_name","exact_file_name","exact_filename","object_name") if isinstance(lower.get(k),str)),None)
            headers=lower.get("headers") if isinstance(lower.get("headers"),dict) else {}
            hlow={str(k).lower().replace("_","-"):v for k,v in headers.items()}
            size=next((lower[k] for k in ("byte_size","size","content_length","size_bytes") if isinstance(lower.get(k),(int,str)) and str(lower[k]).isdigit()),None)
            if size is None and str(hlow.get("content-length"," ")).isdigit(): size=hlow["content-length"]
            etag=next((lower[k] for k in ("etag","e_tag") if isinstance(lower.get(k),str)),hlow.get("etag"))
            modified=next((lower[k] for k in ("last_modified","last-modified") if isinstance(lower.get(k),str)),hlow.get("last-modified"))
            size_description=next((lower[k] for k in ("repository_listed_size","declared_size") if isinstance(lower.get(k),str)),None)
            if url and any(x is not None for x in (filename,size,etag,modified,size_description)) or url and any(k in lower for k in ("url","object_url","download_url","exact_url","resolved_url")):
                found.append({"receipt":receipt,"filename":filename,"url":url,"byte_size":int(size) if size is not None else None,"size_description":size_description,"etag":etag,"last_modified":modified})
            for child in value.values():
                if isinstance(child,(dict,list)): walk(child,receipt,url)
        elif isinstance(value,list):
            for child in value: walk(child,receipt,inherited_url)
    for path in sorted(root.glob("*.json")):
        try: data=json.loads(path.read_text(encoding="utf-8"))
        except (OSError,ValueError): continue
        walk(data,path.name)
    return found

def normalize_historical_evidence(found):
    grouped={}
    for item in found:
        locator=item.get("url") or ("filename:"+item["filename"] if item.get("filename") else None)
        if not locator: continue
        group=grouped.setdefault(locator,{"locator":locator,"occurrence_count":0,"receipts":set(),"values":{k:set() for k in ("filename","url","byte_size","etag","last_modified")}})
        group["occurrence_count"]+=1; group["receipts"].add(item.get("receipt"))
        for key in group["values"]:
            if item.get(key) is not None: group["values"][key].add(item[key])
    out=[]
    for locator,group in sorted(grouped.items()):
        row={"locator":locator,"occurrence_count":group["occurrence_count"],"receipts":sorted(x for x in group["receipts"] if x)}
        for key,values in group["values"].items():
            row[key]=next(iter(values)) if len(values)==1 else None
            if len(values)>1: row[key+"_conflicting_values"]=sorted(values,key=str)
        if row.get("filename") is None and row.get("url"):
            row["filename"]=posixpath.basename(urlsplit(row["url"]).path) or None
        descriptions={item.get("size_description") for item in found if (item.get("url") or ("filename:"+item["filename"] if item.get("filename") else None))==locator and item.get("size_description")}
        row["size_descriptions"]=sorted(descriptions)
        out.append(row)
    return out

def _object_inference(filename):
    lower=filename.lower()
    if lower.endswith(".tar") or lower.endswith(".tar.gz"): typ="compressed archive"
    elif lower.endswith(".xlsx"): typ="spreadsheet file"
    elif lower.endswith(".vcf") or ".vcf." in lower: typ="variant call file"
    elif lower.endswith((".csv.gz",".tsv.gz",".txt.gz",".csv",".tsv",".txt")): typ="tabular data file"
    elif lower.endswith(".gz"): typ="compressed data file"
    else: typ="repository supplementary file"
    modality="UNKNOWN"
    if any(token in lower for token in ("rna", "rsem", "salmon", "tpm", "countmatrix", "counts")): modality="transcriptomic data (inferred from filename)"
    return typ,modality

def build_step3_outputs(stage1_plan,stage2_plan,manifest,response_dir,schema,reconciliation,historical_root=None,disclosed_deviations=()):
    """Build deterministic, patient-free source records and reports from saved fetch evidence."""
    if not isinstance(manifest,dict) or not isinstance(manifest.get("requests"),list): _fail("MALFORMED_MANIFEST","manifest must contain request rows")
    plan_requests=list(stage1_plan.get("requests",[]))+list(stage2_plan.get("requests",[]))
    requests={r["request_id"]:r for r in validate_unique_request_ids(plan_requests)}
    # Correct only the documented C-1 send-loop defect, by request ID and the URL-derived host.
    normalized_manifest=dict(manifest); normalized_rows=[]
    for raw in manifest["requests"]:
        row=dict(raw); planned=requests.get(row.get("request_id")); requested=row.get("requested_url") or (planned or {}).get("url")
        actual_host=urlsplit(requested).hostname if requested else None
        if row.get("request_id") in KNOWN_C1_STALE_HOST_REQUEST_IDS and planned and requested==planned.get("url"):
            row["host"]=actual_host
        normalized_rows.append(row)
    normalized_manifest["requests"]=normalized_rows
    requests,logs=_validate_manifest_bindings(plan_requests,normalized_manifest,disclosed_deviations)
    tracer_urls={r.get("url") for r in stage2_plan.get("requests",[]) if r.get("tracer")}
    manifest=normalized_manifest
    records=[]; retrieval_receipts={}; landing_evidence=[]; private_metadata=[]
    def locator(url,section): return [{"kind":"URL","value":url,"page_or_section":section,"accessed_utc":None}]
    def append_record(data):
        record=build_source_record(data,schema); validate_source_record(record,schema); records.append(record); return record
    for req in sorted(requests.values(),key=lambda x:(int(x.get("stage",1)),x.get("request_id",""))):
        log=logs.get(req["request_id"])
        if not log: continue
        kind=req.get("kind"); url=req.get("url") or log.get("requested_url")
        status=log.get("http_status")
        if kind in ("ega_study_landing","ega_dataset_landing","controlled_landing","dbgap_study_landing"):
            if not url: continue
            accession=urlsplit(url).path.rstrip("/").rsplit("/",1)[-1]
            body=_response_body(log,response_dir) if status==200 else None
            title_pattern=rb"(?is)<title[^>]*>\s*[^<\s][^<]*</"+b"title>"
            informative=bool(body and accession.encode("ascii") in body and re.search(title_pattern,body))
            route="CONTROLLED" if status==200 and informative else "UNKNOWN"
            append_record({"source_object_id":"LANDING:"+accession,"study_id":req.get("study_id","UNKNOWN"),"publication_family_id":"UNKNOWN","repository":"EGA","accession":accession,"object_url":None,"access_route":route,"object_type":"public repository landing evidence; no controlled content accessed","exact_file_name":"","retrieval_status":"CONTROLLED_PENDING" if route=="CONTROLLED" else ("UNAVAILABLE" if status!=200 else "NOT_ATTEMPTED"),"validation_status":"STRUCTURAL_ONLY" if route=="CONTROLLED" else "NOT_VALIDATED","source_locators":locator(url,"public landing response accession and HTML title"),"license_terms":"UNKNOWN","redistribution_status":"CONTROLLED" if route=="CONTROLLED" else "UNCLEAR","patient_sample_crosswalk":"UNKNOWN","notes":"Public landing response contains the requested accession and an HTML title; public landing metadata only, controlled content was not requested." if route=="CONTROLLED" else "Landing response was missing or uninformative; route is UNKNOWN."})
            continue
        if kind=="ena_study_landing":
            body=_response_body(log,response_dir) if status==200 else None
            accession=urlsplit(url).path.rstrip("/").rsplit("/",1)[-1]
            accession_present=bool(body and accession.encode("ascii") in body)
            landing_evidence.append({"study_id":req.get("study_id"),"repository":"ENA","accession":accession,"landing_url":url,"final_url":log.get("final_url"),"http_status":status,"saved_response_request_id":req["request_id"],"requested_accession_present_in_response":accession_present,"evidence_status":"PUBLIC_LANDING_RESPONSE" if accession_present else "UNKNOWN","reason":None if accession_present else "saved 200 response did not contain the requested PRJNA accession"})
            continue
        if req.get("method")=="HEAD" and status==200:
            # The atomic tracer re-retrieves the same object whose HEAD metadata is in stage 2.
            # Emit one versioned source object for that URL, with RETRIEVED replacing LOCATED.
            if url in tracer_urls: continue
            filename=urlsplit(url).path.rstrip("/").rsplit("/",1)[-1]
            headers={str(k).lower():v for k,v in log.get("headers",{}).items()}
            size=int(headers["content-length"]) if str(headers.get("content-length"," ")).isdigit() else None
            typ,modality=_object_inference(filename)
            notes=f"INFERENCE: object_type={typ}; modality={modality}; measurement_unit=UNKNOWN, inferred only from filename."
            if re.search(r"(?i)(clinical|sample[_ -]?name[_ -]?key|sample[_ -]?key)",filename): notes+=" Patient-level clinical/sample object; do not retrieve without separate private-storage authorization."
            if filename.lower().endswith(".tar"):
                # Only aggregate private filelist metadata is retained; member names are never emitted.
                candidates=[m for m in stage2_plan.get("filelist_metadata",[]) if m.get("study_id")==req.get("study_id")]
                if candidates:
                    summary=candidates[0]
                    archive=next((x for x in summary.get("archive_summaries",[]) if x.get("archive_name")==filename),None)
                    if archive:
                        private_metadata.append({"study_id":req.get("study_id"),"archive_file_name":filename,"member_count":archive.get("member_count"),"declared_member_bytes":archive.get("declared_member_bytes")})
                    notes+=" Private filelist aggregate metadata is retained only in runtime scratch; member names withheld."
            append_record({"source_object_id":"OBJ-"+hashlib.sha256((req.get("study_id","")+"\0"+url).encode()).hexdigest()[:20],"study_id":req.get("study_id","UNKNOWN"),"publication_family_id":"UNKNOWN","repository":"GEO","accession":None,"object_url":url,"access_route":"PUBLIC_DIRECT","object_type":typ,"exact_file_name":filename,"source_version":headers.get("etag"),"last_modified":headers.get("last-modified"),"byte_size":size,"sha256":None,"hash_scope":"NOT_RETRIEVED","retrieval_status":"LOCATED","validation_status":"STRUCTURAL_ONLY","source_locators":locator(url,"saved HTTP HEAD response headers"),"license_terms":"UNKNOWN","redistribution_status":"UNCLEAR","patient_sample_crosswalk":"UNKNOWN","modality":modality,"measurement_unit":"UNKNOWN","notes":notes})
            continue
        if req.get("tracer") and status==200 and log.get("tracer_receipt"):
            receipt=dict(log["tracer_receipt"]); validate_retrieval_receipt(receipt)
            if receipt.get("exact_url_or_access_route")!=url or receipt.get("http_repository_metadata",{}).get("final_url")!=log.get("final_url",url) or log.get("requested_url")!=req.get("url") or req.get("request_id")!=log.get("request_id"):
                _fail("TRACER_PROVENANCE_MISMATCH","tracer receipt URL, final URL, or request identity differs from plan and manifest")
            metadata=receipt["http_repository_metadata"]
            receipt_hops=[hop.get("url") if isinstance(hop,dict) else hop for hop in metadata.get("redirect_chain",[])]
            manifest_hops=[hop.get("url") if isinstance(hop,dict) else hop for hop in log.get("redirect_chain",[])]
            if (receipt["source_object_id"]!=req["request_id"]
                or metadata["status"]!=log.get("http_status")
                or ("http_status" in receipt and receipt["http_status"]!=log.get("http_status"))
                or _normalized_headers(metadata["headers"])!=_normalized_headers(log.get("headers",{}))
                or receipt_hops!=manifest_hops):
                _fail("TRACER_PROVENANCE_MISMATCH","tracer receipt identity or HTTP evidence differs from plan and manifest")
            filename=urlsplit(url).path.rsplit("/",1)[-1]
            body=_response_body(log,response_dir)
            body_digest=hashlib.sha256(body).hexdigest()
            if receipt.get("byte_size")!=len(body) or receipt.get("complete_sha256")!=body_digest or log.get("byte_count")!=len(body) or log.get("sha256")!=body_digest:
                _fail("TRACER_BODY_MISMATCH","tracer receipt, manifest row, and saved body size/digest must agree")
            head_log=next((x for x in manifest["requests"] if x.get("method")=="HEAD" and x.get("requested_url")==url and x.get("http_status")==200),{})
            head_headers={str(k).lower():v for k,v in head_log.get("headers",{}).items()}
            rec=append_record({"source_object_id":"OBJ-"+hashlib.sha256((req.get("study_id","")+"\0"+url).encode()).hexdigest()[:20],"study_id":req.get("study_id","UNKNOWN"),"publication_family_id":"UNKNOWN","repository":"GEO","accession":None,"object_url":url,"access_route":"PUBLIC_DIRECT","object_type":"tabular metadata index","exact_file_name":filename,"source_version":head_headers.get("etag"),"last_modified":head_headers.get("last-modified") or log.get("headers",{}).get("last-modified"),"retrieval_utc":receipt["retrieval_utc"],"byte_size":receipt["byte_size"],"sha256":receipt["complete_sha256"],"hash_scope":"FULL_OBJECT","compression":"UNKNOWN","retrieval_status":"RETRIEVED","validation_status":"STRUCTURAL_ONLY","source_locators":locator(url,"saved atomic tracer receipt and matching HEAD metadata"),"license_terms":"UNKNOWN","redistribution_status":"UNCLEAR","patient_sample_crosswalk":"UNKNOWN","modality":"UNKNOWN","measurement_unit":"UNKNOWN","notes":"INFERENCE: filelist.txt is series-level repository metadata. Raw body is PRIVATE_ONLY because sample accessions are present; the record contains no sample identifiers."})
            receipt["source_object_id"]=rec["source_object_id"]
            retrieval_receipts[rec["source_object_id"]]=receipt
    # De-duplicate private aggregate entries while preserving deterministic ordering.
    private_metadata=sorted({(x["study_id"],x["archive_file_name"]):x for x in private_metadata}.values(),key=lambda x:(x["study_id"],x["archive_file_name"]))
    records=sorted(records,key=lambda r:r["source_object_id"]); validate_unique_ids(records)
    historical_root=Path(historical_root) if historical_root else Path(__file__).resolve().parents[2].parents[1]/"outputs/study-clearance-20261002/next-wave"
    historical_occurrences=_historical_evidence(historical_root); historical=normalize_historical_evidence(historical_occurrences); comparisons=[]
    for rec in records:
        if not rec.get("object_url"): continue
        for old in historical:
            if old.get("filename")!=rec.get("exact_file_name") and old.get("url")!=rec.get("object_url"): continue
            observed={"filename":rec.get("exact_file_name"),"url":rec.get("object_url"),"byte_size":rec.get("byte_size"),"etag":rec.get("source_version"),"last_modified":rec.get("last_modified")}
            compared=[k for k in ("filename","url","byte_size","etag","last_modified") if old.get(k) is not None and observed.get(k) is not None]
            mismatches=[k for k in compared if old[k]!=observed[k]]
            if any(k.endswith("conflicting_values") for k in old): mismatches.extend(k[:-17] for k in old if k.endswith("conflicting_values"))
            comparisons.append({"source_object_id":rec["source_object_id"],"historical_locator":old["locator"],"historical_receipts":old["receipts"],"historical_occurrence_count":old["occurrence_count"],"result":"VERSION_DRIFT" if mismatches and any(k in mismatches for k in ("byte_size","etag","last_modified","url")) else ("CONFLICT" if mismatches else "AGREEMENT"),"compared_fields":compared,"mismatched_fields":sorted(set(mismatches)),"historical_filename":old.get("filename"),"historical_url":old.get("url"),"historical_byte_size":old.get("byte_size"),"historical_size_descriptions":old.get("size_descriptions",[]),"size_description_comparison":"UNIT_TEXT_NOT_COMPARABLE_TO_HEAD_BYTE_SIZE" if old.get("size_descriptions") and observed.get("byte_size") is not None else "NOT_AVAILABLE","historical_etag":old.get("etag"),"historical_last_modified":old.get("last_modified"),"evidence_note":"Historical receipt is comparison evidence only; its hash is not verified or copied."})
    plan_cov={r["row_id"]:r for r in stage1_plan.get("coverage",[])}
    row_to_records={row:[] for row in PRIORITY_ROWS}
    for rec in records:
        for row in next((q.get("priority_rows",[]) for q in list(stage1_plan.get("requests",[]))+list(stage2_plan.get("requests",[])) if q.get("study_id")==rec.get("study_id")),[]):
            if row in row_to_records: row_to_records[row].append(rec["source_object_id"])
    coverage=[]
    for row in PRIORITY_ROWS:
        item=plan_cov.get(row,{"row_id":row,"requests":[],"identifiers":[]})
        associated=[r for r in records if row in [x for q in list(stage1_plan.get("requests",[]))+list(stage2_plan.get("requests",[])) if q.get("study_id")==r.get("study_id") for x in q.get("priority_rows",[])]]
        if any(r["retrieval_status"] in ("LOCATED","RETRIEVED") for r in associated): state="OBJECTS_LOCATED"; reason=None
        elif any(r["retrieval_status"]=="CONTROLLED_PENDING" for r in associated): state="CONTROLLED_PENDING"; reason="public EGA landing metadata only; controlled content not accessed"
        else: state="NOT_ATTEMPTED"; reason=item.get("reason") or "no repository object identifier"
        coverage.append({"row_id":row,"study_id":item.get("study_id","UNKNOWN"),"identifiers":item.get("identifiers",[]),"final_state":state,"source_object_ids":sorted({r["source_object_id"] for r in associated}),"reason":reason})
    unresolved=sorted(x["row_id"] for x in coverage if x["final_state"]=="NOT_ATTEMPTED")
    dispositions=reconciliation.get("dispositioned_rows",[])
    included={x.get("row_id") for x in dispositions if x.get("disposition")=="INCLUDED_AS_LEAD" and x.get("row_id")} or {r for c in reconciliation.get("clusters",[]) for r in c.get("row_ids",[])}
    not_attempted=[{"row_id":row,"retrieval_status":"NOT_ATTEMPTED","reason":"outside A-DAV-05 priority subset"} for row in sorted(included-set(PRIORITY_ROWS))]
    counts={"records":len(records),"by_access_route":{k:sum(r["access_route"]==k for r in records) for k in sorted({r["access_route"] for r in records})},"by_retrieval_status":{k:sum(r["retrieval_status"]==k for r in records) for k in sorted({r["retrieval_status"] for r in records})}}
    public_requests=[]
    for row in manifest["requests"]:
        planned=requests.get(row.get("request_id"),{})
        requested_url=row.get("requested_url") or planned.get("url")
        safe={k:row.get(k) for k in ("request_id","method","start_utc","end_utc","http_status","final_url","redirect_chain","headers","byte_count","sha256","error","privacy_status") if k in row}
        safe.update({"stage":row.get("stage",planned.get("stage")),"requested_url":requested_url,"host":urlsplit(requested_url).hostname if requested_url else None,"kind":row.get("kind") or planned.get("kind"),"study_id":row.get("study_id") or planned.get("study_id"),"priority_rows":row.get("priority_rows",planned.get("priority_rows",[]))})
        public_requests.append(safe)
    derived_followups=sum(1 for row in manifest["requests"] if row.get("resume_fallback_attempt"))
    public_manifest={"manifest_version":manifest.get("manifest_version"),"request_cap":manifest.get("request_cap"),"request_count":len(manifest["requests"])+derived_followups,"request_rows":len(manifest["requests"]),"transport_followups":derived_followups,"host_allowlist":manifest.get("host_allowlist"),"requests":sorted(public_requests,key=lambda x:(x.get("stage",0),x.get("start_utc", ""),x.get("request_id","")))}
    requests_by_host={host:sum(1 for row in public_requests if row.get("host")==host) for host in sorted({row.get("host") for row in public_requests if row.get("host")})}
    fixed_old,fixed_new,fixed_url,fixed_method=KNOWN_DUPLICATE_TRACER_DEVIATION
    seen_fixed={x.get("request_id"):x for x in manifest["requests"]}
    duplicate_tracer=[]
    old_row,new_row=seen_fixed.get(fixed_old),seen_fixed.get(fixed_new)
    if old_row and new_row and old_row.get("requested_url")==fixed_url and new_row.get("requested_url")==fixed_url and old_row.get("method")==fixed_method and new_row.get("method")==fixed_method:
        duplicate_tracer=[{"kind":"DUPLICATE_TRACER_GET","request_ids":[fixed_old,fixed_new],"url":fixed_url,"method":fixed_method,"disclosed":True,"single_use":True}]
    historical_crosscheck={"occurrence_count":len(historical_occurrences),"unique_locator_count":len(historical),"duplicate_locator_occurrences":len(historical_occurrences)-len(historical),"matched_unique_locators":len(comparisons),"compared_fields":sorted({field for row in comparisons for field in row["compared_fields"]})}
    records_doc={"schema_version":schema.get("properties",{}).get("schema_version",{}).get("default","1.0.0"),"records":records,"retrieval_receipts":retrieval_receipts,"landing_evidence":landing_evidence,"coverage":coverage,"unresolved_rows":unresolved,"not_attempted":not_attempted,"historical_comparisons":comparisons,"historical_crosscheck":historical_crosscheck,"duplicate_tracer_get":duplicate_tracer,"counts":counts}
    tsv=render_source_tsv(records)
    per_study={}
    for rec in records:
        per_study.setdefault(rec["study_id"],[]).append(rec["exact_file_name"] or rec["accession"] or rec["object_type"])
    route_lines="\n".join(f"| {k} | {v} |" for k,v in counts["by_access_route"].items())
    status_lines="\n".join(f"| {k} | {v} |" for k,v in counts["by_retrieval_status"].items())
    coverage_lines="\n".join(f"| {x['row_id']} | {x['final_state']} | {', '.join(i.get('value','') for i in x['identifiers']) or 'none'} | {x['reason'] or ''} |" for x in coverage)
    study_lines="\n".join(f"- {sid}: {', '.join(sorted(set(names)))}" for sid,names in sorted(per_study.items()))
    conflict_lines="\n".join(f"- {x['source_object_id']} vs unique locator in {', '.join(x['historical_receipts'])}: {x['result']} ({', '.join(x['compared_fields']) or 'no common populated fields'} compared; {', '.join(x['mismatched_fields']) or 'values agree'})." for x in comparisons) or "- No matching historical receipt fields were found."
    report=("# A-DAV-05 source-object verification report\n\n"
        "Offline record construction from the saved 58-request manifest and response bodies. This is not analysis readiness or admission evidence.\n\n"
        "## Counts\n\n| Access route | Records |\n|---|---:|\n"+route_lines+"\n\n| Retrieval status | Records |\n|---|---:|\n"+status_lines+"\n\n"
        "## Objects by study\n\n"+study_lines+"\n\n## Priority coverage\n\n| Priority row | Final state | Identifiers | Reason |\n|---|---|---|---|\n"+coverage_lines+"\n\n"
        "## Historical receipt comparisons\n\n"+conflict_lines+f"\nNormalized {historical_crosscheck['unique_locator_count']} unique historical locators from {historical_crosscheck['occurrence_count']} nested occurrences; {historical_crosscheck['duplicate_locator_occurrences']} occurrences were duplicate locators. There is one comparison per matching unique historical locator. Available filename, URL, size, ETag, and Last-Modified values were compared when present on both sides. Historical hashes were not used as verified hashes.\n\n"
        "## Network accounting\n\n58 request rows of 200; stage 1: 34 (26 HTTP 200, 7 HTTP 404 missing filelists, 1 tracer HTTP_STATUS_INVALID for GSE115821); stage 2: 24 (23 HEAD with no body read, one atomic GET tracer). The same GSE198052 filelist URL was GET in stage 1 and re-retrieved atomically as the stage-2 tracer. Requested-URL host counts: "+", ".join(f"{h} {n}" for h,n in requests_by_host.items())+". The sanitized manifest derives its `host` field from `requested_url`; the historical private manifest host field is known-stale for 32 entries due to the send-loop variable reuse described in the receipt. Minimum start-to-start gap: 0.500 s. All requested URLs used allowlisted hosts. The GSE198052 tracer returned 387 bytes with a full SHA-256 and remains PRIVATE_ONLY because the saved filelist includes sample accessions. Both ENA requests returned HTTP 200, but their saved HTML responses did not contain the requested PRJNA accession; those landing evidence entries are recorded as UNKNOWN.\n")
    files={"SOURCE_OBJECT_RECORDS.json":json.dumps(records_doc,sort_keys=True,indent=2,ensure_ascii=False)+"\n","SOURCE_OBJECT_REGISTRY.tsv":tsv,"OBJECT_VERIFICATION_REPORT.md":report,"FETCH_MANIFEST_PUBLIC.json":json.dumps(public_manifest,sort_keys=True,indent=2,ensure_ascii=False)+"\n"}
    for name,text in files.items(): validate_git_bound_text(text)
    return {"records":records,"retrieval_receipts":retrieval_receipts,"landing_evidence":landing_evidence,"coverage":coverage,"unresolved_rows":unresolved,"not_attempted":not_attempted,"historical_conflicts":comparisons,"historical_crosscheck":historical_crosscheck,"duplicate_tracer_get":duplicate_tracer,"private_filelist_aggregates":private_metadata,"counts":counts,"files":files}

def validate_git_bound_text(text):
    try: _scan_text(text)
    except Exception as exc: raise VerificationError(getattr(exc,"code","SECRET_LOCATOR"),str(exc)) from exc
    gsm_ids=re.findall(r"(?i)(?<![A-Z0-9])GSM\d{4,}(?!\d)",text)
    if any(x.upper() not in ("GSM0000001","GSM0000002") for x in gsm_ids): _fail("PRIVACY_GSM","git-bound content contains a non-synthetic GSM accession")
    component=r"[\w.~+-][^/\s?#\"'<>]*"
    posix_path=r"(?<![A-Za-z0-9._:-<])/(?!/)(?:"+component+r"(?:/"+component+r")*)"
    windows_path=r"(?i)(?:[a-z]:[\\/]+|\\\\)"+component+r"(?:[\\/]"+component+r")*"
    path_scan=re.sub(r"(?i)https?://[^\s\"'<>]+","",text)
    if re.search(posix_path,path_scan) or re.search(windows_path,path_scan): _fail("PRIVACY_PATH","git-bound content contains an absolute local path")
    return True

def inventory_receipts(receipts): return sorted(Path(p).name for p in receipts)

def main(argv=None):
    parser=argparse.ArgumentParser(); sub=parser.add_subparsers(dest="command",required=True); fetch=sub.add_parser("fetch"); fetch.add_argument("--plan",required=True); fetch.add_argument("--out",required=True); fetch.add_argument("--stage",type=int); s2=sub.add_parser("stage2-plan"); s2.add_argument("--stage1-plan",required=True); s2.add_argument("--manifest",required=True); s2.add_argument("--out",required=True); s2.add_argument("--coordinator-reported-status",action="append",default=[],metavar="REQUEST_ID=STATUS")
    args=parser.parse_args(argv)
    if args.command=="fetch":
        plan=json.loads(Path(args.plan).read_text()); result=run_fetch_plan(plan,args.out,stage=args.stage); print(json.dumps({"request_count":result["request_count"],"left_unrequested":result["left_unrequested"]},sort_keys=True)); return 0
    if args.command=="stage2-plan":
        overrides={}
        for value in args.coordinator_reported_status:
            try: request_id,status=value.rsplit("=",1); overrides[request_id]=int(status)
            except Exception: _fail("MALFORMED_STATUS_OVERRIDE","coordinator status must be REQUEST_ID=integer")
        plan=build_stage2_from_manifest(json.loads(Path(args.stage1_plan).read_text()),json.loads(Path(args.manifest).read_text()),Path(args.manifest).parent,coordinator_reported_statuses=overrides)
        Path(args.out).write_text(json.dumps(plan,sort_keys=True,indent=2)+"\n"); print(json.dumps({"stage2_requests":len(plan["requests"]),"left_unrequested":plan["left_unrequested_count"]},sort_keys=True)); return 0
    return 2
if __name__=="__main__": raise SystemExit(main())
