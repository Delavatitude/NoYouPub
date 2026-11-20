"""Local UPnP renderer discovery and a small Cast-compatible control adapter."""
import ipaddress
import json
from pathlib import Path
import socket
import time
from types import SimpleNamespace
from urllib.parse import urlparse, urljoin, parse_qs, urlencode
import uuid
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

import requests

from runtime_paths import DATA_ROOT as ROOT, CODE_ROOT, core_command, binary, initialize
CACHE = ROOT / 'config/dlna-devices.json'
SESSION = requests.Session()
SESSION.trust_env = False


def private_host(value):
    host = str(ipaddress.IPv4Address(value.strip()))
    if not ipaddress.ip_address(host).is_private or ipaddress.ip_address(host).is_loopback or ipaddress.ip_address(host).is_unspecified:
        raise ValueError('Indique une adresse IP locale de TV, par exemple 192.168.1.100.')
    return host


def load():
    try:
        return json.loads(CACHE.read_text())
    except (OSError, ValueError):
        return []


def save(items):
    old = {item['id']: item for item in load()}
    old.update({item['id']: item for item in items})
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    temporary = CACHE.with_suffix('.tmp')
    temporary.write_text(json.dumps(list(old.values()), ensure_ascii=False))
    temporary.replace(CACHE)


def description(location, host):
    host = private_host(host)
    parsed = urlparse(location)
    if parsed.hostname != host or parsed.scheme != 'http':
        return None
    response = SESSION.get(location, timeout=3, allow_redirects=False)
    response.raise_for_status()
    if len(response.content) > 131072:
        raise ValueError('Description TV trop volumineuse.')
    root = ET.fromstring(response.content)
    values = {node.tag.split('}')[-1]: node.text for node in root.iter() if node.tag.split('}')[-1] in ('friendlyName','modelName','UDN')}
    services = {}
    for service in root.iter():
        if service.tag.split('}')[-1] != 'service':
            continue
        fields = {n.tag.split('}')[-1]: n.text for n in service}
        kind = (fields.get('serviceType') or '').split(':')[-2]
        control = urljoin(location, fields.get('controlURL') or '')
        if kind in ('AVTransport','RenderingControl') and urlparse(control).hostname == host:
            services[kind] = {'type': fields['serviceType'], 'url': control}
    if 'AVTransport' not in services:
        return None
    return {'id': str(uuid.UUID((values.get('UDN') or '').removeprefix('uuid:'))),
            'name': values.get('friendlyName') or 'TV DLNA', 'model': values.get('modelName') or '',
            'host': host, 'location': location, 'services': services, 'protocol': 'dlna'}


def discover(timeout=3):
    found = []
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.settimeout(.3)
    try:
        message = b'M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nMAN: "ssdp:discover"\r\nMX: 2\r\nST: urn:schemas-upnp-org:device:MediaRenderer:1\r\n\r\n'
        sock.sendto(message, ('239.255.255.250',1900))
        deadline = time.monotonic() + timeout
        locations = {}
        while time.monotonic() < deadline:
            try:
                body, address = sock.recvfrom(8192)
                headers = dict(line.split(':',1) for line in body.decode(errors='replace').split('\r\n')[1:] if ':' in line)
                for key,value in headers.items():
                    if key.lower() == 'location': locations[value.strip()] = address[0]
            except socket.timeout:
                pass
        for location,host in locations.items():
            try:
                item = description(location,host)
                if item: found.append(item)
            except (OSError, ValueError, ET.ParseError, requests.RequestException):
                continue
    finally:
        sock.close()
    # Direct verification also works when multicast discovery is filtered.
    present = {item['id'] for item in found}
    for known in load():
        if known['id'] in present:
            continue
        try:
            item = description(known['location'], known['host'])
            if item and item['id'] == known['id']:
                found.append(item)
        except (OSError, ValueError, ET.ParseError, requests.RequestException):
            pass
    if found: save(found)
    return found


def infos(items):
    return [SimpleNamespace(uuid=uuid.UUID(d['id']), friendly_name=d['name'], model_name=d['model'], host=d['host'], port=0, protocol='dlna', details=d) for d in items]


def find(device):
    return next((d for d in load() if d['id'] == device or d['name'] == device), None)


def soap(device, service, action, **params):
    target = device['services'].get(service)
    if not target:
        raise ValueError('Cette TV ne propose pas cette commande.')
    fields = ''.join('<'+key+'>'+escape(str(value))+'</'+key+'>' for key,value in params.items())
    body = '<?xml version="1.0"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body><u:'+action+' xmlns:u="'+target['type']+'">'+fields+'</u:'+action+'></s:Body></s:Envelope>'
    # The LG sometimes closes idle keep-alive connections without a reply.
    # Read-only queries can be retried. Commands are verified by their caller.
    for attempt in range(2 if action.startswith('Get') else 1):
        try:
            with requests.Session() as connection:
                connection.trust_env = False
                response = connection.post(target['url'], data=body.encode(),
                    headers={'Content-Type':'text/xml; charset="utf-8"',
                             'SOAPAction':'"'+target['type']+'#'+action+'"', 'Connection':'close'},
                    timeout=20 if action == 'SetAVTransportURI' else (3 if action.startswith('Get') else 5))
            break
        except requests.RequestException:
            if attempt + 1 >= (2 if action.startswith('Get') else 1):
                raise
    root = ET.fromstring(response.content)
    values = {n.tag.split('}')[-1]: n.text or '' for n in root.iter() if not len(n)}
    if response.status_code >= 400:
        raise ValueError('La TV a refusé '+action+' : '+values.get('errorDescription',str(response.status_code)))
    return values


def seconds(value):
    try:
        parts = [float(n) for n in value.split(':')]
        return parts[0]*3600+parts[1]*60+parts[2]
    except (ValueError,IndexError,AttributeError): return 0


class MediaController:
    def __init__(self, cast):
        self.cast = cast
        self.listeners = []
        self.status = SimpleNamespace(player_state='IDLE', content_id='', current_time=0, adjusted_current_time=0, duration=0, stream_type='BUFFERED', idle_reason=None, title='')

    def register_status_listener(self, listener): self.listeners.append(listener)

    def update_status(self, callback_function=None):
        state = soap(self.cast.device,'AVTransport','GetTransportInfo',InstanceID=0)
        position = soap(self.cast.device,'AVTransport','GetPositionInfo',InstanceID=0)
        states = {'PLAYING':'PLAYING','PAUSED_PLAYBACK':'PAUSED','TRANSITIONING':'BUFFERING','STOPPED':'IDLE','NO_MEDIA_PRESENT':'IDLE'}
        self.status.player_state = states.get(state.get('CurrentTransportState'),'IDLE')
        uri = position.get('TrackURI', '')
        if not uri:
            media = soap(self.cast.device, 'AVTransport', 'GetMediaInfo', InstanceID=0)
            uri = media.get('CurrentURI', '')
        self.status.raw_content_id = uri
        stream = urlparse(uri).path.endswith('/stream.ts')
        if stream:
            current = soap(self.cast.device, 'AVTransport', 'GetMediaInfo', InstanceID=0)
            uri = current.get('CurrentURI') or uri
            self.status.raw_content_id = uri
        self.status.playback_rate = float(parse_qs(urlparse(uri).query).get('rate',['1'])[0]) if stream else 1
        offset = float(parse_qs(urlparse(uri).query).get('start',['0'])[0]) if stream else 0
        self.status.content_id = uri.split('?',1)[0] if stream else uri
        self.status.stream_type = 'BUFFERED'
        self.status.current_time = self.status.adjusted_current_time = seconds(position.get('RelTime')) * self.status.playback_rate + offset
        self.status.duration = seconds(position.get('TrackDuration'))
        if self.status.duration: self.status.duration = self.status.duration * self.status.playback_rate + offset
        for listener in self.listeners: listener.new_media_status(self.status)
        if callback_function: callback_function()

    def transport_command(self, action, expected, force=False, **params):
        # LG occasionally returns an error after performing the command.
        error = None
        try:
            initial = soap(self.cast.device, 'AVTransport', 'GetTransportInfo', InstanceID=0)
            if initial.get('CurrentTransportState') in expected and not force:
                return
        except requests.RequestException as exc:
            error = exc
        # A missing acknowledgement is not a refusal: verify the requested state.
        try:
            soap(self.cast.device, 'AVTransport', action, InstanceID=0, **params)
        except (requests.RequestException, ValueError) as exc:
            error = exc
        deadline = time.monotonic() + (35 if action == 'Play' else 15)
        confirmations = 0
        retry_at = time.monotonic() + 3
        retried = False
        while time.monotonic() < deadline:
            try:
                state = soap(self.cast.device, 'AVTransport', 'GetTransportInfo', InstanceID=0)
            except requests.RequestException as exc:
                error = exc
                confirmations = 0
                time.sleep(.4)
                continue
            if state.get('CurrentTransportState') in expected:
                confirmations += 1
                if confirmations >= (2 if action == 'Play' else 1):
                    return
            else:
                confirmations = 0
                # The LG may ignore Play while the new stream is still loading.
                # Retry once after loading; never toggle or repeat Pause/Stop.
                if action == 'Play' and not retried and time.monotonic() >= retry_at and state.get('CurrentTransportState') in {'PAUSED_PLAYBACK', 'STOPPED'}:
                    retried = True
                    try:
                        soap(self.cast.device, 'AVTransport', action, InstanceID=0, **params)
                    except (requests.RequestException, ValueError) as exc:
                        error = exc
            time.sleep(.4)
        if error:
            raise error
        raise ValueError('La TV n’a pas confirmé la commande. Réessaie dans un instant.')

    def play(self): self.transport_command('Play', {'PLAYING'}, Speed=1)
    def pause(self): self.transport_command('Pause', {'PAUSED_PLAYBACK'})
    def stop(self): self.transport_command('Stop', {'STOPPED', 'NO_MEDIA_PRESENT'})
    def restart_at(self, position, paused=False, rate=None):
        self.update_status()
        uri = self.status.raw_content_id
        if urlparse(uri).path.endswith('/remux/source.mp4'):
            uri = uri.replace('/remux/source.mp4','/stream.ts')
        if not urlparse(uri).path.endswith('/stream.ts'):
            raise ValueError('Cette TV ne permet pas de régler la vitesse avec ce lecteur.')
        rate = float(rate if rate is not None else parse_qs(urlparse(uri).query).get('rate',['1'])[0])
        if rate not in (0.75,1,1.25,1.5,1.75,2): raise ValueError('Vitesse invalide.')
        snapshot = json.loads((ROOT/'config/playback.json').read_text())
        duration = snapshot.get('duration') or self.status.duration
        base = uri.split('?',1)[0]
        new_url = base+'?'+urlencode({'start': max(0,min(float(position),max(0,duration-1))), 'rate': rate})
        controller = DLNAController(self.cast.device)
        controller.play_media_url(new_url,title=snapshot.get('title','NoYouPub'),content_type='video/mpeg',
                                  duration=max(0,duration-float(position))/rate, protocol_features='DLNA.ORG_OP=10;DLNA.ORG_CI=0')
        if not controller.wait_for(['PLAYING'],timeout=25):
            raise ValueError('La TV n’a pas confirmé la reprise. Réessaie dans un instant.')
        if paused: controller._cast.media_controller.pause()
        self.update_status()

    def seek(self, position):
        if urlparse(getattr(self.status,'raw_content_id','')).path.endswith('/stream.ts'):
            self.restart_at(position,paused=self.status.player_state=='PAUSED')
            return
        n=int(position)
        soap(self.cast.device,'AVTransport','Seek',InstanceID=0,Unit='REL_TIME',Target=f'{n//3600:02}:{n//60%60:02}:{n%60:02}')


class DLNACast:
    def __init__(self, device):
        self.device=device
        self.uuid=uuid.UUID(device['id'])
        self.name=device['name']
        self.media_controller=MediaController(self)
        self.status=SimpleNamespace(volume_level=0.5,volume_muted=False)
        self.socket_client=SimpleNamespace(is_connected=True, receiver_controller=SimpleNamespace(update_status=self.receiver_status))

    @property
    def app_id(self): return 'CC1AD845'  # Adapter compatibility with ownership checks.
    def wait(self,timeout=10): pass
    def disconnect(self): pass
    def receiver_status(self,callback_function=None):
        if 'RenderingControl' in self.device['services']:
            try:
                volume=soap(self.device,'RenderingControl','GetVolume',InstanceID=0,Channel='Master')
                mute=soap(self.device,'RenderingControl','GetMute',InstanceID=0,Channel='Master')
                self.status.volume_level=float(volume.get('CurrentVolume',50))/100
                self.status.volume_muted=mute.get('CurrentMute')=='1'
            except ValueError:
                self.status.volume_level=None
                self.status.volume_muted=False
        if callback_function: callback_function()
    def set_volume(self,value): soap(self.device,'RenderingControl','SetVolume',InstanceID=0,Channel='Master',DesiredVolume=round(value*100))
    def set_volume_muted(self,value): soap(self.device,'RenderingControl','SetMute',InstanceID=0,Channel='Master',DesiredMute=int(value))


class DLNAController:
    def __init__(self, device): self._cast=DLNACast(device)
    def play_media_url(self,url,title='',content_type='application/x-mpegURL',**kwargs):
        state = soap(self._cast.device,'AVTransport','GetTransportInfo',InstanceID=0)
        if state.get('CurrentTransportState') not in ('STOPPED','NO_MEDIA_PRESENT'):
            self._cast.media_controller.stop()
            time.sleep(.5)
        extra = kwargs.get('duration')
        attributes = 'protocolInfo="http-get:*:' + content_type + ':' + kwargs.get('protocol_features','DLNA.ORG_OP=01;DLNA.ORG_CI=0') + '"'
        if extra is not None:
            milliseconds = int(float(extra) * 1000)
            attributes += f' duration="{milliseconds//3600000:02}:{milliseconds//60000%60:02}:{milliseconds//1000%60:02}.{milliseconds%1000:03}"'
        if kwargs.get('size') is not None:
            attributes += ' size="' + str(int(kwargs['size'])) + '"'
        if kwargs.get('resolution'):
            attributes += ' resolution="' + str(kwargs['resolution']) + '"'
        metadata = '<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/"><item id="0" parentID="-1" restricted="1"><dc:title>'+escape(title)+'</dc:title><upnp:class>object.item.videoItem</upnp:class><res '+attributes+'>'+escape(url)+'</res></item></DIDL-Lite>'

        try:
            soap(self._cast.device,'AVTransport','SetAVTransportURI',InstanceID=0,CurrentURI=url,CurrentURIMetaData=metadata)
        except requests.RequestException:
            # Some LG renderers start loading before replying to this request.
            position = soap(self._cast.device,'AVTransport','GetPositionInfo',InstanceID=0)
            if position.get('TrackURI') != url:
                raise
        self.expected_uri = url
        try:
            self._cast.media_controller.transport_command('Play', {'PLAYING'}, force=True, Speed=1)
        except requests.Timeout:
            state = soap(self._cast.device,'AVTransport','GetTransportInfo',InstanceID=0)
            if state.get('CurrentTransportState') != 'PLAYING':
                raise
    def wait_for(self,states,timeout=35):
        deadline=time.monotonic()+timeout
        confirmed=None
        while time.monotonic()<deadline:
            try:
                self._cast.media_controller.update_status()
                status=self._cast.media_controller.status
                if status.player_state=='PAUSED' and 'PLAYING' in states:
                    self._cast.media_controller.play()
                    confirmed=None
                elif status.player_state in states and getattr(status,'raw_content_id','')==getattr(self,'expected_uri',status.content_id):
                    confirmed=confirmed or time.monotonic()
                    if time.monotonic()-confirmed>=2:
                        return True
                else:
                    confirmed=None
            except (requests.RequestException,ValueError):
                confirmed=None
            time.sleep(.5)
        return False
