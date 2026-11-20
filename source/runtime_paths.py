"""Separate immutable application code from private per-user state."""
import os
import shutil
import sys
from pathlib import Path

CODE_ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
DATA_ROOT = Path(os.environ.get('NOYOUPUB_DATA_DIR', Path.home()/'Library/Application Support/NoYouPub')).expanduser().resolve()
DEFAULT_RESOURCES = Path(sys.executable).resolve().parents[1] if getattr(sys, 'frozen', False) else CODE_ROOT.parent
RESOURCES = Path(os.environ.get('NOYOUPUB_RESOURCES', DEFAULT_RESOURCES)).resolve()
LEGACY_ROOT = Path.home()/'Library/Application Support/YouTube-CATT'

def initialize():
    if DATA_ROOT==LEGACY_ROOT.resolve() or DATA_ROOT.is_relative_to(LEGACY_ROOT.resolve()) or LEGACY_ROOT.resolve().is_relative_to(DATA_ROOT):
        raise RuntimeError('V3 data must be isolated from the legacy installation')
    DATA_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    (DATA_ROOT/'config').mkdir(exist_ok=True, mode=0o700)
    (DATA_ROOT/'config').chmod(0o700)
    config = DATA_ROOT/'config/catt.cfg'
    if not config.exists(): config.write_text('[options]\ndevice =\n\n[aliases]\n', encoding='utf-8')

def binary(name):
    for candidate in (RESOURCES/'bin'/name, DATA_ROOT/'bin'/name, CODE_ROOT/'bin'/name):
        if candidate.is_file() and os.access(candidate, os.X_OK): return str(candidate)
    if os.environ.get('NOYOUPUB_DEVELOPMENT') == '1': return shutil.which(name)
    return None

def core_command(*args):
    if getattr(sys, 'frozen', False): return [sys.executable, *args]
    return [sys.executable, str(CODE_ROOT/'core.py'), *args]
