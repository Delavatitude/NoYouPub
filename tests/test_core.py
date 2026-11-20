import base64, io, json, os, struct, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
_SANDBOX=tempfile.TemporaryDirectory(prefix='noyoupub-unit-')
os.environ['NOYOUPUB_DATA_DIR']=str(Path(_SANDBOX.name).resolve()/'data')
import runtime_paths, preferences, native_host, setup_core
from i18n import t

class PreferencesAndProtocol(unittest.TestCase):
 def setUp(self):runtime_paths.initialize()
 def test_preserve_settings_and_restart(self):
  preferences.PATH.write_text(json.dumps({'quality':720,'custom':{'keep':True}}))
  preferences.set_language('en')
  self.assertEqual(t('Diffusion arrêtée.'),'Casting stopped.')
  self.assertIn('1:05',t('Déplacement à 1:05…'))
  self.assertEqual(preferences.read()['custom'],{'keep':True})
  r=subprocess.run([sys.executable,str(ROOT/'source/core.py'),'language'],capture_output=True,text=True,check=True)
  self.assertEqual(json.loads(r.stdout)['language'],'en')
  self.assertEqual(preferences.PATH.stat().st_mode&0o777,0o600)
  preferences.set_language('fr')
  self.assertEqual(t('Casting stopped.'),'Diffusion arrêtée.')
 def test_invalid_language_does_not_mutate(self):
  before=preferences.PATH.read_bytes() if preferences.PATH.exists() else b''
  with self.assertRaises(ValueError):preferences.set_language('../../xx')
  self.assertEqual(preferences.PATH.read_bytes() if preferences.PATH.exists() else b'',before)
 def test_catalogs_templates(self):
  import re
  fr=json.loads((ROOT/'source/locales/fr.json').read_text());en=json.loads((ROOT/'source/locales/en.json').read_text())
  self.assertEqual(fr.keys(),en.keys())
  for k in fr:self.assertEqual(sorted(re.findall(r'\{\{[^{}]+\}\}',fr[k])),sorted(re.findall(r'\{\{[^{}]+\}\}',en[k])),k)
 def test_content_not_translated(self):
  r=native_host.localize_response({'ok':True,'message':'Diffusion arrêtée.','session':{'title':'Diffusion arrêtée.'}},'en')
  self.assertEqual(r['session']['title'],'Diffusion arrêtée.')
  self.assertEqual(r['message'],'Casting stopped.')
 def test_framing(self):
  stream=io.BytesIO();native_host.send_message(stream,{'action':'preferences','é':'oui'});stream.seek(0)
  self.assertEqual(native_host.read_message(stream)['é'],'oui')
  for value in (b'x',struct.pack('<I',20000),struct.pack('<I',10)+b'{}',struct.pack('<I',2)+b'[]'):
   with self.assertRaises(ValueError):native_host.read_message(io.BytesIO(value))
 def test_origin_rejected_without_side_effects(self):
  with tempfile.TemporaryDirectory() as d:
   data=Path(d)/'absent';env=os.environ|{'NOYOUPUB_DATA_DIR':str(data)}
   r=subprocess.run([sys.executable,str(ROOT/'source/core.py'),'native-host','chrome-extension://untrusted/'],env=env,capture_output=True)
   self.assertEqual(r.returncode,1);self.assertFalse(data.exists());self.assertFalse(r.stdout)
 def test_native_origin_language_roundtrip(self):
  origin=json.loads((ROOT/'source/extension-identity.json').read_text())['origin']
  payload=io.BytesIO();native_host.send_message(payload,{'action':'set_language','value':'en','requestId':42})
  r=subprocess.run([sys.executable,str(ROOT/'source/core.py'),'native-host',origin],input=payload.getvalue(),capture_output=True,check=True)
  reply=native_host.read_message(io.BytesIO(r.stdout));self.assertEqual(reply['requestId'],42);self.assertTrue(reply['ok'])
 def test_command_validation(self):
  for request in ({'action':'shell'},{'action':'cast','url':'https://example.org/watch?v=aaaaaaaaaaa'},{'action':'seek','position':float('nan')},{'action':'speed','rate':True},{'action':'speed','rate':3},{'action':'volume','value':-1}):
   with self.assertRaises((ValueError,TypeError)):native_host.validate(request)
  for speed in (.75,1,1.25,1.5,1.75,2):self.assertEqual(native_host.validate({'action':'speed','rate':speed}),['speed'])
 def test_legacy_runtime_guard(self):
  with patch.object(runtime_paths,'DATA_ROOT',runtime_paths.LEGACY_ROOT.resolve()):
   with self.assertRaises(RuntimeError):runtime_paths.initialize()

class IsolatedSetup(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='noyoupub-install-');self.base=Path(self.tmp.name).resolve();self.home=self.base/'home';self.home.mkdir()
  self.data=self.home/'Library/Application Support/NoYouPub';self.payload=self.base/'payload'
  for path in ['Core/noyoupub-core','bin/node','bin/ffmpeg','bin/ffprobe']:
   p=self.payload/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('#!/bin/sh\nexit 0\n');p.chmod(0o700)
  p=self.payload/'Extension/manifest.json';p.parent.mkdir();p.write_bytes((ROOT/'source/extension/manifest.json').read_bytes())
  self.args={'home':self.home,'payload':self.payload,'data_root':self.data,'allow_development':True}
 def tearDown(self):self.tmp.cleanup()
 def test_lifecycle_keeps_preferences_and_legacy(self):
  legacy=self.home/'Library/Application Support/YouTube-CATT/config';legacy.mkdir(parents=True);(legacy/'catt.cfg').write_text('legacy intact')
  self.assertTrue(setup_core.register_host(**self.args)['ok'])
  preferences_file=self.data/'config/preferences.json';preferences_file.write_text('{"language":"fr","quality":720}')
  self.assertTrue(setup_core.register_host(**self.args)['ok'])
  manifest=self.home/f'Library/Application Support/Google/Chrome/NativeMessagingHosts/{setup_core.HOST}.json'
  self.assertEqual(len(json.loads(manifest.read_text())['allowed_origins']),1)
  setup_core.unregister(self.home,self.data)
  self.assertFalse(manifest.exists());self.assertTrue(preferences_file.exists());self.assertEqual((legacy/'catt.cfg').read_text(),'legacy intact')
  setup_core.register_host(**self.args)
  self.assertEqual(json.loads(preferences_file.read_text())['quality'],720)
 def test_missing_payload_no_mutation(self):
  (self.payload/'bin/node').unlink()
  with self.assertRaises(RuntimeError):setup_core.register_host(**self.args)
  self.assertFalse(self.data.exists())
 def test_public_payload_rejects_scripts(self):
  with self.assertRaises(RuntimeError):setup_core.verify_payload(self.payload)
 def test_payload_symlink_escape(self):
  (self.payload/'Core/escape').symlink_to(self.home)
  with self.assertRaises(RuntimeError):setup_core.register_host(**self.args)
  self.assertFalse(self.data.exists())
  (self.payload/'Core/escape').unlink()
  (self.payload/'Core/absolute-inside').symlink_to(self.payload/'Core/noyoupub-core')
  with self.assertRaises(RuntimeError):setup_core.register_host(**self.args)
  self.assertFalse(self.data.exists())
 def test_unknown_host_untouched(self):
  p=self.home/f'Library/Application Support/Google/Chrome/NativeMessagingHosts/{setup_core.HOST}.json';p.parent.mkdir(parents=True);p.write_text('{"path":"/unknown"}')
  with self.assertRaises(RuntimeError):setup_core.register_host(**self.args)
  self.assertEqual(p.read_text(),'{"path":"/unknown"}')
 def test_legacy_and_parent_refused(self):
  old=self.home/'Library/Application Support/YouTube-CATT'
  for data in (old,old/'config',old.parent,self.home):
   with self.assertRaises(RuntimeError):setup_core.register_host(**(self.args|{'data_root':data}))
 def test_rollback(self):
  real=Path.write_text
  def fail(path,*a,**kw):
   if path.name=='.installation-id':raise OSError('simulated disk failure')
   return real(path,*a,**kw)
  with patch.object(Path,'write_text',fail):
   with self.assertRaises(OSError):setup_core.register_host(**self.args)
  self.assertFalse((self.data/'core').exists());self.assertFalse((self.data/'native-host').exists())
  setup_core.register_host(**self.args)
 def test_import_is_allowlisted_copy(self):
  old=self.home/'Library/Application Support/YouTube-CATT/config';old.mkdir(parents=True)
  (old/'desktop-last-link.txt').write_text('https://www.youtube.com/watch?v=aaaaaaaaaaa');(old/'last-cast.log').write_text('private')
  result=setup_core.import_legacy(self.home,self.data)
  self.assertEqual(result['copied'],['desktop-last-link.txt']);self.assertFalse((self.data/'config/last-cast.log').exists());self.assertTrue((old/'last-cast.log').exists())
 def test_active_relay_prevents_uninstall(self):
  setup_core.register_host(**self.args);(self.data/'config/relay.json').write_text('{}')
  with self.assertRaises(RuntimeError):setup_core.unregister(self.home,self.data)

class RuntimeLifecycle(unittest.TestCase):
 def test_discovery_identity_and_duplicate_labels(self):
  import cast_control
  from types import SimpleNamespace
  def tv(id,host):return SimpleNamespace(uuid=id,host=host,protocol='dlna',friendly_name='TV',model_name='synthetic')
  with patch.object(cast_control,'discover_infos',return_value=[tv('one','192.0.2.1'),tv('one','192.0.2.2'),tv('two','192.0.2.3')]):
   result=cast_control.discover()
   self.assertEqual(len(result),2);self.assertNotEqual(result[0]['name'],result[1]['name'])
 def test_jobs_stale_update_and_cancel(self):
  import jobs
  job='a'*32;jobs.begin(job,title='Synthetic')
  jobs.update('b'*32,'playing','wrong session')
  self.assertTrue(jobs.read()['busy']);self.assertEqual(jobs.read()['job_id'],job)
  self.assertTrue(jobs.cancel()['ok'])
  with self.assertRaises(jobs.Cancelled):jobs.check(job)
  jobs.update(job,'cancelled','Préparation annulée.');self.assertFalse(jobs.read()['busy'])
 def test_shutdown_uses_control_and_grace(self):
  import core
  state=runtime_paths.DATA_ROOT/'config/playback.json';state.write_text('{"device":"synthetic"}')
  try:
   with patch.object(native_host,'handle',return_value={'ok':True}) as control:
    self.assertTrue(core.shutdown()['ok']);self.assertEqual(control.call_args.args[0],{'action':'stop','device':'synthetic'})
  finally:state.unlink()
 def test_shutdown_rejects_external_endpoint(self):
  import core
  state=runtime_paths.DATA_ROOT/'config/relay.json';state.write_text(json.dumps({'local_ip':'8.8.8.8','token':'a'*32,'port':1234}))
  try:
   with self.assertRaises(ValueError):core.shutdown()
  finally:state.unlink()
 def test_system_language_from_macos(self):
  preferences.system_language.cache_clear()
  with patch.object(preferences.sys,'platform','darwin'),patch.object(preferences.subprocess,'run',return_value=type('Reply',(),{'stdout':'(\n    "fr-FR",\n    "en-US"\n)\n'})()):
   self.assertEqual(preferences.system_language(),'fr')
  preferences.system_language.cache_clear()

class Formats(unittest.TestCase):
 def test_hls_and_dash_modes(self):
  from relay import choose_formats
  def video(id,height,protocol='https',acodec='none',**extra):return dict(format_id=id,height=height,protocol=protocol,vcodec='avc1.4d',acodec=acodec,url='https://media.example.invalid/'+id,**extra)
  audio=dict(format_id='audio',vcodec='none',acodec='mp4a.40.2',protocol='https',url='https://media.example.invalid/audio')
  formats=[video('hls',720,'m3u8_native','mp4a.40.2'),video('small',360,acodec='mp4a.40.2'),video('dash',1080),audio]
  v,a=choose_formats(formats,720,False);self.assertIs(v,a);self.assertEqual(v['format_id'],'hls')
  v,a=choose_formats(formats,1080,False);self.assertEqual(v['format_id'],'dash');self.assertEqual(a['format_id'],'audio')
  v,a=choose_formats(formats,480,False);self.assertEqual(v['height'],360)
  v,a=choose_formats(formats,1080,True);self.assertEqual(v['format_id'],'hls')
  with self.assertRaises(RuntimeError):choose_formats([video('drm',720,has_drm=True),audio],1080,False)

if __name__=='__main__':unittest.main(verbosity=2)
