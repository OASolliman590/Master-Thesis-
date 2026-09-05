"""Regression tests through the CLI; fault injection is at filesystem boundaries."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(os.environ.get('BF1_REVIEW_REPO_ROOT', Path(__file__).resolve().parents[2]))
STAR_HEADER = ('gene_id\tgene_name\tgene_type\tunstranded\tstranded_first\tstranded_second'
               '\ttpm_unstranded\tfpkm_unstranded\tfpkm_uq_unstranded\n')

SOURCE_CHANGE_PROBE = r'''
import io, os, runpy, sys
from pathlib import Path
source = Path(sys.argv[1]).resolve()
original_open = io.open
changed = False
class ReadSnapshot:
    def __init__(self, stream): self.stream, self.complete = stream, False
    def __getattr__(self, name): return getattr(self.stream, name)
    def __enter__(self): return self
    def read(self, size=-1):
        data = self.stream.read(size)
        if size < 0 or data == b'': self.complete = True
        return data
    def __exit__(self, *args):
        global changed
        self.stream.close()
        if self.complete and not changed:
            changed = True
            with original_open(source, 'wb') as stream:
                stream.write(b'cg000001\t0.5\ncg000002\tNA\n')
def open_at_boundary(path, mode='r', *args, **kwargs):
    stream = original_open(path, mode, *args, **kwargs)
    if mode == 'rb' and not isinstance(path, int) and Path(path).resolve() == source:
        return ReadSnapshot(stream)
    return stream
io.open = open_at_boundary
sys.argv = ['tools.b_formats', *sys.argv[2:]]
runpy.run_module('tools.b_formats', run_name='__main__')
'''

OUTPUT_COLLISION_PROBE = r'''
import os, runpy, sys
from pathlib import Path
target = Path(sys.argv[1])
original_fsync = os.fsync
injected = False
def sync_at_boundary(fd):
    global injected
    original_fsync(fd)
    if not injected:
        injected = True
        target.write_bytes(b'competing completed output')
os.fsync = sync_at_boundary
sys.argv = ['tools.b_formats', *sys.argv[2:]]
runpy.run_module('tools.b_formats', run_name='__main__')
'''

class TestReviewRegressions(unittest.TestCase):
    def _star_case(self, content):
        with tempfile.TemporaryDirectory(dir=os.environ.get('BF1_TEST_TMP_ROOT')) as folder:
            source, output = Path(folder) / 'source.tsv', Path(folder) / 'summary.json'
            data = content.encode('utf-8')
            source.write_bytes(data)
            result = subprocess.run([sys.executable, '-m', 'tools.b_formats', 'inspect',
                '--format', 'tcga-star-expression', '--input', str(source),
                '--source-sha256', hashlib.sha256(data).hexdigest(), '--completeness',
                'bounded-prefix', '--output', str(output)], cwd=REPO,
                capture_output=True, text=True, timeout=15)
            return result, json.loads(output.read_text()) if output.exists() else None

    def test_star_summary_structural_absence_is_not_a_missing_count(self):
        for row in ['N_unmapped\t\t\t\t\t\t\t\t\n',
                    'N_invented\t\t\t1\t2\t3\t\t\t\n']:
            with self.subTest(row_kind=row.split('\t')[0]):
                result, summary = self._star_case(STAR_HEADER + row)
                self.assertEqual(result.returncode, 3, result.stderr)
                self.assertIsNone(summary)
        result, summary = self._star_case(STAR_HEADER + 'N_unmapped\t\t\t1\t2\t3\t\t\t\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(summary['format_summary']['summary_structural_missing_count'], 3)
        self.assertEqual(summary['format_summary']['summary_finite_value_count'], 3)

    def test_star_blank_record_reports_its_actual_line(self):
        gene = 'ENSG000001\tTEST\tcoding\t1\t2\t3\t1.0\t2.0\t3.0\n'
        result, summary = self._star_case('# gene-model: GENCODE v36\n' + STAR_HEADER + gene + '\n' + gene)
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertIn('row=4 field=record', result.stderr)
        self.assertIsNone(summary)

    def test_cpc_methylation_requires_data_records(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('BF1_TEST_TMP_ROOT')) as folder:
            root = Path(folder)
            source, output = root / 'source.tsv', root / 'summary.json'
            data = b'CPCG0001_rep1\tCPCG0001_rep1_Dectection_Pval\n'
            source.write_bytes(data)
            result = subprocess.run([sys.executable, '-m', 'tools.b_formats', 'inspect',
                '--format', 'cpc-methylation', '--input', str(source),
                '--source-sha256', hashlib.sha256(data).hexdigest(), '--completeness',
                'bounded-prefix', '--output', str(output)], cwd=REPO,
                capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 3, result.stderr)
            self.assertFalse(output.exists())

    def test_competing_output_is_preserved_at_publication(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('BF1_TEST_TMP_ROOT')) as folder:
            root = Path(folder)
            source, output = root / 'source.tsv', root / 'summary.json'
            data = b'cg000001\t0.5\n'
            source.write_bytes(data)
            args = ['inspect', '--format', 'tcga-methylation-beta', '--input', str(source),
                    '--source-sha256', hashlib.sha256(data).hexdigest(),
                    '--completeness', 'full', '--output', str(output)]
            result = subprocess.run([sys.executable, '-c', OUTPUT_COLLISION_PROBE, str(output), *args],
                                    cwd=REPO, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(output.read_bytes(), b'competing completed output')
            self.assertEqual(list(root.glob('.b_formats_*')), [])

    def test_summary_attests_the_snapshot_actually_parsed(self):
        temporary_root = os.environ.get('BF1_TEST_TMP_ROOT')
        with tempfile.TemporaryDirectory(dir=temporary_root) as folder:
            root = Path(folder)
            source, output = root / 'source.tsv', root / 'summary.json'
            initial = b'cg000001\t0.5\n'
            source.write_bytes(initial)
            digest = hashlib.sha256(initial).hexdigest()
            args = ['inspect', '--format', 'tcga-methylation-beta', '--input', str(source),
                    '--source-sha256', digest, '--completeness', 'full', '--output', str(output)]
            result = subprocess.run([sys.executable, '-c', SOURCE_CHANGE_PROBE, str(source), *args],
                                    cwd=REPO, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotEqual(source.read_bytes(), initial, 'Filesystem mutation was not exercised')
            summary = json.loads(output.read_text())
            self.assertEqual(summary['row_count'], 1)
            self.assertEqual(summary['actual_bytes'], len(initial))
            self.assertEqual(summary['actual_source_sha256'], digest)

if __name__ == '__main__':
    unittest.main()
