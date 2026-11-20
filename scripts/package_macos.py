"""Prepare a local DMG from a reviewed build. Never notarizes or distributes."""
import argparse
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile
import sys
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--app',required=True);p.add_argument('--output',required=True);p.add_argument('--development-review',action='store_true');p.add_argument('--adhoc-beta',action='store_true',help='Package an ad hoc signed Apple Silicon beta');p.add_argument('--pre-notarization',action='store_true',help='Prepare a Developer ID signed DMG for manual notarization; not for distribution');a=p.parse_args()
app=Path(a.app).resolve();target=Path(a.output).resolve()
if not app.is_relative_to(ROOT/'artifacts') or not target.is_relative_to(ROOT/'artifacts'):p.error('All paths must remain in artifacts/')
if target.exists():p.error('Output exists; refusing to overwrite')
info=plistlib.loads((app/'Contents/Info.plist').read_bytes())
if info.get('NoYouPubDevelopmentBuild') and not a.development_review:p.error('Development builds cannot be packaged for public release')
if not a.development_review:
    subprocess.run(['codesign','--verify','--deep','--strict',str(app)],check=True)
    signature=subprocess.run(['codesign','-dv','--verbose=4',str(app)],capture_output=True,text=True,check=True)
    if a.adhoc_beta:
        if a.pre_notarization or 'Signature=adhoc' not in signature.stderr:p.error('Expected an ad hoc signed beta')
        runtime = app/'Contents/Resources'
        for name in ('Core/noyoupub-core','bin/node','bin/ffmpeg','bin/ffprobe','runtime-manifest.json'):
            if not (runtime/name).is_file():p.error('Incomplete beta runtime: '+name)
    else:
        if 'Authority=Developer ID Application:' not in signature.stderr:p.error('A real Developer ID Application signature is required')
        if not a.pre_notarization:subprocess.run(['spctl','--assess','--type','execute','--verbose=2',str(app)],check=True)
with tempfile.TemporaryDirectory(prefix='noyoupub-dmg-') as d:
    stage=Path(d);shutil.copytree(app,stage/app.name,symlinks=True)
    (stage/'Applications').symlink_to('/Applications',target_is_directory=True)
    guide = (
        'NoYouPub 3.0.0 beta\n'
        'Déplacez l’application vers Applications sans remplacer votre installation V2.5.\n'
        'Au premier lancement, utilisez Installation et langue pour vérifier le moteur.\n'
        'La passerelle Chrome est facultative pour diffuser depuis l’application Mac.\n\n'
        'Move the app to Applications while keeping your V2.5 installation.\n'
        'On first launch, use Setup and language to check the core.\n'
        'The Chrome bridge is optional when casting from the Mac app.\n'
    )
    if a.adhoc_beta:
        guide += (
            '\nBÊTA / BETA\n'
            'Signature ad hoc, sans notarisation. Gatekeeper peut bloquer l’ouverture.\n'
            'Ad hoc signed and not notarized. Gatekeeper may block first launch.\n'
        )
    if a.development_review:
        guide += (
            '\nREVUE LOCALE / LOCAL REVIEW\n'
            'Signature locale, non notariée. Gatekeeper peut bloquer l’ouverture.\n'
            'Local ad hoc signature, not notarized. Gatekeeper may block launch.\n'
        )
    (stage/'READ-ME.txt').write_text(guide, encoding='utf-8')
    subprocess.run(['hdiutil','create','-ov','-format','UDZO','-volname','NoYouPub V3 Development' if a.development_review else 'NoYouPub','-srcfolder',str(stage),str(target)],check=True)
print(target)
