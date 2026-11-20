"""YouTube URL validation; no desktop GUI dependency."""
from urllib.parse import urlparse, parse_qs, urlencode

def youtube_url(value):
    value = value.strip()
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in ("http", "https") or parsed.username or parsed.password:
        raise ValueError("Colle un lien YouTube complet (https://...).")
    if host == "youtu.be":
        video_id = parsed.path.strip("/").split("/")[0]
    elif host in ("youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"):
        parts = parsed.path.strip("/").split("/")
        video_id = parse_qs(parsed.query).get("v", [""])[0]
        if len(parts) == 2 and parts[0] in ("shorts", "live", "embed"):
            video_id = parts[1]
    else:
        raise ValueError("Ce lanceur accepte uniquement les liens de vidéos YouTube.")
    import re
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise ValueError("Le lien doit désigner une vidéo, pas une chaîne ou une playlist seule.")
    return "https://www.youtube.com/watch?" + urlencode({"v": video_id})

