importScripts('page_state.js');
const HOST = 'fr.local.noyoupub_v3';
const ACTIONS = new Set(['progress','cancel','ping','cast','pause','play','stop','status','devices','seek','volume','mute','speed','settings','enqueue','enqueueVideo','remove','clear','next','previous','resume','mode','language']);
let data = {languagePreference:'follow_app',sharedLanguage:null,device:'',quality:720,queue:[],history:[],last:null};
const tabModes = new Map();
const tabPages = new Map();
function modeForPage(tabId,pageURL,result) {
  return NoYouPubPage.remoteForPage(pageURL,result,tabModes.get(tabId)) ? 'remote' : 'local';
}

let port, serial=0, busy=false, polling=false, timer, lastState=null, problem='', failures=0, retries=0, nextRetry=0;
let pollFinished=Promise.resolve();
const pending = new Map();
const ready = chrome.storage.local.get('catt').then(saved => { if(saved.catt) data={...data,...saved.catt}; });
const save = () => chrome.storage.local.set({catt:data});
function language() {
  const browser=(chrome.i18n?.getUILanguage?.()||'en').startsWith('fr')?'fr':'en';
  return data.languagePreference==='follow_app'?(data.sharedLanguage||browser):data.languagePreference==='system'?browser:data.languagePreference;
}
function videoURL(value) {
  const url = new URL(value);
  if(url.protocol!=='https:' || !['www.youtube.com','youtube.com'].includes(url.hostname) || url.username || url.password) throw new Error('Page YouTube requise.');
  const id=url.pathname==='/watch'?url.searchParams.get('v'):url.pathname.match(/^\/(?:shorts|live)\/([\w-]{11})$/)?.[1];
  if(!/^[\w-]{11}$/.test(id||'')) throw new Error('Ouvre une vidéo YouTube.');
  return `https://www.youtube.com/watch?v=${id}`;
}
function validate(message,sender) {
  if(sender.id!==chrome.runtime.id || sender.frameId!==0 || !sender.tab || new URL(sender.url).origin!=='https://www.youtube.com') throw new Error('Origine non autorisée.');
  if(!message || !ACTIONS.has(message.action)) throw new Error('Commande non autorisée.');
  const request={action:message.action};
  if(['cast','enqueue'].includes(message.action)) {
    request.url=videoURL(sender.tab.url||sender.url);
    if(request.url!==videoURL(message.url) || request.url!==videoURL(sender.tab.url)) throw new Error('La vidéo a changé. Réessaie.');
    request.position=Number.isFinite(message.position)?Math.min(86400,Math.max(0,message.position)):0;
    request.title=typeof message.title==='string'?message.title.slice(0,200):'Vidéo YouTube';
  }
  if(message.action==='enqueueVideo') {
    request.url=videoURL(message.url);
    request.title=typeof message.title==='string'?message.title.slice(0,200):'Vidéo YouTube';
  }
  if(message.action==='language'){if(!['follow_app','system','fr','en'].includes(message.value))throw new Error('Invalid language');request.value=message.value;}
  if(message.action==='mode') {
    if(!['local','remote','auto'].includes(message.mode))throw new Error('Mode invalide.');
    request.mode=message.mode;
  }
  if(message.action==='settings') {
    if(typeof message.device!=='string' || (message.device && !/^[\da-f]{8}(-[\da-f]{4}){3}-[\da-f]{12}$/i.test(message.device))) throw new Error('TV invalide.');
    if(![360,480,720,1080].includes(message.quality)) throw new Error('Qualité invalide.');
    request.device=message.device; request.quality=message.quality;
  }
  for(const [action,key,max] of [['seek','position',86400],['volume','value',1]]) if(message.action===action) {
    if(!Number.isFinite(message[key]) || message[key]<0 || message[key]>max) throw new Error('Valeur invalide.');
    request[key]=message[key];
  }
  if(message.action==='speed') {if(![0.75,1,1.25,1.5,1.75,2].includes(message.rate))throw new Error('Vitesse invalide.');request.rate=message.rate;}
  if(message.action==='mute') {if(typeof message.muted!=='boolean') throw new Error('État du son invalide.');request.muted=message.muted;}
  if(message.action==='remove') {if(typeof message.id!=='string') throw new Error('Vidéo invalide.');request.id=message.id;}
  return request;
}
function ensurePort() {
  if(port) return;
  const connected=chrome.runtime.connectNative(HOST); port=connected;
  connected.onMessage.addListener(result=>{
    const task=pending.get(result.requestId); if(!task)return;
    pending.delete(result.requestId); clearTimeout(task.timer); task.resolve(result);
  });
  connected.onDisconnect.addListener(()=>{
    void chrome.runtime.lastError;
    if(port===connected)port=null;
    for(const task of pending.values()){clearTimeout(task.timer);task.resolve({ok:false,message:'Passerelle absente. Installe NoYouPub Core ou ouvre les réglages de l’application Mac, puis recharge YouTube.'});}
    pending.clear();
  });
  if(!timer)timer=setInterval(()=>poll().catch(error=>{problem=error.message;}),5000);
}
function nativeRequest(request) {
  ensurePort();
  return new Promise(resolve=>{
    const requestId=++serial;
    const timeout=setTimeout(()=>{
      pending.delete(requestId);resolve({ok:false,message:'La TV met trop de temps à répondre.'});
      // A timed-out host may still be processing: close it before accepting new work.
      const old=port;port=null;old?.disconnect();
    },request.action==='cast'?690000:(['play','pause','stop','seek','volume','mute','speed'].includes(request.action)?60000:30000));
    pending.set(requestId,{resolve,timer:timeout});
    port.postMessage({...request,language:language(),requestId});
  });
}
function view(message='') {return {ok:true,...data,language:language(),state:lastState,busy,message:message||problem};}
async function launch(item,position=0,isRecovery=false,remember=true) {
  const response=await nativeRequest({action:'cast',url:item.url,position,device:data.device,quality:data.quality});
  if(!response.ok) {problem=response.message;await save();return response;}
  if(remember&&!isRecovery&&data.last&&data.last.url!==item.url){data.history.push({url:data.last.url,title:data.last.title});data.history=data.history.slice(-50);}
  data.last={url:item.url,title:response.session?.title||item.title,position,device:data.device,quality:data.quality,
    sessionId:response.session?.session_id,active:true,desired:'PLAYING'};
  lastState=null;failures=0;problem='';if(!isRecovery)retries=0;
  await save();return view(response.message);
}
async function nextVideo() {
  if(!data.queue.length)return {ok:false,message:'La file d’attente est vide.'};
  const item=data.queue[0];
  const result=await launch(item);
  if(result.ok){data.queue.shift();await save();return view('Vidéo suivante lancée.');}
  return result; // Keep the item if casting failed.
}
async function previousVideo() {
  if(!data.history.length)return {ok:false,message:'Aucune vidéo précédente dans cette session Cast.'};
  if(data.last&&data.queue.length>=50)return {ok:false,message:'Retire une vidéo de la file avant de revenir en arrière.'};
  const previous=data.history.at(-1),current=data.last;
  const result=await launch(previous,0,false,false);
  if(!result.ok)return result;
  data.history.pop();
  if(current)data.queue.unshift({id:crypto.randomUUID(),url:current.url,title:current.title});
  await save();return view('Vidéo précédente lancée.');
}
function shouldAdvance(last,state) {
  if(state.app_id && !['CC1AD845','E8C28D3C'].includes(state.app_id))return false;
  if(!state.owned && ['PLAYING','PAUSED','BUFFERING'].includes(state.player_state))return false;
  return !!(last?.active && last.sessionId===state.session_id && (state.ended==='FINISHED' || (state.owned && state.player_state==='IDLE' && state.idle_reason==='FINISHED')));
}
function shouldRecover(last,state,hadFailure) {
  if(!last?.active || last.desired!=='PLAYING')return false;
  if(state.player_state==='PAUSED')return false;
  if(!state.owned && ['PLAYING','BUFFERING'].includes(state.player_state))return false;
  if(state.session_id && state.session_id!==last.sessionId)return false;
  if(state.app_id && !['CC1AD845','E8C28D3C'].includes(state.app_id))return false;
  if(state.ended==='CANCELLED' || state.idle_reason==='CANCELLED')return false;
  return !!((state.owned && (state.relay_stale || state.idle_reason==='ERROR')) ||
    (last.sessionId===state.session_id && state.ended==='ERROR') ||
    (hadFailure && !state.owned && state.player_state==='IDLE' && !state.ended));
}
async function poll() {
  await ready;if(busy || polling || (!port && !data.last?.active))return;
  polling=true;
  let finishPoll;pollFinished=new Promise(resolve=>{finishPoll=resolve;});
  try {
    const result=await nativeRequest({action:'status',device:data.device});
    if(!result.ok){failures++;problem=result.message;lastState=null;return;}
    const hadFailure=failures>0;failures=0;lastState=result.state;
    if(data.languagePreference==='follow_app'){void nativeRequest({action:'preferences'}).then(p=>{if(p.ok&&p.language!==data.sharedLanguage){data.sharedLanguage=p.language;return save();}}).catch(()=>{});}
    const state=lastState;
    if(shouldAdvance(data.last,state)) {
      data.last.active=false;await save();
      if(data.queue.length){busy=true;await nextVideo();}
      else problem='Lecture terminée.';
    } else if(shouldRecover(data.last,state,hadFailure)) {
      if(Date.now()>=nextRetry && retries<2){busy=true;retries++;nextRetry=Date.now()+30000;problem='Reconnexion à la TV…';await launch(data.last,Math.max(0,data.last.position-2),true);}
      if(retries>=2)problem='Reconnexion tentée. Utilise « Reprendre » si la lecture reste interrompue.';
    } else if(state.owned && data.last?.sessionId===state.session_id) {
      if(['PLAYING','PAUSED'].includes(state.player_state)) {
        data.last.position=state.current_time;data.last.desired=state.player_state;problem='';
      } else if(state.player_state==='IDLE') data.last.active=false;
      await save();
    } else if(data.last?.active) {
      // Another app or an intentional remote stop must not restart our content.
      data.last.active=false;await save();
    }
  } finally {busy=false;polling=false;finishPoll();}
}
async function dispatch(request,tabId) {
  await ready;
  if(request.action==='language'){data.languagePreference=request.value;await save();if(['fr','en','system'].includes(request.value)){void Promise.resolve().then(()=>nativeRequest({action:'set_language',value:request.value})).catch(()=>{});}return view();}
  if(['progress','cancel'].includes(request.action)) {
    return await chrome.runtime.sendNativeMessage(HOST, {action:request.action,language:language()});
  }
  if(request.action==='status'){ensurePort();return view();}
  if(request.action==='mode'){if(request.mode==='auto')tabModes.delete(tabId);else tabModes.set(tabId,request.mode);return view();}
  if(polling)await pollFinished;
  if(busy)return {ok:false,message:'Commande en cours, réessaie dans un instant.'};
  busy=true;
  try {
    switch(request.action) {
      case 'ping': {try{const prefs=await nativeRequest({action:'preferences'});if(prefs.ok){data.sharedLanguage=prefs.language;await save();}}catch{}const result=await nativeRequest(request);if(result.ok){await save();return {...view(),deviceName:result.device};}return result;}
      case 'devices': return await nativeRequest(request);
      case 'settings': {
        const changing=data.device!==request.device;
        if(changing && data.last?.active)return {ok:false,message:'Arrête la diffusion avant de changer de TV.'};
        data.device=request.device;data.quality=request.quality;
        if(changing){lastState=null;data.history=[];}
        await save();return view('Réglages enregistrés pour la prochaine diffusion.');
      }
      case 'enqueue':
      case 'enqueueVideo':
        if(data.queue.length>=50)return {ok:false,message:'La file est limitée à 50 vidéos.'};
        data.queue.push({id:crypto.randomUUID(),url:request.url,title:request.title});await save();return view('Vidéo ajoutée à la file.');
      case 'remove': data.queue=data.queue.filter(item=>item.id!==request.id);await save();return view('Vidéo retirée.');
      case 'clear': data.queue=[];await save();return view('File vidée.');
      case 'next': return await nextVideo();
      case 'previous': return await previousVideo();
      case 'cast': {const result=await launch(request,request.position);if(result.ok && tabPages.get(tabId)===request.url)tabModes.set(tabId,'remote');return result;}
      case 'resume':
        if(!data.last)return {ok:false,message:'Aucune lecture à reprendre.'};
        data.device=data.last.device;data.quality=data.last.quality;
        return await launch(data.last,Math.max(0,data.last.position-2),false,false);
      default: {
        // Stop disables queue advancement/recovery before issuing the command.
        if(request.action==='stop' && data.last){data.last.active=false;await save();}
        const result=await nativeRequest({...request,device:data.device});
        if(result.ok){
          lastState=result.state;
          if(data.last && lastState?.owned){data.last.position=lastState.current_time;data.last.desired=lastState.player_state;await save();}
          problem='';return view(result.message);
        }
        return result;
      }
    }
  } finally {busy=false;}
}
chrome.runtime.onMessage.addListener((message,sender,reply)=>{
  let request;try {request=validate(message,sender);}catch(error){reply({ok:false,message:error.message});return false;}
  let page;try{page=videoURL(sender.tab.url||sender.url);}catch{page=sender.tab.url||sender.url;}
  if(tabPages.get(sender.tab.id)!==page){tabModes.delete(sender.tab.id);tabPages.set(sender.tab.id,page);}
  dispatch(request,sender.tab.id).then(result=>reply({...result,pageURL:page,busy:request.action==='status'?result.busy:false,mode:modeForPage(sender.tab.id,page,result)})).catch(error=>reply({ok:false,message:error.message}));
  return true;
});
