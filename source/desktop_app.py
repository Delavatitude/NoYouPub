"""Small command bridge for the native macOS launcher."""
import json
import sys
from pathlib import Path

from runtime_paths import DATA_ROOT as ROOT, CODE_ROOT, initialize
from i18n import t
initialize()
PREFERENCE = ROOT / 'config/desktop-tv.json'


def main():
    from native_host import handle
    action = sys.argv[1]
    if action == 'setup-doctor':
        from setup_core import doctor
        report=doctor()
        print('NoYouPub Core '+report['version'])
        for name,available in report['checks'].items(): print(name+' — '+t('Disponible' if available else 'Manquant'))
        if not report['ok']:raise SystemExit(1)
        return
    if action == 'setup-install':
        from setup_core import register_host
        print(t(register_host()['message']));return
    if action == 'setup-uninstall':
        from setup_core import unregister
        unregister();print(t('Passerelle désactivée. Tes préférences sont conservées.'));return
    if action == 'core-shutdown':
        from core import shutdown
        print(t(shutdown()['message']));return
    if action == 'language':
        from preferences import set_language
        print(json.dumps(set_language(sys.argv[2])));return
    if action in ('progress', 'cancel'):
        result = handle({'action': action})
        from native_host import localize_response
        print(json.dumps(localize_response(result), ensure_ascii=False))
        return
    if action == 'diagnostics':
        import socket
        from cast_control import discover
        from dlna import load
        print('Passerelle : ' + handle({'action': 'ping'})['message'])
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(('192.0.2.1', 9))
            print('Adresse du Mac : ' + sock.getsockname()[0])
        except OSError:
            print('Adresse locale : indisponible')
        finally:
            sock.close()
        devices = discover()
        print('Récepteurs vidéo détectés : ' + str(len(devices)))
        for item in devices: print('• ' + item['name'])
        for item in load(): print('DLNA connu : ' + item['name'] + ' — ' + item['host'])
        chrome = Path.home() / 'Library/Application Support/Google/Chrome'
        installed = False
        for profile in [chrome / 'Default', *chrome.glob('Profile *')]:
            for filename in ('Preferences', 'Secure Preferences'):
                try:
                    settings = json.loads((profile/filename).read_text()).get('extensions',{}).get('settings',{})
                    installed |= 'aeddeohcmmadmmndkmppibmbibpgahca' in settings
                except (OSError, ValueError): pass
        print('Extension Chrome : ' + ('enregistrée dans un profil Chrome' if installed else 'pas encore enregistrée'))
        print('L’extension ajoute un bouton dans YouTube ; elle n’ajoute pas Google Cast à une TV.')
        print('Les TV LG DLNA sont prises en charge ; le mode Rapide lit au fil du téléchargement et le mode Compatible prépare le MP4 complet.')
        return
    if action == 'add-ip':
        from dlna import private_host, description, save
        host = private_host(sys.argv[2])
        try:
            item = description('http://' + host + ':1580/', host)
        except Exception:
            item = None
        if item:
            save([item])
            print('TV DLNA reconnue : ' + item['name'])
            return
        from pychromecast.dial import get_device_info
        info = get_device_info(host, timeout=5)
        if not info or not info.uuid or info.cast_type != 'cast':
            raise ValueError('Aucun récepteur DLNA compatible ou Google Cast reconnu à cette adresse. Vérifie l’adresse et les réglages de partage de la TV.')
        path = ROOT/'config/known-hosts.json'
        hosts = json.loads(path.read_text()) if path.exists() else []
        path.write_text(json.dumps(list(dict.fromkeys(hosts + [host]))[-8:]))
        print('Chromecast ajouté : ' + info.friendly_name)
        return
    if action == 'devices':
        from cast_control import discover
        devices = discover()
        if not devices:
            raise ValueError('Aucune TV Google Cast ou DLNA trouvée. Ouvre le diagnostic réseau pour obtenir plus de détails.')
        for item in devices:
            print(item['name'].replace('\n', ' ') + ' | ' + item['id'])
        return
    if action == 'select':
        import uuid
        label = sys.argv[2]
        device = str(uuid.UUID(label.rsplit(' | ', 1)[1]))
        PREFERENCE.write_text(json.dumps({'device': device, 'label': label}), encoding='utf-8')
        print('TV sélectionnée : ' + label.rsplit(' | ', 1)[0])
        return
    if action == 'ping':
        result = handle({'action': 'ping'})
    else:
        if not PREFERENCE.exists():
            raise ValueError('Choisis d’abord une TV dans le menu de l’application.')
        device = json.loads(PREFERENCE.read_text())['device']
        request = {'action': action, 'device': device}
        if action == 'speed': request['rate'] = float(sys.argv[2])
        if action == 'seek': request['position'] = float(sys.argv[2])
        if action == 'cast':
            request.update(url=sys.argv[2], quality=int(sys.argv[3]) if len(sys.argv)>3 else 1080, position=0)
        result = handle(request)
    if not result.get('ok'):
        raise ValueError(result.get('message', 'La commande a échoué.'))
    print(t(result.get('message', 'Commande effectuée.')))


if __name__ == '__main__':
    try:
        import builtins
        original_print = builtins.print
        def localized_print(*args, **kwargs): original_print(*(t(x) if isinstance(x,str) else x for x in args), **kwargs)
        print = localized_print
        main()
    except Exception as error:
        print(t(str(error)), file=sys.stderr)
        sys.exit(1)
