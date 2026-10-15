"""Adversarial release-manifest tests; only temporary synthetic files."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from verify_integration import verify_manifest
class FreezeTests(unittest.TestCase):
    def test_missing_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            errors=[];self.assertEqual(verify_manifest(Path(t),errors),0);self.assertTrue(errors)
    def test_empty_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p=root/'docs/integration/20261015/FREEZE_MANIFEST.json';p.parent.mkdir(parents=True);p.write_text('{"files":[]}')
            errors=[];verify_manifest(root,errors);self.assertTrue(errors)
    def test_valid_then_mutation_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);x=root/'synthetic.txt';x.write_text('synthetic')
            p=root/'docs/integration/20261015/FREEZE_MANIFEST.json';p.parent.mkdir(parents=True);p.write_text(json.dumps({'files':[{'path':'synthetic.txt','sha256':hashlib.sha256(x.read_bytes()).hexdigest()}]}))
            errors=[];verify_manifest(root,errors);self.assertEqual(errors,[])
            x.write_text('changed');verify_manifest(root,errors);self.assertTrue(errors)

class GitSnapshotTests(unittest.TestCase):
    def test_ignored_file_present_on_disk_but_missing_from_index_rejected(self):
        import subprocess
        from verify_integration import verify_git_snapshot
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            def git(*args):subprocess.run(['git',*args],cwd=root,check=True,capture_output=True)
            git('init');(root/'.gitignore').write_text('data/\n')
            x=root/'specs/E/data/synthetic.md';x.parent.mkdir(parents=True);x.write_text('synthetic public contract')
            p=root/'docs/integration/20261015/FREEZE_MANIFEST.json';p.parent.mkdir(parents=True)
            p.write_text(json.dumps({'files':[{'path':'specs/E/data/synthetic.md','sha256':hashlib.sha256(x.read_bytes()).hexdigest()}]}))
            git('add','.gitignore','docs')
            errors=[];verify_git_snapshot(root,errors,'INDEX')
            self.assertIn(['specs/E/data/synthetic.md','missing from Git INDEX'],errors)
            git('add','-f','specs/E/data/synthetic.md')
            errors=[];self.assertEqual(verify_git_snapshot(root,errors,'INDEX'),2);self.assertEqual(errors,[])
            x.write_text('changed');git('add','-f','specs/E/data/synthetic.md')
            errors=[];verify_git_snapshot(root,errors,'INDEX');self.assertTrue(errors)

if __name__=='__main__':unittest.main()
