"""Atomic, allowlisted shared preferences; never mutate legacy data implicitly."""
import json
import locale
import os
import uuid
import sys
import re
import subprocess
from functools import lru_cache
from runtime_paths import DATA_ROOT, initialize

LANGUAGES = ('system', 'fr', 'en')
PATH = DATA_ROOT/'config/preferences.json'

def read():
    try:
        value=json.loads(PATH.read_text())
        return value if isinstance(value,dict) else {}
    except (OSError,ValueError): return {}

def language(value=None):
    value = value or os.environ.get('NOYOUPUB_LANGUAGE') or read().get('language','system')
    if value not in LANGUAGES: value='system'
    if value=='system': value=system_language()
    return value if value in ('fr','en') else 'en'

@lru_cache(maxsize=1)
def system_language():
    # Native Messaging does not inherit the GUI locale. Read macOS' preferred
    # language directly; fall back to the process locale on other platforms.
    if sys.platform=='darwin':
        try:
            result=subprocess.run(['/usr/bin/defaults','read','-g','AppleLanguages'],capture_output=True,text=True,timeout=2,check=True)
            choices=re.findall(r'(?m)^\s*"?([a-z]{2})(?:[-_][A-Za-z0-9-]+)?"?,?\s*$',result.stdout)
            if choices:return choices[0] if choices[0] in ('fr','en') else 'en'
        except (OSError,subprocess.SubprocessError):pass
    return (locale.getlocale()[0] or os.environ.get('LANG','en')).split('_')[0].split('-')[0]

def set_language(value):
    if value not in LANGUAGES: raise ValueError('Invalid language preference')
    initialize();current=read();current['language']=value
    tmp=PATH.with_suffix('.'+uuid.uuid4().hex+'.tmp')
    tmp.write_text(json.dumps(current,ensure_ascii=False));tmp.chmod(0o600);tmp.replace(PATH)
    return {'language':value,'resolved_language':language(value)}
