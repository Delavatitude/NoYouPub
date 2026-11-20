import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
import dlna, requests
class Clock:
    def __init__(self):self.n=0
    def tick(self):self.n+=1;return self.n
for action,start,end,exc in [('pause','PLAYING','PAUSED_PLAYBACK',ValueError('Action Failed')),('play','PAUSED_PLAYBACK','PLAYING',requests.Timeout('ack lost')),('stop','PLAYING','STOPPED',ValueError('Transition not available'))]:
    changed=False
    def soap(device,service,method,**params):
        global changed
        if method=='GetTransportInfo':return {'CurrentTransportState':end if changed else start}
        changed=True
        raise exc
    clock=Clock()
    with patch.object(dlna,'soap',soap),patch.object(dlna.time,'monotonic',clock.tick),patch.object(dlna.time,'sleep',lambda _:None):
        media=dlna.MediaController(type('Cast',(),{'device':{}})())
        getattr(media,action)()
clock=Clock()
def refused(device,service,method,**params):
    if method=='GetTransportInfo':return {'CurrentTransportState':'PLAYING'}
    raise ValueError('Action Failed')
with patch.object(dlna,'soap',refused),patch.object(dlna.time,'monotonic',clock.tick),patch.object(dlna.time,'sleep',lambda _:None):
    try:dlna.MediaController(type('Cast',(),{'device':{}})()).pause()
    except ValueError:pass
    else:raise AssertionError('Un refus réel ne doit pas être annoncé comme une réussite')
print('Réponses LG ambiguës : état réel vérifié ; refus réel conservé comme erreur.')
# A first Play can be ignored while the LG is loading a replacement stream.
plays=0
clock=Clock()
def loading(device,service,method,**params):
    global plays
    if method=='GetTransportInfo':return {'CurrentTransportState':'PLAYING' if plays>=2 else 'PAUSED_PLAYBACK'}
    if method=='Play':plays+=1
    return {}
with patch.object(dlna,'soap',loading),patch.object(dlna.time,'monotonic',clock.tick),patch.object(dlna.time,'sleep',lambda _:None):
    dlna.MediaController(type('Cast',(),{'device':{}})()).play()
assert plays==2
print('Play ignoré pendant le chargement : une relance bornée, puis confirmation de lecture.')

# Acknowledgements and status reads may both time out while the LG loads media.
reads=0; commands=[]; clock=Clock()
def intermittent(device,service,method,**params):
    global reads
    if method=='GetTransportInfo':
        reads+=1
        if reads<=3:raise requests.ReadTimeout('temporary LG delay')
        return {'CurrentTransportState':'PLAYING'}
    commands.append(method)
    raise requests.ReadTimeout('ack lost')
with patch.object(dlna,'soap',intermittent),patch.object(dlna.time,'monotonic',clock.tick),patch.object(dlna.time,'sleep',lambda _:None):
    dlna.MediaController(type('Cast',(),{'device':{}})()).play()
assert commands==['Play'] and reads>=5
print('Retards de réponse LG : lecture confirmée après les timeouts, sans renvoyer la vidéo.')
# A permanently unreachable TV must still fail within a bounded polling window.
clock=Clock();commands=[]
def unreachable(device,service,method,**params):
    if not method.startswith('Get'):commands.append(method)
    raise requests.ReadTimeout('TV unavailable')
with patch.object(dlna,'soap',unreachable),patch.object(dlna.time,'monotonic',clock.tick),patch.object(dlna.time,'sleep',lambda _:None):
    try:dlna.MediaController(type('Cast',(),{'device':{}})()).pause()
    except requests.ReadTimeout:pass
    else:raise AssertionError('Une TV inaccessible ne doit pas être annoncée en pause')
assert commands==['Pause'] and clock.n<30
print('TV inaccessible : échec borné et aucune répétition de Pause.')

# Some LG receivers retain the previous URI and position after acknowledging Stop.
import json
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import cast_control

def ack(callback_function):
    callback_function()

with TemporaryDirectory(prefix='noyoupub-stop-') as directory:
    root = Path(directory)
    config = root / 'config'
    config.mkdir()
    saved_path = config / 'playback.json'
    intent_path = config / 'playback-intent.json'
    url = 'http://localhost/media'
    snapshot = {'device': 'test-tv', 'session_id': 'session-one', 'media_url': url,
                'title': 'Old video', 'url': 'https://www.youtube.com/watch?v=aqz-KE-bpKQ',
                'duration': 600, 'position': 42, 'state': 'PLAYING', 'updated': 1, 'quality': 480}
    saved_path.write_text(json.dumps(snapshot))
    player = SimpleNamespace(player_state='PLAYING', content_id=url, duration=600, title='Old video',
                             adjusted_current_time=42, current_time=42, playback_rate=1.5,
                             stream_type='BUFFERED', idle_reason=None)
    media = SimpleNamespace(status=player, update_status=ack,
                            stop=lambda: setattr(player, 'player_state', 'IDLE'))
    receiver = SimpleNamespace(volume_level=0.3, volume_muted=False)
    cast = SimpleNamespace(uuid='test-tv', name='Test LG', app_id='CC1AD845', status=receiver,
                           media_controller=media, socket_client=SimpleNamespace(
                               receiver_controller=SimpleNamespace(update_status=ack)))
    with patch.object(cast_control, 'ROOT', root), patch.object(cast_control, 'connect', return_value=cast):
        with patch.object(media, 'stop', side_effect=ValueError('Stop refused')):
            try:
                cast_control.control({'action': 'stop', 'device': 'test-tv'})
            except ValueError:
                assert cast_control.status('test-tv')['owned']
            else:
                raise AssertionError('A failed stop must not retire live playback')
        result = cast_control.control({'action': 'stop', 'device': 'test-tv'})
        assert result['ok']
        for state in (result['state'], cast_control.status('test-tv')):
            assert state['player_state'] == 'IDLE'
            assert not state['owned'] and not state['relay_stale']
            assert state['title'] == '' and state['video_url'] is None and state['session_id'] is None
            assert state['current_time'] == state['duration'] == 0 and state['playback_rate'] == 1
        assert json.loads(saved_path.read_text())['state'] == 'IDLE'
        assert json.loads(intent_path.read_text())['action'] == 'stop'

        # A stale PLAYING observation cannot revive an acknowledged stop.
        player.player_state = 'PLAYING'
        assert not cast_control.status('test-tv')['owned']
        # A new session and its natural finish remain available to the queue.
        saved_path.write_text(json.dumps(dict(snapshot, session_id='session-two')))
        assert cast_control.status('test-tv')['owned']
        player.player_state = 'IDLE'
        player.idle_reason = 'FINISHED'
        finished = cast_control.status('test-tv')
        assert finished['owned'] and finished['session_id'] == 'session-two'
        assert finished['idle_reason'] == 'FINISHED'
print('Arrêt LG : ancienne URI neutralisée, nouvelle session et fin naturelle préservées.')
