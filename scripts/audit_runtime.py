"""Offline checks only; no downloading, signing or installation."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
from build_app import validate_vendor
p=argparse.ArgumentParser();p.add_argument('--vendor',required=True);a=p.parse_args()
result=validate_vendor(Path(a.vendor).resolve())
print(json.dumps({'ok':True,'hashed_files':len(result['files']),'notices':result['notices'],'warning':'Portability and hashes checked; license provenance, signatures and clean-machine runtime tests remain separate.'}))
