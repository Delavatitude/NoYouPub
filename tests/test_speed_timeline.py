from pathlib import Path
from unittest.mock import patch
import sys
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
import dlna
uri='http://192.0.2.1:12345/token/stream.ts?start=120&rate=2'
def soap(device,service,action,**params):
    return {'GetTransportInfo':{'CurrentTransportState':'PLAYING'},'GetPositionInfo':{'TrackURI':uri,'RelTime':'00:00:10','TrackDuration':'00:08:10'},'GetMediaInfo':{'CurrentURI':uri}}[action]
with patch.object(dlna,'soap',soap):
    m=dlna.MediaController(SimpleNamespace(device={}))
    m.update_status()
    assert m.status.current_time==140 and m.status.duration==1100
    assert m.status.playback_rate==2 and m.status.content_id==uri.split('?')[0]
    assert m.status.raw_content_id==uri
from stream_http import TransportStreamMixin
class H(TransportStreamMixin):
    path='/token/stream.ts?start=120&rate=2';command='HEAD';headers={'TimeSeekRange.dlna.org':'npt=10-'}
    def __init__(self):self.response_headers={}
    def send_response(self,s):assert s==200
    def send_header(self,k,v):self.response_headers[k]=v
    def end_headers(self):pass
h=H();h.send_transport_stream('', '', None, 600, None,None,None)
assert h.response_headers['TimeSeekRange.dlna.org']=='npt=10.000-240.000/240.000'
print('×2 après déplacement : position et durée en secondes de la vidéo d’origine, seek HTTP en secondes du flux accéléré : OK.')
