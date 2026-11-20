(() => {
  if(window.top!==window)return;
  const CARD='yt-lockup-view-model,ytd-compact-video-renderer,ytd-video-renderer,ytd-grid-video-renderer,ytd-rich-item-renderer';
  let active=false,context=null,scheduled=false,loading=false;
  const style=document.createElement('style');style.textContent=`
    .catt-suggestion-actions{display:flex!important;align-items:center}
    .catt-suggestion-add{border:0!important;border-radius:50%!important;width:32px!important;height:32px!important;min-width:32px!important;background:#e6e6e6!important;color:#171717!important;font:24px Arial!important;cursor:pointer!important;align-self:center;margin:3px!important}.catt-suggestion-add:hover{background:#d3d3d3!important}html[dark] .catt-suggestion-add{background:#333!important;color:#fff!important}.catt-suggestion-add[hidden]{display:none!important}
    .catt-menu-add{display:flex!important;align-items:center;gap:16px;width:100%;box-sizing:border-box;min-height:48px;padding:10px 16px!important;border:0!important;background:transparent!important;color:inherit!important;font:14px Roboto,Arial,sans-serif!important;text-align:left;cursor:pointer}.catt-menu-add:hover,.catt-menu-add:focus-visible{background:#8883!important}.catt-menu-add span:first-child{font-size:26px;width:24px;text-align:center}
    #catt-queue-toast{position:fixed;bottom:28px;left:50%;transform:translateX(-50%);z-index:2147483647;background:#262626;color:#fff;border:1px solid #666;border-radius:9px;padding:13px 20px;max-width:80vw;font:14px Arial;box-shadow:0 4px 14px #0005;pointer-events:none}#catt-queue-toast[hidden]{display:none}
  `;document.head.append(style);
  const toast=document.createElement('div');toast.id='catt-queue-toast';toast.hidden=true;toast.setAttribute('role','status');document.body.append(toast);let toastTimer;
  function tell(text){toast.textContent=NoYouPubI18n.t(text);toast.hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>{toast.hidden=true;},4000);}
  function item(card){
    const link=card?.querySelector('h3 a[href*="watch?v="],a#video-title[href*="watch?v="],a[href*="watch?v="]');if(!link)return null;
    const url=new URL(link.getAttribute('href'),location.href),id=url.searchParams.get('v');
    if(url.origin!==location.origin||!/^[-\w]{11}$/.test(id||''))return null;
    return {url:'https://www.youtube.com/watch?v='+id,title:(card.querySelector('h3')?.getAttribute('title')||card.querySelector('h3')?.textContent||link.getAttribute('title')||link.textContent||'Vidéo YouTube').trim().slice(0,200)};
  }
  async function enqueue(video,event,button){
    if(!event.isTrusted||!video||button.disabled)return;event.preventDefault();event.stopPropagation();button.disabled=true;
    try{const result=await chrome.runtime.sendMessage({action:'enqueueVideo',...video});if(!result?.ok)throw new Error(result?.message||'Ajout impossible.');tell('Ajouté à la file Cast : '+video.title);}
    catch(error){tell(error.message.includes('Extension context invalidated')?'Recharge cette page YouTube pour activer la mise à jour.':error.message);}
    finally{button.disabled=false;}
  }
  function clearContext(){context=null;document.querySelectorAll('.catt-menu-add').forEach(e=>e.remove());}
  function menus(){
    if(!context)return;
    if(!context.card.isConnected||item(context.card)?.url!==context.video.url){clearContext();return;}
    const menu=[...document.querySelectorAll('yt-list-view-model[role="menu"],ytd-menu-popup-renderer [role="menu"],ytd-menu-popup-renderer')].find(e=>e.getBoundingClientRect().width&&e.getBoundingClientRect().height&&getComputedStyle(e).visibility!=='hidden');
    if(!menu||menu.querySelector('.catt-menu-add'))return;
    const video={...context.video},button=document.createElement('button');button.type='button';button.className='catt-menu-add';button.setAttribute('role','menuitem');
    const plus=document.createElement('span'),text=document.createElement('span');plus.textContent='+';plus.setAttribute('aria-hidden','true');text.textContent=NoYouPubI18n.t('Ajouter à la file Cast');button.append(plus,text);button.title=video.title;
    button.addEventListener('click',event=>{event.stopImmediatePropagation();enqueue(video,event,button);});menu.prepend(button);
  }
  function decorate(){
    scheduled=false;
    for(const card of document.querySelectorAll(CARD)){
      if(!item(card))continue;
      const slot=card.querySelector('.ytLockupMetadataViewModelMenuButton,ytd-menu-renderer');if(!slot)continue;
      slot.classList.add('catt-suggestion-actions');
      let button=slot.querySelector('.catt-suggestion-add');
      if(!button){button=document.createElement('button');button.type='button';button.className='catt-suggestion-add';button.textContent='+';button.title=NoYouPubI18n.t('Ajouter à la file Cast');button.setAttribute('aria-label',NoYouPubI18n.t('Ajouter à la file Cast'));button.addEventListener('click',event=>enqueue(item(card),event,button));slot.append(button);}
      button.hidden=!active;
    }
    menus();
  }
  function schedule(){if(!scheduled){scheduled=true;requestAnimationFrame(decorate);}}
  document.addEventListener('click',event=>{
    if(!event.isTrusted)return;
    const target=event.target instanceof Element?event.target:null;if(!target)return;
    if(target.closest('.catt-menu-add,.catt-suggestion-add'))return;
    const button=target.closest('button'),card=button?.closest(CARD);
    if(card&&button.closest('.ytLockupMetadataViewModelMenuButton,ytd-menu-renderer')){
      clearContext();const video=item(card);if(video){context={card,video};schedule();setTimeout(menus,100);setTimeout(menus,350);}
    }else if(!target.closest('[role="menu"],ytd-menu-popup-renderer'))clearContext();
  },true);
  new MutationObserver(schedule).observe(document.body,{childList:true,subtree:true});
  async function refresh(){if(loading||document.hidden)return;loading=true;try{const result=await chrome.runtime.sendMessage({action:'status'});if(result?.ok){const state=result.state;active=!!(state?.owned&&['PLAYING','PAUSED','BUFFERING'].includes(state.player_state))||(!state&&!!result.last?.active);schedule();}}catch{}finally{loading=false;}}
  document.addEventListener('yt-navigate-finish',()=>{clearContext();schedule();refresh();});
  schedule();refresh();setInterval(refresh,5000);
})();
