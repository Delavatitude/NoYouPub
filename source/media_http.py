"""Byte-range delivery for the LG's native MP4 player."""
import re


class MediaFileMixin:
    def send_media_file(self, path, head=False):
        size = path.stat().st_size
        start, end, partial = 0, size - 1, False
        header = self.headers.get('Range')
        print('MP4 ' + self.command + ' Range=' + str(header or 'complet'), flush=True)
        if header:
            match = re.fullmatch(r'bytes=(\d*)-(\d*)', header.strip())
            valid = bool(match and (match[1] or match[2]) and size)
            if valid:
                if match[1]:
                    start = int(match[1])
                    end = min(int(match[2]), size - 1) if match[2] else size - 1
                    valid = start < size and end >= start
                else:
                    suffix = int(match[2])
                    valid = suffix > 0
                    start, end = max(0, size - suffix), size - 1
            if not valid:
                self.send_response(416)
                self.send_header('Content-Range', f'bytes */{size}')
                self.send_header('Content-Length', '0')
                self.end_headers()
                return 0
            partial = True
        length = max(0, end - start + 1)
        self.send_response(206 if partial else 200)
        self.send_header('Content-Type', 'video/mp4')
        self.send_header('Content-Length', str(length))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('transferMode.dlna.org', 'Streaming')
        self.send_header('contentFeatures.dlna.org', 'DLNA.ORG_OP=01;DLNA.ORG_CI=0')
        if partial:
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.end_headers()
        if head:
            return 0
        written = 0
        with path.open('rb') as media:
            media.seek(start)
            while written < length:
                chunk = media.read(min(65536, length - written))
                if not chunk:
                    break
                self.wfile.write(chunk)
                written += len(chunk)
        return written
