"""Private preparation status shared by the native app and Chrome extension."""
import json
import os
from pathlib import Path
import re
import time
import uuid
import tempfile
import shutil

from runtime_paths import DATA_ROOT
ROOT = DATA_ROOT / 'config'
STATUS = ROOT / 'preparation.json'
TERMINAL = {'playing', 'error', 'cancelled', 'ended'}

class Cancelled(Exception):
    pass


def read():
    try:
        value = json.loads(STATUS.read_text())
    except (OSError, ValueError):
        return {}
    if value.get('phase') not in TERMINAL and value.get('pid'):
        try:
            os.kill(value['pid'], 0)
        except PermissionError:
            pass
        except ProcessLookupError:
            value.update(phase='error', message='La préparation a été interrompue. Tu peux réessayer.', busy=False)
    value.pop('_cache', None)
    value['busy'] = bool(value and value.get('phase') not in TERMINAL)
    return value


def write(value):
    ROOT.mkdir(parents=True, exist_ok=True)
    temporary = ROOT / ('.preparation-' + uuid.uuid4().hex + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False))
    temporary.replace(STATUS)


def begin(job_id, **fields):
    now = time.time()
    write({'job_id': job_id, 'phase': 'starting', 'message': 'Connexion à la TV…', 'started': now, 'updated': now, 'busy': True, **fields})


def update(job_id, phase=None, message=None, **fields):
    try:
        value = json.loads(STATUS.read_text())
    except (OSError, ValueError):
        return
    if value.get('job_id') != job_id:
        return
    if phase: value['phase'] = phase
    if message: value['message'] = message
    value.update(fields, updated=time.time())
    value['busy'] = value.get('phase') not in TERMINAL
    write(value)


def check(job_id):
    if (ROOT / ('cancel-' + job_id)).exists():
        raise Cancelled('Préparation annulée. Aucun nouvel envoi à la TV.')


def cancel():
    value = read()
    job = value.get('job_id', '')
    if not value.get('busy') or not re.fullmatch('[a-f0-9]{32}', job):
        return {'ok': True, 'message': 'Aucune préparation en cours.'}
    (ROOT / ('cancel-' + job)).touch()
    return {'ok': True, 'message': 'Annulation demandée…'}


def cleanup(job_id):
    try:
        value = json.loads(STATUS.read_text())
        if value.get('job_id') != job_id or not value.get('_cache'):
            return
        path = Path(value['_cache'])
        if path.parent.resolve() == Path(tempfile.gettempdir()).resolve() and path.name.startswith('youtube-tv-') and not path.is_symlink():
            shutil.rmtree(path, ignore_errors=True)
    except (OSError, ValueError):
        pass
