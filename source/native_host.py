"""Chrome Native Messaging: fixed actions only, no local HTTP command API."""
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import math
import uuid

from runtime_paths import DATA_ROOT as ROOT, CODE_ROOT, core_command, binary, initialize


def read_message(stream):
    header = stream.read(4)
    if not header:
        return None
    if len(header) != 4:
        raise ValueError("Message incomplet")
    length = struct.unpack("<I", header)[0]
    if not 0 < length <= 16384:
        raise ValueError("Message trop volumineux")
    body = stream.read(length)
    if len(body) != length:
        raise ValueError("Message incomplet")
    value = json.loads(body.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Message invalide")
    return value


def send_message(stream, message):
    body = json.dumps(message, ensure_ascii=False).encode("utf-8")
    stream.write(struct.pack("<I", len(body)) + body)
    stream.flush()


def validate(request):
    from launcher import youtube_url
    action = request.get("action")
    if action not in ("ping", "cast", "pause", "play", "stop", "status", "devices", "seek", "volume", "mute", "speed"):
        raise ValueError("Commande non autorisée")
    device = request.get("device", "")
    if not isinstance(device, str):
        raise ValueError("TV invalide")
    if device:
        uuid.UUID(device)
    def number(key, maximum):
        value = request.get(key, 0)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= maximum:
            raise ValueError("Valeur invalide : " + key)
        return value
    if action == 'speed':
        value = number('rate', 2)
        if value not in (0.75,1,1.25,1.5,1.75,2): raise ValueError('Vitesse invalide.')
    if action == "seek":
        number("position", 86400)
    if action == "volume":
        number("value", 1)
    if action == "mute" and not isinstance(request.get("muted"), bool):
        raise ValueError("État du son invalide")
    if action == "cast":
        url = youtube_url(request.get("url", ""))
        position = request.get("position", 0)
        if isinstance(position, bool) or not isinstance(position, (int, float)) or not math.isfinite(position) or not 0 <= position <= 86400:
            raise ValueError("Position invalide")
        quality = request.get("quality", 1080)
        if type(quality) is not int or quality not in (360, 480, 720, 1080):
            raise ValueError("Qualité invalide")
        return ["cast", "--seek-to", str(position), "--target", device, "--quality", str(quality), url]
    return [action]


def localize_response(response, lang=None):
    from i18n import t
    value = dict(response)
    if isinstance(value.get('message'), str): value['message'] = t(value['message'], lang)
    if isinstance(value.get('preparation'), dict):
        value['preparation'] = dict(value['preparation'])
        if 'message' in value['preparation']: value['preparation']['message'] = t(value['preparation']['message'], lang)
    return value


def handle(request):
    if request.get('action') == 'preferences':
        from preferences import read, language
        return {'ok': True, 'language_preference': read().get('language', 'system'), 'language': language()}
    if request.get('action') == 'set_language':
        from preferences import set_language
        return {'ok': True, **set_language(request.get('value'))}

    if request.get('action') == 'progress':
        import jobs
        return {'ok': True, 'preparation': jobs.read()}
    if request.get('action') == 'cancel':
        import jobs
        return jobs.cancel()
    args = validate(request)
    if args[0] == "ping":
        from catt_local import configure
        from importlib.metadata import version
        device = configure().get_config_as_dict()["options"]["device"]
        return {"ok": True, "device": device, "version": version("catt"), "message": "NoYouPub connecté."}
    if args[0] == "devices":
        from cast_control import discover
        return {"ok": True, "devices": discover()}
    if args[0] == "status":
        from cast_control import status
        return {"ok": True, "state": status(request.get("device", ""))}
    if args[0] != "cast":
        from cast_control import control
        return control(request)
    lock = None
    try:
        if args[0] == "cast":
            import fcntl
            lock = open(ROOT / "config" / "chrome-cast.lock", "a+b")
            if lock.tell() == 0:
                lock.write(b"0"); lock.flush()
            lock.seek(0)
            try: fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError: return {"ok": False, "message": "Une vidéo est déjà en cours de préparation."}
        if args[0] == "status":
            args = ["info", "--json-output"]
        result = subprocess.run(
            core_command("catt", *args),
            cwd=ROOT, capture_output=True, encoding="utf-8", errors="replace", timeout=660,
            env=os.environ | {"PYTHONUTF8": "1"},
        )
        if result.returncode:
            return {"ok":False, "message":(result.stdout + result.stderr).strip()[-2500:] or "La commande a échoué."}
        if request["action"] == "status":
            state=json.loads(result.stdout)
            return {"ok":True, "state":{key:state.get(key) for key in ("player_state","current_time","duration","display_name")}}
        messages={"pause":"Lecture en pause sur la TV.","play":"Lecture reprise sur la TV.","stop":"Diffusion arrêtée."}
        from cast_control import playback
        saved = playback()
        return {"ok":True, "message":messages.get(request["action"],result.stdout.strip()),
                "session": {key: saved.get(key) for key in ("session_id", "device", "device_name", "title", "quality", "duration")}}
    finally:
        if lock:
            lock.close()


def main():
    if os.name == "nt":  # Allows protocol checks on Windows as well.
        import msvcrt
        msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    expected = json.loads((CODE_ROOT / "extension-identity.json").read_text(encoding="utf-8"))["origin"]
    if len(sys.argv) < 2 or sys.argv[1] != expected:
        return 1
    initialize()
    while True:
        request = None
        try:
            request = read_message(sys.stdin.buffer)
            if request is None: return 0
            response = localize_response(handle(request), request.get("language"))
        except Exception as error:
            from i18n import t
            response = {"ok":False, "message":t(str(error))[:2000]}
        response["requestId"] = request.get("requestId") if isinstance(request, dict) else None
        send_message(sys.stdout.buffer,response)


if __name__ == "__main__":
    raise SystemExit(main())
