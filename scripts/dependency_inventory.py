"""Export installed package metadata, never environment paths, URLs or credentials."""
import json
from importlib.metadata import distributions
for_json=[]
for d in distributions():
 if d.metadata['Name'].lower()=='pip':continue
 for_json.append({'name':d.metadata['Name'],'version':d.version,'declared_license':d.metadata.get('License-Expression') or d.metadata.get('License','UNKNOWN')})
print(json.dumps({'status':'Metadata snapshot, not a legal clearance or hash lock','packages':sorted(for_json,key=lambda d:d['name'].lower())},indent=2))
