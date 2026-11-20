"""Isolated software checks. Never changes a real TV, installed app or Chrome profile."""
import argparse,os,subprocess,sys,tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--swift',action='store_true');a=p.parse_args()
with tempfile.TemporaryDirectory(prefix='noyoupub-check-') as directory:
 env=os.environ|{'NOYOUPUB_DATA_DIR':str(Path(directory).resolve()/'data'),'PYTHONDONTWRITEBYTECODE':'1'}
 commands=[[sys.executable,str(root/'tests'/n)] for n in ('test_core.py','test_packaging.py','test_media_http.py','test_transport_ack.py','test_relay_errors.py','test_speed_timeline.py','test_stream_http.py')]
 commands += [['node',str(root/'tests/test_page_navigation.cjs')],['node',str(root/'tests/test_extension.cjs')]]
 for file in (root/'source/extension').glob('*.js'):commands.append(['node','--check',str(file)])
 if a.swift:commands.append([sys.executable,str(root/'scripts/test_swift.py')])
 failed=[]
 for command in commands:
  print('CHECK '+Path(command[-1]).name,flush=True)
  result=subprocess.run(command,env=env,cwd=root)
  if result.returncode:failed.append(command)
 if failed:print('FAILED:',failed);sys.exit(1)
 print('All software checks passed. Live TV, clean Mac and notarization are separate manual gates.')
