"""On-demand NoYouPub Core. No daemon or unauthenticated HTTP control socket."""
import argparse
import json
import os
import runpy
import signal
import sys
from runtime_paths import CODE_ROOT, DATA_ROOT, initialize

def shutdown():
    # Stop the TV first and let the relay honor its normal LG shutdown grace.
    try:
        from native_host import handle
        saved=json.loads((DATA_ROOT/'config/playback.json').read_text())
        if saved.get('device'):
            response=handle({'action':'stop','device':saved['device']})
            if response.get('ok'):return {'ok':True,'message':'Playback stopped; the relay will close after its normal grace period.'}
    except Exception:
        pass
    # Stop through the authenticated local relay endpoint, not an untrusted PID.
    from urllib.request import Request, build_opener, ProxyHandler
    try: state=json.loads((DATA_ROOT/'config/relay.json').read_text())
    except (OSError,ValueError): return {'ok':True,'message':'No relay is running.'}
    import ipaddress,re
    host=ipaddress.ip_address(state['local_ip']);token=state['token'];port=int(state['port'])
    if not host.is_private or not re.fullmatch('[A-Za-z0-9_-]{20,80}',token) or not 1<=port<=65535:raise ValueError('Invalid relay state')
    with build_opener(ProxyHandler({})).open(Request(f'http://{host}:{port}/{token}/stop',data=b'',method='POST'),timeout=4) as response:
        return {'ok':response.status==200,'message':'Relay shutdown requested.'}

def main(argv=None):
    args=list(sys.argv[1:] if argv is None else argv)
    if args and args[0]=='relay-worker':
        import relay
        from pathlib import Path
        return relay.worker(args[1],Path(args[2]),float(args[3]),args[4],int(args[5]))
    if args and args[0]=='desktop':
        sys.argv=[str(CODE_ROOT/'desktop_app.py'),*args[1:]]
        runpy.run_module('desktop_app',run_name='__main__');return 0
    if args and args[0]=='setup':
        sys.argv=[str(CODE_ROOT/'installer.py'),*args[1:]]
        import installer
        return installer.main()
    if args and args[0]=='catt':
        sys.argv=[str(CODE_ROOT/'catt_local.py'),*args[1:]]
        runpy.run_module('catt_local',run_name='__main__');return 0
    if args and args[0]=='native-host':
        sys.argv=[str(CODE_ROOT/'native_host.py'),*args[1:]]
        import native_host
        return native_host.main()
    parser=argparse.ArgumentParser(description='NoYouPub Core 3.0 (local beta preparation)')
    parser.add_argument('action',choices=('doctor','request','shutdown','language'))
    parser.add_argument('value',nargs='?')
    options=parser.parse_args(args);initialize()
    if options.action=='doctor':
        from setup_core import doctor
        response=doctor()
    elif options.action=='shutdown': response=shutdown()
    elif options.action=='language':
        from preferences import read,set_language,language
        response=set_language(options.value) if options.value else {'language':read().get('language','system'),'resolved_language':language()}
    else:
        from native_host import handle,localize_response
        request=json.loads(options.value or sys.stdin.read())
        if not isinstance(request,dict):raise ValueError('Request must be an object')
        response=localize_response(handle(request),request.get('language'))
    print(json.dumps(response,ensure_ascii=False));return 0

if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as error:
        from i18n import t
        print(json.dumps({'ok':False,'message':t(str(error))},ensure_ascii=False),file=sys.stderr);raise SystemExit(1)
