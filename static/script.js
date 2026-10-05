document.addEventListener("DOMContentLoaded", () => {
  console.log("🥗 NutriVeda AI Loaded");

  // Mark active nav link
  const path = window.location.pathname;
  document.querySelectorAll('.nav-links a').forEach(a => {
    if (a.getAttribute('href') === path) a.classList.add('active');
  });

  // Animate progress bars on load
  document.querySelectorAll('.progress-bar-fill').forEach(bar => {
    const target = bar.style.width;
    bar.style.width = '0';
    setTimeout(() => { bar.style.width = target; }, 200);
  });

  // ==========================================================
  // SETTINGS PANEL — Theme + Language tabs
  // ==========================================================
  (function () {
    const THEME_KEY = 'nutrisense_theme';
    const toggleBtn = document.getElementById('settings-toggle');
    const panel = document.getElementById('settings-panel');
    const swatches = document.querySelectorAll('.theme-swatch');
    const tabs = document.querySelectorAll('.settings-tab');
    const tabPanels = document.querySelectorAll('.settings-tab-panel');
    if (!toggleBtn || !panel) return;

    const applyTheme = (theme) => {
      if (!theme || theme === 'default') {
        document.documentElement.removeAttribute('data-theme');
      } else {
        document.documentElement.setAttribute('data-theme', theme);
      }
      swatches.forEach(sw => sw.classList.toggle('selected', sw.dataset.theme === (theme || 'default')));
    };
    applyTheme(document.documentElement.getAttribute('data-theme') || 'default');

    const openPanel = () => {
      panel.classList.add('open');
      panel.setAttribute('aria-hidden', 'false');
      toggleBtn.setAttribute('aria-expanded', 'true');
      toggleBtn.classList.add('active');
    };
    const closePanel = () => {
      panel.classList.remove('open');
      panel.setAttribute('aria-hidden', 'true');
      toggleBtn.setAttribute('aria-expanded', 'false');
      toggleBtn.classList.remove('active');
    };

    toggleBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      panel.classList.contains('open') ? closePanel() : openPanel();
    });

    document.addEventListener('click', (e) => {
      if (panel.classList.contains('open') && !e.target.closest('.theme-panel') && !e.target.closest('#settings-toggle')) {
        closePanel();
      }
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closePanel();
    });

    swatches.forEach(sw => {
      sw.addEventListener('click', () => {
        const theme = sw.dataset.theme;
        applyTheme(theme);
        try { localStorage.setItem(THEME_KEY, theme); } catch (e) {}
        closePanel();
      });
    });

    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        tabs.forEach(t => t.classList.toggle('active', t === tab));
        tabPanels.forEach(p => { p.hidden = (p.dataset.tabPanel !== tab.dataset.tab); });
      });
    });
  })();

  // ==========================================================
  // SENIOR CITIZEN MODE — bigger fonts/buttons, simpler layout.
  // Persisted via localStorage like theme/language, applied as a
  // class on <html> so style.css can target it sitewide.
  // ==========================================================
  (function () {
    const SENIOR_KEY = 'nutrisense_senior';
    const checkbox = document.getElementById('senior-mode-checkbox');
    if (!checkbox) return;

    const applySenior = (on) => {
      document.documentElement.classList.toggle('senior-mode', !!on);
      checkbox.checked = !!on;
    };

    let saved = false;
    try { saved = localStorage.getItem(SENIOR_KEY) === 'on'; } catch (e) {}
    applySenior(saved);

    checkbox.addEventListener('change', () => {
      applySenior(checkbox.checked);
      try { localStorage.setItem(SENIOR_KEY, checkbox.checked ? 'on' : 'off'); } catch (e) {}
    });
  })();

  // ==========================================================
  // LANGUAGE SWITCHER — English / मराठी / हिंदी
  // A lightweight sitewide dictionary applied to any element carrying
  // data-i18n (text content) or data-i18n-placeholder (input placeholder).
  // ==========================================================
  (function () {
    const LANG_KEY = 'nutrisense_lang';
    const dict = {
      en: {
        "settings.theme": "Theme", "settings.language": "Language",
        "nav.home": "Home", "nav.analysis": "Analysis", "nav.dashboard": "Dashboard",
        "nav.nutrients": "Nutrients", "nav.bmi": "BMI", "nav.weightloss": "Weight Loss",
        "nav.weightgain": "Weight Gain", "nav.haircare": "Hair Care", "nav.skincare": "Skin Care",
        "nav.foodlog": "Food Diary", "nav.community": "Community", "nav.grandma": "Grandma's Remedies",
        "nav.thali": "Family Thali", "nav.more": "More", "nav.seasonal": "Seasonal Food Guide",
        "nav.protein": "Protein Calculator", "nav.workout": "Home Workout Planner",
        "nav.yoga": "Yoga for Deficiencies", "nav.steps": "Step Goal Tracker",
        "nav.immunity": "Immunity Recipes", "nav.resources": "Video & Official Resources",
        "nav.noresults": "No features match your search.", "nav.feedback": "Feedback",
        "nav.history": "History", "nav.symptomhistory": "Symptom History", "nav.logout": "Log Out",
        "nav.login": "Log In", "nav.signup": "Sign Up", "nav.search": "Search features…",
        "footer.tagline": "Intelligent Nutrition Platform",
        "chatbot.title": "NutriBot Assistant",
        "chatbot.greeting": "Hi! Ask me about a nutrient, deficiency, BMI, or how to log a meal. 🥗",
        "chatbot.placeholder": "Type your question...",
        "settings.accessibility": "Accessibility", "settings.seniormode": "Senior Citizen Mode",
        "settings.seniormodedesc": "Bigger text & buttons, simpler layout — easy on the eyes.",
        "nav.wellnessplus": "Wellness+", "nav.dosha": "Prakruti (Dosha) Quiz",
        "nav.pregnancy": "Pregnancy Nutrition Guide", "nav.agenutrition": "Age-wise Nutrition Needs",
        "nav.cycletracker": "Menstrual Cycle Tracker", "nav.allergytracker": "Allergy Tracker",
        "nav.regional": "Regional Food", "nav.kitchen": "My Kitchen", "nav.onefood": "One Food", "nav.smartplanner": "Smart Planner",
        "regional.eyebrow": "India on Your Plate", "regional.title": "Indian Regional Food Intelligence", "regional.subtitle": "Select a state and discover traditional foods, meal ideas, key nutrients and learning videos from that region.", "regional.choose": "Choose your state", "regional.search": "Search a food, nutrient or cuisine…",
        "kitchen.eyebrow": "Smart Kitchen", "kitchen.title": "What's in My Kitchen?", "kitchen.subtitle": "Select ingredients you already have. NutriVeda turns them into Indian recipe ideas and shows the nutrition value of each option.", "kitchen.pick": "Pick your ingredients", "kitchen.search": "Search ingredients…",
        "onefood.eyebrow": "Food Encyclopedia", "onefood.title": "One Food — Many Solutions", "onefood.subtitle": "Explore one food from every angle: what it is, how to use it, recipes, nutrients, wellness roles and interesting facts.", "onefood.search": "Search foods like amla, ragi, spinach…",
        "planner.eyebrow": "Advanced Personalisation", "planner.title": "Smart Indian Meal Planner", "planner.subtitle": "Combine your goal, food preference and region to get a practical Indian meal framework.",
        "home.overview.eyebrow": "Explore the Intelligence Layer", "home.overview.title": "Nutrition, Food, Yoga & Ayurveda — connected in one journey", "home.overview.desc": "Move from understanding nutrients to choosing regional food, cooking what is already in your kitchen, building a plan and supporting it with movement and Ayurveda-inspired wellness."
      },
      mr: {
        "settings.theme": "थीम", "settings.language": "भाषा",
        "nav.home": "मुख्यपृष्ठ", "nav.analysis": "विश्लेषण", "nav.dashboard": "डॅशबोर्ड",
        "nav.nutrients": "पोषक घटक", "nav.bmi": "बीएमआय", "nav.weightloss": "वजन कमी करा",
        "nav.weightgain": "वजन वाढवा", "nav.haircare": "केसांची काळजी", "nav.skincare": "त्वचेची काळजी",
        "nav.foodlog": "फूड डायरी", "nav.community": "कम्युनिटी", "nav.grandma": "आजीचे उपाय",
        "nav.thali": "फॅमिली थाळी", "nav.more": "अधिक", "nav.seasonal": "ऋतूनुसार आहार",
        "nav.protein": "प्रोटीन कॅल्क्युलेटर", "nav.workout": "घरगुती वर्कआउट प्लॅन",
        "nav.yoga": "कमतरतेसाठी योगा", "nav.steps": "पावले लक्ष्य ट्रॅकर",
        "nav.immunity": "इम्युनिटी रेसिपी", "nav.resources": "व्हिडिओ व अधिकृत स्रोत",
        "nav.noresults": "तुमच्या शोधाशी जुळणारे काही सापडले नाही.", "nav.feedback": "अभिप्राय",
        "nav.history": "इतिहास", "nav.symptomhistory": "लक्षण इतिहास", "nav.logout": "लॉग आउट",
        "nav.login": "लॉग इन", "nav.signup": "साइन अप", "nav.search": "फीचर्स शोधा…",
        "footer.tagline": "इंटेलिजंट न्यूट्रिशन प्लॅटफॉर्म",
        "chatbot.title": "न्यूट्रीबॉट असिस्टंट",
        "chatbot.greeting": "नमस्कार! पोषक घटक, कमतरता, बीएमआय किंवा जेवण कसं लॉग करायचं याबद्दल विचारा. 🥗",
        "chatbot.placeholder": "तुमचा प्रश्न टाइप करा...",
        "settings.accessibility": "सुलभता", "settings.seniormode": "ज्येष्ठ नागरिक मोड",
        "settings.seniormodedesc": "मोठा फॉन्ट व बटणे, सोपी मांडणी — डोळ्यांना सोपे.",
        "nav.wellnessplus": "वेलनेस+", "nav.dosha": "प्रकृती (दोष) क्विझ",
        "nav.pregnancy": "गर्भधारणा पोषण मार्गदर्शक", "nav.agenutrition": "वयानुसार पोषण गरजा",
        "nav.cycletracker": "मासिक पाळी ट्रॅकर", "nav.allergytracker": "अ‍ॅलर्जी ट्रॅकर",
        "nav.regional": "प्रादेशिक आहार", "nav.kitchen": "माझे स्वयंपाकघर", "nav.onefood": "एक अन्न", "nav.smartplanner": "स्मार्ट आहार नियोजक",
        "regional.eyebrow": "तुमच्या ताटात भारत", "regional.title": "भारतीय प्रादेशिक खाद्य बुद्धिमत्ता", "regional.subtitle": "राज्य निवडा आणि त्या प्रदेशातील पारंपरिक पदार्थ, जेवणाच्या कल्पना, महत्त्वाचे पोषक घटक आणि शिकण्यासाठी व्हिडिओ शोधा.", "regional.choose": "तुमचे राज्य निवडा", "regional.search": "पदार्थ, पोषक घटक किंवा पाककृती शोधा…",
        "kitchen.eyebrow": "स्मार्ट स्वयंपाकघर", "kitchen.title": "माझ्या स्वयंपाकघरात काय आहे?", "kitchen.subtitle": "तुमच्याकडे असलेले घटक निवडा. NutriVeda त्यापासून भारतीय पाककृती आणि प्रत्येक पर्यायाची पोषणमाहिती दाखवते.", "kitchen.pick": "घटक निवडा", "kitchen.search": "घटक शोधा…",
        "onefood.eyebrow": "अन्न विश्वकोश", "onefood.title": "एक अन्न — अनेक उपयोग", "onefood.subtitle": "एका अन्नाकडे सर्व बाजूंनी पाहा: ते काय आहे, कसे वापरायचे, पाककृती, पोषक घटक, आरोग्यदायी भूमिका आणि मनोरंजक तथ्ये.", "onefood.search": "आवळा, नाचणी, पालक यांसारखे पदार्थ शोधा…",
        "planner.eyebrow": "प्रगत वैयक्तिकरण", "planner.title": "स्मार्ट भारतीय आहार नियोजक", "planner.subtitle": "तुमचे ध्येय, आहाराची पसंती आणि प्रदेश एकत्र करून व्यावहारिक भारतीय आहाराचा आराखडा मिळवा.",
        "home.overview.eyebrow": "बुद्धिमान पोषण स्तर", "home.overview.title": "पोषण, अन्न, योग आणि आयुर्वेद — एका प्रवासात जोडलेले", "home.overview.desc": "पोषक घटक समजून घेण्यापासून प्रादेशिक अन्न निवडणे, स्वयंपाकघरातील घटकांपासून पाककृती बनवणे, आहार आराखडा तयार करणे आणि योग व आयुर्वेद-प्रेरित कल्याणाशी जोडणे — सर्व एका ठिकाणी."
      },
      hi: {
        "settings.theme": "थीम", "settings.language": "भाषा",
        "nav.home": "होम", "nav.analysis": "विश्लेषण", "nav.dashboard": "डैशबोर्ड",
        "nav.nutrients": "पोषक तत्व", "nav.bmi": "बीएमआई", "nav.weightloss": "वज़न घटाएं",
        "nav.weightgain": "वज़न बढ़ाएं", "nav.haircare": "बालों की देखभाल", "nav.skincare": "त्वचा की देखभाल",
        "nav.foodlog": "फूड डायरी", "nav.community": "कम्युनिटी", "nav.grandma": "दादी-नानी के नुस्खे",
        "nav.thali": "फैमिली थाली", "nav.more": "अधिक", "nav.seasonal": "मौसमी आहार गाइड",
        "nav.protein": "प्रोटीन कैलकुलेटर", "nav.workout": "होम वर्कआउट प्लानर",
        "nav.yoga": "कमी के लिए योग", "nav.steps": "कदम लक्ष्य ट्रैकर",
        "nav.immunity": "इम्युनिटी रेसिपी", "nav.resources": "वीडियो और आधिकारिक संसाधन",
        "nav.noresults": "आपकी खोज से मेल खाने वाला कुछ नहीं मिला.", "nav.feedback": "फीडबैक",
        "nav.history": "इतिहास", "nav.symptomhistory": "लक्षण इतिहास", "nav.logout": "लॉग आउट",
        "nav.login": "लॉग इन", "nav.signup": "साइन अप", "nav.search": "फीचर खोजें…",
        "footer.tagline": "इंटेलिजेंट न्यूट्रिशन प्लेटफ़ॉर्म",
        "chatbot.title": "न्यूट्रीबॉट असिस्टेंट",
        "chatbot.greeting": "नमस्ते! किसी पोषक तत्व, कमी, बीएमआई या भोजन लॉग करने के बारे में पूछें। 🥗",
        "chatbot.placeholder": "अपना सवाल लिखें...",
        "settings.accessibility": "सुगमता", "settings.seniormode": "वरिष्ठ नागरिक मोड",
        "settings.seniormodedesc": "बड़ा फॉन्ट व बटन, सरल लेआउट — आंखों के लिए आसान.",
        "nav.wellnessplus": "वेलनेस+", "nav.dosha": "प्रकृति (दोष) क्विज़",
        "nav.pregnancy": "गर्भावस्था पोषण गाइड", "nav.agenutrition": "उम्र के अनुसार पोषण ज़रूरतें",
        "nav.cycletracker": "मासिक धर्म ट्रैकर", "nav.allergytracker": "एलर्जी ट्रैकर",
        "nav.regional": "क्षेत्रीय भोजन", "nav.kitchen": "मेरी रसोई", "nav.onefood": "एक भोजन", "nav.smartplanner": "स्मार्ट प्लानर",
        "regional.eyebrow": "आपकी थाली में भारत", "regional.title": "भारतीय क्षेत्रीय खाद्य बुद्धिमत्ता", "regional.subtitle": "राज्य चुनें और उस क्षेत्र के पारंपरिक भोजन, भोजन विचार, प्रमुख पोषक तत्व और सीखने वाले वीडियो खोजें.", "regional.choose": "अपना राज्य चुनें", "regional.search": "भोजन, पोषक तत्व या व्यंजन खोजें…",
        "kitchen.eyebrow": "स्मार्ट रसोई", "kitchen.title": "मेरी रसोई में क्या है?", "kitchen.subtitle": "अपने पास मौजूद सामग्री चुनें। NutriVeda उनसे भारतीय रेसिपी और पोषण जानकारी दिखाता है.", "kitchen.pick": "सामग्री चुनें", "kitchen.search": "सामग्री खोजें…",
        "onefood.eyebrow": "भोजन विश्वकोश", "onefood.title": "एक भोजन — कई उपयोग", "onefood.subtitle": "एक भोजन को हर कोण से देखें: यह क्या है, कैसे उपयोग करें, रेसिपी, पोषक तत्व, स्वास्थ्य भूमिका और रोचक तथ्य.", "onefood.search": "आंवला, रागी, पालक जैसे भोजन खोजें…",
        "planner.eyebrow": "उन्नत निजीकरण", "planner.title": "स्मार्ट भारतीय भोजन प्लानर", "planner.subtitle": "अपने लक्ष्य, भोजन पसंद और क्षेत्र को मिलाकर एक व्यावहारिक भारतीय भोजन ढांचा प्राप्त करें.",
        "home.overview.eyebrow": "इंटेलिजेंस लेयर देखें", "home.overview.title": "पोषण, भोजन, योग और आयुर्वेद — एक ही यात्रा में जुड़े", "home.overview.desc": "पोषक तत्व समझने से लेकर क्षेत्रीय भोजन चुनने, रसोई की सामग्री से रेसिपी बनाने, भोजन योजना तैयार करने और योग व आयुर्वेद-प्रेरित वेलनेस तक सब एक जगह."
      }
    };

    // Deep Marathi mode: translate visible interface text, including
    // dynamic cards rendered by feature pages. Original text is cached so
    // switching back to English never leaves mixed-language labels.
    const mrPhraseMap = {
      "Choose your state":"तुमचे राज्य निवडा","Search a food, nutrient or cuisine…":"पदार्थ, पोषक घटक किंवा पाककृती शोधा…",
      "Select ingredients to begin":"घटक निवडून सुरुवात करा","ingredients selected":"घटक निवडले",
      "recipe idea":"पाककृतीची कल्पना","recipe ideas":"पाककृतींच्या कल्पना","Watch recipe on YouTube":"YouTube वर पाककृती पहा",
      "Watch a recipe on YouTube":"YouTube वर पाककृती पहा","Watch recipes & food education on YouTube":"YouTube वर पाककृती व अन्नशिक्षण पहा",
      "Official nutrition reference":"अधिकृत पोषण संदर्भ","Explore this food →":"हे अन्न सविस्तर पाहा →",
      "Food Profile":"अन्न प्रोफाइल","Nutrition facts":"पोषणमाहिती","Uses":"उपयोग","Recipes":"पाककृती",
      "Nutrient profile":"पोषक घटक प्रोफाइल","Wellness roles":"आरोग्यदायी भूमिका","Quick facts":"महत्त्वाची तथ्ये",
      "Advanced Personalisation":"प्रगत वैयक्तिकरण","PERSONALISED FRAMEWORK":"वैयक्तिकृत आराखडा",
      "Breakfast":"नाश्ता","Lunch":"दुपारचे जेवण","Snack":"अल्पोपहार","Dinner":"रात्रीचे जेवण",
      "Balanced":"संतुलित","Weight Loss":"वजन कमी करणे","Healthy Weight Gain":"निरोगी वजन वाढ","Higher Protein":"अधिक प्रथिने",
      "Build My Plan":"माझा आहार आराखडा तयार करा","Clear":"पुसा","Goal":"ध्येय","Diet":"आहार","State":"राज्य",
      "REGION":"प्रदेश","RECIPE MATCHER":"पाककृती शोधक","INDIAN RECIPE":"भारतीय पाककृती","India on Your Plate":"तुमच्या ताटात भारत",
      "Select a state and discover traditional foods, meal ideas, key nutrients and learning videos from that region.":"राज्य निवडा आणि त्या प्रदेशातील पारंपरिक पदार्थ, जेवणाच्या कल्पना, महत्त्वाचे पोषक घटक व शिकण्यासाठी व्हिडिओ शोधा.",
      "No matching food found. Try another search.":"जुळणारा पदार्थ सापडला नाही. दुसरा शोध वापरा.",
      "Choose 1 or more ingredients to see matching recipes.":"जुळणाऱ्या पाककृती पाहण्यासाठी एक किंवा अधिक घटक निवडा.",
      "One Food — Many Solutions":"एक अन्न — अनेक उपयोग","Smart Indian Meal Planner":"स्मार्ट भारतीय आहार नियोजक"
    };
    const mrWordMap = {
      "Home":"मुख्यपृष्ठ","Analysis":"विश्लेषण","Dashboard":"डॅशबोर्ड","Nutrients":"पोषक घटक","BMI":"बीएमआय",
      "Weight":"वजन","Loss":"कमी","Gain":"वाढ","Hair":"केस","Care":"काळजी","Skin":"त्वचा","Food":"अन्न",
      "Diary":"दैनंदिनी","Community":"समुदाय","Resources":"स्रोत","Official":"अधिकृत","Video":"व्हिडिओ",
      "Videos":"व्हिडिओ","Search":"शोधा","features":"फीचर्स","Feature":"फीचर","Select":"निवडा","state":"राज्य",
      "State":"राज्य","food":"अन्न","foods":"पदार्थ","nutrient":"पोषक घटक","nutrients":"पोषक घटक",
      "recipe":"पाककृती","recipes":"पाककृती","protein":"प्रथिने","fibre":"तंतू","fiber":"तंतू","iron":"लोह",
      "calcium":"कॅल्शियम","vitamin":"जीवनसत्त्व","vitamins":"जीवनसत्त्वे","mineral":"खनिज","minerals":"खनिजे",
      "health":"आरोग्य","healthy":"निरोगी","wellness":"कल्याण","nutrition":"पोषण","nutrition facts":"पोषणमाहिती",
      "Indian":"भारतीय","regional":"प्रादेशिक","kitchen":"स्वयंपाकघर","ingredients":"घटक","ingredient":"घटक",
      "meal":"जेवण","meals":"जेवणे","breakfast":"नाश्ता","lunch":"दुपारचे जेवण","dinner":"रात्रीचे जेवण",
      "snack":"अल्पोपहार","plan":"आराखडा","planner":"नियोजक","build":"तयार करा","my":"माझे","your":"तुमचे",
      "body":"शरीर","guide":"मार्गदर्शक","history":"इतिहास","login":"लॉग इन","logout":"लॉग आउट","sign":"नोंदणी",
      "up":"करा","down":"कमी","more":"अधिक","learn":"शिका","watch":"पहा","read":"वाचा","add":"जोडा",
      "clear":"पुसा","today":"आज","daily":"दररोज","source":"स्रोत","sources":"स्रोत","official":"अधिकृत",
      "information":"माहिती","introduction":"परिचय","facts":"तथ्ये","uses":"उपयोग","role":"भूमिका",
      "roles":"भूमिका","calories":"कॅलरी","portion":"प्रमाण","suggestion":"सूचना","suggestions":"सूचना",
      "balanced":"संतुलित","goal":"ध्येय","diet":"आहार","advanced":"प्रगत","personalized":"वैयक्तिकृत",
      "personalised":"वैयक्तिकृत","free":"मोफत","smart":"स्मार्ट","platform":"प्लॅटफॉर्म"
    };
    function deepMarathi() {
      const root=document.body;
      const walk=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
      const nodes=[];
      while(walk.nextNode()) {
        const n=walk.currentNode, p=n.parentElement;
        if(!p || /^(SCRIPT|STYLE|NOSCRIPT|TEXTAREA)$/i.test(p.tagName) || p.closest('[data-no-translate]')) continue;
        nodes.push(n);
      }
      nodes.forEach(n=>{
        if(!n.dataset.originalText) n.dataset.originalText=n.nodeValue;
        let text=n.dataset.originalText;
        Object.entries(mrPhraseMap).forEach(([a,b])=>{ text=text.split(a).join(b); });
        Object.entries(mrWordMap).forEach(([a,b])=>{
          text=text.replace(new RegExp('\\\\b'+a.replace(/[.*+?^${}()|[\\]\\\\]/g,'\\\\$&')+'\\\\b','gi'),b);
        });
        n.nodeValue=text;
      });
    }
    function restoreOriginalText() {
      document.querySelectorAll('body *').forEach(el=>{
        if(el.childNodes.length===1 && el.firstChild.nodeType===Node.TEXT_NODE && el.firstChild.dataset && el.firstChild.dataset.originalText)
          el.firstChild.nodeValue=el.firstChild.dataset.originalText;
      });
    }

    const applyLanguage = (lang) => {
      if (lang !== 'mr') restoreOriginalText();
      const t = dict[lang] || dict.en;
      document.documentElement.setAttribute('lang', lang);
      document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (t[key]) el.textContent = t[key];
      });
      document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        if (t[key]) el.setAttribute('placeholder', t[key]);
      });
      document.querySelectorAll('.lang-option').forEach(btn => {
        btn.classList.toggle('selected', btn.dataset.lang === lang);
      });
      /* v8: handled by static/app2.js */
    };

    let current = 'en';
    try { current = localStorage.getItem(LANG_KEY) || 'en'; } catch (e) {}
    applyLanguage(current);

    document.querySelectorAll('.lang-option').forEach(btn => {
      btn.addEventListener('click', () => {
        const lang = btn.dataset.lang;
        applyLanguage(lang);
        try { localStorage.setItem(LANG_KEY, lang); } catch (e) {}
      });
    });

    // Expose for pages that want their own extra translations later
    window.nutrisenseI18n = { applyLanguage, dict, get current() { return current; } };
  })();

  // Nav "More" dropdown toggle (inline accordion inside the sidebar)
  document.querySelectorAll('.nav-dropdown-toggle').forEach(toggle => {
    toggle.addEventListener('click', (e) => {
      e.stopPropagation();
      const dropdown = toggle.closest('.nav-dropdown');
      const wasOpen = dropdown.classList.contains('open');
      document.querySelectorAll('.nav-dropdown.open').forEach(d => {
        if (d !== dropdown) d.classList.remove('open');
      });
      dropdown.classList.toggle('open', !wasOpen);
    });
  });
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.nav-dropdown')) {
      document.querySelectorAll('.nav-dropdown.open').forEach(d => d.classList.remove('open'));
    }
  });

  // ==========================================================
  // SIDEBAR: mobile hamburger toggle
  // ==========================================================
  const sidebar = document.getElementById('sidebar');
  const sidebarToggle = document.getElementById('sidebar-toggle');
  const sidebarBackdrop = document.getElementById('sidebar-backdrop');

  function closeSidebar() {
    sidebar?.classList.remove('sidebar-open');
    document.body.classList.remove('sidebar-open');
    sidebarToggle?.setAttribute('aria-expanded', 'false');
  }
  function openSidebar() {
    sidebar?.classList.add('sidebar-open');
    document.body.classList.add('sidebar-open');
    sidebarToggle?.setAttribute('aria-expanded', 'true');
  }
  sidebarToggle?.addEventListener('click', (e) => {
    e.stopPropagation();
    sidebar?.classList.contains('sidebar-open') ? closeSidebar() : openSidebar();
  });
  sidebarBackdrop?.addEventListener('click', closeSidebar);
  // Close the off-canvas sidebar after picking a link on mobile
  sidebar?.querySelectorAll('a').forEach(a => a.addEventListener('click', closeSidebar));

  // ==========================================================
  // SIDEBAR: feature search — live-filters the nav links
  // ==========================================================
  const searchInput = document.getElementById('nav-search-input');
  const searchEmpty = document.getElementById('nav-search-empty');
  const navLinks = document.getElementById('nav-links');

  if (searchInput && navLinks) {
    const allLinks = Array.from(navLinks.querySelectorAll('a[data-label]'));

    searchInput.addEventListener('input', () => {
      const q = searchInput.value.trim().toLowerCase();
      let visibleCount = 0;

      allLinks.forEach(a => {
        const label = (a.dataset.label || a.textContent || '').toLowerCase();
        const match = !q || label.includes(q);
        a.dataset.match = match ? 'show' : 'hide';
        if (match) visibleCount++;

        // If a match lives inside the "More" accordion, force it open so it's visible
        const dropdown = a.closest('.nav-dropdown');
        if (dropdown && q) {
          dropdown.classList.toggle('open', dropdown.querySelectorAll('a[data-match="show"]').length > 0);
        } else if (dropdown && !q) {
          dropdown.classList.remove('open');
        }
      });

      if (searchEmpty) searchEmpty.classList.toggle('show', q.length > 0 && visibleCount === 0);
    });

    // Enter jumps straight to the first visible match
    searchInput.addEventListener('keydown', (e) => {
      if (e.key !== 'Enter') return;
      const firstMatch = allLinks.find(a => a.dataset.match !== 'hide' && a.offsetParent !== null)
        || allLinks.find(a => a.dataset.match !== 'hide');
      if (firstMatch) {
        e.preventDefault();
        window.location.href = firstMatch.getAttribute('href');
      }
    });

    // Esc clears the search
    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        searchInput.value = '';
        searchInput.dispatchEvent(new Event('input'));
        searchInput.blur();
      }
    });
  }

  // ==========================================================
  // SCROLL-REVEAL: fade/slide elements into view as user scrolls
  // ==========================================================
  const revealEls = document.querySelectorAll('.reveal, .reveal-stagger');
  if (revealEls.length) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('in-view');
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });
    revealEls.forEach(el => io.observe(el));
  }

  // ==========================================================
  // COUNT-UP: animate numeric stats from 0 to target on reveal
  // ==========================================================
  const counters = document.querySelectorAll('.count-up');
  if (counters.length) {
    const countIo = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        const el = entry.target;
        countIo.unobserve(el);
        const raw = el.dataset.target || el.textContent;
        const match = raw.match(/[\d.]+/);
        if (!match) return;
        const target = parseFloat(match[0]);
        const suffix = raw.replace(match[0], '');
        const duration = 1100;
        const start = performance.now();
        function tick(now) {
          const p = Math.min(1, (now - start) / duration);
          const eased = 1 - Math.pow(1 - p, 3);
          const val = target * eased;
          el.textContent = (target % 1 === 0 ? Math.round(val) : val.toFixed(1)) + suffix;
          if (p < 1) requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);
      });
    }, { threshold: 0.4 });
    counters.forEach(el => countIo.observe(el));
  }

  // ==========================================================
  // TILT HOVER: subtle 3D tilt on cards that opt in
  // ==========================================================
  document.querySelectorAll('.tilt-hover').forEach(card => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width - 0.5;
      const y = (e.clientY - rect.top) / rect.height - 0.5;
      card.style.transform = `translateY(-6px) rotateX(${(-y * 6).toFixed(2)}deg) rotateY(${(x * 6).toFixed(2)}deg)`;
    });
    card.addEventListener('mouseleave', () => {
      card.style.transform = '';
    });
  });

  // ==========================================================
  // PARALLAX BLOBS: ambient blobs drift slightly with scroll
  // ==========================================================
  const blobContainers = document.querySelectorAll('.ambient-blobs');
  if (blobContainers.length) {
    window.addEventListener('scroll', () => {
      const y = window.scrollY;
      blobContainers.forEach(c => {
        c.style.transform = `translateY(${y * 0.08}px)`;
      });
    }, { passive: true });
  }

  // ==========================================================
  // PAGE FADE-IN: whole page softly fades/rises in on load
  // ==========================================================
  document.body.classList.add('page-enter');
  requestAnimationFrame(() => document.body.classList.add('page-enter-active'));

  // ==========================================================
  // BUTTON RIPPLE: material-style ripple on .btn / .btn-outline clicks
  // ==========================================================
  document.querySelectorAll('.btn, .btn-outline').forEach(btn => {
    btn.addEventListener('click', function (e) {
      const rect = this.getBoundingClientRect();
      const ripple = document.createElement('span');
      ripple.className = 'ripple';
      const size = Math.max(rect.width, rect.height);
      ripple.style.width = ripple.style.height = size + 'px';
      ripple.style.left = (e.clientX - rect.left - size / 2) + 'px';
      ripple.style.top = (e.clientY - rect.top - size / 2) + 'px';
      this.appendChild(ripple);
      setTimeout(() => ripple.remove(), 650);
    });
  });

  // ==========================================================
  // TOASTIFY FLASH MESSAGES: server-rendered .alert blocks slide in
  // as floating toasts instead of sitting flat in the page
  // ==========================================================
  const flashAlerts = document.querySelectorAll('form ~ .alert, .card > .alert:first-of-type');
  document.querySelectorAll('.alert').forEach((alert, i) => {
    if (!alert.classList.contains('alert-static')) {
      alert.classList.add('toast-in');
      alert.style.animationDelay = (i * 0.08) + 's';
    }
  });
});

// ==========================================================
// REMINDER / NOTIFICATION BANNER
// Dismiss hides it until the next calendar day (per browser).
// ==========================================================
(function () {
  const banner = document.getElementById('reminder-banner');
  if (!banner) return;
  const today = new Date().toISOString().slice(0, 10);
  const dismissedOn = localStorage.getItem('nutrisense_banner_dismissed');
  if (dismissedOn === today) {
    banner.classList.add('hidden');
  }
})();

function dismissReminder() {
  const banner = document.getElementById('reminder-banner');
  if (!banner) return;
  banner.classList.add('hidden');
  const today = new Date().toISOString().slice(0, 10);
  localStorage.setItem('nutrisense_banner_dismissed', today);
}

// ==========================================================
// AI CHATBOT ASSISTANT WIDGET
// Talks to /api/chatbot, a rule-based assistant (see app.py) that
// answers using the site's own nutrient/deficiency data — no API
// key needed. Swap the backend for a real LLM call any time.
// ==========================================================
function toggleChatbot(forceOpen) {
  const panel = document.getElementById('chatbot-panel');
  if (!panel) return;
  const isOpen = panel.classList.contains('open');
  const shouldOpen = typeof forceOpen === 'boolean' ? forceOpen : !isOpen;
  panel.classList.toggle('open', shouldOpen);
  if (shouldOpen) document.getElementById('chatbot-input').focus();
}

// ==========================================================
// VOICE ASSISTANT — speak your question in Hindi/Marathi/English
// Uses the free browser Web Speech API (webkitSpeechRecognition).
// Speech-recognition language follows the sitewide language
// switcher (EN/मराठी/हिंदी) in Settings, so switching there also
// switches what the mic listens for.
// ==========================================================
(function () {
  const micBtn = document.getElementById('voice-input-btn');
  const input = document.getElementById('chatbot-input');
  const form = document.getElementById('chatbot-form');
  if (!micBtn || !input) return;

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    micBtn.title = 'Voice input is not supported in this browser';
    micBtn.style.opacity = '0.4';
    micBtn.addEventListener('click', () => {
      alert('Voice input needs a browser with speech recognition support (Chrome/Edge on desktop or Android work best).');
    });
    return;
  }

  const speechLangMap = { en: 'en-IN', mr: 'mr-IN', hi: 'hi-IN' };

  const recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;

  let listening = false;

  function currentSpeechLang() {
    let lang = 'en';
    try { lang = localStorage.getItem('nutrisense_lang') || 'en'; } catch (e) {}
    return speechLangMap[lang] || 'en-IN';
  }

  micBtn.addEventListener('click', () => {
    if (listening) { recognition.stop(); return; }
    recognition.lang = currentSpeechLang();
    try {
      recognition.start();
      listening = true;
      micBtn.classList.add('listening');
      micBtn.textContent = '🔴';
    } catch (e) {
      // start() throws if called twice in quick succession — ignore
    }
  });

  recognition.addEventListener('result', (e) => {
    const transcript = e.results[0][0].transcript;
    input.value = transcript;
    input.focus();
    // Auto-submit the recognized query, just like typing + Enter
    if (form) form.requestSubmit ? form.requestSubmit() : form.dispatchEvent(new Event('submit', { cancelable: true }));
  });

  recognition.addEventListener('end', () => {
    listening = false;
    micBtn.classList.remove('listening');
    micBtn.textContent = '🎤';
  });

  recognition.addEventListener('error', () => {
    listening = false;
    micBtn.classList.remove('listening');
    micBtn.textContent = '🎤';
  });
})();

document.addEventListener('DOMContentLoaded', () => {
  const toggleBtn = document.getElementById('chatbot-toggle');
  const form = document.getElementById('chatbot-form');
  const input = document.getElementById('chatbot-input');
  const messages = document.getElementById('chatbot-messages');
  if (!toggleBtn || !form) return;

  toggleBtn.addEventListener('click', () => {
    toggleChatbot();
  });

  function addMessage(text, who) {
    const div = document.createElement('div');
    div.className = 'chat-msg ' + (who === 'user' ? 'chat-user' : 'chat-bot');
    div.textContent = text;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    addMessage(text, 'user');
    input.value = '';
    try {
      const res = await fetch('/api/chatbot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      });
      const data = await res.json();
      addMessage(data.reply, 'bot');
    } catch (err) {
      addMessage("Sorry, I couldn't reach the assistant right now.", 'bot');
    }
  });
});

// ==========================================================
// BARCODE / PHOTO FOOD SCANNER (used on the Food Diary page)
// Uses the html5-qrcode camera library + the free Open Food Facts
// API to look up a scanned product's name automatically.
// ==========================================================
let _barcodeScanner = null;

function startBarcodeScanner() {
  const box = document.getElementById('barcode-reader');
  if (!box || typeof Html5Qrcode === 'undefined') {
    alert('Barcode scanner library failed to load — check your internet connection.');
    return;
  }
  box.style.display = 'block';
  _barcodeScanner = new Html5Qrcode('barcode-reader');
  _barcodeScanner.start(
    { facingMode: 'environment' },
    { fps: 10, qrbox: 220 },
    async (decodedText) => {
      stopBarcodeScanner();
      await lookupBarcodeProduct(decodedText);
    },
    () => {} // ignore per-frame scan failures
  ).catch(() => {
    alert('Could not access the camera. Please allow camera permission and try again.');
    box.style.display = 'none';
  });
}

function stopBarcodeScanner() {
  const box = document.getElementById('barcode-reader');
  if (_barcodeScanner) {
    _barcodeScanner.stop().catch(() => {});
    _barcodeScanner = null;
  }
  if (box) box.style.display = 'none';
}

async function lookupBarcodeProduct(barcode) {
  try {
    const res = await fetch(`https://world.openfoodfacts.org/api/v0/product/${barcode}.json`);
    const data = await res.json();
    if (data.status === 1 && data.product) {
      const p = data.product;
      document.getElementById('food_name').value = p.product_name || `Product ${barcode}`;
      document.getElementById('quantity').value = p.quantity || '';
      const cal = p.nutriments && (p.nutriments['energy-kcal_100g'] || p.nutriments['energy-kcal']);
      if (cal) document.getElementById('calories').value = Math.round(cal);
      document.getElementById('source').value = 'barcode';
    } else {
      alert('Product not found in the Open Food Facts database. You can enter it manually.');
    }
  } catch (err) {
    alert('Lookup failed — check your internet connection and try again.');
  }
}

function handlePhotoScan(fileInput) {
  // Photo-based recognition needs a vision model/API key, which isn't
  // configured here — so we take the photo, but ask the user to confirm
  // the name so nothing gets logged incorrectly. See README to wire up
  // a real image-recognition API later.
  const file = fileInput.files[0];
  if (!file) return;
  document.getElementById('source').value = 'photo';
  const name = prompt('Photo captured! What food is this? (auto food-recognition needs an API key — see README)');
  if (name) document.getElementById('food_name').value = name;
}
