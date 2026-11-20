"""Focused publication hygiene scan; prints findings, never prints matching secrets."""
from pathlib import Path
import argparse,ipaddress,re,subprocess,sys
root=Path(__file__).resolve().parents[1]
tracked=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=root).decode().split('\0')
checks={
 'personal home path':re.compile(r'/' + r'Users/[^/\s]+/'),
 'private signing key':re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
 'provider credential':re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|AKIA[A-Z0-9]{16}|sk-[A-Za-z0-9_-]{35,})\b'),
 'signed media URL':re.compile(r'https?://[^\s\x22\x27]*googlevideo\.com[^\s\x22\x27]*(?:signature|sig|lsig|expire)='),
}
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--history',action='store_true');options=parser.parse_args()
findings=[];seen=set();scanned=0

def scan(name,text,revision='working tree'):
 global scanned
 key=(name,text)
 if key in seen:return
 seen.add(key);scanned+=1
 if Path(name).suffix.lower() in ('.p12','.p8','.key','.log','.dmg','.pkg'):
  findings.append((revision,name,'forbidden artifact'));return
 if '/__pycache__/' in name or name.startswith(('config/','cache/','artifacts/')):
  findings.append((revision,name,'private/generated directory'));return
 for label,pattern in checks.items():
  if pattern.search(text):findings.append((revision,name,label))
 for raw in re.findall(r'(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])',text):
  try:address=ipaddress.ip_address(raw)
  except ValueError:continue
  # Explicit network-range definitions in this scanner are not user addresses.
  if name=='scripts/audit_public_tree.py' and raw in ('10.0.0.0','172.16.0.0','192.168.0.0'):continue
  if raw!='192.168.1.100' and any(address in ipaddress.ip_network(n) for n in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16')):findings.append((revision,name,'private LAN address'))

for name in sorted(set(tracked)-{''}):
 p=root/name
 if p.is_file() and p.suffix.lower() not in ('.png','.jpg','.icns'):scan(name,p.read_text(errors='replace'))
if options.history:
 for revision in subprocess.check_output(['git','rev-list','--all'],cwd=root,text=True).splitlines():
  paths=subprocess.check_output(['git','ls-tree','-r','--name-only','-z',revision],cwd=root).decode().split('\0')
  for name in paths:
   if not name or Path(name).suffix.lower() in ('.png','.jpg','.icns'):continue
   content=subprocess.check_output(['git','show',revision+':'+name],cwd=root).decode(errors='replace')
   scan(name,content,revision[:12])
for revision,path,label in findings:print(revision+': '+path+': '+label)
if findings:sys.exit(1)
print(f'Focused hygiene checks passed for {scanned} distinct text-file revisions. Review binary assets, dependency provenance and release archives separately.')
