from __future__ import annotations

import time
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
import urllib.request

from .errors import ErrorClass, classify_http_exception
from .geo import _geo_series_prefix


def cleanup_stale_part_files(downloads_root: Path, max_age_seconds: int = 3600) -> list[Path]:
    cleaned: list[Path] = []
    now = time.time()
    for path in downloads_root.rglob("*.part"):
        try:
            age = now - path.stat().st_mtime
        except OSError:
            continue
        if age <= max_age_seconds:
            continue
        try:
            path.unlink()
            cleaned.append(path)
        except OSError:
            continue
    return cleaned


def _download_url(url: str, dest: Path) -> tuple[bool, str]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp_dest = dest.with_suffix(dest.suffix + ".part")
    try:
        with urllib.request.urlopen(url, timeout=120) as resp, tmp_dest.open("wb") as fh:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                fh.write(chunk)
        tmp_dest.replace(dest)
        return True, ""
    except HTTPError as exc:
        tmp_dest.unlink(missing_ok=True)
        return False, classify_http_exception(exc).value
    except TimeoutError:
        tmp_dest.unlink(missing_ok=True)
        return False, ErrorClass.NETWORK_TIMEOUT.value
    except URLError as exc:
        tmp_dest.unlink(missing_ok=True)
        reason = str(getattr(exc, "reason", "")).lower()
        if "timed out" in reason:
            return False, ErrorClass.NETWORK_TIMEOUT.value
        return False, ErrorClass.HTTP_OTHER.value
    except Exception:
        tmp_dest.unlink(missing_ok=True)
        return False, ErrorClass.PARSE_ERROR.value


def _download_url_if_missing(url: str, dest: Path) -> tuple[bool, str]:
    if dest.exists() and dest.stat().st_size > 0:
        return True, "already_present"
    return _download_url(url, dest)


def build_planned_downloads(
    cohort_id: str,
    accession: str,
    tokens: Iterable[str],
    cohort_dir: Path,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for token in tokens:
        if token.startswith("GSE"):
            url = (
                "https://ftp.ncbi.nlm.nih.gov/geo/series/"
                f"{_geo_series_prefix(token)}/{token}/soft/{token}_family.soft.gz"
            )
            rows.append(
                {
                    "cohort_id": cohort_id,
                    "accession": accession,
                    "file_kind": "soft",
                    "url": url,
                    "dest_path": str(cohort_dir / f"{token}_family.soft.gz"),
                }
            )
        elif token.startswith(("SRP", "SRX", "SRR", "PRJ")):
            url = f"https://trace.ncbi.nlm.nih.gov/Traces/sra-db-be/runinfo?acc={token}"
            rows.append(
                {
                    "cohort_id": cohort_id,
                    "accession": accession,
                    "file_kind": "runinfo",
                    "url": url,
                    "dest_path": str(cohort_dir / f"{token}_runinfo.csv"),
                }
            )
    return rows
