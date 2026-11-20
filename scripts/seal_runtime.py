"""Refresh runtime digests after nested signing and before signing the outer app."""
import argparse,hashlib,json,os
from pathlib import Path

def seal(resources):
 resources=Path(resources).resolve();manifest=resources/'runtime-manifest.json'
 value=json.loads(manifest.read_text())
 if not value.get('files') or not value.get('notices'):raise ValueError('An audited runtime manifest is required')
 actual=set()
 for name in ('Core','bin','Extension','Notices'):
  directory=resources/name
  if not directory.is_dir():raise ValueError('Missing payload directory: '+name)
  for p in directory.rglob('*'):
   if p.is_symlink() and not p.resolve().is_relative_to(resources):raise ValueError('Escaping symlink')
   if p.is_file():actual.add(p.relative_to(resources).as_posix())
 # No new file can silently enter a previously reviewed/signing inventory.
 if set(value['files'])!=actual:raise ValueError('Runtime file inventory changed; repeat provenance review')
 if any(name not in actual or not name.startswith('Notices/') for name in value['notices']):raise ValueError('Invalid license notice inventory')
 value['files']={name:hashlib.sha256((resources/name).read_bytes()).hexdigest() for name in sorted(actual)}
 temporary=manifest.with_suffix('.sealed.tmp');temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.replace(manifest)
 return len(actual)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--resources',required=True);a=p.parse_args()
 if os.environ.get('NOYOUPUB_RELEASE_APPROVED')!='YES':p.error('No changes made: explicit signing approval is required')
 print('Updated signed-runtime file digests:',seal(a.resources))
