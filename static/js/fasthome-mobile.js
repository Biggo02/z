(()=>{'use strict';

const state={controller:null,busy:new WeakSet()};
const nativePrefixes=['/admin/','/static/','/media/'];
const nativePaths=['/logout','/login?next=','/register'];

function isSameOrigin(url){return url.origin===window.location.origin}
function isNativeLink(a,url){
  if(!isSameOrigin(url)||url.hash&&url.pathname===location.pathname)return true;
  if(a.target&&a.target!=='_self')return true;
  if(a.hasAttribute('download')||a.dataset.noAjax!==undefined)return true;
  if(url.protocol!=='http:'&&url.protocol!=='https:')return true;
  if(nativePrefixes.some(p=>url.pathname.startsWith(p)))return true;
  if(url.pathname==='/logout'||url.pathname==='/login'||url.pathname==='/register')return true;
  return false;
}
function isNativeForm(form){
  if(form.dataset.noAjax!==undefined||form.target&&form.target!=='_self')return true;
  if(form.dataset.ajax==='false')return true;
  const action=new URL(form.getAttribute('action')||location.href,location.href);
  if(!isSameOrigin(action)||action.pathname.startsWith('/admin/'))return true;
  return false;
}
function buttonFor(form){return form.querySelector('button[type="submit"],input[type="submit"]')}
function setBusy(form,busy){
  const btn=buttonFor(form); if(!btn)return;
  if(busy){
    if(!btn.dataset.fhOriginalText)btn.dataset.fhOriginalText=btn.textContent||btn.value||'';
    if(btn.tagName==='INPUT')btn.value='Traitement…'; else btn.textContent='Traitement…';
    btn.disabled=true; btn.setAttribute('aria-busy','true');
  }else{
    if(btn.dataset.fhOriginalText!==undefined){if(btn.tagName==='INPUT')btn.value=btn.dataset.fhOriginalText;else btn.textContent=btn.dataset.fhOriginalText;delete btn.dataset.fhOriginalText}
    btn.disabled=false; btn.removeAttribute('aria-busy');
  }
}
function toast(message,type='info'){
  let host=document.getElementById('fh-toast-host');
  if(!host){host=document.createElement('div');host.id='fh-toast-host';host.setAttribute('aria-live','polite');host.setAttribute('aria-atomic','true');Object.assign(host.style,{position:'fixed',right:'18px',bottom:'18px',zIndex:'9999',display:'grid',gap:'8px',maxWidth:'min(420px,calc(100vw - 36px))'});document.body.appendChild(host)}
  const item=document.createElement('div');item.textContent=message;item.dataset.type=type;Object.assign(item.style,{padding:'12px 15px',borderRadius:'12px',background:'var(--surface,#fff)',color:'var(--text,#17211d)',border:'1px solid var(--border,#e3e9e4)',boxShadow:'0 12px 30px rgba(0,0,0,.16)',fontWeight:'700'});host.appendChild(item);setTimeout(()=>item.remove(),3500)
}
function csrfToken(){return document.querySelector('input[name="csrfmiddlewaretoken"]')?.value||''}
function extractAndRender(html,url,opts={}){
  const parser=new DOMParser(); const doc=parser.parseFromString(html,'text/html');
  if(!doc.body)return false;
  document.title=doc.title||document.title;
  document.body.innerHTML=doc.body.innerHTML;
  if(opts.history==='push')history.pushState({fh:true},'',url.href);
  if(opts.history==='replace')history.replaceState({fh:true},'',url.href);
  if(!opts.preserveScroll)window.scrollTo({top:0,behavior:'auto'});
  executeBodyScripts();
  initPressFeedback();
  return true;
}
function executeBodyScripts(){
  document.querySelectorAll('script').forEach(old=>{
    if(old.src&&old.src.includes('/static/js/fasthome-mobile.js'))return;
    const s=document.createElement('script');
    for(const attr of old.attributes){if(attr.name!=='src')s.setAttribute(attr.name,attr.value)}
    if(old.src){if(!document.querySelector(`script[src="${old.src}"]`)){s.src=old.src;document.head.appendChild(s)}}else{s.textContent=old.textContent;old.replaceWith(s)}
  });
}
async function request(url,options={},meta={}){
  if(state.controller)state.controller.abort();
  const controller=new AbortController();state.controller=controller;
  const headers=new Headers(options.headers||{});headers.set('X-Requested-With','XMLHttpRequest');headers.set('Accept','text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8');options.headers=headers;options.signal=controller.signal;options.credentials='same-origin';
  try{
    const response=await fetch(url,options);
    if(controller.signal.aborted)return;
    const type=response.headers.get('content-type')||'';
    if(type.includes('application/json')){
      const data=await response.json();
      if(data.redirect){const target=new URL(data.redirect,location.href);return request(target.href,{}, {history:'push'})}
      if(data.html){extractAndRender(data.html,new URL(response.url),meta);if(data.message)toast(data.message,'success');return}
      if(data.message)toast(data.message,response.ok?'success':'error');
      if(!response.ok)throw new Error(data.error||data.message||`HTTP ${response.status}`);
      return;
    }
    const html=await response.text();
    if(!response.ok){
      const rendered=extractAndRender(html,new URL(response.url),{history:meta.history});
      if(rendered)toast('Une erreur est survenue. Vérifiez les informations affichées.','error');
      else throw new Error(`HTTP ${response.status}`);
      return;
    }
    if(!html.trim()){toast('Opération effectuée.','success');return}
    extractAndRender(html,new URL(response.url),meta);
  }catch(error){
    if(error.name==='AbortError')return;
    console.error('[Fasthome AJAX]',error);toast('Connexion impossible. Votre page n’a pas été actualisée. Réessayez.','error');
  }finally{if(state.controller===controller)state.controller=null}
}
function handleLink(event){
  if(event.defaultPrevented||event.button!==0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return;
  const a=event.target.closest('a[href]');if(!a)return;
  const url=new URL(a.href,location.href);if(isNativeLink(a,url))return;
  if(url.href===location.href)return;
  event.preventDefault();request(url.href,{method:'GET'},{history:'push'});
}
function handleSubmit(event){
  const form=event.target;if(!(form instanceof HTMLFormElement)||isNativeForm(form))return;
  if(state.busy.has(form)){event.preventDefault();return}
  const action=new URL(form.getAttribute('action')||location.href,location.href);
  const method=(form.getAttribute('method')||'GET').toUpperCase();
  state.busy.add(form);setBusy(form,true);event.preventDefault();
  if(method==='GET'){
    const data=new FormData(form);const params=new URLSearchParams();for(const [k,v] of data.entries()){if(typeof v==='string'&&v!=='')params.append(k,v)}
    action.search=params.toString();request(action.href,{method:'GET'},{history:'push'}).finally(()=>{state.busy.delete(form)});
  }else{
    const data=new FormData(form);const headers={};const csrf=data.get('csrfmiddlewaretoken')||csrfToken();if(csrf)headers['X-CSRFToken']=csrf;
    request(action.href,{method,body:data,headers},{history:'replace'}).finally(()=>{state.busy.delete(form)});
  }
}
function handlePopState(){request(location.href,{method:'GET'},{history:null,preserveScroll:false})}
function initPressFeedback(){
  if(document.documentElement.dataset.fhPressReady)return;document.documentElement.dataset.fhPressReady='1';
  document.addEventListener('pointerdown',e=>{const el=e.target.closest('a,button');if(el)el.classList.add('fh-pressed')},{passive:true});
  document.addEventListener('pointerup',e=>{const el=e.target.closest('a,button');if(el)el.classList.remove('fh-pressed')},{passive:true});
  document.addEventListener('pointercancel',e=>{const el=e.target.closest('a,button');if(el)el.classList.remove('fh-pressed')},{passive:true});
}
function init(){
  initPressFeedback();
  document.addEventListener('click',handleLink);
  document.addEventListener('submit',handleSubmit,true);
  window.addEventListener('popstate',handlePopState);
  history.replaceState({fh:true},'',location.href);
  document.documentElement.classList.add('fh-no-full-refresh');
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
window.FasthomeAjax={request,toast};
})();