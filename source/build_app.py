"""Offline application assembler. Does not install, upload or notarize anything."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import platform
import shutil
import subprocess

SOURCE=Path(__file__).resolve().parent
REPO=SOURCE.parent

def validate_vendor(folder):
    from setup_core import verify_payload
    verify_payload(folder)
    manifest=json.loads((folder/'runtime-manifest.json').read_text())
    if not manifest.get('files') or not manifest.get('notices'):raise RuntimeError('Runtime manifest must include file hashes and license notices')
    for rel,digest in manifest['files'].items():
        path=(folder/rel).resolve()
        if not path.is_relative_to(folder.resolve()) or not path.is_file():raise RuntimeError('Invalid runtime manifest path')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise RuntimeError('Runtime checksum mismatch: '+rel)
    for entry in folder.rglob('*'):
        if entry.is_symlink() and not entry.resolve().is_relative_to(folder.resolve()):raise RuntimeError('Runtime symlink escapes the payload')
        if not entry.is_file():continue
        with entry.open('rb') as f:magic=f.read(4)
        if magic not in (b'\xcf\xfa\xed\xfe',b'\xce\xfa\xed\xfe',b'\xfe\xed\xfa\xcf',b'\xca\xfe\xba\xbe',b'\xca\xfe\xba\xbf'):continue
        linked=subprocess.check_output(['otool','-L',str(entry)],text=True)
        for line in linked.splitlines()[1:]:
            dep=line.strip().split(' (',1)[0]
            if not dep.startswith(('/System/Library/','/usr/lib/','@rpath/','@loader_path/','@executable_path/')):raise RuntimeError('Non-portable runtime dependency: '+dep)
    return manifest

def build(target,development=False,vendor=None,core_only=False,minimum_macos='13.0'):
    if minimum_macos not in ('13.0', '14.0', '15.0', '26.0'):
        raise ValueError('Unsupported minimum macOS version')
    target=Path(target).resolve()
    if not target.is_relative_to((REPO/'artifacts').resolve()):raise RuntimeError('Build output must stay inside this repository’s artifacts folder')
    if target.exists():raise RuntimeError('Output exists. Choose a new output directory; nothing was overwritten.')
    if not development and not vendor:raise RuntimeError('Provide an audited --runtime-vendor or explicitly choose --development. No incomplete public build is produced.')
    if vendor:validate_vendor(Path(vendor).resolve())
    stage=target.with_name('.'+target.name+'.building')
    if stage.exists():raise RuntimeError('A previous staging directory exists; review it before continuing')
    macos=stage/'Contents/MacOS';resources=stage/'Contents/Resources';macos.mkdir(parents=True);resources.mkdir()
    try:
        subprocess.run(['xcrun','swiftc','-target',platform.machine()+'-apple-macos'+minimum_macos,'-parse-as-library','-module-cache-path',str(REPO/'artifacts/swift-cache'),'-O',str(SOURCE/'Localization.swift'),str(SOURCE/'YouTubeTV.swift'),'-o',str(macos/'NoYouPub')],check=True)
        shutil.copy2(SOURCE/'assets/NoYouPub.icns',resources/'NoYouPub.icns');shutil.copy2(SOURCE/'assets/logo-256.png',resources/'logo.png')
        shutil.copytree(SOURCE/'locales',resources/'locales')
        if vendor:
            for name in ('Core','bin','Extension','Notices'):shutil.copytree(Path(vendor)/name,resources/name,symlinks=True)
            shutil.copy2(Path(vendor)/'runtime-manifest.json',resources/'runtime-manifest.json')
        else:
            shutil.copytree(SOURCE,resources/'Source',ignore=shutil.ignore_patterns('__pycache__','*.pyc','assets','extension'))
            shutil.copytree(SOURCE/'extension',resources/'Extension')
        data=dict(CFBundleName='NoYouPub Core Installer' if core_only else 'NoYouPub',CFBundleDisplayName='NoYouPub Core Installer' if core_only else 'NoYouPub',CFBundleIdentifier='fr.local.noyoupub.v3.core-installer' if core_only else 'fr.local.noyoupub.v3',CFBundleExecutable='NoYouPub',CFBundlePackageType='APPL',CFBundleIconFile='NoYouPub.icns',CFBundleShortVersionString='3.0.0',CFBundleVersion='30',LSMinimumSystemVersion='13.0',NSHighResolutionCapable=True,CFBundleDevelopmentRegion='en',CFBundleLocalizations=['fr','en'],NoYouPubDevelopmentBuild=development,NoYouPubCoreOnly=core_only,NSLocalNetworkUsageDescription='Find compatible TVs and send video over your local network.',NSBonjourServices=['_googlecast._tcp'])
        data['LSMinimumSystemVersion'] = minimum_macos
        (stage/'Contents/Info.plist').write_bytes(plistlib.dumps(data))
        for lang,message in [('fr','Trouver les TV compatibles et transmettre la vidéo sur le réseau local.'),('en','Find compatible TVs and send video over your local network.')]:
            d=resources/(lang+'.lproj');d.mkdir();(d/'InfoPlist.strings').write_text('"NSLocalNetworkUsageDescription" = '+json.dumps(message,ensure_ascii=False)+';\n')
        if development:
            subprocess.run(['codesign','--force','--sign','-',str(stage)],check=True)
            subprocess.run(['codesign','--verify','--deep','--strict',str(stage)],check=True)
        # Public signing is a separate reviewed step. Never fabricate Developer ID.
        stage.replace(target)
    except Exception:
        shutil.rmtree(stage,ignore_errors=True);raise
    return target

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--development',action='store_true');p.add_argument('--runtime-vendor');p.add_argument('--core-only',action='store_true');p.add_argument('--minimum-macos',default='13.0');a=p.parse_args()
    print(build(a.output,a.development,a.runtime_vendor,a.core_only,a.minimum_macos))
