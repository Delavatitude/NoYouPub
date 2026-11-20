"""Compile assertions against the actual model, without launching the GUI or a TV."""
from pathlib import Path
import os,subprocess,tempfile
root=Path(__file__).resolve().parents[1]
source=(root/'source/YouTubeTV.swift').read_text()
model=source[:source.index('struct Card<')]
with tempfile.TemporaryDirectory(prefix='noyoupub-swift-') as directory:
 d=Path(directory).resolve();(d/'main.swift').write_text(model+'\n'+(root/'tests/desktop_assertions.swift').read_text())
 subprocess.run(['xcrun','swiftc','-module-cache-path',str(root/'artifacts/swift-cache'),str(root/'source/Localization.swift'),str(d/'main.swift'),'-o',str(d/'test')],check=True)
 subprocess.run([str(d/'test')],env=os.environ|{'NOYOUPUB_DATA_DIR':str(d/'data'),'NOYOUPUB_LOCALES_DIR':str(root/'source/locales')},check=True)
