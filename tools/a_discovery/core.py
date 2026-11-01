"""Allowlisted metadata transport, adapters and proposal construction."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Protocol

from . import __version__

UNKNOWN = "UNKNOWN"
HOSTS = {"eutils.ncbi.nlm.nih.gov", "www.ncbi.nlm.nih.gov", "ftp.ncbi.nlm.nih.gov", "www.ebi.ac.uk", "www.cbioportal.org", "api.github.com", "raw.githubusercontent.com", "metadata.ega-archive.org"}
ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT / ".scratch" / "runtime"


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_url(url: str) -> None:
    p = urllib.parse.urlsplit(url)
    if p.scheme != "https" or p.hostname not in HOSTS or p.username or p.password or p.fragment or p.port not in (None, 443):
        raise ValueError("URL must use HTTPS and an allowlisted host")


def safe_url(url: str) -> str:
    p = urllib.parse.urlsplit(url)
    query = [(k, v) for k, v in urllib.parse.parse_qsl(p.query, keep_blank_values=True) if k.lower() not in {"email", "api_key"}]
    return urllib.parse.urlunsplit((p.scheme, p.netloc, p.path, urllib.parse.urlencode(query), ""))


class ChallengeError(ValueError):
    """The source returned a challenge or a block page."""


def check_response(data: bytes, address: str) -> None:
    head = data[:10000].decode("utf-8", "replace").lower().lstrip()
    challenge = any(marker in head for marker in ("recaptcha", "captcha", "challenge-platform", "cf-chl-", "waf challenge", "checking your browser", "cloudflare ray id", "access denied", "verify you are human", "just a moment..."))
    html = bool(re.match(r"<(?:!doctype\s+html|html|head|body|title|script|div|h1)(?:\s|>|/)", head))
    directory = urllib.parse.urlsplit(address).hostname == "ftp.ncbi.nlm.nih.gov" and urllib.parse.urlsplit(address).path.endswith("/")
    if challenge or (html and not directory):
        raise ChallengeError("BLOCKED_BY_CHALLENGE: source returned a challenge or unexpected HTML")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


@dataclass
class Client:
    requests: list[dict[str, Any]] = field(default_factory=list)
    last_ncbi: float = 0.0
    timeout: float = 30.0
    blocked: bool = False

    def get(self, url: str) -> bytes:
        validate_url(url)
        if urllib.parse.urlsplit(url).hostname == "eutils.ncbi.nlm.nih.gov":
            extras = {k: v for k, v in (("email", os.getenv("NCBI_EMAIL")), ("api_key", os.getenv("NCBI_API_KEY"))) if v}
            if extras:
                url += ("&" if "?" in url else "?") + urllib.parse.urlencode(extras)
        opener = urllib.request.build_opener(NoRedirect())
        for attempt in range(3):
            delay = float(2 ** attempt)
            if urllib.parse.urlsplit(url).hostname == "eutils.ncbi.nlm.nih.gov":
                time.sleep(max(0.0, 0.34 - (time.monotonic() - self.last_ncbi)))
                self.last_ncbi = time.monotonic()
            when = timestamp()
            try:
                with opener.open(urllib.request.Request(url, headers={"User-Agent": "a-discovery/0.1", "Accept": "application/json,text/plain,*/*"}), timeout=self.timeout) as response:
                    limit = 200 if urllib.parse.urlsplit(url).hostname == "raw.githubusercontent.com" else 10_000_000
                    data: bytes = response.read(limit + 1)
                    if len(data) > limit:
                        self.requests.append({"url": safe_url(url), "timestamp": when, "status": response.status, "sha256": None, "outcome": "RESPONSE_TOO_LARGE"})
                        raise ValueError("metadata response too large")
                    entry = {"url": safe_url(url), "timestamp": when, "status": response.status, "sha256": hashlib.sha256(data).hexdigest()}
                    self.requests.append(entry)
                    try:
                        check_response(data, url)
                    except ChallengeError:
                        entry["outcome"] = "BLOCKED_BY_CHALLENGE"
                        raise
                    return data
            except urllib.error.HTTPError as exc:
                data = exc.read(10000)
                entry = {"url": safe_url(url), "timestamp": when, "status": exc.code, "sha256": hashlib.sha256(data).hexdigest()}
                self.requests.append(entry)
                try:
                    check_response(data, url)
                except ChallengeError:
                    entry["outcome"] = "BLOCKED_BY_CHALLENGE"
                    raise
                if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                    raise ValueError(f"HTTP {exc.code} from {safe_url(url)}") from None
                retry_after = exc.headers.get("Retry-After", "") if exc.headers else ""
                if retry_after:
                    try:
                        delay = max(delay, float(retry_after))
                    except ValueError:
                        try:
                            retry_at = parsedate_to_datetime(retry_after)
                            delay = max(delay, (retry_at - datetime.now(timezone.utc)).total_seconds())
                        except (ValueError, TypeError, OverflowError):
                            raise ValueError("invalid Retry-After; refusing to retry") from None
            except urllib.error.URLError:
                self.requests.append({"url": safe_url(url), "timestamp": when, "status": None, "sha256": None})
                if attempt == 2:
                    raise ValueError(f"request failed: {safe_url(url)}") from None
            time.sleep(delay)
        raise ValueError("request failed")


def url(base: str, **params: str) -> str:
    return base + "?" + urllib.parse.urlencode(params)


@dataclass
class Lead:
    identifier: str
    adapter: str
    query_id: str = UNKNOWN


@dataclass
class Record:
    identifier: str
    adapter: str
    facts: dict[str, Any] = field(default_factory=dict)
    locators: dict[str, str] = field(default_factory=dict)
    objects: list[dict[str, Any]] = field(default_factory=list)
    status: str = "OK"

    def add(self, key: str, value: Any, source: str, field_name: str) -> None:
        if value not in (None, "", [], {}):
            self.facts[key] = value
            self.locators[key] = safe_url(source) + "#" + field_name


class Adapter(Protocol):
    name: str
    def search(self, query: str) -> list[Lead]: ...
    def resolve(self, identifier: str) -> Record: ...


class Base:
    name = "base"
    def __init__(self, client: Client):
        self.client = client
    def get(self, address: str) -> bytes:
        data = self.client.get(address)
        check_response(data, address)
        return data
    def json(self, address: str) -> Any:
        return json.loads(self.get(address))
    def search(self, query: str) -> list[Lead]:
        return []


class NCBI(Base):
    name = "ncbi"
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    def search_db(self, query: str, db: str, page_size: int = 100) -> list[str]:
        ids: list[str] = []
        while True:
            address = url(self.base + "esearch.fcgi", db=db, term=query, retmode="json", retmax=str(page_size), retstart=str(len(ids)))
            data = self.json(address).get("esearchresult", {})
            page = [str(x) for x in data.get("idlist", [])]
            ids.extend(page)
            count = int(data.get("count", len(ids)))
            if len(ids) >= count:
                return ids
            if not page:
                raise ValueError("NCBI search pagination ended before reported count")
    def search(self, query: str) -> list[Lead]:
        return [Lead(x, self.name) for x in self.search_db(query, "gds")]
    def resolve(self, identifier: str) -> Record:
        db = "pubmed" if identifier.lower().startswith("pmid:") else "bioproject" if identifier.startswith("PRJ") else "sra" if identifier.startswith(("SRP", "ERP")) else "gds"
        term = identifier.split(":", 1)[-1]
        ids = self.search_db(term, db)
        rec = Record(identifier, self.name)
        if ids:
            address = url(self.base + "esummary.fcgi", db=db, id=",".join(ids), retmode="json")
            data = self.json(address).get("result", {})
            summary = data.get(ids[0], {})
            for key in ("title", "summary", "accession", "gpl", "n_samples", "pubmedids"):
                rec.add(key, summary.get(key), address, "result/" + key)
            linked: dict[str, list[str]] = {}
            accessions: dict[str, list[str]] = {}
            for target in ("gds", "bioproject", "sra", "pubmed"):
                if target == db:
                    continue
                link = url(self.base + "elink.fcgi", dbfrom=db, db=target, id=ids[0], retmode="json")
                groups = self.json(link).get("linksets", [])
                values = [str(v) for group in groups for block in group.get("linksetdbs", []) for v in block.get("links", [])]
                if values:
                    linked[target] = values
                    rec.add("linked_" + target + "_uids", values, link, "linksets/linksetdbs/links")
                    if target == "pubmed":
                        accessions[target] = values
                    else:
                        summary_url = url(self.base + "esummary.fcgi", db=target, id=",".join(values), retmode="json")
                        summaries = self.json(summary_url).get("result", {})
                        found: set[str] = set()
                        pattern = r"\b(?:GSE|GSM|PRJNA|PRJEB|PRJDB|SRP|ERP|DRP)\d+\b"
                        for uid in values:
                            found.update(re.findall(pattern, json.dumps(summaries.get(uid, {})), re.I))
                        if found:
                            accessions[target] = sorted(found)
                            rec.add("linked_" + target + "_accessions", accessions[target], summary_url, "result")
            if accessions:
                rec.facts["linked_accessions"] = accessions
                rec.locators["linked_accessions"] = link + "#linksets"
            if linked:
                rec.facts["linked_uids"] = linked
                rec.locators["linked_uids"] = rec.locators["linked_" + next(iter(linked)) + "_uids"]
                if "pubmed" in linked:
                    rec.add("linked_pmids", linked["pubmed"], link, "linksets/linksetdbs/links")
        return rec


class GEO(Base):
    name = "geo"
    def search(self, query: str) -> list[Lead]:
        return NCBI(self.client).search(query)
    def resolve(self, identifier: str) -> Record:
        address = url("https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi", acc=identifier, targ="self", form="text", view="brief")
        text = self.get(address).decode("utf-8", "replace")
        rec = Record(identifier, self.name)
        # Only series-level fields are emitted; sample records never enter packets.
        for line in text.splitlines():
            m = re.match(r"!Series_(title|summary|overall_design|platform_id|sample_id|pubmed_id|supplementary_file|type)\s*=\s*(.*)", line)
            if m and m.group(1) != "sample_id":
                key, value = m.groups()
                if key in {"supplementary_file", "platform_id", "pubmed_id"}:
                    rec.facts.setdefault(key, []).append(value)
                    rec.locators[key] = address + "#Series_" + key
                else:
                    rec.add(key, value, address, "Series_" + key)
        count = sum(1 for line in text.splitlines() if line.startswith("!Series_sample_id"))
        if count:
            rec.add("sample_count", count, address, "Series_sample_id")
        sample_address = url("https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi", acc=identifier, targ="gsm", form="text", view="brief")
        sample_text = self.get(sample_address).decode("utf-8", "replace")
        counts: dict[str, dict[str, int]] = {}
        for line in sample_text.splitlines():
            m = re.match(r"!Sample_characteristics_ch\d+\s*=\s*([^:]+):\s*(.*)", line)
            if not m:
                continue
            key, value = m.group(1).strip(), m.group(2).strip()
            if re.search(r"patient|subject|sample|identifier|(^|\W)id($|\W)", key, re.I):
                continue
            counts.setdefault(key, {})[value] = counts.setdefault(key, {}).get(value, 0) + 1
        # Suppress unique free-text values, which may be patient identifiers.
        safe_categories = {"cr", "pr", "sd", "pd", "responder", "non-responder", "response", "no response", "yes", "no"}
        counts = {key: {value: n for value, n in values.items() if n > 1 or value.lower() in safe_categories} for key, values in counts.items()}
        counts = {key: values for key, values in counts.items() if values}
        rec.add("characteristic_counts", counts, sample_address, "Sample_characteristics")
        for source in rec.facts.get("supplementary_file", []):
            parsed = urllib.parse.urlsplit(source)
            if parsed.hostname != "ftp.ncbi.nlm.nih.gov" or not parsed.path.startswith("/geo/"):
                continue
            listing = "https://ftp.ncbi.nlm.nih.gov" + parsed.path.rsplit("/", 1)[0] + "/"
            html = self.get(listing).decode("utf-8", "replace")
            for match in re.finditer(r'<a href="([^"/]+)">[^<]*</a>[^\n]*?\s(\d+(?:\.\d+)?[KMGT]?)\s*(?:\n|$)', html, re.I):
                name, size_display = match.groups()
                if name in (".", "..") or not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
                    continue
                rec.objects.append({"file": name, "url": listing + name, "size": int(size_display) if size_display.isdigit() else None, "size_display": size_display, "published_hash": None, "hash_type": None, "version": "GEO listing", "source_locator": listing})
        return rec


class ENA(Base):
    name = "ena"
    base = "https://www.ebi.ac.uk/ena/portal/api/"
    fields = "run_accession,sample_accession,library_strategy,library_layout,instrument_model,fastq_bytes,fastq_md5,fastq_ftp"
    def search(self, query: str) -> list[Lead]:
        address = url(self.base + "search", result="study", query=query, fields="study_accession", format="json", limit="100")
        return [Lead(str(x["study_accession"]), self.name) for x in self.json(address) if x.get("study_accession")]
    def runs(self, identifier: str) -> tuple[list[dict[str, str]], str]:
        address = url(self.base + "filereport", accession=identifier, result="read_run", fields=self.fields, format="tsv")
        rows = list(csv.DictReader(io.StringIO(self.get(address).decode("utf-8")), delimiter="\t"))
        return rows, address
    def resolve(self, identifier: str) -> Record:
        rows, address = self.runs(identifier)
        rec = Record(identifier, self.name)
        rec.add("run_count", len(rows), address, "run_accession")
        rec.add("library_strategies", sorted({r.get("library_strategy", "") for r in rows} - {""}), address, "library_strategy")
        for row in rows:
            paths = row.get("fastq_ftp", "").split(";") if row.get("fastq_ftp") else []
            sizes = row.get("fastq_bytes", "").split(";") if row.get("fastq_bytes") else []
            md5s = row.get("fastq_md5", "").split(";") if row.get("fastq_md5") else []
            if len(paths) != len(sizes) or len(paths) != len(md5s):
                continue
            for path, size, digest in zip(paths, sizes, md5s):
                if size.isdigit() and re.fullmatch(r"[a-fA-F0-9]{32}", digest):
                    rec.objects.append({"file": path.rsplit("/", 1)[-1], "url": "https://" + path, "size": int(size), "published_hash": digest.lower(), "published_md5": digest.lower(), "hash_type": "md5", "version": identifier, "source_locator": address + "#fastq_md5"})
        return rec


class CBioPortal(Base):
    name = "cbioportal"
    base = "https://www.cbioportal.org/api/"
    def search(self, query: str) -> list[Lead]:
        address = self.base + "studies?projection=SUMMARY&pageSize=10000"
        return [Lead("cbioportal:" + str(x["studyId"]), self.name) for x in self.json(address) if query.lower() in (str(x.get("name", "")) + " " + str(x.get("studyId", ""))).lower()]
    def resolve(self, identifier: str) -> Record:
        study = identifier.split(":", 1)[-1]
        if not re.fullmatch(r"[A-Za-z0-9_-]+", study):
            raise ValueError("invalid study identifier")
        rec = Record(identifier, self.name)
        address = self.base + "studies/" + study
        data = self.json(address)
        for key in ("name", "description", "cancerTypeId", "pmid", "allSampleCount", "patientCount"):
            rec.add(key, data.get(key), address, key)
        address = self.base + "studies/" + study + "/clinical-attributes"
        clinical = self.json(address)
        rec.add("clinical_attributes", [x["clinicalAttributeId"] for x in clinical if "clinicalAttributeId" in x], address, "clinicalAttributeId")
        address = self.base + "studies/" + study + "/molecular-profiles"
        profiles = self.json(address)
        rec.add("molecular_profiles", [{"id": x.get("molecularProfileId"), "datatype": x.get("datatype", UNKNOWN), "units": x.get("description", UNKNOWN), "name": x.get("name", UNKNOWN), "molecular_alteration_type": x.get("molecularAlterationType", UNKNOWN)} for x in profiles if "molecularProfileId" in x], address, "molecularProfileId,datatype,description,name")
        commit_url = "https://api.github.com/repos/cBioPortal/datahub/commits/HEAD"
        commit = str(self.json(commit_url).get("sha", ""))
        if re.fullmatch(r"[0-9a-f]{40}", commit):
            rec.add("datahub_commit", commit, commit_url, "sha")
            listing = "https://api.github.com/repos/cBioPortal/datahub/contents/public/" + study + "?ref=" + commit
            entries = self.json(listing)
            rec.add("datahub_file_names", [x.get("name") for x in entries if x.get("type") == "file" and x.get("name")], listing, "name")
            for entry in entries:
                name = entry.get("name", "")
                size = entry.get("size")
                if entry.get("type") != "file" or not re.fullmatch(r"data_[A-Za-z0-9_.-]+", name) or type(size) is not int or not 120 <= size <= 200:
                    continue
                pointer_url = f"https://raw.githubusercontent.com/cBioPortal/datahub/{commit}/public/{study}/{name}"
                pointer = self.get(pointer_url).decode("utf-8", "replace")
                match = re.fullmatch(r"version https://git-lfs.github.com/spec/v1\r?\noid sha256:([0-9a-f]{64})\r?\nsize (\d+)\r?\n?", pointer)
                if match:
                    rec.objects.append({"file": name, "url": f"https://media.githubusercontent.com/media/cBioPortal/datahub/{commit}/public/{study}/{name}", "size": int(match.group(2)), "published_hash": match.group(1), "hash_type": "sha256", "version": commit, "source_locator": pointer_url})
        return rec


class BioStudies(Base):
    name = "biostudies"
    base = "https://www.ebi.ac.uk/biostudies/api/v1/"
    def search(self, query: str) -> list[Lead]:
        address = url(self.base + "search", query=query, pageSize="100")
        return [Lead(str(x["accession"]), self.name) for x in self.json(address).get("hits", []) if x.get("accession")]
    def resolve(self, identifier: str) -> Record:
        address = self.base + "studies/" + identifier
        data = self.json(address)
        rec = Record(identifier, self.name)
        rec.add("title", data.get("title"), address, "title")
        rec.add("file_names", [x.get("path") for x in data.get("section", {}).get("files", []) if x.get("path")], address, "section/files/path")
        return rec


class EGA(Base):
    name = "ega"
    def search(self, query: str) -> list[Lead]:
        leads: list[Lead] = []
        for kind, key in (("studies", "studyId"), ("datasets", "datasetId")):
            address = url("https://metadata.ega-archive.org/" + kind, query=query)
            data = self.json(address)
            entries = data.get("response", {}).get("result", [])
            leads.extend(Lead(str(x[key]), self.name) for x in entries if x.get(key))
        return leads
    def resolve(self, identifier: str) -> Record:
        if not re.fullmatch(r"EGA[SD]\d+", identifier, re.I):
            raise ValueError("invalid EGA accession")
        kind = "datasets" if identifier.upper().startswith("EGAD") else "studies"
        address = "https://metadata.ega-archive.org/" + kind + "/" + identifier
        data = self.json(address)
        results = data.get("response", {}).get("result", [])
        if results:
            data = results[0]
        rec = Record(identifier, self.name)
        rec.add("access", "CONTROLLED", address, "access")
        rec.add("title", data.get("title"), address, "title")
        rec.add("datasets", data.get("datasets"), address, "datasets")
        return rec


class DbGaP(Base):
    name = "dbgap"
    def resolve(self, identifier: str) -> Record:
        if not re.fullmatch(r"phs\d+(?:\.v\d+\.p\d+)?", identifier, re.I):
            raise ValueError("invalid dbGaP accession")
        rec = Record(identifier, self.name)
        rec.add("access", "CONTROLLED", "https://www.ncbi.nlm.nih.gov/gap/", "access-policy")
        ncbi = NCBI(self.client)
        ids = ncbi.search_db(identifier, "gap")
        if ids:
            address = url(ncbi.base + "esummary.fcgi", db="gap", id=ids[0], retmode="json")
            summary = self.json(address).get("result", {}).get(ids[0], {})
            for key in ("title", "accession", "description"):
                rec.add(key, summary.get(key), address, "result/" + key)
        return rec


class EuropePMC(Base):
    name = "europepmc"
    base = "https://www.ebi.ac.uk/europepmc/webservices/rest/"
    def search(self, query: str) -> list[Lead]:
        address = url(self.base + "search", query=query, format="json", pageSize="100")
        return [Lead("pmid:" + str(x["pmid"]), self.name) for x in self.json(address).get("resultList", {}).get("result", []) if x.get("pmid")]
    def resolve(self, identifier: str) -> Record:
        address = url(self.base + "search", query="EXT_ID:" + identifier.split(":")[-1] + " AND SRC:MED", format="json", resultType="core")
        results = self.json(address).get("resultList", {}).get("result", [])
        rec = Record(identifier, self.name)
        if results:
            for key in ("title", "journalTitle", "isOpenAccess", "pmcid", "hasSuppl"):
                rec.add(key, results[0].get(key), address, key)
        return rec


ADAPTERS = {x.name: x for x in (NCBI, GEO, ENA, CBioPortal, BioStudies, EGA, DbGaP, EuropePMC)}


def adapter_for(identifier: str, client: Client) -> Adapter:
    ident = identifier.upper()
    name = "geo" if ident.startswith(("GSE", "GSM")) else "ena" if ident.startswith(("PRJ", "SRP", "ERP")) else "biostudies" if ident.startswith("E-MTAB-") else "ega" if ident.startswith(("EGAS", "EGAD")) else "dbgap" if ident.startswith("PHS") else "cbioportal" if identifier.lower().startswith("cbioportal:") else "europepmc" if identifier.lower().startswith("pmid:") else ""
    if not name:
        raise ValueError("unsupported identifier")
    return ADAPTERS[name](client)


def readiness(record: Record) -> tuple[str, str]:
    f = record.facts
    if f.get("set_aside") is True:
        return "X", "Explicitly set aside"
    if f.get("processed_matrix_public") is True and f.get("response_labels_repository") is True:
        return "R1", "Public processed matrix and per-sample response labels in repository"
    if f.get("processed_matrix_public") is True and f.get("response_labels_paper") is True:
        return "R2", "Public processed matrix with labels in publication"
    if f.get("access") == "CONTROLLED":
        return "R3", "Controlled access"
    if f.get("raw_reads_only") is True:
        return "R3", "Raw reads only"
    return UNKNOWN, "Insufficient evidence to classify readiness"


def drug_tags(text: str) -> list[str]:
    lexicon = json.loads((Path(__file__).parent / "drug_classes.json").read_text(encoding="utf-8"))
    def matches(group: str) -> bool:
        return any(re.search(r"(?<![\w])" + re.escape(term) + r"(?![\w])", text, re.I) for terms in lexicon[group].values() for term in terms)
    return ["COMBINATION"] if matches("ici") and matches("non_ici") else []


def resolve_lead(adapter: Adapter, identifier: str, client: Client) -> Record:
    try:
        return adapter.resolve(identifier)
    except ChallengeError:
        setattr(client, "blocked", True)
        return Record(identifier, adapter.name, status="BLOCKED_BY_CHALLENGE")


def packet(record: Record, query_ids: list[str], known: dict[str, str] | set[str]) -> dict[str, Any]:
    text = " ".join(str(record.facts.get(k, "")) for k in ("title", "summary", "overall_design", "description", "name"))
    tags = drug_tags(text)
    identifiers = {record.identifier.upper().removeprefix("PMID:")}
    for key in ("linked_pmids", "pubmed_id", "pmid"):
        values = record.facts.get(key, [])
        if isinstance(values, list):
            identifiers.update(str(x).upper().removeprefix("PMID:") for x in values)
        elif isinstance(values, (str, int)):
            identifiers.add(str(values).upper().removeprefix("PMID:"))
    linked_accessions = record.facts.get("linked_accessions", {})
    if isinstance(linked_accessions, dict):
        for values in linked_accessions.values():
            if isinstance(values, list):
                identifiers.update(str(x).upper().removeprefix("PMID:") for x in values)
    overlap: Any = UNKNOWN
    if isinstance(known, dict):
        own = record.identifier.upper().removeprefix("PMID:")
        for accession, family in known.items():
            shared = accession.upper().removeprefix("PMID:")
            if family and shared in identifiers and shared != own:
                tags.append("POSSIBLE_OVERLAP")
                overlap = {"family": family, "shared_identifier": accession}
                break
    facts = [{"field": k, "value": v, "source_locator": record.locators[k]} for k, v in record.facts.items() if k not in {"linked_uids", "linked_accessions"}]
    return {"packet_id": record.identifier, "status": record.status, "lane": "C", "query_ids": query_ids, "candidate_label": record.identifier, "proposed_study_id": UNKNOWN, "publication_family_candidates": record.facts.get("linked_pmids", UNKNOWN), "source_object_candidates": record.objects, "object_inventory": record.objects, "cancer_and_disease_state": UNKNOWN, "treatment_and_timing": UNKNOWN, "endpoint_evidence": UNKNOWN, "modality_and_platform": {"platform": record.facts.get("platform_id", UNKNOWN), "modality": record.facts.get("type", UNKNOWN)}, "identity_evidence": UNKNOWN, "suspected_overlap": overlap, "access_and_redistribution_evidence": record.facts.get("access", UNKNOWN), "verified_facts": facts, "inferences": [], "design_implications": tags, "unknowns": ["cancer_and_disease_state", "treatment_and_timing", "endpoint_evidence", "identity_evidence", "admission"], "source_locators": record.locators, "recommended_next_action": "Review source evidence, field map, fetch plan, V3 and signed worksheet; no admission is implied.", "agent_identity": "tools.a_discovery/" + __version__, "timestamp": timestamp(), "readiness": readiness(record)[0], "readiness_reason": readiness(record)[1]}


def atomic_write(path: Path, data: bytes, exclusive: bool = False) -> None:
    import tempfile
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix="." + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if exclusive:
            os.link(temp, path)
            os.unlink(temp)
        else:
            os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def write_json(path: Path, value: Any, exclusive: bool = False) -> None:
    atomic_write(path, (json.dumps(value, indent=2, ensure_ascii=True) + "\n").encode(), exclusive)


def require_scratch(path: Path) -> None:
    if not path.resolve().is_relative_to(SCRATCH.resolve()):
        raise ValueError("discovery output must be under .scratch/runtime")


def receipt(client: Client, query_hash: str | None = None) -> dict[str, Any]:
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        commit = UNKNOWN
    return {"status": "BLOCKED_BY_CHALLENGE" if getattr(client, "blocked", False) or any(x.get("outcome") == "BLOCKED_BY_CHALLENGE" for x in client.requests) else "OK", "tool_version": __version__, "git_commit": commit, "query_file_sha256": query_hash or UNKNOWN, "requests": client.requests}


def table(headers: list[str], rows: list[list[str]], delimiter: str) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, delimiter=delimiter, lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(rows)
    return stream.getvalue().encode()


def save_packets(out: Path, records: list[tuple[Record, list[str]]], client: Client, query_hash: str | None = None) -> None:
    require_scratch(out)
    queue = ROOT / "specs/A/SOURCE_CANDIDATE_QUEUE.tsv"
    with queue.open(encoding="utf-8", newline="") as f:
        known = {row["source_identifier"]: row["original_study_id"] for row in csv.DictReader(f, delimiter="\t") if row["original_study_id"].strip()}
    rows = []
    for rec, ids in records:
        p = packet(rec, ids, known)
        name = re.sub(r"[^A-Za-z0-9_.-]", "_", rec.identifier)
        write_json(out / "packets" / (name + ".json"), p)
        rows.append([rec.identifier, rec.adapter, ";".join(ids), str(p["modality_and_platform"]), ";".join(p["design_implications"]) or UNKNOWN, str(p["readiness"]), UNKNOWN, UNKNOWN, UNKNOWN])
    headers = ["source_identifier", "identifier_type", "discovery_origin", "reported_modality", "candidate_role", "admission_status", "eligible_patient_n", "original_study_id", "patient_pairing_status"]
    atomic_write(out / "candidates.tsv", table(headers, rows, "\t"))
    result = receipt(client, query_hash)
    if any(rec.status == "BLOCKED_BY_CHALLENGE" for rec, _ in records):
        result["status"] = "BLOCKED_BY_CHALLENGE"
    write_json(out / "receipt.json", result)


def save_fastq(project: str, out: Path, client: Client, strategy: str = "RNA-Seq") -> None:
    require_scratch(out)
    if not re.fullmatch(r"(?:PRJEB|PRJNA|SRP|ERP)\d+", project):
        raise ValueError("invalid project identifier")
    rows, _ = ENA(client).runs(project)
    if not rows:
        raise ValueError("no FASTQ metadata returned")
    totals: dict[str, dict[str, int]] = {}
    for row in rows:
        kind = row.get("library_strategy") or UNKNOWN
        sizes = row.get("fastq_bytes", "").split(";")
        if not all(x.isdigit() for x in sizes):
            raise ValueError("incomplete FASTQ sizes; cannot calculate strategy totals")
        entry = totals.setdefault(kind, {"run_count": 0, "total_bytes": 0})
        entry["run_count"] += 1
        entry["total_bytes"] += sum(int(x) for x in sizes)
    rows = [row for row in rows if row.get("library_strategy", "").casefold() == strategy.casefold()]
    if not rows:
        raise ValueError("no runs for selected strategy")
    headers = ENA.fields.split(",")
    atomic_write(out / "fastq" / (project + ".tsv"), table(headers, [[r.get(h, "") for h in headers] for r in rows], "\t"))
    sheet: list[list[str]] = []
    total = 0
    for r in rows:
        files = r.get("fastq_ftp", "").split(";") if r.get("fastq_ftp") else []
        sizes = r.get("fastq_bytes", "").split(";") if r.get("fastq_bytes") else []
        if len(files) not in (1, 2) or len(sizes) != len(files) or any(not x.isdigit() for x in sizes):
            raise ValueError("incomplete FASTQ metadata; cannot create samplesheet")
        if any(not re.fullmatch(r"[A-Za-z0-9.-]+/[A-Za-z0-9_./-]+", f) or ".." in f.split("/") for f in files):
            raise ValueError("invalid FASTQ locator")
        total += sum(int(x) for x in sizes)
        sheet.append([r.get("run_accession", ""), "https://" + files[0], "https://" + files[1] if len(files) == 2 else "", "auto"])
    atomic_write(out / "samplesheet.nfcore.csv", table(["sample", "fastq_1", "fastq_2", "strandedness"], sheet, ","))
    write_json(out / "fastq" / (project + ".size.json"), {"strategy": strategy, "selected_run_count": len(rows), "total_bytes": total, "per_strategy": totals})
    write_json(out / "receipt.json", receipt(client))


def draft_plan(packet_path: Path, cohort: str, out: Path) -> None:
    if not out.name.endswith(".draft") or not re.fullmatch(r"[A-Za-z0-9_-]+", cohort):
        raise ValueError("draft output must end in .draft and cohort must be a safe identifier")
    data = json.loads(packet_path.read_text(encoding="utf-8"))
    objects = []
    for i, obj in enumerate(data.get("object_inventory", data.get("source_object_candidates", []))):
        address = obj.get("url", "")
        p = urllib.parse.urlsplit(address)
        size = obj.get("size", obj.get("expected_size"))
        if (p.scheme != "https" or p.hostname not in HOSTS | {"media.githubusercontent.com", "ftp.sra.ebi.ac.uk"} or p.username or p.password or not isinstance(size, int) or size <= 0
                or re.search(r"(?:GSM|SAM[NED]|SRR|ERR|DRR)\d+", address, re.I)):
            continue
        if obj.get("hash_type") == "md5" or address.lower().endswith((".fastq.gz", ".fq.gz", ".fastq", ".fq")):
            continue
        digest = obj.get("published_hash") if obj.get("hash_type") == "sha256" else obj.get("expected_sha256")
        item = {"id": "object_" + str(i + 1), "url": address, "version": obj.get("version", UNKNOWN), "expected_size": size, "expected_sha256": digest, "max_bytes": size, "host": p.hostname}
        objects.append(item)
    if not objects or len(objects) > 66:
        raise ValueError("packet has no bounded source objects suitable for a draft")
    plan = {"schema_version": 1, "cohort": cohort, "branch_id": "A_BASELINE_BIO", "request_cap": len(objects) * 3, "max_object_bytes": max(x["max_bytes"] for x in objects), "allowed_hosts": sorted({x["host"] for x in objects}), "objects": objects}
    from tools.a_dav.retrieval import load_plan
    load_plan(plan)
    write_json(out, plan, exclusive=True)
