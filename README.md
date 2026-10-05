# NutriVeda AI — v3 Upgrade Notes

## How to run
```
pip install -r requirements.txt
python app.py
```
Then open http://127.0.0.1:5000 in your browser. A `nutrisense.db` SQLite file
is created automatically on first run in the project folder — no separate
database setup needed.

## What's new in v5 — 6 new features + colorful redesign

### 1. Colorful theme
The whole site was re-themed from the earlier green/turmeric palette to a
vibrant violet → magenta → pink → coral scheme. All colors live in the
`:root` CSS variables at the top of `static/style.css` — change the hex
values there to retheme the whole site in one place.

### 2. Meal Diary / Food Log (`/food-log`, login required)
Log breakfast/lunch/dinner/snacks with quantity and calories. Entries are
stored per-user in a new `meal_log` table, and today's total calories are
shown at the top. Delete any entry with the 🗑️ button.

### 3. Reminder / Notification Banner
A colorful, dismissible banner rotates through helpful nutrition reminders
on every page (`REMINDER_MESSAGES` list near the top of `app.py` — add/edit
messages there). Dismissing hides it for the rest of the day via
localStorage (`static/script.js`).

### 4. Community Q&A / Comments (`/community`)
Anyone can browse questions; logged-in users can post a question or reply.
Stored in two new tables, `qa_questions` and `qa_answers`.

### 5. AI Chatbot Assistant (floating 🤖 button, every page)
A rule-based assistant (`chatbot_reply()` in `app.py`) answers questions
about nutrients, deficiencies, symptoms, BMI, and how to use the site — all
using your existing `nutrient_db` / `deficiency_db`, so it works fully
offline with **no API key**. If you want free-form AI conversation instead,
swap the body of `chatbot_reply()` for a call to an LLM API (OpenAI,
Anthropic, etc.) using the user's message as the prompt.

### 6. Barcode / Photo Food Scanner (on the Food Diary page)
- **Barcode scan**: uses the `html5-qrcode` camera library (loaded from a
  CDN, no install needed) to read a barcode, then looks up the product via
  the free [Open Food Facts](https://world.openfoodfacts.org/) API and
  auto-fills the food name, quantity, and calories.
- **Photo scan**: captures a photo and asks you to confirm the food name.
  Automatic food recognition *from* a photo needs a paid vision-AI API
  (e.g. Google Vision, OpenAI GPT-4 Vision) — wire that into
  `handlePhotoScan()` in `static/script.js` if you want it later.

### 7. Social Login — Google (`/login/google`)
Uses Authlib for OAuth 2.0. **This needs your own Google credentials to
work** — it won't function out of the box:
1. Go to https://console.cloud.google.com/apis/credentials
2. Create an OAuth 2.0 Client ID (type: Web application)
3. Add `http://127.0.0.1:5000/login/google/callback` as an authorized
   redirect URI (and your real domain's equivalent once deployed)
4. Set two environment variables before running the app:
   ```
   export GOOGLE_CLIENT_ID="your-client-id"
   export GOOGLE_CLIENT_SECRET="your-client-secret"
   ```
Until these are set, the "Continue with Google" button shows a friendly
message instead of erroring out — everything else works normally.

## What's new in v4 — Admin Panel + Feedback Storage + Interactive Polish

### 1. Feedback now saved to the database
- `/feedback` submissions (name, star rating, what they liked, message) are
  saved into a new `feedback` table — no longer thrown away after showing
  the "Thank You" message.

### 2. Admin Panel — see ALL user data in one place
- New `/admin` page (with its own login at `/admin/login`, separate from
  regular user accounts) shows:
  - Every registered user (name, email, joined date)
  - Every symptom check from every user (BMI, deficiencies detected, date)
  - Every feedback submission
- Default admin login: **username `sanika`, password `admin123`** — both
  set as constants near the top of `app.py` (`ADMIN_USERNAME`,
  `ADMIN_PASSWORD`). Change these before deploying/sharing publicly.
- A small "Admin" link is in the footer of every page.

### 3. Interactive/visual polish
- Buttons now have a material-style ripple animation on click.
- Flash messages (login errors, success banners, etc.) slide in as toasts.
- Pages softly fade/rise in on load instead of popping in instantly.
- All existing scroll-reveal, tilt-hover, parallax-blob, and count-up
  animations from v2 are unchanged and still active.

## What's new in v3 — User Login + History Tracking + Yoga Suggestions

### 1. User Login (Sign Up / Log In / Log Out)
- New `/signup` and `/login` pages, `/logout` route.
- Passwords are hashed with Werkzeug's `generate_password_hash` — never
  stored in plain text.
- Session-based login (`flask.session`) — once logged in, the nav bar shows
  your name with a dropdown (Dashboard / Symptom History / Log Out).
- `/form`, `/symptoms`, `/result`, `/dashboard`, `/history` now all require
  login (`@login_required` decorator) — visiting them while logged out
  redirects to `/login` and sends you back after logging in.

### 2. Automatic Per-User History Tracking (एक वेळ login केले की आपोआप history tracking)
- New SQLite database (`nutrisense.db`) with two tables: `users` and
  `assessments`.
- Every time a symptom check is submitted on `/result`, it's automatically
  saved against the logged-in user: date/time, height, weight, BMI,
  symptoms selected, deficiencies detected, and the deficiency count.
- New `/history` page: a line chart (Chart.js) of "deficiencies detected"
  over time — a downward trend visually shows symptom improvement — plus a
  full table of every past check.
- Dashboard now shows a "Your Progress" summary card with total checks
  completed and the last 5 results at a glance.

### 3. Yoga / Meditation Suggestions Linked to Results
- The Yoga page (`/yoga`) gained two new tabs: **Protein Deficiency** and
  **Vitamin B12 Deficiency** (previously only Calcium, Iron, Stress,
  Vitamin D), so every deficiency in the detector now has matching poses.
- Every tab now also shows a short daily-meditation tip alongside the poses.
- The Result page (`/result`) now shows a "Recommended Yoga & Meditation"
  button for each detected deficiency — clicking it opens `/yoga` with the
  right tab pre-selected (e.g. `/yoga?cond=iron`).

## What's new in v2

### 1. New feature: Vitamin & Mineral Encyclopedia (`/nutrients`)
- 15 nutrients covered: Vitamins A, B1, B3, B6, B12, C, D, E, K + Calcium, Iron,
  Zinc, Magnesium, Potassium, Iodine.
- Each entry has: RDA (recommended daily allowance), a plain-English explanation,
  deficiency warning signs, top Indian food sources, an absorption tip, an
  embedded YouTube video, and a link to an official source (NIH / WHO / ICMR).
- Live search box and Vitamins/Minerals filter chips.
- Click any card to open a detail panel (modal) with the full write-up.

### 2. New feature: Video & Official Resources page (`/resources`)
- Curated YouTube videos grouped by topic (Iron, Calcium, Vitamin D, B12,
  Protein, Yoga/Wellness).
- A grid of official/government health links: WHO, ICMR-NIN, NIH Office of
  Dietary Supplements, India's National Health Portal, FSSAI, and the Academy
  of Nutrition and Dietetics.
- Resource links/snippets were also added directly on the Step Tracker,
  Symptom Checker, Deficiency Guide, and Result pages so users hit relevant
  videos/sources without leaving their current task.

### 3. Visual redesign
- New "botanical/Ayurvedic" color identity layered on top of the original
  green palette: turmeric gold + clay terracotta accents, warm ivory
  backgrounds, and a serif display font (Fraunces) paired with Inter for body
  text.
- Rebuilt homepage hero with an animated "nutrient orbit" signature visual
  (vitamin icons orbiting a central DNA icon), animated gradient blobs,
  a botanical line-texture background, and a scroll cue.
- New homepage sections: feature grid, animated counting stat band, "how it
  works" steps, feature pill row, and a closing call-to-action band.

### 4. Animation system (new in `static/script.js` + `static/style.css`)
- Scroll-reveal: sections fade/slide into view as the user scrolls
  (IntersectionObserver-based, respects `prefers-reduced-motion`).
- Animated count-up numbers for stats.
- Subtle 3D tilt-on-hover for feature/deficiency cards.
- Parallax drift on background gradient blobs.
- All existing animations (progress bars, nav dropdown, card slide-ups) were
  preserved.

### 5. Data/content additions
- `app.py` now contains a `nutrient_db` list with the full vitamin/mineral
  encyclopedia data (RDA, sources, tips, videos, official links), served to
  `/nutrients` both as Jinja-rendered cards and as a JSON blob for the
  client-side search/filter/modal logic.
- Existing deficiency database, BMI calculator, weight plans, hair/skin care,
  yoga, workout, seasonal guide, protein calculator, immunity recipes, step
  tracker, and feedback form are all unchanged in logic — only visually
  refreshed with the new design tokens and animation classes.

## Notes
- All new YouTube embeds use the standard `https://www.youtube.com/embed/...`
  format already used elsewhere in the app — swap any video ID if you want to
  point to different videos.
- Official links (WHO, ICMR-NIN, NIH, NHP, FSSAI) are real, currently active
  government/institutional URLs.
- No external API keys are required — everything runs from the bundled Flask
  app and static data.

## What's new in v6 — Advanced Indian Food Intelligence

### 1. Indian Regional Food Intelligence (`/regional-food`)
- Select a state/region and browse traditional foods, meal use, nutrient highlights and recipe-learning links.
- Covers Indian states/regions in the bundled dataset.
- Search within the selected region.
- YouTube learning links are included for recipe exploration.

### 2. What's in My Kitchen? (`/kitchen`)
- Select ingredients from a searchable ingredient list.
- Matching Indian recipes are generated from the bundled recipe intelligence.
- Each match includes ingredient use, nutrient facts and a YouTube recipe-learning link.
- This feature is designed to reduce food waste and make healthy cooking practical.

### 3. One Food — Many Solutions (`/one-food`)
- A searchable food encyclopedia with individual profiles.
- Each profile contains introduction, uses, recipes, nutrient profile, wellness roles, quick facts, YouTube learning and an official nutrition reference.
- The copy intentionally avoids claiming that a single food cures disease; food is presented as part of a balanced diet.

### 4. Smart Indian Meal Planner (`/smart-meal-planner`)
- Goal selection: balanced, weight loss, healthy weight gain and higher protein.
- Diet preference selector and state selector.
- Generates a practical breakfast/lunch/snack/dinner framework and shows regional food swaps.
- Links back to Food Diary/Dashboard for tracking.

### 5. Expanded nutrition intelligence
- Added additional vitamin/mineral coverage and expanded the deficiency food/symptom database.
- Added more Indian food examples and absorption/lifestyle guidance.

### 6. Home page intelligence overview
- Homepage now gives a visual overview of nutrition, food intelligence, yoga, Ayurveda-inspired wellness, tracking and advanced planning.
- New modules are accessible from the homepage and sidebar.

### 7. Marathi language mode
- Settings → Language → मराठी now applies Marathi translations to the navigation, settings, new advanced pages and visible interface phrases.
- Dynamic text generated by the new food-intelligence pages is also translated through the deep Marathi layer.
- English source text is cached in the browser so switching back to English restores the original interface.

### 8. Distinct theme appearances
- Existing themes now receive different background treatments, geometry, card shapes and visual effects in addition to palette changes.
- Nature/Ayurvedic, Ocean/Wellness, Modern/Futuristic, Premium/Luxury, Dark Premium, Fresh Mint and other themes each have a distinct visual treatment.

## Safety / academic presentation note
NutriVeda AI is an educational wellness and nutrition platform. It should not diagnose disease or claim that foods, yoga or Ayurveda cure medical conditions. For pregnancy, allergies, chronic disease, supplements, severe symptoms or therapeutic diets, users should consult a qualified healthcare professional.

## What's new in v7
- Top navigation bar (full menu drawer, settings and All-features menu) replaces the always-open sidebar.
- New fonts: Bricolage Grotesque + Mukta (supports Devanagari for Marathi/Hindi).
- AI Guide (top right): your welcome video plus per-feature steps; "Play & read aloud" speaks them. Edit the `GUIDE` table in `static/enhance.js`; replace `static/videos/ai_guide.mp4` to change the video.
- Banner with icon and photo on every feature page.
- Yoga: 10 need tabs, level filter, search, step-by-step poses with cautions, timers, breathing pacer, daily streak, food pairing.
- Symptoms: search, body-area filters, severity and duration, live nutrient match, safety flag.

## What's new in v8
- Navigation is a hidden right-side drawer: tap the round menu button (top right) or press M. It has search, recently visited pages, colour-coded feature tiles, language buttons and style cards.
- 6 website styles, each with its own shape, fonts, borders, shadows and background: Aurora (default), Ayurveda, Neo Pop, Zen, Midnight, Bazaar. Defined in `static/theme.css`.
- New login and sign-up pages (video panel, floating foods, icon fields).
- Food photos (50 foods strip and a scrolling band on the home page) and a photo banner on every feature page. Photos load from loremflickr.com by keyword, so they need internet and are generic photos of that food; emoji show if offline.
- Marathi / Hindi: `static/i18n_rows.js` is a hand-written dictionary (menus, 50 foods, nutrients, deficiencies, symptoms, yoga and login labels). Everything else is translated by the Google Translate widget, which needs internet and is machine translation. Add rows as `English|मराठी|हिंदी`.
- Yoga: embedded YouTube video for Calcium and Energy, and a "Watch on YouTube" search button for every yoga type and every pose. Add more by putting a video ID in the `VID` map in `templates/yoga.html`.
- Chatbot voice typing: live dictation into the box (not auto-sent), EN / मराठी / हिंदी mic language, optional read-aloud of replies. Works in Chrome and Edge.
