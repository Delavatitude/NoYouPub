/* Shared explicit-language localization; Chrome's native catalogs also localize the manifest. */
(() => {
  if(globalThis.NoYouPubI18n)return;
  let lang=(chrome.i18n?.getUILanguage?.()||'en').startsWith('fr')?'fr':'en';
  let index={},messages={},french={},english={},generation=0;
  const roots=new Set(),cache=new Map();
  const escape=s=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
  const browser=()=>((chrome.i18n?.getUILanguage?.()||'en').startsWith('fr')?'fr':'en');
  async function resource(path){if(!cache.has(path))cache.set(path,fetch(chrome.runtime.getURL(path)).then(r=>{if(!r.ok)throw Error('Locale unavailable');return r.json();}));return cache.get(path);}
  function t(value){
    if(typeof value!=='string')return value;
    const exact=index[value];if(exact)return messages[exact]?.message||value;
    for(const [key,id]of Object.entries(index)){
      for(const text of [key,english[id]?.message||key]){
        if(value===text)return messages[id]?.message||value;
        if(text.includes('{{')){
          const tokens=text.match(/\{\{[^{}]+\}\}/g)||[];let pattern=escape(text);
          for(const token of tokens)pattern=pattern.replace(escape(token),'([\\s\\S]*?)');
          const match=value.match(new RegExp('^'+pattern+'$'));
          if(match){let out=messages[id]?.message||key;tokens.forEach((token,i)=>{out=out.replace(token,()=>match[i+1]);});return out;}
        }
      }
    }
    for(const key of Object.keys(index).sort((a,b)=>b.length-a.length)){
      const id=index[key];for(const text of [key,english[id]?.message||key]){
        if(text&&value.startsWith(text)&&value.length>text.length&&(/\s$/.test(text)||' :·—→'.includes(value[text.length])))return (messages[id]?.message||key)+value.slice(text.length);
      }
    }
    return value;
  }
  function apply(root){
    if(!root.isConnected)return;
    const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);let node;
    while((node=walker.nextNode())){
      if(node.parentElement?.closest('[data-i18n-skip],style,script'))continue;
      const value=t(node.nodeValue);if(value!==node.nodeValue)node.nodeValue=value;
    }
    for(const el of [...(root.matches?.('[title],[aria-label],[placeholder]')?[root]:[]),...root.querySelectorAll('[title],[aria-label],[placeholder]')]){
      if(el.closest('[data-i18n-skip]'))continue;
      for(const name of ['title','aria-label','placeholder'])if(el.hasAttribute(name)){const old=el.getAttribute(name),value=t(old);if(value!==old)el.setAttribute(name,value);}
    }
  }
  async function setLanguage(value){
    value=value==='fr'?'fr':'en';const current=++generation;
    try{
      const [idx,fr,en]=await Promise.all([resource('i18n-index.json'),resource('_locales/fr/messages.json'),resource('_locales/en/messages.json')]);
      if(current!==generation)return;lang=value;index=idx;french=fr;english=en;messages=lang==='fr'?french:english;
      for(const root of roots)apply(root);
    }catch{/* A reloaded extension will ask the page to refresh through its existing error path. */}
  }
  function observe(root){
    roots.add(root);let scheduled=false;
    const observer=new MutationObserver(()=>{if(scheduled)return;scheduled=true;queueMicrotask(()=>{scheduled=false;apply(root);});});
    observer.observe(root,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['title','aria-label','placeholder']});apply(root);
  }
  globalThis.NoYouPubI18n={t,observe,setLanguage,get language(){return lang;}};
  chrome.storage.local.get('catt').then(saved=>{
    const data=saved.catt||{},choice=data.languagePreference||'follow_app';
    setLanguage(choice==='follow_app'?(data.sharedLanguage||browser()):choice==='system'?browser():choice);
  }).catch(()=>setLanguage(browser()));
  chrome.storage.onChanged?.addListener((changes,area)=>{if(area==='local'&&changes.catt){const d=changes.catt.newValue||{},choice=d.languagePreference||'follow_app';setLanguage(choice==='follow_app'?(d.sharedLanguage||browser()):choice==='system'?browser():choice);}});
})();
