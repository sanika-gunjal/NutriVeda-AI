(function(){
const $=s=>document.querySelector(s),LS=(k,v)=>{try{return v===undefined?localStorage.getItem(k):localStorage.setItem(k,v)}catch(e){}};
const A=window.NV_ACTIVE||'home', LANG=LS('nutrisense_lang')||'en';

/* ===== DRAWER ===== */
const G=[['Check','#7c3aed,#a855f7',[['/form','activity','Symptoms'],['/dashboard','bar-chart-2','Dashboard'],['/nutrients','droplet','Nutrients'],['/bmi','heart','BMI'],['/dosha-quiz','aperture','Dosha Quiz'],['/age-nutrition','user','Age Nutrition']]],
['Eat','#ea580c,#fb923c',[['/food-log','book-open','Food Diary'],['/smart-meal-planner','cpu','Meal Planner'],['/regional-food','map','Regional Food'],['/kitchen','shopping-bag','My Kitchen'],['/one-food','search','One Food'],['/family-thali','disc','Family Thali'],['/seasonal','sunrise','Seasonal Food'],['/immunity','shield','Immunity'],['/grandma-remedy','coffee',"Grandma's Remedies"]]],
['Move','#0891b2,#22d3ee',[['/yoga','wind','Yoga'],['/workout','target','Workout'],['/steps','compass','Step Tracker'],['/protein','zap','Protein'],['/weightloss','trending-down','Weight Loss'],['/weightgain','trending-up','Weight Gain'],['/haircare','scissors','Hair Care'],['/skincare','sun','Skin Care']]],
['Wellness','#be185d,#f472b6',[['/pregnancy','smile','Pregnancy'],['/cycle-tracker','calendar','Cycle Tracker'],['/allergy-tracker','alert-triangle','Allergies']]],
['More','#4b5563,#9ca3af',[['/community','users','Community'],['/resources','play-circle','Videos & Links'],['/history','clock','History'],['/feedback','message-circle','Feedback']]]];
const list=$('#nvd-list');
if(list){
 list.innerHTML=G.map(([n,c,items])=>`<div class="nvd-grp"><div class="nvd-sec">${n}</div><div class="nvd-grid">${items.map(([h,i,l])=>`<a class="nvd-tile ${location.pathname===h?'active':''}" href="${h}" data-l="${l.toLowerCase()}"><span class="nvd-ic" style="background:linear-gradient(135deg,${c})"><i data-feather="${i}"></i></span>${l}</a>`).join('')}</div></div>`).join('');
 // recent
 let R=[];try{R=JSON.parse(LS('nv_recent')||'[]')}catch(e){}
 const cur=G.flatMap(g=>g[2]).find(x=>x[0]===location.pathname);
 if(cur){R=[cur,...R.filter(x=>x[0]!==cur[0])].slice(0,4);LS('nv_recent',JSON.stringify(R))}
 $('#nvd-recent').innerHTML=R.filter(x=>x[0]!==location.pathname).map(x=>`<a href="${x[0]}">${x[2]}</a>`).join('');
}
const open=v=>{document.body.classList.toggle('nvd-open',v);$('#tb-menu')?.setAttribute('aria-expanded',v);$('#nvdrawer')?.setAttribute('aria-hidden',!v);if(v)setTimeout(()=>$('#nvd-q')?.focus(),300)};
$('#tb-menu')?.addEventListener('click',()=>open(!document.body.classList.contains('nvd-open')));
$('#nvd-x')?.addEventListener('click',()=>open(false));$('#nvd-back')?.addEventListener('click',()=>open(false));
document.addEventListener('keydown',e=>{if(e.key==='Escape')open(false);if((e.key==='m'||e.key==='M')&&!/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)&&!e.ctrlKey&&!e.metaKey){e.preventDefault();open(!document.body.classList.contains('nvd-open'))}});
$('#nvd-q')?.addEventListener('input',e=>{const q=e.target.value.toLowerCase();document.querySelectorAll('.nvd-tile').forEach(t=>{const ok=t.textContent.toLowerCase().includes(q)||t.dataset.l.includes(q);t.style.display=ok?'':'none'});document.querySelectorAll('.nvd-grp').forEach(g=>g.style.display=[...g.querySelectorAll('.nvd-tile')].some(t=>t.style.display!=='none')?'':'none')});

/* ===== THEMES ===== */
const TH=[['default','Aurora','linear-gradient(135deg,#7c3aed,#f472b6)'],['ayurveda','Ayurveda','linear-gradient(135deg,#4f7a45,#e0a21f)'],['neo','Neo Pop','linear-gradient(135deg,#ffd23f,#ff4d8d);border:2px solid #111'],['zen','Zen','linear-gradient(135deg,#f1f1f1,#444)'],['midnight','Midnight','linear-gradient(135deg,#0b1022,#8b7cff)'],['bazaar','Bazaar','linear-gradient(135deg,#9b1b30,#f59f00)']];
const curT=document.documentElement.getAttribute('data-theme')||'default', tb=$('#nvd-themes');
if(tb){tb.innerHTML=TH.map(([k,n,b])=>`<button type="button" data-t="${k}" class="${k===curT?'on':''}"><i style="background:${b}"></i>${n}</button>`).join('');
 tb.onclick=e=>{const b=e.target.closest('button');if(!b)return;const k=b.dataset.t;k==='default'?document.documentElement.removeAttribute('data-theme'):document.documentElement.setAttribute('data-theme',k);LS('nutrisense_theme',k);tb.querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b))}}

/* ===== LANGUAGE (curated dictionary + Google Translate for the rest) ===== */
const MAP={mr:{},hi:{}};(window.NV_ROWS||'').split('\n').forEach(r=>{const [e,m,h]=r.split('|');if(e){MAP.mr[e]=m;MAP.hi[e]=h}});
const D=MAP[LANG];
function tr(s){if(!D)return s;const t=s.trim();if(!t)return s;const lead=s.match(/^\s*/)[0],trail=s.match(/\s*$/)[0];
 const core=x=>{if(D[x])return D[x];const m=x.match(/^([^\p{L}\p{N}]+)\s*(.+)$/u);if(m&&D[m[2]])return m[1]+' '+D[m[2]];
  if(/ · |, /.test(x)||/\d+ kcal/.test(x))return x.split(/( · |, )/).map(p=>/^( · |, )$/.test(p)?p:(D[p]||p.replace(/(\d+) kcal/,'$1 '+(D.kcal||'kcal')))).join('');return x};
 return lead+core(t)+trail}
const M=new WeakMap();let busy=false;
function one(n){const cur=n.nodeValue;if(!cur.trim())return;let r=M.get(n);if(!r){r={o:cur,t:cur};M.set(n,r)}else if(cur!==r.t&&cur!==r.o){r.o=cur}const t=tr(r.o);r.t=t;if(t!==cur)n.nodeValue=t}
function pass(root){if(!D)return;busy=true;const w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,{acceptNode:n=>/^(SCRIPT|STYLE|TEXTAREA|NOSCRIPT)$/.test(n.parentNode.nodeName)||n.parentNode.closest('[data-no-translate]')?NodeFilter.FILTER_REJECT:NodeFilter.FILTER_ACCEPT});const a=[];while(w.nextNode())a.push(w.currentNode);a.forEach(one);
 (root.querySelectorAll?root:document).querySelectorAll('[placeholder]').forEach(i=>{if(!i.dataset.ph)i.dataset.ph=i.placeholder;i.placeholder=tr(i.dataset.ph)});busy=false}
if(D){document.documentElement.lang=LANG;pass(document.body);
 new MutationObserver(ms=>{if(busy)return;busy=true;ms.forEach(m=>{m.addedNodes.forEach(n=>{if(n.nodeType===3)one(n);else if(n.nodeType===1)pass(n)});if(m.type==='characterData')one(m.target)});busy=false}).observe(document.body,{childList:true,subtree:true,characterData:true});
 // Google Translate translates everything else (needs internet)
 document.cookie='googtrans=/en/'+LANG+';path=/';
 const d=document.createElement('div');d.id='gt_el';document.body.appendChild(d);
 window.nvGT=()=>new google.translate.TranslateElement({pageLanguage:'en',includedLanguages:'mr,hi',autoDisplay:false},'gt_el');
 const s=document.createElement('script');s.src='https://translate.google.com/translate_a/element.js?cb=nvGT';document.head.appendChild(s)}
else{document.cookie='googtrans=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/'}
document.querySelectorAll('#nvd-lang button').forEach(b=>{b.classList.toggle('on',b.dataset.l===LANG);b.onclick=()=>{LS('nutrisense_lang',b.dataset.l);if(b.dataset.l==='en')document.cookie='googtrans=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/';else document.cookie='googtrans=/en/'+b.dataset.l+';path=/';location.reload()}});

/* ===== CHATBOT VOICE TYPING ===== */
window.addEventListener('load',()=>{
 const old=$('#voice-input-btn'),input=$('#chatbot-input'),form=$('#chatbot-form'),msgs=$('#chatbot-messages');if(!old||!input||!form)return;
 const mic=old.cloneNode(true);old.replaceWith(mic);mic.title='Voice typing';
 const row=document.createElement('div');row.className='cb-voice';
 row.innerHTML='<span>Voice typing</span><button type="button" data-v="en-IN">EN</button><button type="button" data-v="mr-IN">मराठी</button><button type="button" data-v="hi-IN">हिंदी</button><button type="button" id="cb-speak">Read replies aloud</button>';
 const live=document.createElement('div');live.className='cb-live';form.before(row);form.before(live);
 let vl={mr:'mr-IN',hi:'hi-IN'}[LANG]||'en-IN',speak=false;
 const mark=()=>row.querySelectorAll('[data-v]').forEach(b=>b.classList.toggle('on',b.dataset.v===vl));mark();
 row.onclick=e=>{const b=e.target.closest('button');if(!b)return;if(b.dataset.v){vl=b.dataset.v;mark();if(rec&&on){rec.stop()}}if(b.id==='cb-speak'){speak=!speak;b.classList.toggle('on',speak);if(!speak)speechSynthesis.cancel()}};
 const SR=window.SpeechRecognition||window.webkitSpeechRecognition;let rec=null,on=false,base='';
 if(!SR){mic.style.opacity='.4';mic.onclick=()=>{live.textContent='Voice typing works in Chrome or Edge.'};}
 else{mic.onclick=()=>{if(on){rec.stop();return}base=input.value?input.value+' ':'';rec=new SR();rec.lang=vl;rec.continuous=true;rec.interimResults=true;
  rec.onresult=e=>{let t='';for(let i=0;i<e.results.length;i++)t+=e.results[i][0].transcript;input.value=base+t;live.textContent=t};
  rec.onstart=()=>{on=true;mic.classList.add('listening');live.textContent='Listening…';if(D)live.textContent=tr('Listening…')};
  rec.onend=()=>{on=false;mic.classList.remove('listening');live.textContent='';input.focus()};
  rec.onerror=ev=>{live.textContent=ev.error==='not-allowed'?'Allow the microphone to use voice typing.':'Voice error: '+ev.error};
  try{rec.start()}catch(e){}}}
 new MutationObserver(ms=>{if(!speak||!('speechSynthesis' in window))return;ms.forEach(m=>m.addedNodes.forEach(n=>{if(n.classList?.contains('chat-bot')&&n.textContent.length>2){const u=new SpeechSynthesisUtterance(n.textContent);u.lang=vl;speechSynthesis.speak(u)}}))}).observe(msgs,{childList:true});
 if(D)pass(row);
});
if(window.feather)feather.replace({'stroke-width':2});
})();
