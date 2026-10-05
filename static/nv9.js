/* NutriVeda v9 — navbar menus, 10 themes, 23 languages, context-aware chatbot */
(function(){
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const LS=(k,v)=>{try{return v===undefined?localStorage.getItem(k):localStorage.setItem(k,v)}catch(e){return null}};
const THEMES=[['default','Aurora','linear-gradient(135deg,#7c3aed,#f472b6)'],['ayurveda','Ayurveda','linear-gradient(135deg,#4f7a45,#e0a21f)'],['saffron','Saffron','linear-gradient(135deg,#c2410c,#f59e0b)'],['forest','Forest','linear-gradient(135deg,#15803d,#86efac)'],['ocean','Ocean','linear-gradient(135deg,#0369a1,#14b8a6)'],['rose','Rose','linear-gradient(135deg,#be185d,#fbcfe8)'],['zen','Zen','linear-gradient(135deg,#444,#e6e6e6)'],['midnight','Midnight','linear-gradient(135deg,#1a1433,#7c3aed)'],['bazaar','Bazaar','linear-gradient(135deg,#e11d48,#f59e0b)'],['neo','Neo Pop','linear-gradient(135deg,#ffd23f,#ff4d8d)']];
const LANGS=[['en','English','English'],['as','অসমীয়া','Assamese'],['bn','বাংলা','Bengali'],['brx','बड़ो','Bodo'],['doi','डोगरी','Dogri'],['gu','ગુજરાતી','Gujarati'],['hi','हिन्दी','Hindi'],['kn','ಕನ್ನಡ','Kannada'],['ks','کٲشُر','Kashmiri'],['gom','कोंकणी','Konkani'],['mai','मैथिली','Maithili'],['ml','മലയാളം','Malayalam'],['mni-Mtei','ꯃꯅꯤꯄꯨꯔꯤ','Manipuri'],['mr','मराठी','Marathi'],['ne','नेपाली','Nepali'],['or','ଓଡ଼ିଆ','Odia'],['pa','ਪੰਜਾਬੀ','Punjabi'],['sa','संस्कृतम्','Sanskrit'],['sat','ᱥᱟᱱᱛᱟᱲᱤ','Santali'],['sd','سنڌي','Sindhi'],['ta','தமிழ்','Tamil'],['te','తెలుగు','Telugu'],['ur','اردو','Urdu']];
const nav=$('#nv9-nav'); if(!nav) return;
const path=location.pathname;
const h=()=>{document.documentElement.style.setProperty('--nv9-h',nav.offsetHeight+'px')};h();addEventListener('resize',h);
/* dropdown behaviour */
const dds=$$('.nv9-dd');
const closeAll=()=>dds.forEach(d=>{d.classList.remove('open');$('.nv9-btn',d).setAttribute('aria-expanded','false')});
dds.forEach(d=>$('.nv9-btn',d).addEventListener('click',e=>{e.stopPropagation();const o=!d.classList.contains('open');closeAll();if(o){d.classList.add('open');$('.nv9-btn',d).setAttribute('aria-expanded','true')}}));
document.addEventListener('click',e=>{if(!e.target.closest('.nv9-dd'))closeAll()});
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeAll()});
$$('.nv9-profmenu [data-open]').forEach(b=>b.addEventListener('click',e=>{e.stopPropagation();const k=b.dataset.open;closeAll();const t=$(k==='lang'?'#nv9-lang':'#nv9-theme');if(k==='settings'){location.href='/dashboard#settings';return}t.classList.add('open');$('.nv9-btn',t).setAttribute('aria-expanded','true')}));
/* mega menu */
const G=[['Check','#7c3aed,#a855f7',[['/form','activity','Symptoms','Spot nutrient gaps'],['/dashboard','bar-chart-2','Dashboard','Your health overview'],['/nutrients','droplet','Nutrients','Vitamins & minerals'],['/bmi','heart','BMI','Body mass index'],['/dosha-quiz','aperture','Dosha Quiz','Vata · Pitta · Kapha'],['/age-nutrition','user','Age Nutrition','Needs by life stage']]],
['Eat','#ea580c,#fb923c',[['/food-log','book-open','Food Diary','Log meals & calories'],['/smart-meal-planner','cpu','Meal Planner','Smart Indian plans'],['/regional-food','map','Regional Food','Foods by region'],['/kitchen','shopping-bag','My Kitchen','Cook what you have'],['/one-food','search','One Food','Many solutions'],['/family-thali','disc','Family Thali','Balanced family meals'],['/seasonal','sunrise','Seasonal Food','Eat with the season'],['/immunity','shield','Immunity','Kadha & recipes'],['/grandma-remedy','coffee',"Grandma's Remedies",'Home wisdom']]],
['Move','#0891b2,#22d3ee',[['/yoga','wind','Yoga','Poses for deficiencies'],['/workout','target','Workout','Home workout planner'],['/steps','compass','Step Tracker','Daily step goals'],['/protein','zap','Protein','Daily protein needs'],['/weightloss','trending-down','Weight Loss','Indian diet plans'],['/weightgain','trending-up','Weight Gain','Healthy gain plans'],['/haircare','scissors','Hair Care','Foods & remedies'],['/skincare','sun','Skin Care','Glow from within']]],
['Wellness','#be185d,#f472b6',[['/pregnancy','smile','Pregnancy','Trimester nutrition'],['/cycle-tracker','calendar','Cycle Tracker','Track your cycle'],['/allergy-tracker','alert-triangle','Allergies','Know your triggers']]],
['More','#4b5563,#9ca3af',[['/community','users','Community','Ask & share'],['/resources','play-circle','Videos & Links','Trusted resources'],['/history','clock','History','Past assessments'],['/feedback','message-circle','Feedback','Help us improve']]]];
const L=$('#nv9-links'),M=$('#nv9-mega'),SC=$('#nv9-scrim');let openG=-1;
if(L&&M){
  L.innerHTML='<a href="/" class="'+(path==='/'?'act':'')+'">Home</a>'+G.map((g,i)=>`<button type="button" data-g="${i}" aria-expanded="false" aria-controls="nv9-mega" class="${g[2].some(x=>x[0]===path)?'act':''}">${g[0]}<i data-feather="chevron-down" class="cv"></i></button>`).join('');
  const closeM=()=>{openG=-1;M.classList.remove('open');SC.classList.remove('open');$$('button',L).forEach(b=>b.setAttribute('aria-expanded','false'))};
  const showM=i=>{closeAll();openG=i;const g=G[i];M.innerHTML=`<div class="nv9-mhead"><h4>${g[0]}</h4></div><div class="nv9-mgrid">${g[2].map(([h,ic,n,d])=>`<a href="${h}" class="${path===h?'on':''}"><span class="nv9-mi" style="background:linear-gradient(135deg,${g[1]})"><i data-feather="${ic}"></i></span><span><b>${n}</b><small>${d}</small></span></a>`).join('')}</div>`;
    M.classList.add('open');SC.classList.add('open');$$('button',L).forEach(b=>b.setAttribute('aria-expanded',String(+b.dataset.g===i)));if(window.feather)feather.replace()};
  L.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;e.stopPropagation();const hv=matchMedia('(hover:hover)').matches;(+b.dataset.g===openG&&!hv)?closeM():showM(+b.dataset.g)});
  L.addEventListener('mouseover',e=>{const b=e.target.closest('button');if(b&&matchMedia('(hover:hover)').matches&&+b.dataset.g!==openG)showM(+b.dataset.g)});
  document.addEventListener('click',e=>{if(!e.target.closest('#nv9-mega,#nv9-links'))closeM()});
  nav.addEventListener('mouseleave',e=>{if(matchMedia('(hover:hover)').matches&&!(e.relatedTarget&&e.relatedTarget.closest&&e.relatedTarget.closest('#nv9-mega')))closeM()});M.addEventListener('mouseleave',e=>{if(matchMedia('(hover:hover)').matches&&!(e.relatedTarget&&e.relatedTarget.closest&&e.relatedTarget.closest('#nv9-nav')))closeM()});
  SC.addEventListener('click',closeM);document.addEventListener('keydown',e=>{if(e.key==='Escape')closeM()});
  dds.forEach(d=>$('.nv9-btn',d).addEventListener('click',closeM));
  $('#nv9-search')?.addEventListener('click',()=>{closeM();$('#tb-menu')?.click()});
}
/* scroll state + progress */
const pg=$('#nv9-progress');const onS=()=>{nav.classList.toggle('sc',scrollY>8);const m=document.documentElement.scrollHeight-innerHeight;if(pg)pg.style.width=(m>0?scrollY/m*100:0)+'%'};addEventListener('scroll',onS,{passive:true});onS();
/* themes */
const cur=document.documentElement.getAttribute('data-theme')||'default';
const tm=$('.nv9-thememenu');
tm.innerHTML=THEMES.map(([k,n,b])=>`<button type="button" data-t="${k}" class="${k===cur?'on':''}"><i style="background:${b}"></i>${n}</button>`).join('');
$('#nv9-theme .nv9-cur').textContent=(THEMES.find(t=>t[0]===cur)||THEMES[0])[1];
tm.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;const k=b.dataset.t;k==='default'?document.documentElement.removeAttribute('data-theme'):document.documentElement.setAttribute('data-theme',k);LS('nutrisense_theme',k);$$('button',tm).forEach(x=>x.classList.toggle('on',x===b));$('#nv9-theme .nv9-cur').textContent=b.textContent;closeAll()});
/* languages: en/mr/hi use the built-in dictionary; the rest use Google Translate */
const lang=LS('nutrisense_lang')||'en', lm=$('.nv9-langmenu');
lm.innerHTML=LANGS.map(([c,n,e])=>`<button type="button" data-l="${c}" lang="${c}" class="${c===lang?'on':''}">${n}<small>${e}</small></button>`).join('');
$('#nv9-lang .nv9-cur').textContent=(LANGS.find(l=>l[0]===lang)||LANGS[0])[1];
lm.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;const c=b.dataset.l;LS('nutrisense_lang',c);
  const exp='expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/';
  if(c==='en'||c==='mr'||c==='hi'){document.cookie='googtrans=;'+exp}else{document.cookie='googtrans=/en/'+c+';path=/'}
  location.reload()});
if(lang!=='en'&&lang!=='mr'&&lang!=='hi'){document.documentElement.lang=lang;document.cookie='googtrans=/en/'+lang+';path=/';
  const d=document.createElement('div');d.id='gt_el9';d.hidden=true;document.body.appendChild(d);
  window.nvGT9=()=>new google.translate.TranslateElement({pageLanguage:'en',includedLanguages:LANGS.map(l=>l[0]).join(','),autoDisplay:false},'gt_el9');
  const s=document.createElement('script');s.src='https://translate.google.com/translate_a/element.js?cb=nvGT9';document.head.appendChild(s)}
/* context-aware chatbot suggestions */
const CTX=[['/haircare',['Foods for hair fall','Best oils for dandruff','Ayurvedic hair mask']],['/skincare',['Foods for glowing skin','Ayurvedic face pack','Acne home remedies']],['/yoga',['Yoga for low iron','Poses for stress','Morning yoga routine']],['/regional-food',['Healthy Kerala foods','Punjab diet tips','Millet dishes by state']],['/immunity',['Immunity kadha recipe','Vitamin C foods','Turmeric milk benefits']],['/dosha-quiz',['What is Vata?','Pitta diet tips','Kapha balancing foods']],['/bmi',['What is a healthy BMI?','Diet for weight loss','Diet for weight gain']],['/food-log',['How to log a meal','Daily calorie needs','High-protein Indian foods']],['/symptoms',['Tired all the time','Vitamin B12 deficiency','Hair fall causes']],['/nutrients',['Iron-rich foods','Calcium sources','Vitamin D sources']],['/dashboard',['Explain my dashboard','Improve my score','Today\'s meal ideas']],['/weightloss',['Indian weight-loss diet','Low-calorie snacks','Walking goals']],['/weightgain',['Healthy weight-gain foods','High-calorie snacks','Protein ideas']],['/kitchen',['Recipes from my pantry','Use leftover rice','Quick dal ideas']],['/grandma-remedy',['Cough remedy','Digestion remedy','Cold remedy with tulsi']]];
const hit=(CTX.find(c=>path.startsWith(c[0]))||[0,['Check my symptoms','Iron-rich foods','Calculate my BMI','Immunity tips']])[1];
const form=$('#chatbot-form'),inp=$('#chatbot-input'),panel=$('#chatbot-panel');
if(form&&inp&&panel){const c=document.createElement('div');c.className='nv9-chips';c.setAttribute('aria-label','Suggested questions');
  c.innerHTML=hit.map(t=>`<button type="button">${t}</button>`).join('');form.before(c);
  c.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;inp.value=b.textContent;form.requestSubmit?form.requestSubmit():form.dispatchEvent(new Event('submit',{cancelable:true}))});
  /* keep the conversation + open state across pages */
  const msgs=$('#chatbot-messages'),K='nv9_chat';
  try{const s=sessionStorage.getItem(K);if(s&&msgs){msgs.innerHTML=s;msgs.scrollTop=msgs.scrollHeight}if(sessionStorage.getItem(K+'_open')==='1')panel.classList.add('open')}catch(e){}
  const save=()=>{try{sessionStorage.setItem(K,msgs.innerHTML);sessionStorage.setItem(K+'_open',panel.classList.contains('open')?'1':'0')}catch(e){}};
  new MutationObserver(save).observe(msgs,{childList:true});new MutationObserver(save).observe(panel,{attributes:true,attributeFilter:['class']})}
/* scroll reveal */
if('IntersectionObserver' in window){const io=new IntersectionObserver(es=>es.forEach(x=>{if(x.isIntersecting){x.target.classList.add('in');io.unobserve(x.target)}}),{threshold:.12});
  $$('main section, body > section, .card, .feature-card, .hero-content-new > *').forEach(el=>{if(!el.closest('.nv9-nav,#nvdrawer,.chatbot-widget')){el.classList.add('nv9-rv');io.observe(el)}})}
if(window.feather)feather.replace();
})();
