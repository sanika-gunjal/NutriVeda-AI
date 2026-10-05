(function(){
const $=s=>document.querySelector(s), U=id=>`https://images.unsplash.com/photo-${id}?w=1600&q=70`;
const IM={yoga:'1544367567-0f2fcb009e0b',food:'1490645935967-10de6ba17061',bowl:'1512621776951-a57141f2eefd',fit:'1517836357463-d25dfeac3438',herb:'1610832958506-aa56368176cf',spice:'1585937421612-70a008356fbe'};
const G=(icon,img,title,info,steps)=>({icon,img:IM[img],title,info,steps});
const GUIDE={
home:G('home','bowl','Welcome to NutriVeda AI','Your Indian food and wellness companion. Everything starts from the top menu.',['Use Symptoms to check what your body may be missing.','Open Yoga for poses matched to each need.','Log meals in Food Diary and plan the week in Meal Planner.','Tap All features for the full list.']),
form:G('activity','herb','Symptom checker','Pick what you feel and see which nutrients may be low.',['Search or filter by body area.','Tick every symptom that applies.','Set how severe and how long.','Press Analyse and read your result.']),
yoga:G('wind','yoga','Yoga for your needs','Poses, breathing and a daily streak for each deficiency or goal.',['Choose a need tab.','Filter by level and read the steps.','Press Start timer on a pose.','Use the breathing pacer, then mark poses done to grow your streak.']),
dashboard:G('bar-chart-2','fit','Dashboard','Your progress and recent checks in one place.',['Review total checks.','Open any recent result.','Return weekly to watch the trend.']),
nutrients:G('droplet','herb','Nutrient encyclopedia','Vitamins and minerals with Indian food sources.',['Search a nutrient.','Filter vitamins or minerals.','Open a card for the full write-up.']),
bmi:G('heart','fit','BMI calculator','A quick body-mass check.',['Enter height and weight.','Read your range.','Follow the links to a plan.']),
'food-log':G('book-open','food','Food diary','Log meals and see today\'s calories.',['Pick the meal.','Enter food, quantity and calories.','Scan a barcode if you like.','Delete a row with the bin button.']),
'smart-meal-planner':G('cpu','bowl','Smart meal planner','A day plan built from your goal and region.',['Choose goal and diet.','Pick your state.','Generate the plan and swap foods.']),
kitchen:G('shopping-bag','food','What\'s in my kitchen','Find recipes from what you already have.',['Select ingredients.','Read the matching recipes.','Open the video to learn each one.']),
'one-food':G('search','spice','One food, many uses','A profile for each food.',['Search a food.','Read uses, recipes and nutrients.','Check the official reference.']),
'regional-food':G('map','spice','Regional food','Traditional foods by state.',['Pick a state.','Search within it.','Open a food for details.']),
weightloss:G('trending-down','fit','Weight loss plan','A gentle food and activity plan.',['Enter your details.','Read the plan.','Track meals in the diary.']),
weightgain:G('trending-up','food','Weight gain plan','Healthy ways to add weight.',['Enter your details.','Read meals and snacks.','Track progress weekly.']),
haircare:G('scissors','herb','Hair care','Food and home care for hair.',['Pick your concern.','Read the foods that help.','Follow the routine.']),
skincare:G('sun','herb','Skin care','Food and routines for skin.',['Pick your skin type.','Read the foods to add.','Follow the routine.']),
yogaDefault:null};
const DEF=G('help-circle','bowl','How this page works','Use the top menu to move between features.',['Read the page from the top.','Use the buttons and filters shown.','Open All features for more tools.']);
const A=window.NV_ACTIVE||'home', g=GUIDE[A]||DEF;
const BK={yoga:'yoga',form:'healthy,vegetables',nutrients:'fruits,vegetables',dashboard:'healthy,food','food-log':'thali',weightloss:'salad',weightgain:'nuts,dryfruits',haircare:'herbs',skincare:'turmeric',immunity:'ginger,tulsi',protein:'lentils',kitchen:'spices','one-food':'indian,spices','regional-food':'indian,food',seasonal:'fruits',workout:'fitness',steps:'walking',pregnancy:'fruits,milk','dosha-quiz':'ayurveda','smart-meal-planner':'thali'};
const TITLE={form:'Symptom checker',yoga:'Yoga for your needs'};

// dropdown
document.querySelectorAll('.tb-drop>button').forEach(b=>b.addEventListener('click',e=>{e.stopPropagation();b.parentNode.classList.toggle('open')}));
document.addEventListener('click',()=>document.querySelectorAll('.tb-drop.open').forEach(d=>d.classList.remove('open')));



// guide
const gd=$('#guide'),vid=$('#guide-video');
$('#guide-title').textContent=g.title;$('#guide-info').textContent=g.info;
$('#guide-steps').innerHTML=g.steps.map(s=>`<li>${s}</li>`).join('');
const open=v=>{gd.classList.toggle('open',v);if(!v){vid.pause();speechSynthesis?.cancel()}};
$('#tb-guide')?.addEventListener('click',()=>open(!gd.classList.contains('open')));
$('#guide-x')?.addEventListener('click',()=>open(false));
$('#guide-play')?.addEventListener('click',()=>{vid.muted=false;vid.currentTime=0;vid.play();
  if('speechSynthesis' in window){speechSynthesis.cancel();const lang=localStorage.getItem('nutrisense_lang')||'en';
   const u=new SpeechSynthesisUtterance(g.title+'. '+g.info+' '+g.steps.map((s,i)=>'Step '+(i+1)+'. '+s).join(' '));u.lang={mr:'mr-IN',hi:'hi-IN'}[lang]||'en-IN';u.rate=.95;setTimeout(()=>speechSynthesis.speak(u),9000)}});
$('#guide-mute')?.addEventListener('click',e=>{vid.muted=!vid.muted;speechSynthesis?.cancel();e.currentTarget.lastChild.textContent=vid.muted?' Unmute':' Mute'});
if(A==='home'&&!sessionStorage.getItem('nv_welcomed')){sessionStorage.setItem('nv_welcomed','1');vid.muted=true;open(true);vid.play().catch(()=>{})}

// banner on feature pages
if(A!=='home'&&A!=='login'&&A!=='signup'&&!document.querySelector('.nv-banner')){
  const b=document.createElement('section');b.className='nv-banner';b.style.backgroundImage=`url(https://loremflickr.com/1600/420/${encodeURIComponent(BK[A]||'indian,food')}?lock=7)`;
  b.innerHTML=`<div class="row"><span class="bi"><i data-feather="${g.icon}"></i></span><div><h1>${g.title}</h1><p>${g.info}</p></div></div>`;
  const ref=document.getElementById('reminder-banner');ref?ref.after(b):document.body.prepend(b);
}

// 50 foods
const TAGS={yoga:['stress','energy','bones'],form:['iron','calcium','b12','vitd','protein'],weightloss:['wl'],weightgain:['wg'],haircare:['hair'],skincare:['skin'],immunity:['immunity'],protein:['protein'],seasonal:['immunity'],workout:['protein','energy'],steps:['energy'],'food-log':['energy'],nutrients:['iron','calcium','b12','vitd'],dashboard:['energy'],bmi:['wl','wg'],pregnancy:['iron','calcium'],'dosha-quiz':['digest']};
const F=window.NV_FOODS||[],T=TAGS[A]||[],cats=['All',...new Set(F.map(f=>f.cat))],chips=$('#nv-fchips'),grid=$('#nv-fgrid');
let cat='All';
function paint(){if(!grid)return;const m=f=>f.tags.some(t=>T.includes(t));
 const list=F.filter(f=>cat==='All'||f.cat===cat).sort((a,b)=>m(b)-m(a));
 grid.innerHTML=list.map(f=>`<div class="nv-fcard ${m(f)?'match':''}"><span class="em">${f.emoji}<img loading="lazy" alt="${f.name}" src="https://loremflickr.com/120/120/${f.kw}?lock=${f.id}" onerror="this.remove()"></span><div><b>${f.name}</b><small>${f.nutrient} · ${f.kcal} kcal</small></div></div>`).join('');
 chips.innerHTML=cats.map(c=>`<button type="button" class="${c===cat?'on':''}" data-c="${c}">${c}</button>`).join('')}
chips?.addEventListener('click',e=>{const c=e.target.dataset?.c;if(c){cat=c;paint()}});
paint();
window.NV={foods:F,openGuide:open};
if(window.feather)feather.replace({'stroke-width':2});
})();
