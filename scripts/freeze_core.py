"""Developer-only recipe: freeze the existing Python core in an isolated build venv."""
import argparse
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--python',required=True,help='Python inside an isolated build venv with the locked dependencies and PyInstaller installed');a=p.parse_args()
modules=['native_host','desktop_app','installer','setup_core','runtime_paths','preferences','i18n','relay','catt_local','cast_control','dlna','jobs','media_http','stream_http','launcher']
args=[a.python,'-m','PyInstaller','--noconfirm','--clean','--onedir','--name','noyoupub-core','--distpath',str(ROOT/'artifacts/frozen'),'--workpath',str(ROOT/'artifacts/pyinstaller'),'--specpath',str(ROOT/'artifacts'),'--collect-all','yt_dlp','--collect-all','yt_dlp_ejs','--collect-all','catt','--collect-all','pychromecast','--add-data',str(ROOT/'source/locales')+':locales','--add-data',str(ROOT/'source/extension-identity.json')+':.']
for module in modules:args+=['--hidden-import',module]
args+=[str(ROOT/'source/core.py')]
subprocess.run(args,check=True)
print('Frozen core prepared locally. Node, FFmpeg, ffprobe and license notices must still be assembled and audited; this is not a public release.')
