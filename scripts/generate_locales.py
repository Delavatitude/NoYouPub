"""Generate Chrome-native catalogs from the shared resources; no translation service."""
from pathlib import Path
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]/'source'
fr=json.loads((ROOT/'locales/fr.json').read_text());en=json.loads((ROOT/'locales/en.json').read_text())
if set(fr)!=set(en):raise SystemExit('Catalog key mismatch')
# Guard plain Swift L() keys; interpolated templates are checked by model tests.
for match in re.finditer(r'L\("((?:[^"\\]|\\.)*)"\)',(ROOT/'YouTubeTV.swift').read_text()):
 raw=match[1]
 if '\\(' in raw:continue
 key=json.loads('"'+raw+'"')
 if key not in fr:raise SystemExit('Missing Swift translation: '+key)
index={key:'m'+hashlib.sha256(key.encode()).hexdigest()[:16] for key in fr}
for lang,values in [('fr',fr),('en',en)]:
 for key in fr:
  if sorted(re.findall(r'\{\{.*?\}\}',key))!=sorted(re.findall(r'\{\{.*?\}\}',values[key])):raise SystemExit('Placeholder mismatch: '+key)
 target=ROOT/'extension/_locales'/lang;target.mkdir(parents=True,exist_ok=True)
 out={index[key]:{'message':values[key]} for key in fr}
 out['extensionDescription']={'message': 'Diffuser YouTube vers une TV compatible avec NoYouPub Core.' if lang=='fr' else 'Cast YouTube to a compatible TV with NoYouPub Core.'}
 (target/'messages.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
(ROOT/'extension/i18n-index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n')
print('Generated FR/EN Chrome catalogs:',len(index))
