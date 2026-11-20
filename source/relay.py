"""Private media relay for Google Cast and LG/DLNA.

Only registered Google video URLs can be fetched. Clients are restricted to the
selected Chromecast and this PC; every route also requires an unpredictable token.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urljoin, urlparse
import json
import os
import re
import secrets
import subprocess
import sys
import threading
import time
import uuid
import shutil
import tempfile
import signal
import jobs
from media_http import MediaFileMixin
from stream_http import TransportStreamMixin

import requests

from runtime_paths import DATA_ROOT as ROOT, CODE_ROOT, core_command, binary, initialize
STATE = ROOT / "config" / "relay.json"
PLAYBACK = ROOT / "config" / "playback.json"
PORT = 45123


def atomic_json(path, data):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def stop_child(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def start(url, position=0, device="", quality=1080):
    job_id = uuid.uuid4().hex
    jobs.begin(job_id, url=url, quality=quality)
    result = ROOT / "config" / ("start-" + job_id + ".json")
    log = open(ROOT / "config" / "last-cast.log", "w", encoding="utf-8")
    process = subprocess.Popen(
        core_command("relay-worker", url, str(result), str(position), device, str(quality)),
        cwd=ROOT, stdout=log, stderr=log, stdin=subprocess.DEVNULL, start_new_session=True,
        env=os.environ | {"PYTHONUTF8": "1"},
    )
    log.close()
    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        try:
            jobs.check(job_id)
        except jobs.Cancelled:
            stop_child(process)
            jobs.cleanup(job_id)
            jobs.update(job_id, 'cancelled', 'Préparation annulée. Tu peux choisir une autre vidéo.')
            print('Préparation annulée.')
            return 1
        progress = jobs.read()
        if progress.get('job_id') == job_id and progress.get('phase') == 'downloading' and time.time() - progress.get('advanced', time.time()) > 60:
            stop_child(process)
            jobs.cleanup(job_id)
            message = 'Le serveur vidéo YouTube ne répond plus. Réessaie en 480p ou avec une autre vidéo.'
            jobs.update(job_id, 'error', message)
            print(message)
            return 1
        if result.exists():
            status = json.loads(result.read_text(encoding="utf-8"))
            result.unlink()
            print(status["message"])
            return 0 if status["ok"] else 1
        if process.poll() is not None:
            jobs.cleanup(job_id)
            jobs.update(job_id, 'error', 'Le relais s’est arrêté. Tu peux réessayer.')
            print("Le relais s'est arrêté. Voir config/last-cast.log.")
            return 1
        time.sleep(0.25)
    stop_child(process)
    jobs.cleanup(job_id)
    jobs.update(job_id, 'error', 'La préparation a dépassé le délai. Réessaie en 480p.')
    print("La préparation a dépassé le délai autorisé. Réessaie.")
    return 1


def choose_formats(formats, quality=1080, hls_only=True):
    from yt_dlp.utils import determine_protocol
    def protocol(f):
        return f.get('protocol') or determine_protocol(f)
    def hls(f):
        return (protocol(f) or '').startswith('m3u8')
    def aac(f):
        codec = (f.get('acodec') or '').lower()
        return codec.startswith(('mp4a', 'aac')) or (hls(f) and f.get('vcodec') == 'none' and not codec and f.get('ext') in ('mp4', 'm4a'))
    def usable(f):
        return bool(f.get('url') and not f.get('has_drm') and
                    protocol(f) in ('http', 'https', 'http_dash_segments', 'm3u8', 'm3u8_native'))
    videos = [f for f in formats if usable(f) and (not hls_only or hls(f))
              and (f.get('vcodec') or '').lower().startswith(('avc1', 'h264'))
              and 0 < (f.get('height') or 0) <= quality
              and (f.get('acodec') in (None, 'none') or aac(f))]
    audios = [f for f in formats if usable(f) and (not hls_only or hls(f))
              and f.get('vcodec') == 'none' and aac(f)]
    candidates = [v for v in videos if aac(v) or audios]
    if not candidates:
        if hls_only:
            raise RuntimeError('Aucune piste HLS H.264/AAC compatible n’est disponible pour ce récepteur Google Cast.')
        raise RuntimeError('YouTube ne propose pas de vidéo H.264 avec du son AAC dans cette qualité. Essaie une autre qualité ou une autre vidéo.')
    video = max(candidates, key=lambda f: (f.get('height') or 0, hls(f), f.get('fps') or 0, f.get('tbr') or 0))
    if aac(video):
        return video, video
    audio = max(audios, key=lambda f: (
        'original' in (f.get('format_note') or '').lower(),
        (f.get('language') or '').startswith('fr'),
        hls(f) == hls(video), (f.get('acodec') or '').startswith('mp4a.40.2'),
        f.get('tbr') or 0, str(f.get('format_id') or '')))
    return video, audio


def friendly_error(error, stage):
    message = re.sub(r"https?://\S+", "[adresse média]", str(error))
    if isinstance(error, requests.RequestException) and stage == 'tv':
        return 'La TV ne répond pas ou n’a pas confirmé le démarrage. Vérifie sa connexion et réessaie la diffusion.'
    if isinstance(error, requests.RequestException) and stage == 'relay':
        return 'Le relais vidéo local n’a pas pu démarrer. Réessaie la diffusion ou utilise le mode compatible.'
    if stage == 'youtube' and any(term in message.lower() for term in ('timed out', 'unable to download', 'http error 403', 'network is unreachable')):
        return 'Le serveur vidéo YouTube ne répond pas ou refuse le téléchargement. Réessaie en 480p ou avec une autre vidéo.'
    return message


def worker(url, result, position=0, device="", quality=1080):
    stage = "device"
    server = None
    mux_process = None
    mux_directory = None
    stream_processes = set()
    stream_lock = threading.Lock()
    fast_ts = False
    token = secrets.token_urlsafe(24)
    job_id = result.stem.removeprefix('start-')
    def interrupted(*_):
        raise jobs.Cancelled('Préparation annulée.')
    signal.signal(signal.SIGTERM, interrupted)
    try:
        jobs.update(job_id, 'device', 'Recherche et connexion à la TV…', pid=os.getpid())
        jobs.check(job_id)
        from catt_local import configure
        cli = configure()
        from cast_control import discover_infos
        from catt.util import get_local_ip
        from catt.controllers import setup_cast
        from catt.stream_info import DEFAULT_YTDL_OPTS
        import yt_dlp

        device = device or cli.get_config_as_dict()["options"]["device"]
        target = None
        import dlna
        known = dlna.find(device)
        if known:
            try:
                fresh = dlna.description(known['location'], known['host'])
                if fresh and fresh['id'] == known['id']:
                    target = dlna.infos([fresh])[0]
            except (requests.RequestException, OSError, ValueError):
                pass
        if target is None:
            devices = [d for d in discover_infos() if d.friendly_name == device or str(d.uuid) == device]
            if len(devices) != 1:
                raise RuntimeError('TV introuvable ou nom ambigu : ' + device)
            target = devices[0]
        device = target.friendly_name
        dlna_target = getattr(target, 'protocol', '') == 'dlna'
        try:
            playback_mode = json.loads((ROOT/'config/playback-mode.json').read_text()).get('mode','fast')
        except (OSError,ValueError):
            playback_mode = 'fast'
        fast_ts = dlna_target and (playback_mode == 'fast' or os.environ.get('NOYOUPUB_FAST_TS') == '1')
        ffmpeg = binary('ffmpeg')
        if dlna_target and not ffmpeg:
            raise RuntimeError('FFmpeg est nécessaire pour diffuser sur cette TV LG/DLNA. Installe FFmpeg, puis réessaie.')
        local_ip = get_local_ip(target.host)
        if not local_ip:
            raise RuntimeError("Impossible de déterminer l'adresse locale du PC.")
        stage = "youtube"
        jobs.update(job_id, 'extracting', 'Analyse du lien YouTube et des pistes disponibles…')
        jobs.check(job_id)
        with yt_dlp.YoutubeDL(dict(DEFAULT_YTDL_OPTS)) as ydl:
            info = ydl.extract_info(url, download=False, process=False)
        jobs.update(job_id, title=info.get('title', 'Vidéo YouTube'), duration=info.get('duration') or 0, quality=quality, device_name=device)
        try:
            video, audio = choose_formats(info.get('formats', []), quality, hls_only=not dlna_target or fast_ts)
        except RuntimeError:
            if not fast_ts:
                raise
            fast_ts = False
            video, audio = choose_formats(info.get('formats', []), quality, hls_only=False)
        jobs.check(job_id)
        jobs.update(job_id, quality=video.get('height'))

        previous_relay = None
        if STATE.exists():
            try:
                previous_relay = json.loads(STATE.read_text(encoding='utf-8'))
            except (OSError, ValueError):
                pass

        routes = {}
        routes_lock = threading.Lock()
        prefix = f"http://{local_ip}:{PORT}/{token}"
        stopping = threading.Event()
        counts = {"requests": 0, "bytes": 0}

        def register(remote):
            parsed = urlparse(remote)
            if parsed.scheme != "https" or not (parsed.hostname or "").endswith(".googlevideo.com"):
                raise ValueError("Hôte média non autorisé : " + str(parsed.hostname) + " (" + parsed.scheme + ")")
            with routes_lock:
                key = str(len(routes))
                routes[key] = remote
            return prefix + "/media/" + key

        master = b''
        if not dlna_target or fast_ts:
            video_url = register(video['url'])
            if video is audio:
                master = ('#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-STREAM-INF:BANDWIDTH=12000000,RESOLUTION='
                          + str(video['width'])+'x'+str(video['height'])+',CODECS="'
                          + video['vcodec']+','+video['acodec']+'"\n'+video_url+'\n').encode()
            else:
                audio_url = register(audio['url'])
                master = ('#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-INDEPENDENT-SEGMENTS\n'
                          '#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="audio",NAME="Original",DEFAULT=YES,AUTOSELECT=YES,URI="'
                          + audio_url + '"\n#EXT-X-STREAM-INF:BANDWIDTH=12000000,RESOLUTION='
                          + str(video['width'])+'x'+str(video['height'])
                          + ',CODECS="'+video['vcodec']+',mp4a.40.2",AUDIO="audio"\n'+video_url+'\n').encode()

        if dlna_target and not fast_ts:
            ffmpeg = binary('ffmpeg')
            if not ffmpeg:
                raise RuntimeError('FFmpeg est nécessaire pour diffuser sur cette TV LG/DLNA. Installe FFmpeg, puis réessaie.')
            mux_directory = tempfile.TemporaryDirectory(prefix='youtube-tv-')
            mux_root = Path(mux_directory.name)
            jobs.update(job_id, _cache=str(mux_root))
            jobs.update(job_id, 'preparing', 'Téléchargement et préparation pour la LG. La TV démarre à la fin.', fraction=0, bytes=0)
            downloaded = {}
            advanced = time.time()
            reported_at = 0
            def download_progress(data):
                nonlocal advanced, reported_at
                jobs.check(job_id)
                detail = data.get('info_dict') or {}
                key = str(detail.get('format_id') or data.get('filename') or 'media')
                amount = data.get('downloaded_bytes') or 0
                if amount > downloaded.get(key, 0): advanced = time.time()
                downloaded[key] = amount
                if time.time() - reported_at < .25 and data.get('status') != 'finished': return
                reported_at = time.time()
                total = data.get('total_bytes') or data.get('total_bytes_estimate')
                audio_track = detail.get('vcodec') == 'none'
                message = 'Téléchargement de la vidéo avec le son…' if video is audio else ('Téléchargement du son (2/2)…' if audio_track else 'Téléchargement de la vidéo (1/2)…')
                jobs.update(job_id, 'downloading', message, bytes=sum(downloaded.values()),
                            fraction=min(.99, amount / total) if total else None,
                            advanced=advanced, stalled=time.time()-advanced > 12)
                if sum(downloaded.values()) > 2 * 1024**3:
                    raise RuntimeError('Cette vidéo dépasse la limite de cache. Réessaie en 480p.')
            options = dict(DEFAULT_YTDL_OPTS)
            options.update(format=str(video['format_id']) if video is audio else str(video['format_id'])+'+'+str(audio['format_id']),
                           outtmpl=str(mux_root / 'source.%(ext)s'), merge_output_format='mp4',
                           ffmpeg_location=ffmpeg, hls_prefer_native=True,
                           concurrent_fragment_downloads=3, skip_unavailable_fragments=False,
                           socket_timeout=10, retries=2, fragment_retries=2, extractor_retries=1,
                           progress_hooks=[download_progress], noprogress=True, quiet=True,
                           source_address='0.0.0.0')
            with yt_dlp.YoutubeDL(options) as downloader:
                downloader.process_ie_result(info, download=True)
            source_file = mux_root / 'source.mp4'
            if not source_file.is_file():
                raise RuntimeError('Le téléchargement n’a pas produit de vidéo complète. Réessaie en 480p.')
            jobs.check(job_id)
            jobs.update(job_id, 'preparing', 'Optimisation du MP4 pour la pause et la reprise…', fraction=None)
            prepared_file = mux_root / 'prepared.mp4'
            mux_process = subprocess.Popen([ffmpeg, '-hide_banner', '-loglevel', 'error', '-nostdin',
                '-i', str(source_file), '-map', '0:v:0', '-map', '0:a:0', '-c', 'copy',
                '-movflags', '+faststart', str(prepared_file)], stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=sys.stdout)
            deadline = time.monotonic() + 120
            while mux_process.poll() is None:
                jobs.check(job_id)
                if time.monotonic() > deadline:
                    raise RuntimeError('L’optimisation du MP4 prend trop de temps. Réessaie avec une qualité inférieure.')
                time.sleep(.25)
            if mux_process.returncode or not prepared_file.is_file():
                raise RuntimeError('La préparation du MP4 compatible LG a échoué.')
            source_file.unlink()
            source_file = prepared_file
            jobs.update(job_id, 'preparing', 'Vidéo MP4 prête pour la LG.', fraction=1)

        class Handler(TransportStreamMixin, MediaFileMixin, BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def allowed(self):
                return self.client_address[0] in (target.host, local_ip, "127.0.0.1") and self.path.startswith("/" + token + "/")

            def do_OPTIONS(self):
                if not self.allowed():
                    self.send_error(403)
                    return
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Headers", "Range, Content-Type")
                self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
                self.end_headers()

            def do_POST(self):
                if not self.allowed() or self.client_address[0] != local_ip or self.path != "/" + token + "/stop":
                    self.send_error(403)
                    return
                self.send_response(200)
                self.end_headers()
                stopping.set()

            def do_HEAD(self):
                self.respond(head=True)

            def do_GET(self):
                self.respond()

            def send_data(self, body, mime, head):
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                if not head:
                    self.wfile.write(body)

            def respond(self, head=False):
                if not self.allowed():
                    self.send_error(403)
                    return
                try:
                    if dlna_target and urlparse(self.path).path == '/' + token + '/stream.ts':
                        counts['requests'] += 1
                        self.send_transport_stream(ffmpeg, video_url if fast_ts else str(source_file), None if not fast_ts or video is audio else audio_url,
                                                   info.get('duration') or 0,stream_processes,stream_lock,sys.stdout)
                        return
                    mux_prefix = '/' + token + '/remux/'
                    if dlna_target and not fast_ts and self.path.startswith(mux_prefix):
                        name = self.path[len(mux_prefix):]
                        if name != 'source.mp4':
                            self.send_error(404)
                            return
                        counts['requests'] += 1
                        counts['bytes'] += self.send_media_file(source_file, head)
                        return
                    if not dlna_target and self.path == "/" + token + "/master.m3u8":
                        self.send_data(master, "application/vnd.apple.mpegurl", head)
                        return
                    key = self.path.removeprefix("/" + token + "/media/")
                    with routes_lock:
                        remote = routes.get(key)
                    if remote is None:
                        self.send_error(404)
                        return
                    headers = {"User-Agent": "Mozilla/5.0"}
                    if self.headers.get("Range"):
                        headers["Range"] = self.headers["Range"]
                    with requests.get(remote, headers=headers, stream=True, timeout=(10, 30)) as upstream:
                        if upstream.status_code not in (200, 206):
                            self.send_error(502, "Media unavailable")
                            return
                        counts["requests"] += 1
                        mime = upstream.headers.get("Content-Type", "application/octet-stream")
                        print("Média", counts["requests"], upstream.status_code, mime, upstream.headers.get("Content-Length", "?"), flush=True)
                        if "mpegurl" in mime or urlparse(remote).path.endswith(".m3u8"):
                            lines = []
                            for line in upstream.text.splitlines():
                                if line and not line.startswith("#"):
                                    line = register(urljoin(remote, line))
                                elif 'URI="' in line:
                                    line = re.sub(r'URI="([^"]+)"', lambda m: 'URI="' + register(urljoin(remote, m[1])) + '"', line)
                                lines.append(line)
                            self.send_data(("\n".join(lines) + "\n").encode(), "application/vnd.apple.mpegurl", head)
                        else:
                            chunks = []
                            size = 0
                            for chunk in upstream.iter_content(65536):
                                size += len(chunk)
                                if size > 32 * 1024 * 1024:
                                    raise RuntimeError("Fragment vidéo trop volumineux")
                                chunks.append(chunk)
                            body = b"".join(chunks)
                            if body.startswith(b"ID3"):
                                mime = "audio/aac"
                            elif body.startswith(b"\x47"):
                                mime = "video/mp2t"
                            self.send_response(upstream.status_code)
                            self.send_header("Content-Type", mime)
                            self.send_header("Content-Length", str(len(body)))
                            self.send_header("Access-Control-Allow-Origin", "*")
                            self.send_header("Access-Control-Expose-Headers", "Content-Length, Content-Range")
                            for name in ("Content-Range", "Accept-Ranges"):
                                if upstream.headers.get(name):
                                    self.send_header(name, upstream.headers[name])
                            self.end_headers()
                            if not head:
                                self.wfile.write(body)
                                counts["bytes"] += len(body)
                            print("Fragment envoyé", len(body), mime, flush=True)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass
                except Exception as exc:
                    print(type(exc).__name__ + ": " + re.sub(r"https?://\S+", "[adresse média]", str(exc)), flush=True)

        jobs.check(job_id)
        jobs.update(job_id, 'sending', 'Connexion du flux vidéo à la TV…' if fast_ts else 'Vidéo prête. Envoi et démarrage sur la TV…', fraction=None if fast_ts else 1, streaming=fast_ts)
        server = ThreadingHTTPServer((local_ip, 0), Handler)
        old_prefix = prefix
        prefix = f'http://{local_ip}:{server.server_port}/{token}'
        if not dlna_target or fast_ts:
            video_url = video_url.replace(old_prefix, prefix, 1)
            if video is not audio:
                audio_url = audio_url.replace(old_prefix, prefix, 1)
            master = master.replace(old_prefix.encode(), prefix.encode())
        server.daemon_threads = True
        threading.Thread(target=server.serve_forever, daemon=True).start()
        stage = "relay"
        if fast_ts:
            jobs.update(job_id, 'sending', 'Vérification du démarrage du flux…', fraction=None, streaming=True)
            with requests.Session() as probe:
                probe.trust_env = False
                with probe.get(prefix+'/stream.ts', stream=True, timeout=(3,20)) as response:
                    response.raise_for_status()
                    first = next(response.iter_content(188*4), b'')
                    if not first or first[0] != 0x47:
                        raise RuntimeError('Le flux rapide n’a pas pu être préparé. Utilise le mode compatible.')
            print('Flux TS prêt avant connexion TV.', flush=True)
        atomic_json(STATE, {"pid": os.getpid(), "local_ip": local_ip, "token": token, "port": server.server_port, "speed_control": True})

        stage = "tv"
        if getattr(target, 'protocol', '') == 'dlna':
            from dlna import DLNAController
            cst = DLNAController(target.details)
        else:
            cst = setup_cast(target.host, controller="default", prep="app")
        media_url = prefix + ("/stream.ts" if fast_ts else ("/remux/source.mp4" if dlna_target else "/master.m3u8"))
        snapshot = {"session_id": uuid.uuid4().hex, "job_id": job_id, "url": url, "device": str(target.uuid),
                    "device_name": device, "title": info.get("title", "YouTube"),
                    "quality": video["height"], "duration": info.get("duration") or 0,
                    "media_url": media_url, "position": position, "state": "BUFFERING", "ended": None}
        snapshot_lock = threading.Lock()
        def save_status(status):
            nonlocal media_url
            try:
                if json.loads(STATE.read_text()).get('token') != token:
                    return
            except (OSError, ValueError):
                return
            with snapshot_lock:
                if status.content_id == prefix + '/stream.ts':
                    media_url = status.content_id
                    snapshot['media_url'] = media_url
                if status.content_id == media_url:
                    snapshot["position"] = max(0, float(status.adjusted_current_time if status.adjusted_current_time is not None else status.current_time or 0))
                    snapshot["state"] = status.player_state
                    snapshot["playback_rate"] = getattr(status, "playback_rate", 1)
                    snapshot["ended"] = status.idle_reason if status.player_state == "IDLE" else None
                elif status.player_state == "IDLE" and snapshot["state"] in ("PLAYING", "PAUSED"):
                    snapshot["state"] = "IDLE"
                    snapshot["ended"] = status.idle_reason or "CANCELLED"
                snapshot["updated"] = time.time()
                atomic_json(PLAYBACK, snapshot)
        class Listener:
            def new_media_status(self, status):
                print("État", status.player_state, status.current_time, status.idle_reason, flush=True)
                save_status(status)
            def load_media_failed(self, queue_item_id, error_code):
                print("Erreur lecteur", error_code, flush=True)
        cst._cast.media_controller.register_status_listener(Listener())
        playback_options = {'duration': info.get('duration') or 0,
                            'resolution': f"{video['width']}x{video['height']}"} if dlna_target else {}
        if fast_ts:
            playback_options['protocol_features'] = 'DLNA.ORG_OP=10;DLNA.ORG_CI=0'
        if dlna_target and not fast_ts:
            playback_options['size'] = source_file.stat().st_size
        cst.play_media_url(media_url, title=info.get("title", "YouTube"),
                           content_type="video/mpeg" if fast_ts else ("video/mp4" if dlna_target else "application/x-mpegURL"), stream_type="BUFFERED",
                           current_time=position,
                           media_info={"hlsSegmentFormat": "aac", "hlsVideoSegmentFormat": "mpeg2_ts"}, **playback_options)
        if not cst.wait_for(["PLAYING"], timeout=35):
            raise RuntimeError(f"La lecture n'a pas démarré (requêtes reçues : {counts['requests']}). Vérifier l'accès réseau local au relais.")
        if dlna_target and position > 0:
            cst._cast.media_controller.seek(position)
        if previous_relay and previous_relay.get('local_ip') == local_ip:
            try:
                requests.post(f"http://{local_ip}:{previous_relay.get('port',45123)}/{previous_relay['token']}/stop",timeout=2)
            except requests.RequestException:
                pass
        atomic_json(result, {"ok": True, "message": f"Lecture confirmée sur {device} : {info.get('title', '')}\n{video['height']}p · piste {(audio.get('language') or 'originale')}\nGarde le Mac allumé pendant la lecture."})
        jobs.update(job_id, 'playing', 'Lecture confirmée par la TV.', fraction=1)
        print("Lecture confirmée.", flush=True)
        save_status(cst._cast.media_controller.status)
        deadline = time.monotonic() + 21600
        terminal_since = None
        failed_since = None
        stop_since = None
        while not stopping.wait(3) and time.monotonic() < deadline:
            try:
                intent = json.loads((ROOT / 'config/playback-intent.json').read_text())
            except (OSError, ValueError):
                intent = {}
            intent_action = intent.get('action') if intent.get('session_id') == snapshot['session_id'] else None
            if intent_action == 'seek' and time.time()-intent.get('updated',0) < 60:
                continue
            if intent_action == 'stop':
                if not dlna_target:
                    break
                stop_since = stop_since or time.monotonic()
                # The LG may still finish its media HTTP requests after Stop.
                if time.monotonic() - stop_since > 30:
                    break
                continue
            stop_since = None
            try:
                cst._cast.media_controller.update_status()
                status = cst._cast.media_controller.status
                failed_since = None
            except (requests.RequestException, ValueError) as error:
                failed_since = failed_since or time.monotonic()
                print('État TV temporairement indisponible : ' + type(error).__name__, flush=True)
                if time.monotonic() - failed_since > 60:
                    raise RuntimeError('La TV ne répond plus depuis une minute. Vérifie la connexion, puis relance la lecture.')
                continue
            save_status(status)
            different_media = bool(status.content_id and status.content_id != media_url)
            inactive = cst._cast.app_id != 'CC1AD845' or different_media or status.player_state == 'IDLE' or not status.content_id
            if dlna_target and intent_action == 'pause' and not different_media:
                # LG can briefly report STOPPED or an empty URI while pausing.
                terminal_since = None
                continue
            if inactive:
                terminal_since = terminal_since or time.monotonic()
                if not dlna_target or time.monotonic() - terminal_since >= 15:
                    break
            else:
                terminal_since = None
        jobs.update(job_id, 'ended', 'Lecture terminée ou arrêtée.')
        print("Relais terminé.", flush=True)
    except Exception as exc:
        message = friendly_error(exc, stage)
        print(type(exc).__name__ + ": " + re.sub(r"https?://\S+", "[adresse média]", str(exc)), flush=True)
        jobs.update(job_id, 'cancelled' if isinstance(exc, jobs.Cancelled) else 'error', message)
        atomic_json(result, {"ok": False, "message": message})
        print(message, flush=True)
    finally:
        with stream_lock:
            for process in list(stream_processes):
                if process.poll() is None:
                    process.terminate()
        if mux_process is not None and mux_process.poll() is None:
            mux_process.terminate()
            try:
                mux_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                mux_process.kill()
                mux_process.wait()
        if server:
            server.shutdown()
            server.server_close()
        if mux_directory is not None:
            mux_directory.cleanup()
        if STATE.exists():
            try:
                if json.loads(STATE.read_text(encoding="utf-8")).get("token") == token:
                    STATE.unlink()
            except (OSError, ValueError):
                pass


if __name__ == "__main__":
    worker(sys.argv[2], Path(sys.argv[3]), float(sys.argv[4]) if len(sys.argv)>4 else 0,
           sys.argv[5] if len(sys.argv)>5 else "", int(sys.argv[6]) if len(sys.argv)>6 else 1080)
