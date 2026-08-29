(()=>{'use strict';
const FH={controller:null,busy:new WeakSet(),initialized:false};
const NATIVE_PREFIXES=['/admin/','/static/','/media/'];

function sameOrigin(url){return url.origin===location.origin}
function nativeLink(a,url){
  if(!sameOrigin(url))return true;
  if(a.target&&a.target!=='_self')return true;
  if(a.hasAttribute('download')||a.dataset.noAjax!==undefined||a.dataset.ajax==='false')return true;
  if(url.protocol!=='http:'&&url.protocol!=='https:')return true;
  if(NATIVE_PREFIXES.some(p=>url.pathname.startsWith(p)))return true;
  if(['/logout','/login','/register'].includes(url.pathname))return true;
  if(url.hash&&url.pathname===location.pathname)return true;
  return false;
}
function nativeForm(form){
  if(form.dataset.noAjax!==undefined||form.dataset.ajax==='false')return true;
  if(form.target&&form.target!=='_self')return true;
  const action=new URL(form.getAttribute('action')||location.href,location.href);
  return !sameOrigin(action)||action.pathname.startsWith('/admin/')||['/logout','/login','/register'].includes(action.pathname);
}
function submitButton(form){return form.querySelector('button[type="submit"],input[type="submit"]')}
function busy(form,on){
  const b=submitButton(form);if(!b)return;
  if(on){
    b.dataset.fhText=b.tagName==='INPUT'?(b.value||''):(b.textContent||'');
    if(b.tagName==='INPUT')b.value='Traitement…';else b.textContent='Traitement…';
    b.disabled=true;b.setAttribute('aria-busy','true');
  }else if(b.dataset.fhText!==undefined){
    if(b.tagName==='INPUT')b.value=b.dataset.fhText;else b.textContent=b.dataset.fhText;
    delete b.dataset.fhText;b.disabled=false;b.removeAttribute('aria-busy');
  }
}
function toast(message,type='info'){
  let host=document.getElementById('fh-toast-host');
  if(!host){host=document.createElement('div');host.id='fh-toast-host';host.setAttribute('aria-live','polite');Object.assign(host.style,{position:'fixed',right:'18px',bottom:'18px',zIndex:'99999',display:'grid',gap:'8px',maxWidth:'min(420px,calc(100vw - 36px))'});document.body.appendChild(host)}
  const item=document.createElement('div');item.textContent=message;item.dataset.type=type;Object.assign(item.style,{padding:'12px 15px',borderRadius:'12px',background:'var(--surface,#fff)',color:'var(--text,#17211d)',border:'1px solid var(--border,#e3e9e4)',boxShadow:'0 12px 30px rgba(0,0,0,.16)',fontWeight:'700'});host.appendChild(item);setTimeout(()=>item.remove(),3500);
}
function csrf(form){return form?.querySelector('input[name="csrfmiddlewaretoken"]')?.value||document.querySelector('input[name="csrfmiddlewaretoken"]')?.value||''}
function scriptsIn(root){
  root.querySelectorAll('script').forEach(old=>{
    const s=document.createElement('script');
    for(const a of old.attributes){if(a.name!=='src')s.setAttribute(a.name,a.value)}
    if(old.src){if(!document.querySelector(`script[src="${old.src}"]`)){s.src=old.src;document.head.appendChild(s)}}else{s.textContent=old.textContent;old.replaceWith(s)}
  });
}
function renderDocument(html,url,{push=false,replace=false,preserveScroll=false}={}){
  const doc=new DOMParser().parseFromString(html,'text/html');
  if(!doc.body)return false;
  const currentMain=document.querySelector('main')||document.querySelector('[data-page]')||document.querySelector('.container');
  const nextMain=doc.querySelector('main')||doc.querySelector('[data-page]')||doc.querySelector('.container');
  if(currentMain&&nextMain){
    currentMain.replaceWith(nextMain.cloneNode(true));
  }else{
    const currentContent=document.querySelector('[data-ajax-content]');
    const nextContent=doc.querySelector('[data-ajax-content]');
    if(currentContent&&nextContent)currentContent.replaceWith(nextContent.cloneNode(true));
    else return false;
  }
  if(doc.title)document.title=doc.title;
  if(push)history.pushState({fh:true},'',url.href);
  if(replace)history.replaceState({fh:true},'',url.href);
  if(!preserveScroll)window.scrollTo(0,0);
  scriptsIn(document);
  return true;
}
async function ajax(url,options={},meta={}){
  if(FH.controller)FH.controller.abort();
  const controller=new AbortController();FH.controller=controller;
  const headers=new Headers(options.headers||{});
  headers.set('X-Requested-With','XMLHttpRequest');
  headers.set('Accept','text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8');
  options.headers=headers;options.credentials='same-origin';options.signal=controller.signal;
  try{
    const response=await fetch(url,options);
    if(controller.signal.aborted)return {aborted:true};
    if(response.redirected&&(new URL(response.url).pathname==='/login'||new URL(response.url).pathname==='/register')){
      window.location.href=response.url;return;
    }
    const type=response.headers.get('content-type')||'';
    if(type.includes('application/json')){
      const data=await response.json();
      if(data.redirect){history.replaceState({fh:true},'',data.redirect);return ajax(data.redirect,{method:'GET'},{push:false,replace:false});}
      if(data.html){renderDocument(data.html,new URL(response.url),meta);if(data.message)toast(data.message,'success');return data;}
      if(data.message)toast(data.message,response.ok?'success':'error');
      if(!response.ok)throw new Error(data.error||data.message||`HTTP ${response.status}`);
      return data;
    }
    const html=await response.text();
    if(!response.ok){
      if(renderDocument(html,new URL(response.url),{push:false,replace:false,preserveScroll:true}))toast('Vérifiez les informations affichées.','error');
      else throw new Error(`HTTP ${response.status}`);
      return;
    }
    if(!html.trim()){toast('Opération effectuée.','success');return;}
    if(!renderDocument(html,new URL(response.url),meta)){
      console.warn('[Fasthome AJAX] Réponse HTML sans zone remplaçable; navigation classique.',url);
      window.location.href=url;return;
    }
    return html;
  }catch(e){
    if(e.name==='AbortError')return;
    console.error('[Fasthome AJAX]',e);toast('Connexion impossible. Réessayez.','error');
  }finally{if(FH.controller===controller)FH.controller=null}
}
function clickHandler(e){
  if(e.defaultPrevented||e.button!==0||e.metaKey||e.ctrlKey||e.shiftKey||e.altKey)return;
  const a=e.target.closest('a[href]');if(!a)return;
  const url=new URL(a.href,location.href);if(nativeLink(a,url)||url.href===location.href)return;
  e.preventDefault();ajax(url.href,{method:'GET'},{push:true,replace:false});
}
function submitHandler(e){
  const form=e.target;if(!(form instanceof HTMLFormElement)||nativeForm(form))return;
  if(FH.busy.has(form)){e.preventDefault();return;}
  e.preventDefault();FH.busy.add(form);busy(form,true);
  const action=new URL(form.getAttribute('action')||location.href,location.href);
  const method=(form.getAttribute('method')||'GET').toUpperCase();
  const run=method==='GET'?(()=>{const p=new URLSearchParams(new FormData(form));action.search=p.toString();return ajax(action.href,{method:'GET'},{push:true,replace:false});})():(()=>{const data=new FormData(form);const headers={};const token=csrf(form);if(token)headers['X-CSRFToken']=token;return ajax(action.href,{method,body:data,headers},{push:false,replace:true});})();
  Promise.resolve(run).finally(()=>{FH.busy.delete(form);busy(form,false);});
}
function popHandler(){ajax(location.href,{method:'GET'},{push:false,replace:false,preserveScroll:false});}
function init(){
  if(FH.initialized)return;FH.initialized=true;
  document.addEventListener('click',clickHandler,true);
  document.addEventListener('submit',submitHandler,true);
  window.addEventListener('popstate',popHandler);
  history.replaceState({fh:true},'',location.href);
  document.documentElement.classList.add('fh-no-full-refresh');
  console.info('[Fasthome AJAX] actif');
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
window.FasthomeAjax={request:ajax,toast};
})();
