"""Persistent Chromecast connection used only by the authorized native host."""
import json
import requests
from pathlib import Path
import threading
import time
import uuid

from runtime_paths import DATA_ROOT as ROOT, CODE_ROOT, core_command, binary, initialize
connections = {}
last_audible = {}


def default_device():
    from catt_local import configure
    return configure().get_config_as_dict()["options"]["device"]


def discover_infos():
    from concurrent.futures import ThreadPoolExecutor
    from pychromecast.discovery import discover_chromecasts
    import dlna
    try:
        hosts = json.loads((ROOT / 'config/known-hosts.json').read_text())
    except (OSError, ValueError):
        hosts = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        renderers = pool.submit(dlna.discover)
        infos, browser = discover_chromecasts(timeout=8, known_hosts=hosts)
        try:
            result = [item for item in infos if item.cast_type == 'cast']
        finally:
            browser.stop_discovery()
        return result + dlna.infos(renderers.result())


def discover():
    from collections import Counter
    # One identity may be advertised at multiple UPnP locations. Different
    # identities with the same friendly name must remain separate choices.
    items = list({(getattr(item, 'protocol', 'cast'), str(item.uuid)): item
                  for item in discover_infos()}.values())
    names = Counter(item.friendly_name for item in items)
    devices = []
    for item in items:
        label = item.friendly_name + (' · LG/DLNA' if getattr(item, 'protocol', '') == 'dlna' else '')
        if names[item.friendly_name] > 1:
            label += ' · ' + str(item.host)
        devices.append({'id': str(item.uuid), 'name': label, 'model': item.model_name})
    return sorted(devices, key=lambda item: item['name'])


def connect(device):
    key = device or default_device()
    import dlna
    renderer = dlna.find(key)
    if renderer:
        cast = connections.get(key)
        if not isinstance(cast, dlna.DLNACast) or cast.device != renderer:
            cast = dlna.DLNACast(renderer)
            connections[key] = cast
        return cast
    cast = connections.get(key)
    if cast and cast.socket_client.is_connected:
        return cast
    if cast:
        cast.disconnect()
        connections.pop(key, None)
    import pychromecast
    from pychromecast.discovery import discover_listed_chromecasts
    try:
        device_uuid = uuid.UUID(key)
    except ValueError:
        device_uuid = None
    infos, browser = discover_listed_chromecasts(
        uuids=[device_uuid] if device_uuid else None,
        friendly_names=None if device_uuid else [key], discovery_timeout=5)
    try:
        if len(infos) != 1:
            raise ValueError("Chromecast introuvable ou nom ambigu. Actualise la liste des TV.")
        cast = pychromecast.get_chromecast_from_cast_info(infos[0], browser.zc)
        cast.wait(timeout=10)
        if not cast.socket_client.is_connected:
            raise RuntimeError("La TV ne répond pas.")
        connections[key] = cast
        return cast
    finally:
        browser.stop_discovery()


def playback():
    try:
        return json.loads((ROOT / "config/playback.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def status(device):
    cast = connect(device)
    receiver_ready = threading.Event()
    cast.socket_client.receiver_controller.update_status(callback_function=lambda *_: receiver_ready.set())
    if not receiver_ready.wait(5):
        raise RuntimeError("La TV ne répond pas à la demande de volume.")
    media = cast.media_controller
    if cast.app_id == "CC1AD845":
        ready = threading.Event()
        media.update_status(callback_function=lambda *_: ready.set())
        if not ready.wait(5):
            raise RuntimeError("La TV ne répond pas à la demande d’état.")
    state, receiver = media.status, cast.status
    saved = playback()
    same_device = saved.get("device") == str(cast.uuid)
    owned = same_device and cast.app_id == "CC1AD845" and state.content_id == saved.get("media_url")
    # Keep controls working for a relay launched before this version was installed.
    if not saved and cast.app_id == "CC1AD845":
        try:
            legacy = json.loads((ROOT / "config/relay.json").read_text(encoding="utf-8"))
            owned = state.content_id == f"http://{legacy['local_ip']}:45123/{legacy['token']}/master.m3u8"
        except (OSError, ValueError, KeyError):
            pass
    saved = saved if same_device else {}
    player_state = state.player_state if cast.app_id == "CC1AD845" else "IDLE"
    stopped = False
    if saved.get("session_id") and (player_state == "IDLE" or saved.get("ended") == "CANCELLED"):
        try:
            intent = json.loads((ROOT / "config/playback-intent.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            intent = {}
        stopped = intent.get("action") == "stop" and intent.get("session_id") == saved["session_id"]
    if stopped:
        # LG can keep the previous media URI and timeline after confirming Stop.
        player_state = "IDLE"
        owned = False
    position = 0 if stopped else state.adjusted_current_time or state.current_time or 0
    rate = 1 if stopped else getattr(state, "playback_rate", 1)
    if receiver and receiver.volume_level is not None and receiver.volume_level > 0:
        last_audible[str(cast.uuid)] = receiver.volume_level
    if owned or stopped:
        # Share fresh command observations with the desktop UI without changing
        # the relay heartbeat used to detect a stalled media worker.
        try:
            current = playback()
            if current.get('session_id') == saved.get('session_id'):
                current.update(position=position, state=player_state,
                               observed_at=time.time(), playback_rate=rate)
                if stopped:
                    current.update(duration=0, title=None, ended="CANCELLED")
                target = ROOT/'config/playback.json'
                temporary = target.with_suffix('.' + uuid.uuid4().hex + '.tmp')
                temporary.write_text(json.dumps(current, ensure_ascii=False))
                temporary.replace(target)
        except OSError:
            pass
    return {"player_state": player_state,
            "current_time": position,
            "duration": 0 if stopped else state.duration or (saved.get("duration", 0) if owned else 0),
            "playback_rate": rate,
            "live": not stopped and state.stream_type == "LIVE", "owned": owned,
            "app_id": cast.app_id, "idle_reason": "CANCELLED" if stopped else state.idle_reason,
            "volume": receiver.volume_level if receiver else None,
            "muted": receiver.volume_muted if receiver else False,
            "device": str(cast.uuid), "device_name": cast.name,
            "title": saved.get("title", state.title or "") if owned else "",
            "session_id": None if stopped else saved.get("session_id"),
            "ended": "CANCELLED" if stopped else saved.get("ended"),
            "quality": None if stopped else saved.get("quality"),
            "video_url": saved.get("url") if owned else None,
            "relay_stale": owned and time.time() - saved.get("updated", 0) > 20}


def control(request):
    device, action = request.get("device", ""), request["action"]
    state = status(device)
    cast = connect(device)
    media = cast.media_controller
    if action not in ("volume", "mute") and not state["owned"]:
        raise ValueError("Lance une vidéo avec « Diffuser sur ma TV » pour la piloter ici.")
    is_stream = '/stream.ts' in getattr(media.status, 'raw_content_id', '')
    if action in ('pause', 'play', 'stop', 'seek', 'speed'):
        intent = {'session_id': state.get('session_id'), 'action': 'seek' if action == 'speed' or is_stream and action in ('seek','play') else action, 'updated': time.time()}
        path = ROOT / 'config/playback-intent.json'
        temporary = path.with_suffix('.' + uuid.uuid4().hex + '.tmp')
        temporary.write_text(json.dumps(intent), encoding='utf-8')
        temporary.replace(path)
    if action == 'speed':
        try:
            supported = json.loads((ROOT/'config/relay.json').read_text()).get('speed_control', False)
        except (OSError, ValueError):
            supported = False
        if not supported:
            raise ValueError('Relance cette vidéo avec NoYouPub pour activer le réglage de vitesse.')
        if not hasattr(media, 'restart_at'):
            raise ValueError('Le réglage de vitesse est actuellement disponible sur la TV LG/DLNA.')
        media.restart_at(state['current_time'], paused=state['player_state']=='PAUSED', rate=request['rate'])
    elif action == "seek":
        if state["live"] or not state["duration"]:
            raise ValueError("Le déplacement n’est pas disponible pour cette vidéo.")
        paused = state["player_state"] == "PAUSED"
        media.seek(min(request["position"], max(0, state["duration"] - 1)))
        if paused:
            media.pause()
    elif action == 'play' and is_stream and state['player_state'] != 'PLAYING':
        try:
            media.play()
        except (requests.RequestException, ValueError):
            media.restart_at(state['current_time'])
    elif action == "volume":
        cast.set_volume(request["value"])
        if request["value"] > 0 and state["muted"]:
            cast.set_volume_muted(False)
    elif action == "mute":
        if not request["muted"] and state["volume"] == 0:
            cast.set_volume(last_audible.get(str(cast.uuid), 0.25))
        cast.set_volume_muted(request["muted"])
    else:
        getattr(media, action)()
    if action == 'speed' or is_stream and action in ('seek','play'):
        intent['action'] = 'pause' if action in ('seek','speed') and state['player_state'] == 'PAUSED' else 'play'
        temporary = path.with_suffix('.' + uuid.uuid4().hex + '.tmp')
        temporary.write_text(json.dumps(intent), encoding='utf-8')
        temporary.replace(path)
    return {"ok": True, "state": status(device), "message": {
        "pause": "Lecture en pause sur la TV.", "play": "Lecture reprise sur la TV.",
        "stop": "Diffusion arrêtée.", "seek": "Position mise à jour.",
        "speed": "Vitesse de lecture mise à jour.",
        "volume": "Volume mis à jour.", "mute": "Son mis à jour."
    }[action]}
