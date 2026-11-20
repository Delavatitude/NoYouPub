"""Real synthetic media check; never contacts YouTube or a TV."""
import argparse,array,io,json,os,subprocess,sys,tempfile,threading
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'source'))
from stream_http import TransportStreamMixin
p=argparse.ArgumentParser();p.add_argument('--ffmpeg',required=True);p.add_argument('--ffprobe',required=True);a=p.parse_args()
class Handler(TransportStreamMixin):
 command='GET';headers={}
 def __init__(self,rate):self.path=f'/synthetic/stream.ts?rate={rate}';self.wfile=io.BytesIO();self.response_headers={}
 def send_response(self,status):self.status=status
 def send_header(self,key,value):self.response_headers[key]=value
 def end_headers(self):pass
 def send_error(self,status):self.status=status
with tempfile.TemporaryDirectory(prefix='noyoupub-media-') as directory:
 d=Path(directory);source=d/'source.mp4'
 subprocess.run([a.ffmpeg,'-v','error','-f','lavfi','-i','testsrc2=size=320x180:rate=30','-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','8','-c:v','h264_videotoolbox','-allow_sw','1','-pix_fmt','yuv420p','-c:a','aac',str(source)],check=True,timeout=30)
 for rate in (.75,1,1.25,1.5,1.75,2):
  h=Handler(rate);processes=set()
  with (d/'ffmpeg.log').open('w') as log:h.send_transport_stream(a.ffmpeg,str(source),None,8,processes,threading.Lock(),log)
  assert not processes
  out=d/f'{rate}.ts';out.write_bytes(h.wfile.getvalue())
  info=json.loads(subprocess.check_output([a.ffprobe,'-v','error','-show_format','-of','json',str(out)],timeout=10));duration=float(info['format']['duration']);assert abs(duration-8/rate)<.25,(rate,duration)
  pcm=subprocess.check_output([a.ffmpeg,'-v','error','-i',str(out),'-ss','1','-t','1','-vn','-ac','1','-ar','16000','-f','s16le','pipe:1'],timeout=10)
  samples=array.array('h',pcm);crossings=sum(x<=0<y for x,y in zip(samples,samples[1:]));assert abs(crossings-440)<10,(rate,crossings)
  print(f'Rate {rate}: duration {duration:.2f}s, tone {crossings}Hz, child cleaned up.')
