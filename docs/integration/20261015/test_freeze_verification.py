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
if __name__=='__main__':unittest.main()
