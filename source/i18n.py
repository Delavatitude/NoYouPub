"""Bilingual message boundary with literal and placeholder-safe matching."""
from functools import lru_cache
import json
import re
from runtime_paths import CODE_ROOT
from preferences import language

@lru_cache(maxsize=4)
def catalog(lang): return json.loads((CODE_ROOT/'locales'/(lang+'.json')).read_text())

def t(value,lang=None):
    if not isinstance(value,str): return value
    lang=language(lang);fr=catalog('fr');target=catalog(lang)
    if value in target:return target[value]
    # Reverse translation supports a language change while a message is visible.
    for key,english in catalog('en').items():
        if value==english:return target.get(key,key)
    # Interpolated values are matched as text, never executed or formatted as code.
    for origin in ('fr','en'):
        for key,template in catalog(origin).items():
            slots=re.findall(r'\{\{([^{}]+)\}\}',template)
            if not slots:continue
            pattern=re.escape(template)
            for slot in slots:pattern=pattern.replace(re.escape('{{'+slot+'}}'),'(.*?)',1)
            match=re.fullmatch(pattern,value,re.S)
            if match:
                out=target.get(key,key)
                for slot,part in zip(slots,match.groups()):out=out.replace('{{'+slot+'}}',part)
                return out
    # Dynamic counters and device names appended to a translated label.
    for key in sorted(fr,key=len,reverse=True):
        for template in (key,catalog('en').get(key,key)):
            if value.startswith(template) and template and len(value)>len(template) and (template[-1].isspace() or value[len(template)] in ' :·—→'):
                return target.get(key,key)+value[len(template):]
    return value
