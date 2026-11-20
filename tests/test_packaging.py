import hashlib,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'source'),str(ROOT/'scripts')]
from build_app import build
from seal_runtime import seal

class PackagingBoundaries(unittest.TestCase):
 def test_refuse_external_build_output(self):
  with tempfile.TemporaryDirectory() as d:
   output=Path(d)/'outside.app'
   with self.assertRaises(RuntimeError):build(output,development=True)
   self.assertFalse(output.exists())
 def test_no_incomplete_public_build(self):
  output=ROOT/'artifacts/blocked-incomplete-public-test.app'
  self.assertFalse(output.exists())
  with self.assertRaises(RuntimeError):build(output)
  self.assertFalse(output.exists())
 def test_signing_guard(self):
  result=subprocess.run(['bash',str(ROOT/'scripts/release_macos.sh')],env=os.environ|{'NOYOUPUB_RELEASE_APPROVED':'NO'},capture_output=True)
  self.assertEqual(result.returncode,2)
 def test_hash_signed_bytes_without_accepting_new_code(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   for name in ['Core/core','bin/node','Extension/manifest.json','Notices/LICENSE']:
    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('synthetic reviewed bytes')
   manifest={'files':{p.relative_to(root).as_posix():'before-signing' for p in root.rglob('*') if p.is_file()},'notices':['Notices/LICENSE']}
   (root/'runtime-manifest.json').write_text(json.dumps(manifest))
   (root/'Core/core').write_text('synthetic signed bytes')
   self.assertEqual(seal(root),4)
   updated=json.loads((root/'runtime-manifest.json').read_text())
   self.assertEqual(updated['files']['Core/core'],hashlib.sha256(b'synthetic signed bytes').hexdigest())
   (root/'Core/unreviewed').write_text('new file')
   with self.assertRaises(ValueError):seal(root)

if __name__=='__main__':unittest.main(verbosity=2)
