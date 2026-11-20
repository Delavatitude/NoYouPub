import io, sys, threading
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
from stream_http import TransportStreamMixin, seek_seconds
assert seek_seconds('npt=01:02:03.5-',4000)==3723.5
assert seek_seconds('npt=800-',100)==99.9
for bad in ('bytes=0-1','npt=1:2-','npt=abc-'):
    try: seek_seconds(bad,100)
    except ValueError: pass
    else: raise AssertionError(bad)
class Handler(TransportStreamMixin):
    command='GET'
    path='/secret/stream.ts?start=120'
    headers={'TimeSeekRange.dlna.org':'npt=10-'}
    def __init__(self): self.wfile=io.BytesIO();self.response_headers={}
    def send_response(self,status):self.status=status
    def send_header(self,key,value):self.response_headers[key]=value
    def end_headers(self):pass
    def send_error(self,status):self.status=status
class Process:
    def __init__(self):self.stdout=io.BytesIO(b'\x47'*752);self.running=True
    def poll(self):return None if self.running else 0
    def terminate(self):self.running=False
    def wait(self,timeout=None):return 0
h=Handler();processes=set();p=Process()
with patch('stream_http.subprocess.Popen',return_value=p) as launch:
    h.send_transport_stream('/ffmpeg','/video','/audio',600,processes,threading.Lock(),None)
    args=launch.call_args.args[0]
    assert args.count('-ss')==2 and args.count('130.0')==2,args
assert h.response_headers['TimeSeekRange.dlna.org']=='npt=10.000-480.000/480.000'
assert h.wfile.getvalue()==b'\x47'*752 and not processes and not p.running
h=Handler();h.command='HEAD'
with patch('stream_http.subprocess.Popen') as launch:
    h.send_transport_stream('/ffmpeg','/video',None,600,set(),threading.Lock(),None)
    launch.assert_not_called()
h=Handler();h.headers={'TimeSeekRange.dlna.org':'invalid'}
h.send_transport_stream('/ffmpeg','/video',None,600,set(),threading.Lock(),None)
assert h.status==406
print('Flux rapide : temps de reprise, décalage après déplacement, HEAD et nettoyage du processus vérifiés.')
