"""Explicit, per-user core registration. No administrator privileges or network installs."""
import importlib.util
import hashlib
import base64
import json
import os
from pathlib import Path
import shutil
import stat
import uuid
from runtime_paths import CODE_ROOT, DATA_ROOT, RESOURCES, initialize, binary

HOST='fr.local.noyoupub_v3'
MARKER='noyoupub-core-v3'
VERSION='3.0.0-beta'
MACHO=(b'\xcf\xfa\xed\xfe',b'\xce\xfa\xed\xfe',b'\xfe\xed\xfa\xcf',b'\xca\xfe\xba\xbe',b'\xca\xfe\xba\xbf')

def doctor():
    import sys
    checks={'python':sys.version_info >= (3,11)}
    for package in ('catt','yt_dlp','yt_dlp_ejs','pychromecast','requests'):checks[package]=importlib.util.find_spec(package) is not None
    import subprocess
    for name in ('node','ffmpeg','ffprobe'):
        executable=binary(name);checks[name]=False
        if not executable:continue
        try:
            if name=='node':
                result=subprocess.run([executable,'--version'],capture_output=True,text=True,timeout=8,check=True)
                checks[name]=int(result.stdout.strip().lstrip('v').split('.')[0])>=22
            elif name=='ffmpeg':
                result=subprocess.run([executable,'-hide_banner','-encoders'],capture_output=True,text=True,timeout=8,check=True)
                checks[name]='h264_videotoolbox' in result.stdout and ' aac ' in result.stdout
            else:
                subprocess.run([executable,'-version'],capture_output=True,timeout=8,check=True);checks[name]=True
        except (OSError,ValueError,subprocess.SubprocessError):pass
    manifest=Path.home()/f'Library/Application Support/Google/Chrome/NativeMessagingHosts/{HOST}.json'
    checks['chrome_bridge']=manifest.is_file()
    return {'ok':all(v for k,v in checks.items() if k!='chrome_bridge'),'checks':checks,'version':VERSION,'message':'Le moteur ne nécessite pas de fenêtre ouverte.'}

def verify_payload(payload,allow_development=False):
    payload=Path(payload).resolve()
    core=payload/'Core/noyoupub-core'
    paths=[core,*[payload/'bin'/n for n in ('node','ffmpeg','ffprobe')]]
    for p in paths:
        if not p.is_file() or not os.access(p,os.X_OK):raise RuntimeError('Missing executable: '+p.name)
        if not allow_development:
            with p.open('rb') as f:magic=f.read(4)
            if magic not in MACHO:raise RuntimeError('Expected a verified macOS executable: '+p.name)
    if not (payload/'Extension/manifest.json').is_file():raise RuntimeError('Missing Chrome extension payload')
    if not (payload/'runtime-manifest.json').is_file() and not allow_development:raise RuntimeError('Missing audited runtime manifest')
    for entry in payload.rglob('*'):
        if entry.is_symlink() and (Path(os.readlink(entry)).is_absolute() or not entry.resolve().is_relative_to(payload)):
            raise RuntimeError('Payload symlink escapes its root')
    identity=json.loads((CODE_ROOT/'extension-identity.json').read_text())
    extension=json.loads((payload/'Extension/manifest.json').read_text())
    key=base64.b64decode(extension.get('key',''),validate=True)
    extension_id=''.join(chr(ord('a')+int(c,16)) for c in hashlib.sha256(key).hexdigest()[:32])
    if identity['origin']!='chrome-extension://'+extension_id+'/':
        raise RuntimeError('Extension identity mismatch')
    if not allow_development:
        audit=json.loads((payload/'runtime-manifest.json').read_text())
        if not (payload/'Notices').is_dir() or not audit.get('files') or not audit.get('notices'):raise RuntimeError('Runtime audit is incomplete')
        covered=set()
        for name,digest in audit['files'].items():
            file=(payload/name).resolve()
            if not file.is_relative_to(payload) or not file.is_file():raise RuntimeError('Invalid runtime manifest path')
            if hashlib.sha256(file.read_bytes()).hexdigest()!=digest:raise RuntimeError('Runtime checksum mismatch')
            covered.add(file)
        for directory in ('Core','bin','Extension'):
            for file in (payload/directory).rglob('*'):
                if file.is_file() and file.resolve() not in covered:raise RuntimeError('Unhashed runtime file: '+str(file.relative_to(payload)))
        for name in audit['notices']:
            notice=(payload/name).resolve()
            if not notice.is_relative_to(payload) or notice not in covered:raise RuntimeError('Missing audited license notice')
    return payload

def validate_destination(home,root):
    root=Path(root)
    legacy=(Path(home)/'Library/Application Support/YouTube-CATT').resolve()
    resolved=root.resolve()
    if root.is_symlink() or resolved==legacy or resolved.is_relative_to(legacy) or legacy.is_relative_to(resolved):
        raise RuntimeError('Refusing to modify the legacy installation or its parent')
    if resolved==Path(home).resolve() or resolved==Path('/'):
        raise RuntimeError('Unsafe data directory')
    for part in (root,*root.parents):
        if part.is_symlink():raise RuntimeError('Data path must not contain symlinks')
    if (root/'config').is_symlink():raise RuntimeError('Configuration must not be a symlink')

def register_host(home=None,payload=None,data_root=None,allow_development=False):
    home=Path(home or Path.home()).resolve()
    root=Path(data_root or (home/'Library/Application Support/NoYouPub'))
    validate_destination(home,root)
    payload=verify_payload(payload or RESOURCES,allow_development)
    manifest=home/f'Library/Application Support/Google/Chrome/NativeMessagingHosts/{HOST}.json'
    wrapper=root/'native-host'
    if manifest.exists():
        previous=json.loads(manifest.read_text())
        if previous.get('path')!=str(wrapper):raise RuntimeError('Native host belongs to another installation')
    marker=root/'.installation-id'
    if marker.exists():
        if marker.read_text()!=MARKER:raise RuntimeError('Unknown installation marker')
        if not wrapper.is_file() or not manifest.is_file():raise RuntimeError('Incomplete installation: uninstall the owned Core and install again')
        return {'ok':True,'message':'Passerelle Chrome activée.'}
    if root.exists() and any(p.name not in ('config',) for p in root.iterdir()):raise RuntimeError('Folder contains unowned files')
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    stage=root/('.stage-'+uuid.uuid4().hex);stage.mkdir(mode=0o700)
    committed=[]
    previous_manifest=manifest.read_bytes() if manifest.exists() else None
    temp=None
    try:
        for source,target in [('Core','core'),('bin','bin'),('Extension','extension')]+([('Notices','notices')] if (payload/'Notices').is_dir() else []):
            shutil.copytree(payload/source,stage/target,symlinks=True)
        # Shell quoting permits spaces; no user-controlled executable or origin argument is evaluated.
        import shlex
        body='#!/bin/sh\nexport NOYOUPUB_DATA_DIR='+shlex.quote(str(root))+'\nexport NOYOUPUB_RESOURCES='+shlex.quote(str(root))+'\nexec '+shlex.quote(str(root/'core/noyoupub-core'))+' native-host "$@"\n'
        for name in ('core','bin','extension','notices'):
            if not (stage/name).exists():continue
            (stage/name).replace(root/name);committed.append(root/name)
        wrapper.write_text(body);wrapper.chmod(0o700);committed.append(wrapper)
        # Extension key is a public key. Its derived stable ID is retained across upgrades.
        origin=json.loads((CODE_ROOT/'extension-identity.json').read_text())['origin']
        config=root/'config';config.mkdir(exist_ok=True,mode=0o700);config.chmod(0o700)
        if not (config/'catt.cfg').exists():(config/'catt.cfg').write_text('[options]\ndevice =\n\n[aliases]\n')
        manifest.parent.mkdir(parents=True,exist_ok=True)
        contents={'name':HOST,'description':'NoYouPub Core','type':'stdio','path':str(wrapper),'allowed_origins':[origin]}
        temp=manifest.with_suffix('.'+uuid.uuid4().hex+'.tmp');temp.write_text(json.dumps(contents,indent=2));temp.chmod(0o600);temp.replace(manifest)
        marker.write_text(MARKER);committed.append(marker);marker.chmod(0o600)
        setup=config/'setup-complete.json';setup.write_text(json.dumps({'version':VERSION,'bridge':HOST}));committed.append(setup);setup.chmod(0o600)
        return {'ok':True,'message':'Passerelle Chrome activée.','extension_path':str(root/'extension')}
    except Exception:
        if previous_manifest is None:manifest.unlink(missing_ok=True)
        else:manifest.write_bytes(previous_manifest)
        if temp is not None:temp.unlink(missing_ok=True)
        for p in reversed(committed):
            if p.is_dir():shutil.rmtree(p)
            else:p.unlink(missing_ok=True)
        raise
    finally:shutil.rmtree(stage,ignore_errors=True)

def unregister(home=None,data_root=None,remove_data=False):
    home=Path(home or Path.home()).resolve();root=Path(data_root or home/'Library/Application Support/NoYouPub')
    validate_destination(home,root)
    marker=root/'.installation-id'
    if root.is_symlink() or not marker.is_file() or marker.read_text()!=MARKER:raise RuntimeError('Installation ownership could not be verified')
    if (root/'config/relay.json').exists():raise RuntimeError('Stop the core before uninstalling')
    manifest=home/f'Library/Application Support/Google/Chrome/NativeMessagingHosts/{HOST}.json'
    if manifest.exists():
        if json.loads(manifest.read_text()).get('path')!=str(root/'native-host'):raise RuntimeError('Native host belongs to another installation')
        manifest.unlink()
    for name in ('core','bin','extension','notices'):
        p=root/name
        if p.is_symlink():p.unlink()
        elif p.is_dir():shutil.rmtree(p)
    for name in ('native-host','.installation-id','config/setup-complete.json'):(root/name).unlink(missing_ok=True)
    if remove_data:shutil.rmtree(root)
    return {'ok':True,'message':'Preferences kept.' if not remove_data else 'Core and preferences removed.'}

def import_legacy(home=None,data_root=None):
    home=Path(home or Path.home()).resolve();old=home/'Library/Application Support/YouTube-CATT/config';root=Path(data_root or home/'Library/Application Support/NoYouPub');new=root/'config'
    validate_destination(home,root)
    allowed=('catt.cfg','desktop-tv.json','desktop-last-link.txt','playback-mode.json','known-hosts.json','dlna-devices.json')
    new.mkdir(parents=True,exist_ok=True,mode=0o700);copied=[]
    for name in allowed:
        source=old/name;target=new/name
        if source.is_file() and not source.is_symlink() and not target.exists():shutil.copyfile(source,target);target.chmod(0o600);copied.append(name)
    return {'ok':True,'copied':copied}
