"""Local CATT entry point: isolated settings and YouTube JS support."""
from pathlib import Path
import os
import shutil
import sys

from runtime_paths import DATA_ROOT as ROOT, CODE_ROOT, core_command, binary, initialize


def configure():
    initialize()
    import catt.cli as cli
    import catt.stream_info as stream

    cli.CONFIG_DIR = ROOT / "config"
    cli.CONFIG_PATH = cli.CONFIG_DIR / "catt.cfg"
    cli.STATE_PATH = cli.CONFIG_DIR / "state.json"
    node = binary("node")
    if not node and os.environ.get('NOYOUPUB_DEVELOPMENT') == '1' and (ROOT/"config/node-path.txt").exists():
        node = (ROOT/"config/node-path.txt").read_text().strip()
    if not node: raise RuntimeError("Node.js 22 ou plus récent est nécessaire.")
    stream.DEFAULT_YTDL_OPTS.update({
        "js_runtimes": {"node": {"path": node}},
        "cachedir": str(ROOT / "cache"),
        "noplaylist": True,
        "socket_timeout": 20,
        "retries": 2,
    })
    return cli


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "cast":
        from launcher import youtube_url
        from relay import start
        position = float(sys.argv[sys.argv.index("--seek-to") + 1]) if "--seek-to" in sys.argv else 0
        if not 0 <= position <= 86400:
            raise SystemExit("Position invalide")
        device = sys.argv[sys.argv.index("--target") + 1] if "--target" in sys.argv else ""
        quality = int(sys.argv[sys.argv.index("--quality") + 1]) if "--quality" in sys.argv else 1080
        if quality not in (360, 480, 720, 1080):
            raise SystemExit("Qualité invalide")
        raise SystemExit(start(youtube_url(sys.argv[-1]), position, device, quality))
    if len(sys.argv) > 1 and sys.argv[1] == "update":
        raise SystemExit('Update the signed NoYouPub package; in-place dependency upgrades are disabled.')
    configure().main()
