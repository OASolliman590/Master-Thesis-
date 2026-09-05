"""Outcome-independent GEO format/feature audit; no scores or associations."""
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import tempfile
import urllib.request
import gzip
from datetime import datetime, timezone

URL = 'https://ftp.ncbi.nlm.nih.gov/geo/series/GSE107nnn/GSE107299/suppl/GSE107299_Matrix_processed_data.tsv.gz'
CAP = 50_000_000
TARGETS = {'HLA-A', 'HLA-B', 'HLA-C', 'B2M', 'TAP1', 'TAP2', 'PSMB8', 'PSMB9'}

def main():
    out = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    size = 0
    with tempfile.TemporaryFile() as cache:
        with urllib.request.urlopen(URL, timeout=60) as response:
            headers = {k: response.headers.get(k) for k in ['Content-Length', 'Last-Modified', 'ETag']}
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > CAP:
                    raise RuntimeError('Explicit 50 MB acquisition cap exceeded')
                digest.update(chunk)
                cache.write(chunk)
        expected = headers.get('Content-Length')
        if expected is not None and size != int(expected):
            raise RuntimeError('Incomplete source transfer')
        cache.seek(0)
        annotations = []
        matched = {}
        malformed = 0
        with gzip.GzipFile(fileobj=cache) as uncompressed:
            with io.TextIOWrapper(uncompressed, encoding='utf-8') as text:
                reader = csv.reader(text, delimiter='\t')
                header = next(reader)
                for row in reader:
                    if len(row) != len(header):
                        malformed += 1
                        continue
                    annotations.append(row[:7])
                    if row[1] in TARGETS:
                        finite = sum(math.isfinite(float(x)) for x in row[7:] if x not in {'NA', 'NaN', ''})
                        matched.setdefault(row[1], []).append({'gene_id': row[0], 'finite_samples': finite, 'sample_count': len(row)-7})
        if malformed:
            raise RuntimeError(f'{malformed} malformed rows')
    with (out / 'GSE107299_gene_annotation.tsv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle, delimiter='\t')
        writer.writerow(header[:7])
        writer.writerows(annotations)
    summary = {'schema_version': 1, 'url': URL, 'retrieved_utc': datetime.now(timezone.utc).isoformat(), 'headers': headers,
               'complete': True, 'compressed_bytes': size, 'full_sha256': digest.hexdigest(), 'feature_rows': len(annotations),
               'sample_columns': len(header)-7, 'sample_ids': header[7:], 'target_coverage': matched,
               'missing_targets': sorted(TARGETS-set(matched)), 'malformed_rows': malformed,
               'scope': 'Full compressed object and all feature rows checked; no scores, patient associations or expression matrix retained.'}
    (out / 'GSE107299_full_expression_audit.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k != 'sample_ids'}, indent=2))

if __name__ == '__main__':
    main()
