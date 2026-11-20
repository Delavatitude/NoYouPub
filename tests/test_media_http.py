from pathlib import Path
import sys,tempfile,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import requests
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
from media_http import MediaFileMixin
with tempfile.TemporaryDirectory() as directory:
    path=Path(directory)/'video.mp4'
    content=bytes(range(256))*20
    path.write_bytes(content)
    class Handler(MediaFileMixin,BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):self.send_media_file(path)
        def do_HEAD(self):self.send_media_file(path,head=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    url=f'http://127.0.0.1:{server.server_port}/video.mp4'
    try:
        full=requests.get(url,timeout=2)
        assert full.status_code==200 and full.content==content
        for header,expected in [('bytes=0-31',content[:32]),('bytes=200-',content[200:]),('bytes=-64',content[-64:]),('bytes=5100-9999',content[5100:])]:
            r=requests.get(url,headers={'Range':header},timeout=2)
            assert r.status_code==206 and r.content==expected,(header,r.status_code)
            assert int(r.headers['Content-Length'])==len(expected)
        head=requests.head(url,headers={'Range':'bytes=100-199'},timeout=2)
        assert head.status_code==206 and not head.content and head.headers['Content-Range']=='bytes 100-199/5120'
        for header in ('bytes=99999-','bytes=10-2','bytes=-0','bytes=0-1,3-4','bytes=abc'):
            r=requests.get(url,headers={'Range':header},timeout=2)
            assert r.status_code==416 and r.headers['Content-Range']=='bytes */5120'
        print('MP4 : lecture complète, HEAD, reprise par plage, fin de fichier et plages invalides vérifiés.')
    finally:server.shutdown();server.server_close()
