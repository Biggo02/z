(function(){
  'use strict';
  const form=document.querySelector('form[enctype="multipart/form-data"]');
  if(!form || !document.getElementById('rooms-area')) return;

  const draftKey='fasthome-property-draft-v3:'+location.pathname;
  const saveUrl='/properties/autosave/';
  const headings=[...form.querySelectorAll('h2')];
  const steps=[
    {title:'Logement',icon:'🏠',match:'Informations du logement'},
    {title:'Services',icon:'💧',match:'Eau et'},
    {title:'Photos',icon:'📷',match:'Photos du logement'},
    {title:'Localisation',icon:'📍',match:'Localisation'},
    {title:'Publication',icon:'📢',match:'Extérieur, équipements et sécurité'}
  ];

  const style=document.createElement('style');
  style.textContent=`
  .draft-progress{margin:0 0 18px;padding:12px;background:#f7f9fb;border:1px solid #e4e9ee;border-radius:15px;position:sticky;top:8px;z-index:20}
  .draft-progress-top{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:10px}.draft-progress-title{font-weight:800;color:#18344d}.draft-save-state{font-size:.72rem;color:#64707d}.draft-bar{height:7px;background:#e4e9ee;border-radius:99px;overflow:hidden}.draft-bar>span{display:block;height:100%;width:0;background:#163a5f;border-radius:inherit;transition:width .25s ease}.draft-steps{display:grid;grid-template-columns:repeat(5,1fr);gap:5px;margin-top:10px}.draft-step{border:0;background:transparent;padding:5px 2px;border-radius:9px;cursor:pointer;color:#65717d;font-size:.65rem;font-weight:700}.draft-step.active{background:#e7eef5;color:#163a5f}.draft-step.done{color:#24613f}.draft-step-icon{display:block;font-size:1rem;margin-bottom:2px}.draft-panel{display:none}.draft-panel.active{display:block}.draft-nav{display:flex;justify-content:space-between;gap:8px;margin:14px 0 4px}.draft-nav .btn{min-width:120px}.draft-required-note{padding:10px 12px;background:#fff8e8;border:1px solid #f0dfaa;border-radius:10px;color:#68551f;font-size:.76rem;margin:8px 0 14px}.draft-resume{padding:11px 12px;background:#edf5ff;border:1px solid #cddff1;border-radius:10px;margin-bottom:12px;font-size:.78rem}.draft-resume button{margin-left:8px;border:0;background:none;color:#163a5f;font-weight:800;cursor:pointer}.draft-mobile-title{display:none}
  @media(max-width:760px){.draft-progress{top:4px;padding:9px}.draft-steps{gap:2px}.draft-step{font-size:.57rem}.draft-step-icon{font-size:.9rem}.draft-nav .btn{min-width:0;flex:1;font-size:.75rem;padding:9px 7px}.draft-mobile-title{display:block;margin:0 0 8px;font-size:1rem}}
  `;
  document.head.appendChild(style);

  const progress=document.createElement('div');
  progress.className='draft-progress';
  progress.innerHTML='<div class="draft-progress-top"><span class="draft-progress-title">Préparation de la publication</span><span class="draft-save-state" id="draftSaveState">Brouillon non enregistré</span></div><div class="draft-bar"><span id="draftBarFill"></span></div><div class="draft-steps"></div>';
  form.parentNode.insertBefore(progress,form);
  const stepRow=progress.querySelector('.draft-steps');

  const panels=[];
  headings.forEach((heading,i)=>{
    const panel=document.createElement('section');
    panel.className='draft-panel';
    const title=heading.textContent.trim();
    const stepIndex=Math.min(i,steps.length-1);
    heading.parentNode.insertBefore(panel,heading);
    panel.appendChild(heading);
    let node=panel.nextSibling;
    while(node && !(node.nodeType===1 && node.tagName==='H2')){const next=node.nextSibling;panel.appendChild(node);node=next;}
    panels.push({panel,title,index:stepIndex});
  });

  const findPanel=t=>panels.find(p=>p.title.includes(t));
  const p1=findPanel('Informations du logement');
  const p2=findPanel('Eau et');
  const p3=findPanel('Photos du logement');
  const p4=findPanel('Localisation');
  const p5=findPanel('Extérieur, équipements et sécurité');
  const effectivePanels=[p1,p2,p3,p4,p5].filter(Boolean);
  if(p5){
    const finalIndex=panels.indexOf(p5);
    for(let i=finalIndex+1;i<panels.length;i++){const p=panels[i];while(p.panel.firstChild)p5.panel.appendChild(p.panel.firstChild);p.panel.remove();}
  }

  effectivePanels.forEach((p,i)=>{
    const s=steps[i]||steps[steps.length-1];
    const b=document.createElement('button');b.type='button';b.className='draft-step';b.dataset.index=i;b.innerHTML=`<span class="draft-step-icon">${s.icon}</span>${s.title}`;
    b.addEventListener('click',()=>show(i));stepRow.appendChild(b);p.panel.classList.add('draft-panel');
  });

  let current=0;
  let propertyId=form.dataset.propertyId||'';
  let saving=false;
  let submitting=false;
  let timer=null;

  function fields(){return [...form.querySelectorAll('input,select,textarea')].filter(el=>el.name && el.type!=='file' && el.name!=='csrfmiddlewaretoken' && !el.disabled)}
  function requiredCompletion(){const f=fields();const required=f.filter(x=>x.required);if(!required.length)return f.filter(x=>String(x.value||'').trim()).length/Math.max(f.length,1);return required.filter(x=>String(x.value||'').trim()).length/required.length}
  function state(text){const el=document.getElementById('draftSaveState');if(el)el.textContent=text}
  function csrf(){const el=form.querySelector('[name=csrfmiddlewaretoken]');return el?el.value:''}
  function saveLocal(){const data={};fields().forEach(el=>{if(el.type==='checkbox')data[el.name]=el.checked;else data[el.name]=el.value});try{localStorage.setItem(draftKey,JSON.stringify(data))}catch(e){}}
  function restoreLocal(){let raw=null;try{raw=localStorage.getItem(draftKey)}catch(e){}if(!raw)return;let data;try{data=JSON.parse(raw)}catch(e){return};let changed=false;fields().forEach(el=>{if(!(el.name in data))return;if(el.type==='checkbox'){if(el.checked!==Boolean(data[el.name])){el.checked=Boolean(data[el.name]);changed=true}}else if(!el.value && data[el.name]){el.value=data[el.name];changed=true}});if(changed){const note=document.createElement('div');note.className='draft-resume';note.innerHTML='<strong>Votre saisie précédente a été retrouvée.</strong> <button type="button">Conserver</button> <button type="button">Effacer</button>';form.parentNode.insertBefore(note,form);note.querySelectorAll('button')[0].onclick=()=>note.remove();note.querySelectorAll('button')[1].onclick=()=>{try{localStorage.removeItem(draftKey)}catch(e){}location.reload()};}}
  function updateProgress(){const pct=Math.round(requiredCompletion()*100);document.getElementById('draftBarFill').style.width=pct+'%';document.querySelectorAll('.draft-step').forEach((b,i)=>{b.classList.toggle('active',i===current);b.classList.toggle('done',i<current)});}
  function show(i){current=Math.max(0,Math.min(effectivePanels.length-1,i));effectivePanels.forEach((p,n)=>p.panel.classList.toggle('active',n===current));let nav=effectivePanels[current].panel.querySelector('.draft-nav');if(!nav){nav=document.createElement('div');nav.className='draft-nav';nav.innerHTML='<button type="button" class="btn btn-light draft-prev">← Précédent</button><button type="button" class="btn btn-primary draft-next">Continuer →</button>';effectivePanels[current].panel.appendChild(nav);nav.querySelector('.draft-prev').onclick=()=>show(current-1);nav.querySelector('.draft-next').onclick=()=>show(current+1)}nav.querySelector('.draft-prev').style.visibility=current?'visible':'hidden';nav.querySelector('.draft-next').textContent=current===effectivePanels.length-1?'Vérifier la publication →':'Continuer →';updateProgress();window.scrollTo({top:0,behavior:'smooth'})}

  async function saveServer(includeFiles){
    if(submitting || saving) return;
    const type=form.querySelector('[name="property_type"]');
    if(!propertyId && (!type || !type.value)){state('Sélectionnez le type pour sauvegarder');saveLocal();return;}
    saving=true;state('Sauvegarde…');
    try{
      const data=new FormData();
      fields().forEach(el=>{if(el.type==='checkbox'){if(el.checked)data.append(el.name,'on')}else data.append(el.name,el.value)});
      if(propertyId)data.append('property_id',propertyId);
      if(includeFiles){form.querySelectorAll('input[type=file][name]').forEach(input=>{[...input.files].forEach(file=>data.append(input.name,file))})}
      const response=await fetch(saveUrl,{method:'POST',headers:{'X-CSRFToken':csrf(),'X-Requested-With':'XMLHttpRequest'},body:data,credentials:'same-origin'});
      const payload=await response.json().catch(()=>({}));
      if(!response.ok || !payload.ok) throw new Error(payload.error||'Impossible de sauvegarder le brouillon.');
      propertyId=payload.property_id||propertyId;
      if(propertyId){
        form.dataset.propertyId=propertyId;
        const editUrl='/properties/'+encodeURIComponent(propertyId)+'/edit/';
        if(location.pathname!==editUrl)history.replaceState({propertyId},'',editUrl);
        try{localStorage.removeItem(draftKey)}catch(e){}
      }
      state('Brouillon sauvegardé automatiquement');
    }catch(error){
      state('Sauvegarde locale — '+(error.message||'serveur indisponible'));
      saveLocal();
    }finally{saving=false}
  }
  function queueSave(includeFiles){clearTimeout(timer);timer=setTimeout(()=>saveServer(includeFiles),includeFiles?100:900)}

  form.addEventListener('input',()=>{if(!submitting){saveLocal();clearTimeout(timer);timer=setTimeout(()=>saveServer(false),900);updateProgress()}});
  form.addEventListener('change',e=>{if(!submitting){saveLocal();queueSave(e.target && e.target.type==='file');updateProgress()}});
  form.querySelectorAll('input[type=file][name]').forEach(input=>input.addEventListener('change',()=>queueSave(true)));
  form.addEventListener('submit',()=>{submitting=true;clearTimeout(timer);try{localStorage.removeItem(draftKey)}catch(e){}});
  window.addEventListener('beforeunload',()=>{if(!submitting)saveLocal()});

  restoreLocal();
  show(0);
  updateProgress();
  if(propertyId)state('Brouillon enregistré sur le serveur');
  else if(requiredCompletion()>0)queueSave(false);
})();
