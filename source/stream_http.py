"""On-demand MPEG-TS delivery with DLNA time seeking."""
import re
import subprocess
from urllib.parse import urlparse, parse_qs


def seek_seconds(header, duration):
    if not header:
        return 0.0
    match = re.match(r'npt=([0-9:.]+)-', header.strip(), re.I)
    if not match:
        raise ValueError('Invalid time seek')
    parts = [float(p) for p in match[1].split(':')]
    if len(parts) not in (1, 3):
        raise ValueError('Invalid time seek')
    value = parts[0] if len(parts)==1 else parts[0]*3600+parts[1]*60+parts[2]
    return max(0, min(value, max(0, duration-.1))) if duration else max(0,value)


class TransportStreamMixin:
    def send_transport_stream(self, ffmpeg, video_url, audio_url, duration, processes, lock, log):
        try:
            clip_start = float(parse_qs(urlparse(self.path).query).get('start',['0'])[0])
            clip_start = max(0,min(clip_start,max(0,duration-.1)))
            rate = float(parse_qs(urlparse(self.path).query).get('rate',['1'])[0])
            if rate not in (0.75,1,1.25,1.5,1.75,2): raise ValueError('Invalid playback rate')
            remaining = max(0,duration-clip_start) / rate
            relative = seek_seconds(self.headers.get('TimeSeekRange.dlna.org'), remaining)
            start = clip_start + relative * rate
        except ValueError:
            self.send_error(406)
            return
        print('TS',self.command,'npt=',start,'Range=',self.headers.get('Range'),flush=True)
        self.send_response(200)
        self.send_header('Content-Type','video/mpeg')
        self.send_header('Connection','close')
        self.send_header('transferMode.dlna.org','Streaming')
        self.send_header('contentFeatures.dlna.org','DLNA.ORG_OP=10;DLNA.ORG_CI=0')
        self.send_header('TimeSeekRange.dlna.org',f'npt={relative:.3f}-{remaining:.3f}/{remaining:.3f}')
        self.send_header('X-Content-Duration',str(remaining))
        self.end_headers()
        self.close_connection = True
        if self.command=='HEAD':
            return
        args=[ffmpeg,'-hide_banner','-loglevel','error','-nostdin']
        if start:args+=['-ss',str(start)]
        input_options = ['-rw_timeout','20000000','-allowed_extensions','ALL','-allowed_segment_extensions','ALL','-extension_picky','0'] if video_url.startswith('http') else []
        args+=input_options+['-i',video_url]
        if audio_url:
            if start:args+=['-ss',str(start)]
            args+=['-rw_timeout','20000000','-allowed_extensions','ALL','-allowed_segment_extensions','ALL','-extension_picky','0','-i',audio_url]
        args+=['-map','0:v:0','-map','1:a:0' if audio_url else '0:a:0']
        if rate == 1:
            args+=['-c','copy']
        else:
            args+=['-vf',f'setpts=(PTS-STARTPTS)/{rate},fps=30',
                   '-af',f'asetpts=PTS-STARTPTS,atempo={rate}',
                   '-c:v','h264_videotoolbox','-allow_sw','1','-realtime','1',
                   '-b:v','6000k','-pix_fmt','yuv420p','-g','60','-c:a','aac','-b:a','160k']
        args+=['-avoid_negative_ts','make_zero','-mpegts_flags','+resend_headers','-muxdelay','0','-f','mpegts','pipe:1']
        process=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=log)
        with lock:processes.add(process)
        try:
            while True:
                data=process.stdout.read(65536)
                if not data:break
                self.wfile.write(data)
        except (BrokenPipeError,ConnectionResetError):
            pass
        finally:
            if process.poll() is None:process.terminate()
            try:process.wait(timeout=3)
            except subprocess.TimeoutExpired:process.kill();process.wait()
            process.stdout.close()
            with lock:processes.discard(process)
