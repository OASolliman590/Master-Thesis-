"""Retrieve or verify the pinned public TCGA ABSOLUTE table.

Cache verification preserves the original retrieval timestamp and records a
separate verification timestamp. A cached body without a receipt is rejected;
no retrieval time is inferred from filesystem metadata or the current clock.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
from pathlib import Path
import urllib.request


DEFAULT_OUTPUT_DIR = Path(r"E:\Master_Thesis\planning\next_evidence\B_TCGA_cellularity")
DEFAULT_URL = "https://api.gdc.cancer.gov/data/4f277128-f793-4354-a13d-30cc7fe9f6b5"
DEFAULT_SOURCE_PAGE = "https://gdc.cancer.gov/about-data/publications/PanCan-CellOfOrigin"
DEFAULT_SHA256 = "f430a975433d82e0098d7405619d4f12a0c765fcd97e7d63cc9b1de7f2d763cd"
BODY_NAME = "TCGA_mastercalls.abs_tables_JSedit.fixed.txt"
MAX_BYTES = 3_000_000


def utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--source-page", default=DEFAULT_SOURCE_PAGE)
    parser.add_argument("--expected-sha256", default=DEFAULT_SHA256)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    expected = args.expected_sha256.lower()
    if len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected):
        raise ValueError("expected SHA-256 must be 64 lowercase or uppercase hexadecimal characters")

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    body_path = output_dir / BODY_NAME
    receipt_path = output_dir / "retrieval.json"
    downloaded = not body_path.exists()

    if downloaded:
        with urllib.request.urlopen(args.url, timeout=45) as response:
            declared_size = response.headers.get("Content-Length")
            if declared_size and int(declared_size) > MAX_BYTES:
                raise ValueError(f"declared size exceeds cap: {declared_size}")
            body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise ValueError("download cap exceeded")
    else:
        if not receipt_path.exists():
            raise ValueError("cached body exists without retrieval.json; retrieval time is unknown")
        body = body_path.read_bytes()

    digest = hashlib.sha256(body).hexdigest()
    if digest != expected:
        raise ValueError(f"source SHA-256 mismatch: expected {expected}, observed {digest}")

    checked_at = utc_now()
    if downloaded:
        body_path.write_bytes(body)
        receipt = {
            "url": args.url,
            "source_page": args.source_page,
            "bytes": len(body),
            "sha256": digest,
            "retrieved_utc": checked_at,
            "verified_utc": checked_at,
        }
    else:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("sha256") != digest or receipt.get("bytes") != len(body):
            raise ValueError("cached body disagrees with its existing retrieval receipt")
        if receipt.get("url") != args.url:
            raise ValueError("cached receipt URL disagrees with requested URL")
        if not isinstance(receipt.get("retrieved_utc"), str) or not receipt["retrieved_utc"]:
            raise ValueError("cached receipt has no valid retrieved_utc to preserve")
        receipt["verified_utc"] = checked_at

    temporary_receipt = receipt_path.with_suffix(".json.tmp")
    temporary_receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    temporary_receipt.replace(receipt_path)
    print(json.dumps(receipt))
    print(body.decode().splitlines()[:3])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
