from flask import Flask, render_template, request, redirect, url_for, session, flash, g, jsonify, Response
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
import json
import os
import re
import random
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")

# =======================
# GOOGLE SOCIAL LOGIN (OAuth 2.0 via Authlib)
# Set these two environment variables to turn Google Sign-In on. Until they
# are set, the "Continue with Google" button shows a friendly message
# instead of crashing the app. Get credentials from:
# https://console.cloud.google.com/apis/credentials
# =======================
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_LOGIN_ENABLED = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)

oauth = None
if GOOGLE_LOGIN_ENABLED:
    from authlib.integrations.flask_client import OAuth
    oauth = OAuth(app)
    oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

# =======================
# SITE-WIDE REMINDER BANNER
# Rotated messages shown as a dismissible banner on every page (see
# base.html + script.js). Dismissing hides it for the rest of the day
# via localStorage — no server storage needed.
# =======================
REMINDER_MESSAGES = [
    {"icon": "💧", "text": "Reminder: have you had enough water today? Aim for 8 glasses."},
    {"icon": "🥗", "text": "Don't forget to log today's meals in your Food Diary!"},
    {"icon": "☀️", "text": "10–15 minutes of morning sunlight helps your body make Vitamin D."},
    {"icon": "🚶", "text": "A short walk after meals aids digestion — check the Step Tracker."},
    {"icon": "🧘", "text": "Feeling low on energy? Try a 5-minute breathing break from the Yoga page."},
]

@app.context_processor
def inject_globals():
    return {
        "reminder": random.choice(REMINDER_MESSAGES),
        "google_login_enabled": GOOGLE_LOGIN_ENABLED,
    }

# Simple fixed admin login so YOU (the site owner) can see all user data,
# assessment history, and feedback from one place at /admin.
# Change these before sharing the project publicly.
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "sanika")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nutriveda.db")

# =======================
# DATABASE HELPERS
# =======================
def get_db():
    """Open (or reuse) a per-request SQLite connection."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    """Create tables on first run (safe to call every startup)."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            height REAL,
            weight REAL,
            bmi REAL,
            symptoms TEXT,
            detected TEXT,
            deficiency_count INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT NOT NULL,
            rating INTEGER,
            liked TEXT,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    # Meal Diary / Food Log
    conn.execute("""
        CREATE TABLE IF NOT EXISTS meal_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            meal_type TEXT NOT NULL,
            food_name TEXT NOT NULL,
            quantity TEXT,
            calories INTEGER,
            source TEXT DEFAULT 'manual',
            logged_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    # Community Q&A
    conn.execute("""
        CREATE TABLE IF NOT EXISTS qa_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS qa_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER NOT NULL,
            user_id INTEGER,
            name TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (question_id) REFERENCES qa_questions (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    # Optional: users who signed up / logged in via Google
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_oauth (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            provider TEXT NOT NULL,
            provider_uid TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    # Family Thali Comparison — household members + their daily thali log
    conn.execute("""
        CREATE TABLE IF NOT EXISTS family_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            age INTEGER,
            role TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS thali_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            entry_date TEXT NOT NULL,
            items TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (member_id) REFERENCES family_members (id)
        )
    """)
    # Menstrual Cycle Tracker — each row is one logged period start;
    # cycle phase + nutrition tips are computed on the fly from these.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cycle_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            period_start TEXT NOT NULL,
            cycle_length INTEGER NOT NULL DEFAULT 28,
            period_length INTEGER NOT NULL DEFAULT 5,
            symptoms TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    # Allergy Tracker — foods/ingredients a user reacts to. Checked
    # against Food Diary entries to raise an in-app warning.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS allergies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            allergen TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'Moderate',
            notes TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    conn.commit()
    conn.close()

# =======================
# LOGIN REQUIRED DECORATOR
# =======================
def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "info")
            return redirect(url_for("login", next=request.path))
        return view_func(*args, **kwargs)
    return wrapped

def admin_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        return view_func(*args, **kwargs)
    return wrapped

# Maps deficiency names -> yoga.html tab keys, for auto-suggesting the
# right yoga/meditation tab straight from the result page.
YOGA_SUGGESTION_MAP = {
    "Iron Deficiency": "iron",
    "Calcium Deficiency": "calcium",
    "Vitamin D Deficiency": "vitamind",
    "Protein Deficiency": "protein",
    "Vitamin B12 Deficiency": "b12",
}

# =======================
# DEFICIENCY DATABASE
# =======================
deficiency_db = {
    "Iron Deficiency": {
        "symptoms": ["fatigue", "hairfall", "pale skin", "weak immunity"],
        "foods": ["Spinach", "Jaggery", "Dates", "Beetroot", "Ragi", "Rajma",
                  "Chana", "Pomegranate", "Apple", "Anjeer", "Fenugreek",
                  "Amaranth", "Black Sesame", "Peas", "Soybean", "Tofu",
                  "Groundnut", "Red Rice", "Drumstick", "Broccoli"],
        "lifestyle": "Pair iron foods with vitamin C (lemon, amla) for better absorption. Avoid tea/coffee 1 hour after meals."
    },
    "Calcium Deficiency": {
        "symptoms": ["bone pain", "muscle cramps", "weak bones"],
        "foods": ["Milk", "Curd", "Paneer", "Ragi", "Sesame Seeds", "Almonds",
                  "Walnuts", "Soy Milk", "Tofu", "Broccoli", "Okra", "Figs",
                  "Chia Seeds", "Moringa", "Cheese", "Yogurt", "Cabbage"],
        "lifestyle": "15–20 min of morning sun exposure for vitamin D helps calcium absorption. Daily walking strengthens bones."
    },
    "Vitamin D Deficiency": {
        "symptoms": ["back pain", "low immunity", "fatigue"],
        "foods": ["Mushroom (sun-dried)", "Fortified Milk", "Egg Yolk", "Fortified Cereals"],
        "lifestyle": "Get 15–20 minutes of direct morning sunlight daily on arms and face. This is the primary natural source."
    },
    "Protein Deficiency": {
        "symptoms": ["muscle loss", "weakness", "slow recovery"],
        "foods": ["Dal", "Chana", "Eggs", "Milk", "Paneer", "Soybean", "Tofu", "Peanuts",
                  "Rajma", "Moong", "Masoor", "Chickpeas", "Greek Yogurt"],
        "lifestyle": "Include a protein source in every meal. Spread intake across the day rather than in one large meal."
    },
    "Vitamin B12 Deficiency": {
        "symptoms": ["memory loss", "fatigue", "tingling hands"],
        "foods": ["Milk", "Curd", "Eggs", "Cheese", "Fortified Cereals", "Nutritional Yeast"],
        "lifestyle": "Vegetarians are at higher risk. Get blood levels checked annually. Supplement if needed with doctor guidance."
    }
}


# Expanded deficiency intelligence: additional common nutrition gaps and
# culturally familiar Indian food sources.
deficiency_db.update({
    "Vitamin C Deficiency": {
        "symptoms":["bleeding gums","slow wound healing","frequent infections","fatigue"],
        "foods":["Amla","Guava","Lemon","Orange","Capsicum","Tomato","Papaya","Cabbage"],
        "lifestyle":"Add a vitamin-C-rich fruit or vegetable to at least one or two meals each day."
    },
    "Folate Deficiency": {
        "symptoms":["fatigue","pale skin","mouth sores","weakness"],
        "foods":["Spinach","Methi","Lentils","Chana","Rajma","Peanuts","Beetroot","Citrus fruits"],
        "lifestyle":"Rotate leafy greens and pulses through the week; pregnancy requires clinician-guided folate planning."
    },
    "Zinc Deficiency": {
        "symptoms":["slow wound healing","frequent infections","poor appetite","taste changes"],
        "foods":["Chana","Pumpkin Seeds","Sesame","Dairy","Eggs","Whole Grains","Peanuts"],
        "lifestyle":"Soaking/sprouting pulses can improve mineral bioavailability; avoid high-dose supplements without advice."
    },
    "Magnesium Deficiency": {
        "symptoms":["muscle cramps","weakness","low appetite","fatigue"],
        "foods":["Ragi","Peanuts","Sesame","Spinach","Dal","Whole Grains","Pumpkin Seeds"],
        "lifestyle":"Build meals around whole grains, pulses, leafy vegetables, nuts and seeds."
    },
    "Iodine Deficiency": {
        "symptoms":["thyroid enlargement","fatigue","cold intolerance","poor concentration"],
        "foods":["Iodized Salt","Dairy","Eggs","Fish","Seafood"],
        "lifestyle":"Use adequately iodized salt in normal cooking; people with thyroid conditions should follow clinician guidance."
    }
})

# =======================
# VITAMIN & MINERAL ENCYCLOPEDIA
# Comprehensive reference: RDA, deficiency signs, Indian food
# sources, absorption tips, and curated learning resources.
# =======================
nutrient_db = [
    {
        "key": "vitamin-a", "name": "Vitamin A", "category": "vitamin",
        "also_known": "Retinol / Beta-Carotene",
        "icon": "👁️", "icon_bg": "background:linear-gradient(135deg,#f59e0b,#b45309);",
        "rda": "700–900 mcg/day (adults)",
        "short": "Supports vision, immune function, and skin health.",
        "long": "Vitamin A is essential for low-light and colour vision, maintains the skin and mucous membrane barrier against infection, and supports immune cell function. It exists as retinol (animal foods) and beta-carotene (plant foods), which the body converts as needed.",
        "deficiency_signs": ["Night blindness", "Dry eyes", "Frequent infections", "Dry, rough skin", "Slow wound healing"],
        "foods": ["Carrot", "Sweet Potato", "Spinach", "Mango", "Papaya", "Pumpkin", "Egg Yolk", "Milk", "Red Bell Pepper", "Amaranth Leaves"],
        "tip": "Beta-carotene absorbs best with a little fat — cook carrots or spinach with a teaspoon of ghee or oil.",
        "video": "https://www.youtube.com/embed/X2tDtpkbWE4",
        "official_name": "NIH — Vitamin A Fact Sheet",
        "official_url": "https://ods.od.nih.gov/factsheets/VitaminA-Consumer/",
        "official_desc": "Office of Dietary Supplements consumer fact sheet on Vitamin A."
    },
    {
        "key": "vitamin-b1", "name": "Vitamin B1 (Thiamine)", "category": "vitamin",
        "also_known": "Thiamine",
        "icon": "⚡", "icon_bg": "background:linear-gradient(135deg,#c8862a,#9c6418);",
        "rda": "1.1–1.2 mg/day",
        "short": "Helps convert food into cellular energy and supports nerve function.",
        "long": "Thiamine is a coenzyme in carbohydrate metabolism, helping turn the food you eat into usable energy. It's also needed for healthy nerve signalling, which is why severe deficiency (beriberi) causes nerve and heart problems.",
        "deficiency_signs": ["Fatigue", "Irritability", "Tingling in hands/feet", "Loss of appetite", "Confusion (severe cases)"],
        "foods": ["Whole Wheat", "Brown Rice", "Lentils (Dal)", "Peanuts", "Sunflower Seeds", "Green Peas", "Oats"],
        "tip": "Thiamine is lost in excess washing/boiling of rice and dal — use minimal water and don't over-rinse.",
        "video": "https://www.youtube.com/embed/8O7xVZK33-8",
        "official_name": "NIH — Thiamine Fact Sheet",
        "official_url": "https://ods.od.nih.gov/factsheets/Thiamin-Consumer/",
        "official_desc": "Office of Dietary Supplements fact sheet on Vitamin B1."
    },
    {
        "key": "vitamin-b3", "name": "Vitamin B3 (Niacin)", "category": "vitamin",
        "also_known": "Niacin",
        "icon": "🔥", "icon_bg": "background:linear-gradient(135deg,#c8862a,#9c6418);",
        "rda": "14–16 mg/day",
        "short": "Supports energy metabolism, skin health, and nervous system function.",
        "long": "Niacin helps enzymes convert carbohydrates, fats, and proteins into energy. It also supports DNA repair and healthy skin. Severe long-term deficiency causes pellagra (dermatitis, diarrhoea, dementia).",
        "deficiency_signs": ["Skin rashes/pigmentation", "Digestive upset", "Fatigue", "Mouth soreness", "Memory issues (severe)"],
        "foods": ["Peanuts", "Brown Rice", "Whole Wheat", "Mushrooms", "Green Peas", "Sesame Seeds", "Dates"],
        "tip": "Niacin from plant foods is well absorbed; pairing with B-complex-rich whole grains supports overall metabolism.",
        "video": "https://www.youtube.com/embed/8O7xVZK33-8",
        "official_name": "NIH — Niacin Fact Sheet",
        "official_url": "https://ods.od.nih.gov/factsheets/Niacin-Consumer/",
        "official_desc": "Office of Dietary Supplements fact sheet on Vitamin B3."
    },
    {
        "key": "vitamin-b6", "name": "Vitamin B6", "category": "vitamin",
        "also_known": "Pyridoxine",
        "icon": "🧠", "icon_bg": "background:linear-gradient(135deg,#c8862a,#9c6418);",
        "rda": "1.3–1.7 mg/day",
        "short": "Involved in brain development, mood regulation, and protein metabolism.",
        "long": "Vitamin B6 helps the body break down protein and is involved in producing neurotransmitters like serotonin and dopamine, which affect mood and sleep. It also supports red blood cell formation.",
        "deficiency_signs": ["Irritability/low mood", "Confusion", "Weakened immunity", "Cracked lips (cheilosis)", "Anemia"],
        "foods": ["Chickpeas (Chana)", "Banana", "Potato", "Brown Rice", "Spinach", "Watermelon", "Sunflower Seeds"],
        "tip": "B6 is water-soluble and heat-sensitive — lightly steam vegetables rather than over-boiling.",
        "video": "https://www.youtube.com/embed/AcvB-tUWXNs",
        "official_name": "NIH — Vitamin B6 Fact Sheet",
        "official_url": "https://ods.od.nih.gov/factsheets/VitaminB6-Consumer/",
        "official_desc": "Office of Dietary Supplements fact sheet on Vitamin B6."
    },
    {
        "key": "vitamin-b12", "name": "Vitamin B12", "category": "vitamin",
        "also_known": "Cobalamin",
        "icon": "🩸", "icon_bg": "background:linear-gradient(135deg,#c8862a,#9c6418);",
        "rda": "2.4 mcg/day",
        "short": "Essential for nerve function, red blood cell formation, and DNA synthesis.",
        "long": "Vitamin B12 is required to make healthy red blood cells and maintain the protective covering of nerves. It's found almost exclusively in animal products, which makes vegetarians and vegans a high-risk group for deficiency.",
        "deficiency_signs": ["Memory loss", "Fatigue", "Tingling in hands/feet", "Pale or jaundiced skin", "Mood changes"],
        "foods": ["Milk", "Curd", "Paneer", "Eggs", "Cheese", "Fortified Cereals", "Nutritional Yeast"],
        "tip": "Vegetarians should get B12 blood levels checked annually — diet alone often isn't enough without dairy/eggs or fortified foods.",
        "video": "https://www.youtube.com/embed/AcvB-tUWXNs",
        "official_name": "NIH — Vitamin B12 Fact Sheet",
        "official_url": "https://ods.od.nih.gov/factsheets/VitaminB12-Consumer/",
        "official_desc": "Office of Dietary Supplements fact sheet on Vitamin B12."
    },
    {
        "key": "vitamin-c", "name": "Vitamin C", "category": "vitamin",
        "also_known": "Ascorbic Acid",
        "icon": "🍊", "icon_bg": "background:linear-gradient(135deg,#f59e0b,#b45309);",
        "rda": "65–90 mg/day",
        "short": "Boosts immunity, aids iron absorption, and supports collagen production.",
        "long": "Vitamin C is a powerful antioxidant that supports immune defence, helps the body absorb non-heme (plant-based) iron more efficiently, and is required to build collagen for skin, blood vessels, and wound healing.",
        "deficiency_signs": ["Bleeding gums", "Slow wound healing", "Frequent colds", "Dry, rough skin", "Joint pain (severe)"],
        "foods": ["Amla (Indian Gooseberry)", "Orange", "Lemon", "Guava", "Bell Pepper", "Tomato", "Papaya", "Kiwi"],
        "tip": "Vitamin C is destroyed by heat — eat citrus fruits and amla raw or only lightly cooked.",
        "video": "https://www.youtube.com/embed/CqL2RxXJiqI",
        "official_name": "NIH — Vitamin C Fact Sheet",
        "official_url": "https://ods.od.nih.gov/factsheets/VitaminC-Consumer/",
        "official_desc": "Office of Dietary Supplements fact sheet on Vitamin C."
    },
    {
        "key": "vitamin-d", "name": "Vitamin D", "category": "vitamin",
        "also_known": "Calciferol / The Sunshine Vitamin",
        "icon": "☀️", "icon_bg": "background:linear-gradient(135deg,#f59e0b,#b45309);",
        "rda": "15–20 mcg (600–800 IU)/day",
        "short": "Vital for calcium absorption, bone strength, and immune regulation.",
        "long": "Vitamin D enables the gut to absorb calcium and phosphorus, making it essential for bone strength. It's mostly made in the skin via sunlight exposure rather than obtained from food, which is why deficiency is extremely common, even in sunny countries, due to indoor lifestyles.",
        "deficiency_signs": ["Bone/back pain", "Frequent illness", "Fatigue", "Muscle weakness", "Mood changes"],
        "foods": ["Mushroom (sun-dried)", "Fortified Milk", "Egg Yolk", "Fortified Cereals"],
        "tip": "15–20 minutes of midday sun on arms and face, a few times a week, is the primary natural source — food alone rarely covers it.",
        "video": "https://www.youtube.com/embed/9Wd1eVHkjpE",
        "official_name": "NIH — Vitamin D Fact Sheet",
        "official_url": "https://ods.od.nih.gov/factsheets/VitaminD-Consumer/",
        "official_desc": "Office of Dietary Supplements fact sheet on Vitamin D."
    },
    {
        "key": "vitamin-e", "name": "Vitamin E", "category": "vitamin",
        "also_known": "Tocopherol",
        "icon": "🌻", "icon_bg": "background:linear-gradient(135deg,#f59e0b,#b45309);",
        "rda": "15 mg/day",
        "short": "Antioxidant that protects cells and supports skin and eye health.",
        "long": "Vitamin E protects cell membranes from oxidative damage, supports immune function, and contributes to skin elasticity and eye health. It's fat-soluble, so it's best absorbed alongside dietary fat.",
        "deficiency_signs": ["Muscle weakness", "Vision problems", "Dry/rough skin", "Weakened immunity"],
        "foods": ["Almonds", "Sunflower Seeds", "Peanuts", "Spinach", "Avocado", "Wheat Germ", "Mustard Oil"],
        "tip": "Lightly roasted nuts and seeds preserve more vitamin E than deep-fried versions.",
        "video": "https://www.youtube.com/embed/X2tDtpkbWE4",
        "official_name": "NIH — Vitamin E Fact Sheet",
        "official_url": "https://ods.od.nih.gov/factsheets/VitaminE-Consumer/",
        "official_desc": "Office of Dietary Supplements fact sheet on Vitamin E."
    },
    {
        "key": "vitamin-k", "name": "Vitamin K", "category": "vitamin",
        "also_known": "Phylloquinone",
        "icon": "🩹", "icon_bg": "background:linear-gradient(135deg,#f59e0b,#b45309);",
        "rda": "90–120 mcg/day",
        "short": "Essential for normal blood clotting and bone metabolism.",
        "long": "Vitamin K activates proteins needed for blood clotting, preventing excess bleeding from cuts and injuries. It also plays a supporting role in bone mineralisation alongside calcium and vitamin D.",
        "deficiency_signs": ["Easy bruising", "Excess bleeding from cuts", "Bleeding gums", "Heavy menstrual bleeding"],
        "foods": ["Spinach", "Broccoli", "Cabbage", "Mustard Greens", "Fenugreek Leaves", "Cauliflower"],
        "tip": "Vitamin K is fat-soluble — a drizzle of oil or ghee with leafy greens improves absorption.",
        "video": "https://www.youtube.com/embed/X2tDtpkbWE4",
        "official_name": "NIH — Vitamin K Fact Sheet",
        "official_url": "https://ods.od.nih.gov/factsheets/VitaminK-Consumer/",
        "official_desc": "Office of Dietary Supplements fact sheet on Vitamin K."
    },
    {
        "key": "calcium", "name": "Calcium", "category": "mineral",
        "also_known": "Ca",
        "icon": "🦴", "icon_bg": "background:linear-gradient(135deg,#40916c,#1b4332);",
        "rda": "1000–1200 mg/day",
        "short": "Builds and maintains strong bones and teeth; supports muscle and nerve function.",
        "long": "Calcium is the most abundant mineral in the body, stored mainly in bones and teeth. Beyond skeletal strength, it's needed for muscle contraction (including the heartbeat) and nerve signal transmission. The body draws calcium from bones if dietary intake is too low, weakening them over time.",
        "deficiency_signs": ["Bone pain", "Muscle cramps", "Weak/brittle bones", "Brittle nails", "Numbness/tingling"],
        "foods": ["Milk", "Curd", "Paneer", "Ragi", "Sesame Seeds", "Almonds", "Tofu", "Broccoli", "Figs", "Moringa"],
        "tip": "Pair calcium-rich foods with 15–20 minutes of morning sunlight — vitamin D is required for the gut to actually absorb calcium.",
        "video": "https://www.youtube.com/embed/3o7valt2A1k",
        "official_name": "ICMR-NIN — Dietary Guidelines for Indians",
        "official_url": "https://www.nin.res.in/",
        "official_desc": "Official RDA tables and dietary guidance from India's National Institute of Nutrition."
    },
    {
        "key": "iron", "name": "Iron", "category": "mineral",
        "also_known": "Fe",
        "icon": "🩸", "icon_bg": "background:linear-gradient(135deg,#40916c,#1b4332);",
        "rda": "8–18 mg/day (higher for menstruating women)",
        "short": "Carries oxygen in the blood; deficiency is one of the most common globally.",
        "long": "Iron is a core component of haemoglobin, the protein in red blood cells that carries oxygen from your lungs to the rest of the body. Without enough iron, the body can't make enough healthy red blood cells, leading to iron-deficiency anaemia — the most common nutritional deficiency worldwide.",
        "deficiency_signs": ["Fatigue", "Hair fall", "Pale skin", "Weak immunity", "Shortness of breath", "Dizziness"],
        "foods": ["Spinach", "Jaggery", "Dates", "Beetroot", "Ragi", "Rajma", "Chana", "Pomegranate", "Fenugreek", "Sesame Seeds"],
        "tip": "Pair iron-rich foods with vitamin C (lemon, amla, tomato) to boost absorption, and avoid tea/coffee within an hour of meals — tannins block iron uptake.",
        "video": "https://www.youtube.com/embed/CDjPNTjJzv8",
        "official_name": "WHO — Iron Deficiency Anaemia",
        "official_url": "https://www.who.int/news-room/fact-sheets/detail/anaemia",
        "official_desc": "World Health Organization fact sheet on anaemia and iron deficiency."
    },
    {
        "key": "zinc", "name": "Zinc", "category": "mineral",
        "also_known": "Zn",
        "icon": "🛡️", "icon_bg": "background:linear-gradient(135deg,#40916c,#1b4332);",
        "rda": "8–11 mg/day",
        "short": "Supports immune function, wound healing, and taste/smell perception.",
        "long": "Zinc is involved in hundreds of enzyme reactions, supports immune cell production, helps wounds heal, and is needed for normal taste and smell. It also plays a role in growth and development, particularly important in children.",
        "deficiency_signs": ["Frequent infections", "Slow wound healing", "Loss of taste/smell", "Hair thinning", "Poor appetite"],
        "foods": ["Pumpkin Seeds", "Chickpeas", "Cashews", "Yogurt", "Whole Grains", "Sesame Seeds", "Peanuts"],
        "tip": "Soaking or sprouting legumes and grains before cooking reduces phytates, which otherwise block zinc absorption.",
        "video": "https://www.youtube.com/embed/CqL2RxXJiqI",
        "official_name": "NIH — Zinc Fact Sheet",
        "official_url": "https://ods.od.nih.gov/factsheets/Zinc-Consumer/",
        "official_desc": "Office of Dietary Supplements fact sheet on Zinc."
    },
    {
        "key": "magnesium", "name": "Magnesium", "category": "mineral",
        "also_known": "Mg",
        "icon": "💪", "icon_bg": "background:linear-gradient(135deg,#40916c,#1b4332);",
        "rda": "310–420 mg/day",
        "short": "Supports muscle/nerve function, energy production, and bone health.",
        "long": "Magnesium is involved in over 300 enzymatic reactions, including energy production, muscle relaxation, and nerve signalling. It also works alongside calcium and vitamin D for bone health, and low levels are linked to cramps, fatigue, and poor sleep.",
        "deficiency_signs": ["Muscle cramps/twitches", "Fatigue", "Poor sleep", "Irregular heartbeat (severe)", "Irritability"],
        "foods": ["Spinach", "Almonds", "Cashews", "Whole Grains", "Bananas", "Dark Chocolate", "Black Beans"],
        "tip": "Cooking leafy greens lightly (steaming, not boiling away the water) preserves more magnesium than deep boiling.",
        "video": "https://www.youtube.com/embed/8O7xVZK33-8",
        "official_name": "NIH — Magnesium Fact Sheet",
        "official_url": "https://ods.od.nih.gov/factsheets/Magnesium-Consumer/",
        "official_desc": "Office of Dietary Supplements fact sheet on Magnesium."
    },
    {
        "key": "potassium", "name": "Potassium", "category": "mineral",
        "also_known": "K",
        "icon": "❤️", "icon_bg": "background:linear-gradient(135deg,#40916c,#1b4332);",
        "rda": "2600–3400 mg/day",
        "short": "Regulates fluid balance, nerve signals, and healthy blood pressure.",
        "long": "Potassium helps balance fluids inside and outside cells, supports normal nerve and muscle function (including the heart), and helps counteract sodium's effect on blood pressure. It's lost through sweat, so needs rise with heat and activity.",
        "deficiency_signs": ["Muscle weakness", "Cramps", "Fatigue", "Irregular heartbeat (severe)", "Constipation"],
        "foods": ["Banana", "Coconut Water", "Potato", "Spinach", "Sweet Potato", "Curd", "Beans", "Orange"],
        "tip": "Coconut water and buttermilk (chaas) are quick, natural ways to replenish potassium lost through sweating in hot weather.",
        "video": "https://www.youtube.com/embed/Hu1plUSXcKY",
        "official_name": "NIH — Potassium Fact Sheet",
        "official_url": "https://ods.od.nih.gov/factsheets/Potassium-Consumer/",
        "official_desc": "Office of Dietary Supplements fact sheet on Potassium."
    },
    {
        "key": "iodine", "name": "Iodine", "category": "mineral",
        "also_known": "I",
        "icon": "🦋", "icon_bg": "background:linear-gradient(135deg,#40916c,#1b4332);",
        "rda": "150 mcg/day",
        "short": "Required to make thyroid hormones, which regulate metabolism.",
        "long": "Iodine is essential for the thyroid gland to produce hormones that regulate metabolism, growth, and brain development. It's especially critical during pregnancy for fetal brain development. Iodised salt programs have made severe deficiency rare, but mild deficiency still occurs.",
        "deficiency_signs": ["Goitre (neck swelling)", "Fatigue", "Weight gain", "Cold sensitivity", "Developmental issues in children"],
        "foods": ["Iodised Salt", "Milk", "Curd", "Eggs", "Seaweed (where available)", "Fish"],
        "tip": "Use iodised salt for cooking and add it after cooking rather than during prolonged boiling, since iodine can be lost to heat over time.",
        "video": "https://www.youtube.com/embed/9Wd1eVHkjpE",
        "official_name": "WHO — Iodine Deficiency",
        "official_url": "https://www.who.int/news-room/fact-sheets/detail/micronutrients",
        "official_desc": "World Health Organization fact sheet on micronutrient deficiencies including iodine."
    },
]

nutrient_db_by_key = {n["key"]: n for n in nutrient_db}

# =======================
# GRANDMA'S REMEDY BOT
# A rule-based assistant for traditional Indian/Ayurvedic home remedies.
# Every reply pairs the remedy with a plain-language, science-aware note —
# this is folk knowledge, not medical advice, and the bot always says so.
# =======================
GRANDMA_REMEDY_DB = [
    {
        "keywords": ["cold", "sardi", "nak vahane", "runny nose", "blocked nose", "congestion"],
        "title": "Common Cold",
        "remedy": "Grandma's kadha: boil 1 cup water with a small piece of ginger, 4–5 tulsi "
                   "leaves, a pinch of turmeric and a crushed black pepper. Simmer 5 minutes, "
                   "strain, add honey once warm (not hot) and sip slowly. Steam inhalation with "
                   "ajwain (carom seeds) in hot water also helps clear a blocked nose.",
        "caveat": "Ginger, tulsi and turmeric have mild anti-inflammatory and soothing properties "
                   "backed by some evidence, and warm fluids genuinely help with congestion — but "
                   "they don't shorten a cold or kill the virus. See a doctor if fever crosses 3 "
                   "days, or breathing feels difficult."
    },
    {
        "keywords": ["cough", "khokla", "khokala", "gala", "throat irritation", "dry cough"],
        "title": "Cough",
        "remedy": "Mix 1 tsp honey with a few drops of ginger juice and take 2–3 times a day. "
                   "A classic combo is warm milk with a pinch of turmeric (haldi doodh) before bed. "
                   "For a wet cough, some families use mulethi (licorice root) chewed slowly.",
        "caveat": "Honey has reasonable evidence for easing cough, especially at night — but never "
                   "give honey to children under 1 year (infant botulism risk). Turmeric milk is "
                   "soothing more than medicinal in proven effect. See a doctor if cough lasts over "
                   "2 weeks or brings up blood or thick colored phlegm."
    },
    {
        "keywords": ["upset stomach", "pot bigadle", "pot bigadala", "indigestion", "apachan",
                     "loose motion", "diarrhea", "julab"],
        "title": "Upset Stomach / Indigestion",
        "remedy": "Keep it light: khichdi (rice-moong dal) with a little ghee is easy to digest. "
                   "Jeera (cumin) water — boil 1 tsp cumin seeds in water, strain, sip warm — "
                   "settles the stomach. For loose motions, saunf (fennel) water and plain curd "
                   "rice help, along with plenty of fluids (ORS is best for rehydration).",
        "caveat": "Bland, low-fibre foods like khichdi genuinely rest the gut, and cumin/fennel "
                   "have carminative (gas-relieving) properties with some supporting evidence. "
                   "For diarrhea, hydration (ORS) matters more than any single remedy. See a "
                   "doctor if it lasts beyond 2 days, or there's blood, high fever, or signs of "
                   "dehydration."
    },
    {
        "keywords": ["acidity", "heartburn", "gas", "pot fugane", "jalan", "acid reflux"],
        "title": "Acidity / Gas",
        "remedy": "Cold milk (plain, not with anything acidic) can calm a burning sensation. "
                   "Chewing a few saunf (fennel) seeds after meals or sipping jeera water aids "
                   "digestion. Avoid lying down right after a heavy meal.",
        "caveat": "Fennel and cumin are traditionally used for digestion and have mild supporting "
                   "evidence; eating smaller meals and not lying down right after eating are both "
                   "genuinely useful habits. Frequent or severe acidity should be checked by a "
                   "doctor rather than managed with home remedies alone."
    },
    {
        "keywords": ["constipation", "baddhakoshtata", "bad koshtata", "pot saaf nahi", "kabj"],
        "title": "Constipation",
        "remedy": "A glass of warm water with lemon first thing in the morning, plus soaked "
                   "raisins or 1 tsp isabgol (psyllium husk) in warm milk at night, is a common "
                   "family remedy. Regular meal timing and enough water through the day help too.",
        "caveat": "Isabgol (psyllium husk) is genuinely fibre-based and has real evidence for "
                   "easing constipation; the lemon water mainly helps via hydration. If it "
                   "persists beyond a week, or comes with pain or bleeding, see a doctor."
    },
    {
        "keywords": ["headache", "dokedukhi", "doke dukhi", "migraine", "sir dukhna"],
        "title": "Headache",
        "remedy": "A few drops of clove or peppermint oil massaged gently on the temples, along "
                   "with resting in a dark, quiet room, is a common home approach. Staying "
                   "hydrated and not skipping meals also matters — many 'headaches' are actually "
                   "dehydration or low blood sugar.",
        "caveat": "Peppermint oil on the temples has some real evidence for tension headaches. "
                   "But recurring or severe headaches, or ones with vision changes or vomiting, "
                   "need medical attention — don't rely on home remedies alone for those."
    },
    {
        "keywords": ["sore throat", "ghasa khavkhavne", "gala dukhna", "throat pain"],
        "title": "Sore Throat",
        "remedy": "Gargle with warm salt water 2–3 times a day. Warm turmeric milk before bed and "
                   "sucking on a small piece of mulethi (licorice) are also common family remedies.",
        "caveat": "Warm salt-water gargling has decent evidence for easing throat pain and is "
                   "genuinely safe for most people. If the sore throat comes with high fever, "
                   "white patches, or lasts more than a week, get it checked — it could need "
                   "antibiotics, which no home remedy can substitute for."
    },
    {
        "keywords": ["weakness", "thakva", "ashaktapana", "fatigue", "low energy", "tiredness"],
        "title": "Weakness / Fatigue",
        "remedy": "A glass of warm milk with a pinch of turmeric and a few soaked almonds, or "
                   "dates with milk, is a traditional pick-me-up. Iron-rich foods like jaggery, "
                   "spinach and dates are often recommended for ongoing tiredness.",
        "caveat": "Iron-rich foods can genuinely help if the tiredness is linked to mild iron "
                   "deficiency, but persistent fatigue can have many causes (thyroid, anemia, "
                   "sleep issues, stress). If it doesn't improve in a couple of weeks, a blood "
                   "test is more useful than any remedy — check the Symptom Checker on this app."
    },
    {
        "keywords": ["joint pain", "sandhedukhi", "sandhe dukhi", "knee pain", "back pain"],
        "title": "Joint / Body Pain",
        "remedy": "Warm mustard or sesame oil massage on the affected area, and applying a warm "
                   "compress, is a common family remedy. Turmeric milk before bed is also used "
                   "for general body ache.",
        "caveat": "Warm oil massage and heat can genuinely ease minor muscular stiffness by "
                   "improving local blood flow. Turmeric's anti-inflammatory effect in food "
                   "amounts is modest at best. Persistent or worsening joint pain, swelling, or "
                   "pain after an injury needs a doctor's evaluation, not just home remedies."
    },
    {
        "keywords": ["insomnia", "nidraash", "zop yet nahi", "sleep problem", "cant sleep"],
        "title": "Trouble Sleeping",
        "remedy": "Warm turmeric or plain milk an hour before bed, along with a fixed sleep "
                   "schedule and no screens right before bed, is the classic family advice.",
        "caveat": "Warm milk before bed is mostly comforting/habitual rather than strongly proven "
                   "sedative; consistent sleep timing and reduced screen light before bed have "
                   "much stronger evidence. If sleeplessness continues for weeks, it's worth "
                   "discussing with a doctor rather than relying on home remedies."
    },
]

def grandma_bot_reply(message):
    msg = (message or "").lower().strip()
    if not msg:
        return {
            "title": None,
            "text": "Tell me what's bothering you — cold, cough, upset stomach, headache, "
                    "acidity, weakness, joint pain, sore throat, or trouble sleeping — and "
                    "I'll share the family remedy along with an honest note on what's actually "
                    "backed by evidence.",
            "caveat": None
        }

    greetings = ["hi", "hello", "hey", "namaste", "hii"]
    if any(msg == gtext or msg.startswith(gtext + " ") for gtext in greetings):
        return {
            "title": None,
            "text": "Namaste! I'm Grandma's Remedy Bot 🍵 — ask me about a cold, cough, upset "
                    "stomach, acidity, headache, weakness, joint pain, sore throat, constipation "
                    "or sleep trouble, and I'll share what's traditionally done at home.",
            "caveat": None
        }

    for entry in GRANDMA_REMEDY_DB:
        if any(k in msg for k in entry["keywords"]):
            return {"title": entry["title"], "text": entry["remedy"], "caveat": entry["caveat"]}

    return {
        "title": None,
        "text": "I don't have a family remedy for that one yet. Try asking about a cold, cough, "
                "upset stomach, acidity, constipation, headache, sore throat, weakness, joint "
                "pain, or trouble sleeping.",
        "caveat": None
    }

@app.route("/grandma-remedy")
def grandma_remedy():
    return render_template("grandma_remedy.html")

@app.route("/api/grandma-bot", methods=["POST"])
def api_grandma_bot():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "")
    return jsonify(grandma_bot_reply(message))

# =======================
# FAMILY THALI COMPARISON
# Lets a household log what each family member ate today (from a common
# Indian-thali checklist) and compares nutrient coverage across the family
# so it's easy to see who's falling short on what.
# =======================
THALI_NUTRIENT_TAGS = {
    "Roti / Chapati":            ["Fibre & Grains"],
    "Rice":                      ["Fibre & Grains"],
    "Dal (Toor / Moong / Masoor)": ["Protein", "Iron", "Fibre & Grains"],
    "Sabzi / Mixed Vegetable":   ["Fibre & Grains", "Vitamin C", "Iron"],
    "Curd / Dahi":               ["Calcium", "Protein"],
    "Milk":                      ["Calcium", "Protein", "Vitamin B12"],
    "Egg":                       ["Protein", "Vitamin B12"],
    "Fruit (Banana/Apple/Orange)": ["Fibre & Grains", "Vitamin C"],
}
THALI_NUTRIENT_CATEGORIES = ["Protein", "Iron", "Calcium", "Vitamin B12", "Fibre & Grains", "Vitamin C"]

def compute_thali_coverage(item_names):
    """Given a list of thali item names, return which nutrient categories are covered."""
    covered = set()
    for item in item_names:
        for tag in THALI_NUTRIENT_TAGS.get(item, []):
            covered.add(tag)
    return covered

@app.route("/family-thali", methods=["GET", "POST"])
@login_required
def family_thali():
    db = get_db()
    today = datetime.now().strftime("%Y-%m-%d")

    if request.method == "POST":
        action = request.form.get("action")

        if action == "add_member":
            name = request.form.get("member_name", "").strip()
            age = request.form.get("member_age", "").strip()
            role = request.form.get("member_role", "").strip()
            if name:
                db.execute(
                    "INSERT INTO family_members (user_id, name, age, role, created_at) VALUES (?,?,?,?,?)",
                    (session["user_id"], name, int(age) if age.isdigit() else None, role, datetime.now().isoformat())
                )
                db.commit()
                flash(f"Added {name} to your family.", "success")
            return redirect(url_for("family_thali"))

        if action == "delete_member":
            member_id = request.form.get("member_id")
            db.execute(
                "DELETE FROM family_members WHERE id = ? AND user_id = ?",
                (member_id, session["user_id"])
            )
            db.execute("DELETE FROM thali_entries WHERE member_id = ?", (member_id,))
            db.commit()
            return redirect(url_for("family_thali"))

        if action == "log_thali":
            member_id = request.form.get("member_id")
            items = request.form.getlist("items")
            member = db.execute(
                "SELECT * FROM family_members WHERE id = ? AND user_id = ?",
                (member_id, session["user_id"])
            ).fetchone()
            if member and items:
                db.execute("DELETE FROM thali_entries WHERE member_id = ? AND entry_date = ?", (member_id, today))
                db.execute(
                    "INSERT INTO thali_entries (member_id, entry_date, items, created_at) VALUES (?,?,?,?)",
                    (member_id, today, json.dumps(items), datetime.now().isoformat())
                )
                db.commit()
                flash(f"Logged today's thali for {member['name']}.", "success")
            return redirect(url_for("family_thali"))

    members = db.execute(
        "SELECT * FROM family_members WHERE user_id = ? ORDER BY created_at ASC",
        (session["user_id"],)
    ).fetchall()

    comparison = []
    gap_counter = {cat: 0 for cat in THALI_NUTRIENT_CATEGORIES}
    for member in members:
        entry = db.execute(
            "SELECT * FROM thali_entries WHERE member_id = ? AND entry_date = ?",
            (member["id"], today)
        ).fetchone()
        items = json.loads(entry["items"]) if entry else []
        covered = compute_thali_coverage(items)
        gaps = [c for c in THALI_NUTRIENT_CATEGORIES if c not in covered]
        for g in gaps:
            gap_counter[g] += 1
        comparison.append({
            "member": member,
            "items": items,
            "covered": covered,
            "gaps": gaps,
            "logged": entry is not None
        })

    family_alerts = []
    if members:
        for cat, count in gap_counter.items():
            if count >= 2 and count == len([c for c in comparison if c["logged"]]) and count > 0:
                family_alerts.append(f"The whole family logged today is low on {cat} — worth adding to tomorrow's thali.")
            elif count >= 2:
                family_alerts.append(f"{count} family members are low on {cat} today.")

    return render_template(
        "family_thali.html",
        members=members,
        comparison=comparison,
        categories=THALI_NUTRIENT_CATEGORIES,
        food_items=sorted(THALI_NUTRIENT_TAGS.keys()),
        today=today,
        family_alerts=family_alerts
    )


# =======================
# HOME PAGE
# =======================
@app.route("/")
def index():
    return render_template("index.html")

# =======================
# AUTH: SIGNUP / LOGIN / LOGOUT
# =======================
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("Please fill in all fields.", "error")
            return render_template("signup.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("signup.html")

        db = get_db()
        existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            flash("An account with this email already exists. Please log in.", "error")
            return render_template("signup.html")

        db.execute(
            "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (name, email, generate_password_hash(password), datetime.now().isoformat())
        )
        db.commit()

        user = db.execute("SELECT id, name FROM users WHERE email = ?", (email,)).fetchone()
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        flash(f"Welcome to NutriVeda, {user['name']}!", "success")
        return redirect(url_for("dashboard"))

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Incorrect email or password.", "error")
            return render_template("login.html")

        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        flash(f"Welcome back, {user['name']}!", "success")
        next_page = request.args.get("next")
        return redirect(next_page or url_for("dashboard"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You've been logged out.", "info")
    return redirect(url_for("index"))

# =======================
# SOCIAL LOGIN — GOOGLE
# =======================
@app.route("/login/google")
def login_google():
    if not GOOGLE_LOGIN_ENABLED:
        flash("Google Sign-In isn't configured yet. Add GOOGLE_CLIENT_ID and "
              "GOOGLE_CLIENT_SECRET (see README) to enable it.", "info")
        return redirect(url_for("login"))
    redirect_uri = url_for("login_google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@app.route("/login/google/callback")
def login_google_callback():
    if not GOOGLE_LOGIN_ENABLED:
        return redirect(url_for("login"))

    token = oauth.google.authorize_access_token()
    userinfo = token.get("userinfo")
    if not userinfo:
        userinfo = oauth.google.get("userinfo").json()
    email = (userinfo.get("email") or "").strip().lower()
    name = userinfo.get("name") or email.split("@")[0]
    google_uid = userinfo.get("sub", email)

    if not email:
        flash("Google didn't return an email address — please try again.", "error")
        return redirect(url_for("login"))

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if user is None:
        # Auto-create an account with a random unusable password (Google-only login)
        db.execute(
            "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (name, email, generate_password_hash(os.urandom(16).hex()), datetime.now().isoformat())
        )
        db.commit()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        db.execute(
            "INSERT INTO user_oauth (user_id, provider, provider_uid) VALUES (?, 'google', ?)",
            (user["id"], google_uid)
        )
        db.commit()

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    flash(f"Welcome, {user['name']}! Signed in with Google.", "success")
    return redirect(url_for("dashboard"))

# =======================
# HEALTH ANALYSIS FORM
# =======================
@app.route("/form")
@login_required
def form():
    return render_template("form.html")

# =======================
# HISTORY HELPERS
# =======================
def _migrate_history():
    """Safely add history columns to existing databases (old rows are kept)."""
    conn = sqlite3.connect(DB_PATH)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(assessments)")}
    for col, ddl in (("feature", "TEXT"), ("goal", "TEXT"), ("health_score", "REAL"), ("report", "TEXT")):
        if col not in cols:
            conn.execute(f"ALTER TABLE assessments ADD COLUMN {col} {ddl}")
    conn.commit(); conn.close()

def _health_score(bmi, count):
    """0-100 estimate derived only from stored BMI and deficiency count."""
    if bmi is None:
        return None
    return max(0, 100 - 12 * int(count or 0) - (0 if 18.5 <= bmi <= 24.9 else 10))

def _build_report(symptoms, detected):
    """Foods / nutrients / lifestyle / yoga for a list of detected deficiencies."""
    foods, lifestyle, yoga = [], [], []
    for d in detected:
        info = deficiency_db.get(d)
        if not info:
            continue
        foods += [f for f in info.get("foods", []) if f not in foods]
        if info.get("lifestyle") and info["lifestyle"] not in lifestyle:
            lifestyle.append(info["lifestyle"])
        if d in YOGA_SUGGESTION_MAP:
            yoga.append(YOGA_SUGGESTION_MAP[d])
    return {"deficiencies": detected, "nutrients": [d.replace(" Deficiency", "") for d in detected],
            "foods": foods, "lifestyle": lifestyle, "yoga": yoga}

HISTORY_FEATURES = {
    "bmi": "BMI Analysis", "weightloss": "Weight Loss", "weightgain": "Weight Gain",
    "food_log": "Food Diary", "smart_meal_planner": "Meal Planner", "family_thali": "Family Thali",
    "allergy_tracker": "Allergy Tracker", "cycle_tracker": "Cycle Tracker",
}

@app.after_request
def _log_feature_use(resp):
    """Record every successful feature submission in the user's history."""
    try:
        feature = HISTORY_FEATURES.get(request.endpoint)
        if feature and request.method == "POST" and session.get("user_id") and resp.status_code < 400:
            form = {k: v for k, v in request.form.items() if "password" not in k.lower()}
            bmi = None
            try:
                bmi = round(float(form["weight"]) / ((float(form["height"]) / 100) ** 2), 2)
            except Exception:
                pass
            db = sqlite3.connect(DB_PATH)
            db.execute(
                """INSERT INTO assessments (user_id, created_at, bmi, symptoms, detected, deficiency_count,
                   feature, goal, report) VALUES (?,?,?,?,?,?,?,?,?)""",
                (session["user_id"], datetime.now().isoformat(timespec="seconds"), bmi, "", "", 0,
                 feature, form.get("goal", ""), json.dumps({"inputs": form}, ensure_ascii=False)))
            db.commit(); db.close()
    except Exception:
        pass
    return resp

def _history_records(user_id):
    """All of one user's records, oldest first, as plain dicts (old rows upgraded on read)."""
    rows = get_db().execute("SELECT * FROM assessments WHERE user_id = ? ORDER BY created_at ASC, id ASC", (user_id,)).fetchall()
    out = []
    for r in rows:
        symptoms = [x.strip() for x in (r["symptoms"] or "").split(",") if x.strip()]
        detected = [x.strip() for x in (r["detected"] or "").split(",") if x.strip()]
        try:
            rep = json.loads(r["report"]) if r["report"] else None
        except Exception:
            rep = None
        if not rep:
            rep = _build_report(symptoms, detected)
            rep["inputs"] = {"height_cm": r["height"], "weight_kg": r["weight"], "symptoms": symptoms}
        feature = r["feature"] or "Symptom Analysis"
        score = r["health_score"] if r["health_score"] is not None else _health_score(r["bmi"], r["deficiency_count"]) if feature == "Symptom Analysis" else None
        out.append({"id": r["id"], "ts": r["created_at"], "feature": feature, "symptoms": symptoms,
                    "bmi": r["bmi"], "detected": detected, "count": r["deficiency_count"] or 0,
                    "goal": r["goal"] or "", "score": score, "report": rep})
    return out

@app.route("/result", methods=["POST"])
@login_required
def result():
    name   = session.get("user_name", request.form.get("name", "Guest"))
    height = float(request.form.get("height", 170))
    weight = float(request.form.get("weight", 65))
    symptoms = request.form.getlist("symptoms")

    bmi = round(weight / ((height / 100) ** 2), 2)

    detected = []
    for d, info in deficiency_db.items():
        if any(s in info["symptoms"] for s in symptoms):
            detected.append(d)

    yoga_links = [(d, YOGA_SUGGESTION_MAP[d]) for d in detected if d in YOGA_SUGGESTION_MAP]

    # Auto-save this assessment (full report) to the logged-in user's history
    report = _build_report(symptoms, detected)
    report["inputs"] = {"height_cm": height, "weight_kg": weight, "symptoms": symptoms}
    goal = request.form.get("goal", "")
    db = get_db()
    db.execute(
        """INSERT INTO assessments
           (user_id, created_at, height, weight, bmi, symptoms, detected, deficiency_count,
            feature, goal, health_score, report)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            session["user_id"], datetime.now().isoformat(timespec="seconds"),
            height, weight, bmi,
            ", ".join(symptoms), ", ".join(detected), len(detected),
            "Symptom Analysis", goal, _health_score(bmi, len(detected)),
            json.dumps(report, ensure_ascii=False)
        )
    )
    db.commit()

    return render_template(
        "result.html",
        name=name,
        bmi=bmi,
        detected=detected,
        db=deficiency_db,
        yoga_links=yoga_links
    )

# =======================
# DASHBOARD
# =======================
@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    name = session.get("user_name", "User")
    db = get_db()
    history = db.execute(
        "SELECT * FROM assessments WHERE user_id = ? ORDER BY created_at DESC LIMIT 5",
        (session["user_id"],)
    ).fetchall()
    total_checks = db.execute(
        "SELECT COUNT(*) AS c FROM assessments WHERE user_id = ?", (session["user_id"],)
    ).fetchone()["c"]
    latest = history[0] if history else None
    return render_template(
        "dashboard.html",
        name=name,
        history=history,
        total_checks=total_checks,
        latest=latest
    )

# =======================
# HISTORY / SYMPTOM IMPROVEMENT TRACKING
# =======================
@app.route("/history")
@login_required
def history():
    records = _history_records(session["user_id"])
    sym = [r for r in records if r["feature"] == "Symptom Analysis"]
    now_month = datetime.now().strftime("%Y-%m")
    month_checks = sum(1 for r in records if r["ts"].startswith(now_month))
    progress = None
    insight = ""
    if records:
        insight = f"You have completed {len(records)} health check{'s' if len(records) != 1 else ''} so far"
        insight += f", {month_checks} of them this month." if month_checks else "."
    if len(sym) >= 2:
        f, l = sym[0], sym[-1]
        progress = {"first_ts": f["ts"], "last_ts": l["ts"],
                    "def": [f["count"], l["count"]], "bmi": [f["bmi"], l["bmi"]],
                    "sym": [len(f["symptoms"]), len(l["symptoms"])]}
        insight += (f" Your recorded possible nutrient concerns changed from {f['count']} to {l['count']}"
                    f" between your first and latest symptom analysis.")
    return render_template("history.html", records_json=json.dumps(records, ensure_ascii=False),
                           progress=progress, insight=insight, total=len(records))

@app.route("/history/export.csv")
@login_required
def history_export():
    import csv, io
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow(["Date", "Time", "Feature", "Symptoms", "BMI", "Possible concerns", "Count", "Foods", "Lifestyle", "Yoga", "Goal", "Health score"])
    for r in reversed(_history_records(session["user_id"])):
        d, _, t = r["ts"].partition("T")
        rep = r["report"]
        w.writerow([d, t[:5], r["feature"], "; ".join(r["symptoms"]), r["bmi"] or "", "; ".join(r["detected"]), r["count"],
                    "; ".join(rep.get("foods", [])), " | ".join(rep.get("lifestyle", [])), "; ".join(rep.get("yoga", [])),
                    r["goal"], r["score"] if r["score"] is not None else ""])
    return Response("\ufeff" + buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=nutriveda_history.csv"})

# =======================
# SYMPTOMS & DEFICIENCY
# =======================
@app.route("/symptoms")
@login_required
def symptoms():
    all_symptoms = sorted({s for d in deficiency_db.values() for s in d["symptoms"]})
    return render_template("symptoms.html", symptoms=all_symptoms, ddb={k: v["symptoms"] for k, v in deficiency_db.items()})

@app.route("/deficiency")
def deficiency():
    return render_template("deficiency.html", deficiencies=deficiency_db)

# =======================
# BMI PAGE
# =======================
@app.route("/bmi", methods=["GET", "POST"])
def bmi():
    bmi_value = None
    category = None
    if request.method == "POST":
        h = float(request.form["height"])
        w = float(request.form["weight"])
        bmi_value = round(w / ((h / 100) ** 2), 2)
        if bmi_value < 18.5:
            category = "Underweight"
        elif bmi_value < 25:
            category = "Normal"
        elif bmi_value < 30:
            category = "Overweight"
        else:
            category = "Obese"
    return render_template("bmi.html", bmi=bmi_value, category=category)

# =======================
# HAIR CARE
# =======================
@app.route("/haircare")
def haircare():
    return render_template("haircare.html")

# =======================
# SKIN CARE
# =======================
@app.route("/skincare")
def skincare():
    return render_template("skincare.html")


# Expanded nutrient coverage for the advanced encyclopedia
nutrient_db.extend([{'key': 'vitamin-b2', 'name': 'Vitamin B2 (Riboflavin)', 'category': 'vitamin', 'also_known': 'Riboflavin', 'icon': '⚙️', 'icon_bg': 'background:linear-gradient(135deg,#facc15,#ca8a04);', 'rda': '1.1–1.3 mg/day', 'short': 'Supports energy metabolism, skin and normal red-blood-cell function.', 'long': 'Riboflavin helps enzymes release energy from food and supports normal cellular function. It also contributes to maintaining healthy skin and blood cells.', 'deficiency_signs': ['Cracked corners of mouth', 'Sore throat', 'Fatigue', 'Skin inflammation'], 'foods': ['Milk', 'Curd', 'Almonds', 'Eggs', 'Mushrooms', 'Spinach'], 'tip': 'Include dairy or fortified alternatives, eggs, nuts and leafy vegetables across the week.', 'video': 'https://www.youtube.com/results?search_query=Vitamin+B2+nutrition', 'official_name': 'NIH — Riboflavin Fact Sheet', 'official_url': 'https://ods.od.nih.gov/factsheets/Riboflavin-Consumer/', 'official_desc': 'Office of Dietary Supplements consumer information on riboflavin.'}, {'key': 'folate', 'name': 'Folate (Vitamin B9)', 'category': 'vitamin', 'also_known': 'Folic acid', 'icon': '🌱', 'icon_bg': 'background:linear-gradient(135deg,#22c55e,#15803d);', 'rda': '400 mcg DFE/day (adults)', 'short': 'Important for DNA synthesis and red-blood-cell formation.', 'long': 'Folate is needed for DNA and cell division and is especially important during pregnancy for neural-tube development.', 'deficiency_signs': ['Fatigue', 'Mouth sores', 'Pale skin', 'Megaloblastic anaemia'], 'foods': ['Lentils', 'Chana', 'Spinach', 'Methi', 'Peanuts', 'Citrus fruits'], 'tip': 'Regularly include pulses and leafy greens; pregnancy needs are higher and should be discussed with a clinician.', 'video': 'https://www.youtube.com/results?search_query=Folate+Vitamin+B9+nutrition', 'official_name': 'NIH — Folate Fact Sheet', 'official_url': 'https://ods.od.nih.gov/factsheets/Folate-Consumer/', 'official_desc': 'Office of Dietary Supplements consumer information on folate.'}, {'key': 'vitamin-b5', 'name': 'Vitamin B5 (Pantothenic Acid)', 'category': 'vitamin', 'also_known': 'Pantothenic acid', 'icon': '🔋', 'icon_bg': 'background:linear-gradient(135deg,#fb923c,#ea580c);', 'rda': '5 mg/day (adults)', 'short': 'Helps the body make and use energy and synthesize important molecules.', 'long': 'Pantothenic acid is part of coenzyme A, which is central to energy metabolism and the synthesis of fatty acids and hormones.', 'deficiency_signs': ['Fatigue', 'Irritability', 'Numbness or burning sensations (rare)'], 'foods': ['Mushrooms', 'Avocado', 'Eggs', 'Yogurt', 'Lentils', 'Sunflower seeds'], 'tip': 'Deficiency is uncommon with a varied diet.', 'video': 'https://www.youtube.com/results?search_query=Vitamin+B5+nutrition', 'official_name': 'NIH — Pantothenic Acid Fact Sheet', 'official_url': 'https://ods.od.nih.gov/factsheets/PantothenicAcid-Consumer/', 'official_desc': 'Office of Dietary Supplements consumer information on pantothenic acid.'}, {'key': 'vitamin-b7', 'name': 'Biotin (Vitamin B7)', 'category': 'vitamin', 'also_known': 'Biotin', 'icon': '💇', 'icon_bg': 'background:linear-gradient(135deg,#ec4899,#be185d);', 'rda': '30 mcg/day (adults)', 'short': 'Supports carbohydrate, fat and protein metabolism.', 'long': 'Biotin is a water-soluble B vitamin involved in enzymes that process fats, carbohydrates and proteins.', 'deficiency_signs': ['Hair thinning', 'Skin rash', 'Fatigue', 'Neurological symptoms (severe)'], 'foods': ['Eggs (cooked)', 'Nuts', 'Seeds', 'Sweet potato', 'Legumes'], 'tip': 'A balanced diet usually provides enough; avoid high-dose supplements unless medically advised.', 'video': 'https://www.youtube.com/results?search_query=Biotin+Vitamin+B7+nutrition', 'official_name': 'NIH — Biotin Fact Sheet', 'official_url': 'https://ods.od.nih.gov/factsheets/Biotin-Consumer/', 'official_desc': 'Office of Dietary Supplements consumer information on biotin.'}, {'key': 'selenium', 'name': 'Selenium', 'category': 'mineral', 'also_known': 'Se', 'icon': '🛡️', 'icon_bg': 'background:linear-gradient(135deg,#475569,#0f172a);', 'rda': '55 mcg/day (adults)', 'short': 'Supports thyroid hormone metabolism and antioxidant protection.', 'long': 'Selenium is a component of selenoproteins that help protect cells from oxidative damage and support thyroid function.', 'deficiency_signs': ['Muscle weakness', 'Hair/nail changes', 'Thyroid-related problems (severe)'], 'foods': ['Eggs', 'Fish', 'Sunflower seeds', 'Whole grains', 'Dairy'], 'tip': 'Food selenium varies by soil and region, so variety is more useful than chasing a single food.', 'video': 'https://www.youtube.com/results?search_query=Selenium+nutrition+foods', 'official_name': 'NIH — Selenium Fact Sheet', 'official_url': 'https://ods.od.nih.gov/factsheets/Selenium-Consumer/', 'official_desc': 'Office of Dietary Supplements consumer information on selenium.'}])

# =======================
# WEIGHT LOSS
# =======================
@app.route("/weightloss", methods=["GET", "POST"])
def weightloss():
    plan = None
    if request.method == "POST":
        plan = {
            "tips": "Low calorie diet, walking 30 min daily, yoga",
            "foods": ["Green Salad", "Dal", "Brown Rice", "Curd", "Oats",
                      "Moong Dal", "Cucumber", "Lemon Water", "Sprouts"],
            "video": "https://www.youtube.com/embed/UBMk30rjy0o"
        }
    return render_template("weightloss.html", plan=plan)

# =======================
# WEIGHT GAIN
# =======================
@app.route("/weightgain", methods=["GET", "POST"])
def weightgain():
    plan = None
    if request.method == "POST":
        plan = {
            "tips": "Calorie-rich nutritious foods, strength training",
            "foods": ["Milk", "Paneer", "Rice", "Dal", "Dry Fruits",
                      "Banana", "Peanut Butter", "Ghee", "Chana", "Eggs"],
            "video": "https://www.youtube.com/embed/1skBf6h2ksI"
        }
    return render_template("weightgain.html", plan=plan)

# =======================
# FEEDBACK
# =======================
@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    submitted = False
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        rating = request.form.get("rating", 5)
        liked = request.form.get("liked", "")
        message = request.form.get("feedback", "").strip()

        db = get_db()
        db.execute(
            """INSERT INTO feedback (user_id, name, rating, liked, message, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                session.get("user_id"), name, int(rating), liked, message,
                datetime.now().isoformat()
            )
        )
        db.commit()
        submitted = True

    return render_template("feedback.html", submitted=submitted)

# =======================
# SEASONAL FOOD GUIDE
# =======================
@app.route("/seasonal")
def seasonal():
    return render_template("seasonal.html")

# =======================
# PRAKRUTI (DOSHA) QUIZ — Vata / Pitta / Kapha
# =======================
@app.route("/dosha-quiz")
def dosha_quiz():
    return render_template("dosha_quiz.html")

# =======================
# PREGNANCY NUTRITION GUIDE — trimester-wise
# =======================
@app.route("/pregnancy")
def pregnancy():
    return render_template("pregnancy.html")

# =======================
# AGE-WISE NUTRITION NEEDS — infant to senior
# =======================
@app.route("/age-nutrition")
def age_nutrition():
    return render_template("age_nutrition.html")

# =======================
# MENSTRUAL CYCLE TRACKER — cycle-phase based nutrition
# =======================
@app.route("/cycle-tracker", methods=["GET", "POST"])
@login_required
def cycle_tracker():
    db = get_db()
    if request.method == "POST":
        period_start = request.form.get("period_start", "").strip()
        cycle_length = request.form.get("cycle_length", "28").strip()
        period_length = request.form.get("period_length", "5").strip()
        symptoms = ", ".join(request.form.getlist("symptoms"))

        if period_start:
            db.execute(
                """INSERT INTO cycle_logs (user_id, period_start, cycle_length, period_length, symptoms, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (session["user_id"], period_start,
                 int(cycle_length) if cycle_length.isdigit() else 28,
                 int(period_length) if period_length.isdigit() else 5,
                 symptoms, datetime.now().isoformat())
            )
            db.commit()
            flash("Cycle logged! Your nutrition plan below is now up to date.", "success")
        return redirect(url_for("cycle_tracker"))

    logs = db.execute(
        "SELECT * FROM cycle_logs WHERE user_id = ? ORDER BY period_start DESC",
        (session["user_id"],)
    ).fetchall()

    latest = logs[0] if logs else None
    cycle_info = None
    if latest:
        start_date = datetime.strptime(latest["period_start"], "%Y-%m-%d")
        days_since = (datetime.now() - start_date).days % latest["cycle_length"]
        period_len = latest["period_length"]
        cycle_len = latest["cycle_length"]
        ovulation_day = cycle_len - 14  # luteal phase is ~14 days, works back from next period

        if days_since < period_len:
            phase = "menstrual"
        elif days_since < ovulation_day - 2:
            phase = "follicular"
        elif days_since <= ovulation_day + 2:
            phase = "ovulation"
        else:
            phase = "luteal"

        next_period_date = start_date + timedelta(days=cycle_len)
        while next_period_date <= datetime.now():
            next_period_date += timedelta(days=cycle_len)

        cycle_info = {
            "day": days_since + 1,
            "phase": phase,
            "next_period": next_period_date.strftime("%d %b %Y"),
            "cycle_length": cycle_len,
        }

    return render_template("cycle_tracker.html", logs=logs, cycle_info=cycle_info)

@app.route("/cycle-tracker/delete/<int:log_id>", methods=["POST"])
@login_required
def cycle_tracker_delete(log_id):
    db = get_db()
    db.execute("DELETE FROM cycle_logs WHERE id = ? AND user_id = ?", (log_id, session["user_id"]))
    db.commit()
    flash("Entry removed.", "info")
    return redirect(url_for("cycle_tracker"))

# =======================
# ALLERGY TRACKER — flags matching foods in the Food Diary
# =======================
@app.route("/allergy-tracker", methods=["GET", "POST"])
@login_required
def allergy_tracker():
    db = get_db()
    if request.method == "POST":
        allergen = request.form.get("allergen", "").strip()
        severity = request.form.get("severity", "Moderate")
        notes = request.form.get("notes", "").strip()
        if allergen:
            db.execute(
                "INSERT INTO allergies (user_id, allergen, severity, notes, created_at) VALUES (?, ?, ?, ?, ?)",
                (session["user_id"], allergen, severity, notes, datetime.now().isoformat())
            )
            db.commit()
            flash(f"Added {allergen} to your allergy list.", "success")
        return redirect(url_for("allergy_tracker"))

    allergies = db.execute(
        "SELECT * FROM allergies WHERE user_id = ? ORDER BY created_at DESC",
        (session["user_id"],)
    ).fetchall()
    return render_template("allergy_tracker.html", allergies=allergies)

@app.route("/allergy-tracker/delete/<int:allergy_id>", methods=["POST"])
@login_required
def allergy_tracker_delete(allergy_id):
    db = get_db()
    db.execute("DELETE FROM allergies WHERE id = ? AND user_id = ?", (allergy_id, session["user_id"]))
    db.commit()
    flash("Removed from your allergy list.", "info")
    return redirect(url_for("allergy_tracker"))

# =======================
# VEGETARIAN PROTEIN CALCULATOR
# =======================
@app.route("/protein")
def protein():
    return render_template("protein.html")

# =======================
# HOME WORKOUT PLANNER
# =======================
@app.route("/workout")
def workout():
    return render_template("workout.html")

# =======================
# YOGA FOR DEFICIENCIES
# =======================
@app.route("/yoga")
def yoga():
    return render_template("yoga.html")

# =======================
# STEP GOAL TRACKER
# =======================
@app.route("/steps")
def steps():
    return render_template("steps.html")

# =======================
# IMMUNITY BOOSTER RECIPES
# =======================
@app.route("/immunity")
def immunity():
    return render_template("immunity.html")

# =======================
# VITAMIN & MINERAL ENCYCLOPEDIA
# =======================
@app.route("/nutrients")
def nutrients():
    return render_template(
        "nutrients.html",
        nutrients=nutrient_db,
        nutrients_json=json.dumps(nutrient_db)
    )

@app.route("/resources")
def resources():
    return render_template("resources.html")

# =======================
# MEAL DIARY / FOOD LOG
# =======================
@app.route("/food-log", methods=["GET", "POST"])
@login_required
def food_log():
    db = get_db()
    if request.method == "POST":
        meal_type = request.form.get("meal_type", "Snack")
        food_name = request.form.get("food_name", "").strip()
        quantity = request.form.get("quantity", "").strip()
        calories = request.form.get("calories", "").strip()
        source = request.form.get("source", "manual")

        if food_name:
            db.execute(
                """INSERT INTO meal_log (user_id, meal_type, food_name, quantity, calories, source, logged_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (session["user_id"], meal_type, food_name, quantity,
                 int(calories) if calories.isdigit() else None, source,
                 datetime.now().isoformat())
            )
            db.commit()

            # Allergy Tracker integration: warn if this food matches
            # (or contains/is contained in) a saved allergen. Matching is
            # word-level and trims a trailing 's' so "Peanuts" still
            # catches "Peanut Chikki" and vice versa.
            allergy_rows = db.execute(
                "SELECT allergen, severity FROM allergies WHERE user_id = ?",
                (session["user_id"],)
            ).fetchall()

            def _norm_words(text):
                return {w.rstrip("s") for w in re.findall(r"[a-zA-Z]+", text.lower()) if len(w) > 2}

            food_words = _norm_words(food_name)
            hits = []
            for a in allergy_rows:
                allergen_words = _norm_words(a["allergen"])
                if allergen_words & food_words:
                    hits.append(a)
            if hits:
                names = ", ".join(f'{h["allergen"]} ({h["severity"]})' for h in hits)
                flash(f"⚠️ Allergy warning: {food_name} may contain/relate to your logged allergen(s): {names}.", "error")
            else:
                flash(f"Logged {food_name} to your food diary!", "success")
        return redirect(url_for("food_log"))

    today = datetime.now().strftime("%Y-%m-%d")
    entries = db.execute(
        "SELECT * FROM meal_log WHERE user_id = ? ORDER BY logged_at DESC LIMIT 100",
        (session["user_id"],)
    ).fetchall()
    today_entries = [e for e in entries if e["logged_at"][:10] == today]
    today_calories = sum(e["calories"] or 0 for e in today_entries)
    user_allergies = db.execute(
        "SELECT * FROM allergies WHERE user_id = ? ORDER BY created_at DESC",
        (session["user_id"],)
    ).fetchall()

    return render_template(
        "food_log.html",
        entries=entries,
        today_entries=today_entries,
        today_calories=today_calories,
        user_allergies=user_allergies
    )

@app.route("/food-log/delete/<int:entry_id>", methods=["POST"])
@login_required
def food_log_delete(entry_id):
    db = get_db()
    db.execute("DELETE FROM meal_log WHERE id = ? AND user_id = ?", (entry_id, session["user_id"]))
    db.commit()
    flash("Entry removed from your food diary.", "info")
    return redirect(url_for("food_log"))

# =======================
# COMMUNITY Q&A / COMMENTS
# =======================
@app.route("/community", methods=["GET", "POST"])
def community():
    db = get_db()
    if request.method == "POST":
        if "user_id" not in session:
            flash("Please log in to post a question.", "info")
            return redirect(url_for("login", next=request.path))
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        if title:
            db.execute(
                "INSERT INTO qa_questions (user_id, name, title, body, created_at) VALUES (?, ?, ?, ?, ?)",
                (session["user_id"], session.get("user_name", "User"), title, body, datetime.now().isoformat())
            )
            db.commit()
            flash("Your question has been posted!", "success")
        return redirect(url_for("community"))

    questions = db.execute(
        """SELECT q.*, (SELECT COUNT(*) FROM qa_answers a WHERE a.question_id = q.id) AS answer_count
           FROM qa_questions q ORDER BY q.created_at DESC"""
    ).fetchall()
    return render_template("community.html", questions=questions)

@app.route("/community/<int:question_id>", methods=["GET", "POST"])
def community_thread(question_id):
    db = get_db()
    question = db.execute("SELECT * FROM qa_questions WHERE id = ?", (question_id,)).fetchone()
    if question is None:
        flash("That question doesn't exist anymore.", "error")
        return redirect(url_for("community"))

    if request.method == "POST":
        if "user_id" not in session:
            flash("Please log in to reply.", "info")
            return redirect(url_for("login", next=request.path))
        body = request.form.get("body", "").strip()
        if body:
            db.execute(
                "INSERT INTO qa_answers (question_id, user_id, name, body, created_at) VALUES (?, ?, ?, ?, ?)",
                (question_id, session["user_id"], session.get("user_name", "User"), body, datetime.now().isoformat())
            )
            db.commit()
        return redirect(url_for("community_thread", question_id=question_id))

    answers = db.execute(
        "SELECT * FROM qa_answers WHERE question_id = ? ORDER BY created_at ASC", (question_id,)
    ).fetchall()
    return render_template("community_thread.html", question=question, answers=answers)

# =======================
# AI CHATBOT ASSISTANT
# A lightweight, rule-based assistant that answers common nutrition
# questions using the site's own deficiency & nutrient databases — works
# fully offline, no API key required. Swap in a real LLM API call here
# (see README) if you want free-form conversation.
# =======================
def chatbot_reply(message):
    msg = message.lower().strip()

    if not msg:
        return "Ask me about a deficiency, a nutrient, your BMI, or how to log a meal!"

    greetings = ["hi", "hello", "hey", "namaste", "hii"]
    if any(msg == g or msg.startswith(g + " ") for g in greetings):
        return "Hello! 👋 I'm your NutriVeda assistant. Ask me things like " \
               "'what foods have iron' or 'symptoms of vitamin d deficiency'."

    if "bmi" in msg:
        return "You can calculate your BMI on the BMI page (top menu). " \
               "Just enter your height and weight and I'll show your category."

    if any(w in msg for w in ["log", "diary", "track my food", "add meal"]):
        return "Head to Food Diary (menu bar) to log breakfast, lunch, dinner or snacks — " \
               "you can type it in manually or scan a packaged product's barcode."

    if "scan" in msg or "barcode" in msg:
        return "On the Food Diary page, tap 'Scan Barcode' and point your camera at a " \
               "packaged food's barcode — I'll fetch its name automatically via Open Food Facts."

    # Search nutrient_db by name
    for nutrient in nutrient_db:
        if nutrient["name"].lower() in msg or nutrient["key"].replace("-", " ") in msg:
            foods = ", ".join(nutrient["foods"][:6])
            return f"{nutrient['name']}: {nutrient['short']} Good sources: {foods}."

    # Search deficiency_db by name or symptom
    for name, info in deficiency_db.items():
        short_name = name.replace(" Deficiency", "").lower()
        if short_name in msg or "deficiency" in msg and short_name in msg:
            foods = ", ".join(info["foods"][:6])
            return f"For {name}, common signs are {', '.join(info['symptoms'])}. " \
                   f"Helpful foods: {foods}. Tip: {info['lifestyle']}"

    for name, info in deficiency_db.items():
        for symptom in info["symptoms"]:
            if symptom in msg:
                return f"'{symptom}' can be linked to {name}. Common foods that help: " \
                       f"{', '.join(info['foods'][:6])}. Try the full Symptom Checker for a proper check."

    if any(w in msg for w in ["weight loss", "lose weight"]):
        return "Check out the Weight Loss planner in the menu for a sample diet + workout plan."
    if any(w in msg for w in ["weight gain", "gain weight"]):
        return "Check out the Weight Gain planner in the menu for calorie-rich food ideas."
    if "protein" in msg:
        return "Visit the Protein Calculator (under More ▾) to estimate your daily protein needs."
    if "yoga" in msg or "meditat" in msg:
        return "The Yoga page has deficiency-specific routines — Iron, Calcium, Vitamin D, Protein & B12."

    return "I'm not fully sure about that yet — try asking about a specific vitamin/mineral, " \
           "a symptom, your BMI, or how to use the Food Diary. You can also ask a question " \
           "on the Community page and get help from others!"

@app.route("/api/chatbot", methods=["POST"])
def api_chatbot():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "")
    return jsonify({"reply": chatbot_reply(message)})

# =======================
# BARCODE FOOD LOOKUP (proxy-free — client calls Open Food Facts directly,
# this endpoint just logs the result once the user confirms it)
# =======================


# =======================
# ADVANCED FOOD INTELLIGENCE
# =======================

REGIONAL_FOOD_DB = {'Andhra Pradesh': [('Pesarattu', 'Green-gram crepe with ginger/chilli.', 'Protein, iron, fibre', 'Breakfast', 'https://www.youtube.com/results?search_query=Andhra+Pesarattu+recipe'), ('Gongura Pappu', 'Toor dal cooked with gongura leaves.', 'Protein, folate, iron', 'Lunch', 'https://www.youtube.com/results?search_query=Gongura+pappu+recipe'), ('Pulihora', 'Tamarind rice with peanuts and spices.', 'Carbohydrate, healthy fats, magnesium', 'Meal', 'https://www.youtube.com/results?search_query=Andhra+Pulihora+recipe')], 'Arunachal Pradesh': [('Thukpa', 'Warm noodle soup with vegetables and herbs.', 'Carbohydrate, fibre, protein when made with egg/tofu', 'Meal', 'https://www.youtube.com/results?search_query=Arunachal+Thukpa+recipe'), ('Chura Sabzi', 'Fresh cheese-based preparation with local greens.', 'Protein, calcium', 'Meal', 'https://www.youtube.com/results?search_query=Arunachal+Chura+Sabzi'), ('Zan', 'Millet-based porridge/meal.', 'Complex carbs, fibre, minerals', 'Breakfast', 'https://www.youtube.com/results?search_query=Arunachal+Zan+recipe')], 'Assam': [('Masor Tenga', 'Light sour fish curry with tomato or elephant apple.', 'Protein, B12, omega-3', 'Lunch', 'https://www.youtube.com/results?search_query=Assam+Masor+Tenga+recipe'), ('Khar', 'Traditional alkaline preparation usually served with rice.', 'Fibre and plant nutrients depending on vegetables', 'Meal', 'https://www.youtube.com/results?search_query=Assam+Khar+recipe'), ('Pitha', 'Rice-flour snack with regionally varied fillings.', 'Carbohydrate; nutrients vary by filling', 'Snack', 'https://www.youtube.com/results?search_query=Assamese+Pitha+recipe')], 'Bihar': [('Litti Chokha', 'Roasted wheat balls stuffed with sattu, served with vegetable mash.', 'Protein, fibre, iron', 'Meal', 'https://www.youtube.com/results?search_query=Bihar+Litti+Chokha+recipe'), ('Sattu Paratha', 'Whole-wheat flatbread filled with roasted gram flour.', 'Protein, fibre, iron', 'Breakfast', 'https://www.youtube.com/results?search_query=Bihar+Sattu+Paratha+recipe'), ('Chana Ghugni', 'Spiced chickpea curry.', 'Protein, fibre, folate', 'Snack/Meal', 'https://www.youtube.com/results?search_query=Bihar+Chana+Ghugni+recipe')], 'Chhattisgarh': [('Fara', 'Steamed rice-flour dumplings with lentils/spices.', 'Carbohydrate, protein, low-oil preparation', 'Snack', 'https://www.youtube.com/results?search_query=Chhattisgarh+Fara+recipe'), ('Chila', 'Rice/lentil pancake, often paired with chutney.', 'Protein, fibre, iron', 'Breakfast', 'https://www.youtube.com/results?search_query=Chhattisgarh+Chila+recipe'), ('Bafauri', 'Steamed gram-flour dumplings.', 'Protein, fibre', 'Snack', 'https://www.youtube.com/results?search_query=Chhattisgarh+Bafauri+recipe')], 'Goa': [('Goan Fish Curry', 'Fish simmered in coconut and spices.', 'Protein, omega-3, B12', 'Lunch', 'https://www.youtube.com/results?search_query=Goan+fish+curry+recipe'), ('Sol Kadhi', 'Coconut milk and kokum beverage.', 'Hydration, healthy fats', 'Drink', 'https://www.youtube.com/results?search_query=Goan+Sol+Kadhi+recipe'), ('Poi with Vegetable Bhaji', 'Local bread with vegetable curry.', 'Carbohydrate, fibre, micronutrients', 'Meal', 'https://www.youtube.com/results?search_query=Goan+Poi+bhaji+recipe')], 'Gujarat': [('Undhiyu', 'Mixed winter vegetables cooked with beans and spices.', 'Fibre, folate, potassium', 'Meal', 'https://www.youtube.com/results?search_query=Gujarati+Undhiyu+recipe'), ('Handvo', 'Fermented lentil-rice savoury cake.', 'Protein, fibre, B vitamins', 'Snack', 'https://www.youtube.com/results?search_query=Gujarati+Handvo+recipe'), ('Thepla', 'Spiced flatbread commonly made with wheat and fenugreek.', 'Fibre, iron, complex carbs', 'Breakfast', 'https://www.youtube.com/results?search_query=Gujarati+Thepla+recipe')], 'Haryana': [('Bajra Roti', 'Pearl-millet flatbread.', 'Fibre, iron, magnesium', 'Meal', 'https://www.youtube.com/results?search_query=Haryana+Bajra+Roti+recipe'), ('Bajra Khichdi', 'Millet and lentil one-pot meal.', 'Protein, fibre, iron', 'Meal', 'https://www.youtube.com/results?search_query=Haryana+Bajra+Khichdi+recipe'), ('Chaas', 'Spiced buttermilk.', 'Protein, calcium, hydration', 'Drink', 'https://www.youtube.com/results?search_query=Indian+chaas+recipe')], 'Himachal Pradesh': [('Rajma Madra', 'Kidney beans in a yogurt-based gravy.', 'Protein, fibre, iron', 'Meal', 'https://www.youtube.com/results?search_query=Himachali+Rajma+Madra+recipe'), ('Siddu', 'Steamed wheat bun with savoury or sweet filling.', 'Carbohydrate, fibre depending on filling', 'Breakfast', 'https://www.youtube.com/results?search_query=Himachali+Siddu+recipe'), ('Himachali Dham', 'Traditional lentil, rice and vegetable feast.', 'Protein, fibre, micronutrients', 'Meal', 'https://www.youtube.com/results?search_query=Himachali+Dham+recipe')], 'Jharkhand': [('Dhuska', 'Fried/steamed rice and lentil pancake.', 'Protein, carbohydrate', 'Breakfast', 'https://www.youtube.com/results?search_query=Jharkhand+Dhuska+recipe'), ('Rugra', 'Edible wild mushroom preparation.', 'Protein, fibre and minerals', 'Meal', 'https://www.youtube.com/results?search_query=Jharkhand+Rugra+recipe'), ('Sattu Drink', 'Roasted gram flour drink with water and spices.', 'Protein, fibre, iron', 'Drink', 'https://www.youtube.com/results?search_query=Sattu+drink+recipe')], 'Karnataka': [('Ragi Mudde', 'Finger-millet balls served with sambar or curry.', 'Calcium, fibre, complex carbs', 'Meal', 'https://www.youtube.com/results?search_query=Karnataka+Ragi+Mudde+recipe'), ('Bisi Bele Bath', 'Rice, lentils and vegetables cooked with spices.', 'Protein, fibre, carbohydrates', 'Meal', 'https://www.youtube.com/results?search_query=Bisi+Bele+Bath+recipe'), ('Neer Dosa', 'Thin rice crepes.', 'Carbohydrate, low-fat base', 'Breakfast', 'https://www.youtube.com/results?search_query=Karnataka+Neer+Dosa+recipe')], 'Kerala': [('Puttu Kadala', 'Steamed rice-coconut puttu with black chickpea curry.', 'Protein, fibre, iron', 'Breakfast', 'https://www.youtube.com/results?search_query=Kerala+Puttu+Kadala+recipe'), ('Avial', 'Mixed vegetables cooked with coconut and yogurt.', 'Fibre, potassium, micronutrients', 'Meal', 'https://www.youtube.com/results?search_query=Kerala+Avial+recipe'), ('Appam & Vegetable Stew', 'Fermented rice-coconut pancakes with vegetable stew.', 'Carbohydrate, fibre, micronutrients', 'Breakfast', 'https://www.youtube.com/results?search_query=Kerala+Appam+Vegetable+Stew')], 'Madhya Pradesh': [('Poha', 'Flattened rice with onion, peas and peanuts.', 'Carbohydrate, fibre, healthy fats', 'Breakfast', 'https://www.youtube.com/results?search_query=MP+Poha+recipe'), ('Dal Bafla', 'Wheat dumplings with dal and ghee.', 'Protein, fibre, iron', 'Meal', 'https://www.youtube.com/results?search_query=Madhya+Pradesh+Dal+Bafla'), ('Bhutte Ka Kees', 'Grated corn cooked with spices and milk.', 'Carbohydrate, fibre, folate', 'Snack', 'https://www.youtube.com/results?search_query=Bhutte+Ka+Kees+recipe')], 'Maharashtra': [('Pithla Bhakri', 'Gram-flour curry with millet/jowar flatbread.', 'Protein, fibre, iron, magnesium', 'Meal', 'https://www.youtube.com/results?search_query=Maharashtrian+Pithla+Bhakri'), ('Usal Misal', 'Sprouted legumes with spicy vegetable gravy.', 'Protein, fibre, folate, iron', 'Meal', 'https://www.youtube.com/results?search_query=Maharashtrian+Usal+Misal+recipe'), ('Poha', 'Flattened rice with peanuts, onion and lemon.', 'Carbohydrate, iron, healthy fats', 'Breakfast', 'https://www.youtube.com/results?search_query=Maharashtrian+Poha+recipe')], 'Manipur': [('Eromba', 'Mashed vegetables with fermented fish or a vegetarian version.', 'Fibre, potassium; protein varies', 'Meal', 'https://www.youtube.com/results?search_query=Manipuri+Eromba+recipe'), ('Singju', 'Fresh vegetable and herb salad.', 'Fibre, folate, vitamin C', 'Side', 'https://www.youtube.com/results?search_query=Manipuri+Singju+recipe'), ('Black Rice Kheer', 'Dessert using aromatic black rice.', 'Anthocyanins, carbohydrate', 'Dessert', 'https://www.youtube.com/results?search_query=Manipuri+Black+Rice+Kheer')], 'Meghalaya': [('Jadoh', 'Rice and meat dish, traditionally pork-based.', 'Protein, iron, B12; saturated fat varies', 'Meal', 'https://www.youtube.com/results?search_query=Meghalaya+Jadoh+recipe'), ('Tungrymbai', 'Fermented soybean preparation.', 'Plant protein, fibre', 'Side/Meal', 'https://www.youtube.com/results?search_query=Meghalaya+Tungrymbai+recipe'), ('Pukhlein', 'Rice-flour and jaggery sweet.', 'Carbohydrate, small amounts of iron', 'Snack', 'https://www.youtube.com/results?search_query=Meghalaya+Pukhlein+recipe')], 'Mizoram': [('Bai', 'Light vegetable and herb stew.', 'Fibre, potassium, micronutrients', 'Meal', 'https://www.youtube.com/results?search_query=Mizoram+Bai+recipe'), ('Sawchiar', 'Rice-based one-pot dish with protein source.', 'Carbohydrate, protein', 'Meal', 'https://www.youtube.com/results?search_query=Mizoram+Sawchiar+recipe'), ('Chhum Han', 'Steamed mixed vegetables.', 'Fibre, vitamin C, folate', 'Side', 'https://www.youtube.com/results?search_query=Mizoram+Chhum+Han')], 'Nagaland': [('Axone Bean Curry', 'Fermented soybean preparation used in Naga cooking.', 'Plant protein, fibre', 'Meal', 'https://www.youtube.com/results?search_query=Naga+Axone+recipe'), ('Smoked Meat with Greens', 'Traditional smoked meat paired with vegetables.', 'Protein, iron; sodium can be high', 'Meal', 'https://www.youtube.com/results?search_query=Nagaland+smoked+meat+greens'), ('Naga Chutney', 'Chilli-based condiment with local ingredients.', 'Vitamin C; use small portions due to heat/salt', 'Side', 'https://www.youtube.com/results?search_query=Naga+chutney+recipe')], 'Odisha': [('Dalma', 'Lentils cooked with vegetables and mild spices.', 'Protein, fibre, potassium', 'Meal', 'https://www.youtube.com/results?search_query=Odisha+Dalma+recipe'), ('Pakhala Bhata', 'Fermented rice with water/curd and accompaniments.', 'Carbohydrate, probiotics depending on preparation', 'Meal', 'https://www.youtube.com/results?search_query=Odisha+Pakhala+Bhata'), ('Chakuli Pitha', 'Fermented rice-lentil pancake.', 'Protein, carbohydrate, B vitamins', 'Breakfast', 'https://www.youtube.com/results?search_query=Odisha+Chakuli+Pitha')], 'Punjab': [('Sarson Saag & Makki Roti', 'Mustard greens with maize flatbread.', 'Folate, vitamin K, fibre, complex carbs', 'Meal', 'https://www.youtube.com/results?search_query=Punjabi+Sarson+Saag+Makki+Roti'), ('Chole', 'Chickpea curry with spices.', 'Protein, fibre, iron', 'Meal', 'https://www.youtube.com/results?search_query=Punjabi+Chole+recipe'), ('Rajma Chawal', 'Kidney beans with rice.', 'Protein, fibre, iron', 'Meal', 'https://www.youtube.com/results?search_query=Punjabi+Rajma+Chawal')], 'Rajasthan': [('Dal Baati Churma', 'Lentils with baked wheat baati and sweet crumble.', 'Protein, fibre, iron; calorie dense', 'Meal', 'https://www.youtube.com/results?search_query=Rajasthani+Dal+Baati+Churma'), ('Gatte ki Sabzi', 'Gram-flour dumplings in spiced gravy.', 'Protein, fibre', 'Meal', 'https://www.youtube.com/results?search_query=Rajasthani+Gatte+ki+Sabzi'), ('Bajra Khichdi', 'Pearl millet and lentil porridge.', 'Fibre, magnesium, protein', 'Meal', 'https://www.youtube.com/results?search_query=Rajasthani+Bajra+Khichdi')], 'Sikkim': [('Thukpa', 'Noodle soup with vegetables and protein.', 'Carbohydrate, fibre, protein', 'Meal', 'https://www.youtube.com/results?search_query=Sikkim+Thukpa+recipe'), ('Gundruk', 'Fermented leafy vegetable preparation.', 'Fibre and micronutrients', 'Side', 'https://www.youtube.com/results?search_query=Sikkim+Gundruk+recipe'), ('Kinema', 'Fermented soybean dish.', 'Plant protein, fibre', 'Side', 'https://www.youtube.com/results?search_query=Sikkim+Kinema+recipe')], 'Tamil Nadu': [('Idli Sambar', 'Steamed fermented rice-lentil cakes with lentil vegetable stew.', 'Protein, fibre, B vitamins', 'Breakfast', 'https://www.youtube.com/results?search_query=Tamil+Idli+Sambar+recipe'), ('Ven Pongal', 'Rice and moong dal cooked with spices.', 'Protein, carbohydrate', 'Breakfast', 'https://www.youtube.com/results?search_query=Tamil+Ven+Pongal+recipe'), ('Kootu', 'Vegetables and lentils cooked together.', 'Protein, fibre, potassium', 'Side', 'https://www.youtube.com/results?search_query=Tamil+Kootu+recipe')], 'Telangana': [('Jonna Roti', 'Sorghum flatbread.', 'Fibre, iron, magnesium', 'Meal', 'https://www.youtube.com/results?search_query=Telangana+Jonna+Roti'), ('Sarva Pindi', 'Rice-flour and peanut savoury pancake.', 'Carbohydrate, healthy fats, protein', 'Breakfast', 'https://www.youtube.com/results?search_query=Telangana+Sarva+Pindi'), ('Pesarattu', 'Green gram crepe, often served with chutney.', 'Protein, fibre, iron', 'Breakfast', 'https://www.youtube.com/results?search_query=Telangana+Pesarattu')], 'Tripura': [('Mui Borok', 'Traditional platter featuring vegetables, herbs and protein.', 'Fibre, micronutrients; varies by dish', 'Meal', 'https://www.youtube.com/results?search_query=Tripura+Mui+Borok'), ('Chakhwi', 'Light vegetable preparation with bamboo shoot.', 'Fibre, potassium', 'Meal', 'https://www.youtube.com/results?search_query=Tripura+Chakhwi'), ('Mosdeng Serma', 'Tomato/chilli-based side with herbs and protein variations.', 'Vitamin C, antioxidants', 'Side', 'https://www.youtube.com/results?search_query=Tripura+Mosdeng+Serma')], 'Uttar Pradesh': [('Dal Kachori', 'Spiced lentil-stuffed pastry.', 'Protein and carbohydrate; fried so calorie dense', 'Snack', 'https://www.youtube.com/results?search_query=UP+Dal+Kachori+recipe'), ('Bedmi Puri with Aloo', 'Urid-dal stuffed fried bread with potato curry.', 'Protein, carbohydrate; calorie dense', 'Breakfast', 'https://www.youtube.com/results?search_query=UP+Bedmi+Puri+recipe'), ('Bajra Roti & Dal', 'Millet flatbread with lentils.', 'Fibre, magnesium, protein', 'Meal', 'https://www.youtube.com/results?search_query=UP+Bajra+Roti+Dal')], 'Uttarakhand': [('Kafuli', 'Leafy green gravy made with spinach/fenugreek.', 'Folate, iron, vitamin K', 'Meal', 'https://www.youtube.com/results?search_query=Uttarakhand+Kafuli+recipe'), ('Bhatt ki Churdkani', 'Black soybean curry.', 'Plant protein, fibre, iron', 'Meal', 'https://www.youtube.com/results?search_query=Uttarakhand+Bhatt+ki+Churdkani'), ('Jhangore ki Kheer', 'Barnyard millet pudding.', 'Fibre, minerals, carbohydrate', 'Dessert', 'https://www.youtube.com/results?search_query=Uttarakhand+Jhangore+ki+Kheer')], 'West Bengal': [('Shorshe Ilish', 'Hilsa fish in mustard gravy.', 'Protein, omega-3, B12', 'Meal', 'https://www.youtube.com/results?search_query=Bengali+Shorshe+Ilish+recipe'), ('Moong Dal with Vegetables', 'Lentils cooked with seasonal vegetables.', 'Protein, fibre, folate', 'Meal', 'https://www.youtube.com/results?search_query=Bengali+Moong+Dal+vegetables'), ('Cholar Dal', 'Bengal gram dal with spices.', 'Protein, fibre, iron', 'Meal', 'https://www.youtube.com/results?search_query=Bengali+Cholar+Dal')], 'Jammu & Kashmir': [('Rajma Rice', 'Kidney beans with rice, common in Jammu cuisine.', 'Protein, fibre, iron', 'Meal', 'https://www.youtube.com/results?search_query=Jammu+Rajma+Chawal'), ('Haak Saag', 'Simple cooked leafy greens.', 'Folate, vitamin K, fibre', 'Side', 'https://www.youtube.com/results?search_query=Kashmiri+Haak+Saag'), ('Kahwa', 'Green tea with saffron, cardamom and nuts.', 'Polyphenols; nuts add healthy fats', 'Drink', 'https://www.youtube.com/results?search_query=Kashmiri+Kahwa+recipe')], 'Ladakh': [('Thukpa', 'Hearty noodle soup suited to cold climates.', 'Carbohydrate, protein depending on additions', 'Meal', 'https://www.youtube.com/results?search_query=Ladakhi+Thukpa+recipe'), ('Skyu', 'Traditional wheat-pasta stew with vegetables.', 'Carbohydrate, fibre, micronutrients', 'Meal', 'https://www.youtube.com/results?search_query=Ladakh+Skyu+recipe'), ('Barley Tsampa', 'Roasted barley flour used as a staple.', 'Fibre, complex carbs, magnesium', 'Breakfast', 'https://www.youtube.com/results?search_query=Ladakh+Tsampa')], 'Delhi': [('Chole Bhature', 'Chickpea curry with fried bread.', 'Protein, fibre; high energy', 'Meal', 'https://www.youtube.com/results?search_query=Delhi+Chole+Bhature'), ('Rajma Chawal', 'Kidney beans and rice.', 'Protein, fibre, iron', 'Meal', 'https://www.youtube.com/results?search_query=Delhi+Rajma+Chawal'), ('Fruit Chaat', 'Fresh fruit with spices and lemon.', 'Vitamin C, fibre, potassium', 'Snack', 'https://www.youtube.com/results?search_query=Delhi+Fruit+Chaat')], 'Puducherry': [('Vegetable Kuzhambu', 'Tamarind-spiced vegetable gravy.', 'Fibre, potassium, antioxidants', 'Meal', 'https://www.youtube.com/results?search_query=Puducherry+vegetable+kuzhambu'), ('Idli with Sambar', 'Fermented rice-lentil cakes with vegetable dal.', 'Protein, fibre, B vitamins', 'Breakfast', 'https://www.youtube.com/results?search_query=Puducherry+Idli+Sambar'), ('Coconut Rice', 'Rice tempered with coconut and spices.', 'Carbohydrate, healthy fats', 'Meal', 'https://www.youtube.com/results?search_query=Puducherry+Coconut+Rice')]}

KITCHEN_RECIPE_DB = [('Moong Dal', 'moong dal, tomato, onion, turmeric', 'Moong Dal Tadka', 'Protein 12g, fibre 6g, folate, iron', 'https://www.youtube.com/results?search_query=Moong+Dal+Tadka+Indian+recipe'), ('Besan', 'besan, onion, tomato, coriander', 'Vegetable Besan Chilla', 'Protein, iron, fibre, folate', 'https://www.youtube.com/results?search_query=Besan+Chilla+recipe'), ('Rice', 'rice, vegetables, peas, carrot', 'Vegetable Pulao', 'Carbohydrate, fibre, potassium', 'https://www.youtube.com/results?search_query=Indian+Vegetable+Pulao+recipe'), ('Potato', 'potato, peas, tomato, cumin', 'Aloo Matar', 'Carbohydrate, vitamin C, potassium', 'https://www.youtube.com/results?search_query=Aloo+Matar+recipe'), ('Spinach', 'spinach, onion, garlic, tomato', 'Palak Dal', 'Iron, folate, fibre, protein', 'https://www.youtube.com/results?search_query=Palak+Dal+recipe'), ('Paneer', 'paneer, spinach, tomato, onion', 'Palak Paneer', 'Protein, calcium, vitamin K, iron', 'https://www.youtube.com/results?search_query=Palak+Paneer+recipe'), ('Chickpeas', 'chickpeas, onion, tomato, ginger', 'Chana Masala', 'Protein, fibre, iron, folate', 'https://www.youtube.com/results?search_query=Chana+Masala+recipe'), ('Rajma', 'rajma, tomato, onion, ginger', 'Rajma Masala', 'Protein, fibre, iron, potassium', 'https://www.youtube.com/results?search_query=Rajma+Masala+recipe'), ('Poha', 'poha, onion, peanuts, lemon', 'Maharashtrian Kanda Poha', 'Carbohydrate, iron, healthy fats, vitamin C', 'https://www.youtube.com/results?search_query=Maharashtrian+Kanda+Poha'), ('Ragi', 'ragi flour, onion, curd, coriander', 'Ragi Dosa', 'Calcium, fibre, iron, complex carbs', 'https://www.youtube.com/results?search_query=Ragi+Dosa+recipe'), ('Jowar', 'jowar flour, water, oil', 'Jowar Bhakri', 'Fibre, iron, magnesium, complex carbs', 'https://www.youtube.com/results?search_query=Jowar+Bhakri+recipe'), ('Oats', 'oats, vegetables, peas, spices', 'Masala Oats', 'Fibre, beta-glucan, protein', 'https://www.youtube.com/results?search_query=Indian+Masala+Oats+recipe'), ('Egg', 'egg, onion, tomato, coriander', 'Masala Omelette', 'Protein, B12, choline, selenium', 'https://www.youtube.com/results?search_query=Indian+Masala+Omelette'), ('Curd', 'curd, cucumber, cumin, coriander', 'Cucumber Raita', 'Protein, calcium, probiotics', 'https://www.youtube.com/results?search_query=Cucumber+Raita+recipe'), ('Tomato', 'tomato, lentils, garlic, cumin', 'Tomato Dal', 'Protein, vitamin C, lycopene, folate', 'https://www.youtube.com/results?search_query=Tomato+Dal+recipe'), ('Methi', 'methi leaves, wheat flour, yogurt', 'Methi Thepla', 'Fibre, iron, folate, complex carbs', 'https://www.youtube.com/results?search_query=Methi+Thepla+recipe'), ('Sweet Potato', 'sweet potato, cumin, lemon, chilli', 'Chaat-style Sweet Potato', 'Beta-carotene, fibre, potassium, vitamin C', 'https://www.youtube.com/results?search_query=Sweet+Potato+Chaat+Indian'), ('Lentils', 'lentils, rice, vegetables, ghee', 'Dal Khichdi', 'Protein, fibre, iron, easy-to-digest meal', 'https://www.youtube.com/results?search_query=Dal+Khichdi+recipe')]

ONE_FOOD_DB = [{'name': 'Amla (Indian Gooseberry)', 'intro': 'Amla is a tart fruit widely used in Indian food and traditional wellness practices.', 'uses': ['Chutney', 'Murabba', 'Amla water', 'Fresh fruit with salt/spices'], 'recipes': ['Amla Chutney', 'Amla Rice', 'Amla Sharbat'], 'nutrients': ['Vitamin C', 'Polyphenols', 'Fibre', 'Manganese'], 'wellness': ['Supports normal immune function', 'Helps add vitamin C to meals', 'Useful for fibre-rich snack combinations'], 'facts': ['One of the better-known Indian sources of vitamin C', 'Vitamin C supports collagen formation and iron absorption', 'Taste is sour/astringent; pair with meals if preferred'], 'video': 'https://www.youtube.com/results?search_query=amla+recipes+Indian', 'source': 'https://ods.od.nih.gov/factsheets/VitaminC-Consumer/'}, {'name': 'Ragi', 'intro': 'Ragi (finger millet) is a whole grain commonly used in South and Western Indian cooking.', 'uses': ['Ragi dosa', 'Ragi mudde', 'Ragi porridge', 'Ragi roti'], 'recipes': ['Ragi Dosa', 'Ragi Mudde', 'Ragi Porridge'], 'nutrients': ['Calcium', 'Fibre', 'Iron', 'Complex carbohydrates'], 'wellness': ['Supports a fibre-rich diet', 'Provides plant-based calcium', 'Useful in balanced breakfast options'], 'facts': ['Naturally gluten-free', 'Pairs well with pulses to build a more balanced meal', 'Calcium values vary by processing and preparation'], 'video': 'https://www.youtube.com/results?search_query=ragi+recipes+Indian', 'source': 'https://www.nin.res.in/'}, {'name': 'Spinach', 'intro': 'Spinach is a leafy green that can be used in dals, sabzis, soups and breads.', 'uses': ['Palak dal', 'Palak paneer', 'Spinach paratha', 'Green smoothie'], 'recipes': ['Palak Dal', 'Palak Paneer', 'Spinach Paratha'], 'nutrients': ['Folate', 'Vitamin K', 'Vitamin A carotenoids', 'Iron'], 'wellness': ['Adds leafy-green vegetables to the diet', 'Supports folate and vitamin K intake', 'Vitamin C-rich foods can complement plant iron absorption'], 'facts': ['Plant iron is non-heme iron', 'Cooking changes volume and nutrient density per serving', 'Lemon or amla can add vitamin C to a spinach meal'], 'video': 'https://www.youtube.com/results?search_query=healthy+Indian+spinach+recipes', 'source': 'https://ods.od.nih.gov/factsheets/Iron-Consumer/'}, {'name': 'Banana', 'intro': 'Banana is an accessible fruit used in breakfast, snacks and several Indian preparations.', 'uses': ['Snack', 'Banana shake', 'Banana dosa', 'Fruit bowl'], 'recipes': ['Banana Oats Bowl', 'Banana Sheera', 'Banana Pancake'], 'nutrients': ['Potassium', 'Vitamin B6', 'Fibre', 'Carbohydrates'], 'wellness': ['Convenient energy source', 'Helps increase fruit intake', 'Pairs with yogurt or nuts for a more balanced snack'], 'facts': ['Ripening changes starch into more simple sugars', 'Potassium contributes to normal muscle and nerve function', 'Portion size matters for total carbohydrate intake'], 'video': 'https://www.youtube.com/results?search_query=healthy+banana+Indian+recipes', 'source': 'https://ods.od.nih.gov/factsheets/Potassium-Consumer/'}, {'name': 'Turmeric', 'intro': 'Turmeric is a yellow spice used in curries, dals, vegetables and traditional preparations.', 'uses': ['Dal', 'Sabzi', 'Haldi milk', 'Rice seasoning'], 'recipes': ['Turmeric Dal', 'Haldi Milk', 'Turmeric Vegetable Roast'], 'nutrients': ['Manganese', 'Iron (small amounts)', 'Plant compounds including curcuminoids'], 'wellness': ['Adds flavour without relying on heavy sauces', 'Helps increase spice variety in meals', 'Curcumin research is ongoing; food use is not a treatment for disease'], 'facts': ["Curcumin is one of turmeric's studied compounds", 'Black pepper and fat can alter curcumin absorption, but food effects are not equivalent to supplements', 'Avoid presenting turmeric as a cure'], 'video': 'https://www.youtube.com/results?search_query=turmeric+Indian+recipes', 'source': 'https://www.nccih.nih.gov/health/turmeric'}, {'name': 'Lentils (Dal)', 'intro': 'Dal is a staple Indian pulse family covering masoor, moong, toor and other varieties.', 'uses': ['Dal tadka', 'Khichdi', 'Dal soup', 'Dal paratha'], 'recipes': ['Dal Tadka', 'Dal Khichdi', 'Moong Dal Chilla'], 'nutrients': ['Protein', 'Fibre', 'Folate', 'Iron', 'Magnesium'], 'wellness': ['Supports plant-protein intake', 'Fibre supports digestive health', 'Pairs with grains to make a balanced meal'], 'facts': ['Different dals have different nutrient profiles', 'Soaking can reduce cooking time', 'Combining pulses with varied grains improves dietary diversity'], 'video': 'https://www.youtube.com/results?search_query=Indian+dal+recipes', 'source': 'https://www.nin.res.in/'}, {'name': 'Curd (Dahi)', 'intro': 'Dahi is a fermented dairy food used in raita, kadhi, marinades and meals.', 'uses': ['Raita', 'Kadhi', 'Lassi', 'Marinade'], 'recipes': ['Cucumber Raita', 'Kadhi', 'Fruit Yogurt Bowl'], 'nutrients': ['Protein', 'Calcium', 'Phosphorus', 'Vitamin B12'], 'wellness': ['Convenient calcium source', 'Adds protein to snacks and meals', 'Fermented foods can contribute to dietary variety'], 'facts': ['Nutrient content depends on milk and preparation', 'Choose unsweetened versions when limiting added sugar', 'People with milk allergy should avoid dairy'], 'video': 'https://www.youtube.com/results?search_query=Indian+dahi+recipes', 'source': 'https://ods.od.nih.gov/factsheets/Calcium-Consumer/'}, {'name': 'Chickpeas (Chana)', 'intro': 'Chickpeas are a versatile pulse used in chole, salads, chaat and roasted snacks.', 'uses': ['Chole', 'Chana salad', 'Chana chaat', 'Roasted chana'], 'recipes': ['Chana Masala', 'Chana Chaat', 'Chana Sundal'], 'nutrients': ['Protein', 'Fibre', 'Folate', 'Iron', 'Magnesium'], 'wellness': ['Helps build protein-rich vegetarian meals', 'High fibre can improve meal satiety', 'Useful base for affordable meals'], 'facts': ['Soaking and cooking improve texture and digestibility', 'Roasted chana is a convenient snack', 'Pair with vitamin C-rich vegetables for dietary iron support'], 'video': 'https://www.youtube.com/results?search_query=Indian+chana+recipes', 'source': 'https://www.nin.res.in/'}, {'name': 'Moringa (Drumstick Leaves)', 'intro': 'Moringa leaves are used in regional Indian cooking and are nutrient-dense leafy greens.', 'uses': ['Moringa dal', 'Leaf stir-fry', 'Soup', 'Chutney'], 'recipes': ['Moringa Dal', 'Moringa Poriyal', 'Moringa Soup'], 'nutrients': ['Beta-carotene', 'Calcium', 'Iron', 'Folate'], 'wellness': ['Adds leafy greens and micronutrients', 'Useful in varied vegetable intake', 'Works well with lentils and grains'], 'facts': ['Nutrient levels vary by plant part and preparation', 'Food use is different from concentrated supplements', 'Wash and cook appropriately'], 'video': 'https://www.youtube.com/results?search_query=moringa+Indian+recipes', 'source': 'https://www.nin.res.in/'}, {'name': 'Peanut', 'intro': 'Peanuts are common in Indian snacks, chutneys, poha and vegetable dishes.', 'uses': ['Peanut chutney', 'Poha', 'Roasted snack', 'Peanut curry'], 'recipes': ['Peanut Chutney', 'Kanda Poha', 'Peanut Sundal'], 'nutrients': ['Protein', 'Healthy unsaturated fats', 'Magnesium', 'Niacin'], 'wellness': ['Adds energy and plant protein', 'Healthy fats can improve meal satiety', 'Useful for budget-friendly nutrition'], 'facts': ['Peanuts are calorie dense', 'Nut/peanut allergy can be severe', 'Unsalted forms are useful when reducing sodium'], 'video': 'https://www.youtube.com/results?search_query=Indian+peanut+recipes', 'source': 'https://ods.od.nih.gov/factsheets/Magnesium-Consumer/'}, {'name': 'Sweet Potato', 'intro': 'Sweet potato is a colourful root vegetable that works in snacks, curries and chaat.', 'uses': ['Roasted snack', 'Chaat', 'Curry', 'Mash'], 'recipes': ['Sweet Potato Chaat', 'Sweet Potato Curry', 'Roasted Sweet Potato'], 'nutrients': ['Beta-carotene', 'Fibre', 'Potassium', 'Vitamin C'], 'wellness': ['Fibre-rich carbohydrate option', 'Orange varieties provide beta-carotene', 'Works as a filling snack with protein'], 'facts': ['Cooking method changes energy density', 'Beta-carotene-rich varieties are orange or yellow', 'Pair with protein for a more balanced snack'], 'video': 'https://www.youtube.com/results?search_query=Indian+sweet+potato+recipes', 'source': 'https://ods.od.nih.gov/factsheets/VitaminA-Consumer/'}, {'name': 'Sesame Seeds (Til)', 'intro': 'Sesame is a traditional Indian seed used in chutneys, sweets and savoury dishes.', 'uses': ['Til chutney', 'Til-gul', 'Laddoo', 'Vegetable topping'], 'recipes': ['Til Chutney', 'Til-Gul Ladoo', 'Sesame Vegetable Stir-fry'], 'nutrients': ['Calcium', 'Magnesium', 'Healthy fats', 'Protein'], 'wellness': ['Adds mineral-rich seeds to meals', 'Useful plant-protein and healthy-fat addition', 'Small portions add flavour and energy'], 'facts': ['Seeds are energy dense', 'Calcium content varies with processing', 'Sesame is a common allergen'], 'video': 'https://www.youtube.com/results?search_query=Indian+sesame+til+recipes', 'source': 'https://ods.od.nih.gov/factsheets/Calcium-Consumer/'}]

SMART_MEAL_DB = {
    "weight-loss": {
        "label": "Balanced Weight Loss",
        "breakfast": ["Vegetable poha + curd", "Moong chilla + mint chutney", "Idli + sambar"],
        "lunch": ["2 phulka + dal + sabzi + salad", "Jowar bhakri + pithla + vegetables", "Rice + rajma + cucumber raita"],
        "snack": ["Fruit + roasted chana", "Buttermilk + peanuts", "Sprouts chaat"],
        "dinner": ["Moong khichdi + vegetables", "2 phulka + paneer/soy sabzi", "Vegetable dal soup + roti"]
    },
    "weight-gain": {
        "label": "Healthy Weight Gain",
        "breakfast": ["Stuffed paneer paratha + curd", "Banana oats bowl + nuts", "Poha + peanuts + milk"],
        "lunch": ["Rice + dal + ghee + vegetables + curd", "Bhakri + pithla + potato/vegetable + buttermilk", "Rajma chawal + raita"],
        "snack": ["Banana + peanut chikki", "Milk + dates + nuts", "Paneer sandwich"],
        "dinner": ["Khichdi + ghee + curd", "Roti + dal + paneer + vegetables", "Rice + chana + vegetable"]
    },
    "balanced": {
        "label": "Everyday Balanced Plate",
        "breakfast": ["Vegetable upma + curd", "Idli + sambar + fruit", "Poha + sprouts + lemon"],
        "lunch": ["Roti + dal + 2 vegetables + salad", "Rice + sambar + poriyal + curd", "Bhakri + usal + vegetable + chaas"],
        "snack": ["Fruit + nuts", "Roasted chana + buttermilk", "Sprouts chaat"],
        "dinner": ["Dal khichdi + vegetables", "Roti + dal + sabzi", "Millet roti + mixed dal + salad"]
    },
    "high-protein": {
        "label": "Higher-Protein Indian Plate",
        "breakfast": ["Moong chilla + paneer", "Egg bhurji + roti + curd", "Besan chilla + sprouts"],
        "lunch": ["Dal + paneer + roti + salad", "Rajma + rice + curd", "Chole + roti + vegetables"],
        "snack": ["Roasted chana + curd", "Milk + peanuts", "Sprouts + paneer cubes"],
        "dinner": ["Soy/paneer bhurji + roti", "Dal + egg curry + rice", "Moong khichdi + curd + salad"]
    }
}

@app.route("/regional-food")
def regional_food():
    return render_template("regional_food.html", regional_json=json.dumps(REGIONAL_FOOD_DB, ensure_ascii=False))

@app.route("/kitchen")
def kitchen():
    return render_template("kitchen.html", kitchen_json=json.dumps(KITCHEN_RECIPE_DB, ensure_ascii=False))

@app.route("/one-food")
def one_food():
    return render_template("one_food.html", foods_json=json.dumps(ONE_FOOD_DB, ensure_ascii=False))

@app.route("/smart-meal-planner", methods=["GET", "POST"])
def smart_meal_planner():
    goal = request.form.get("goal", "balanced") if request.method == "POST" else request.args.get("goal", "balanced")
    diet = request.form.get("diet", "vegetarian") if request.method == "POST" else request.args.get("diet", "vegetarian")
    state = request.form.get("state", "Maharashtra") if request.method == "POST" else request.args.get("state", "Maharashtra")
    plan = SMART_MEAL_DB.get(goal, SMART_MEAL_DB["balanced"])
    state_foods = REGIONAL_FOOD_DB.get(state, REGIONAL_FOOD_DB["Maharashtra"])
    return render_template(
        "smart_meal_planner.html",
        plan=plan,
        goal=goal,
        diet=diet,
        state=state,
        regional_foods=state_foods,
        states=sorted(REGIONAL_FOOD_DB.keys())
    )

@app.route("/api/food-intelligence")
def food_intelligence_api():
    return jsonify({
        "regional": REGIONAL_FOOD_DB,
        "kitchen": KITCHEN_RECIPE_DB,
        "one_food": ONE_FOOD_DB
    })

# =======================
# ADMIN — view all user data, assessments & feedback in one place
# =======================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("is_admin"):
        return redirect(url_for("admin_panel"))

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["is_admin"] = True
            return redirect(url_for("admin_panel"))
        flash("Invalid admin credentials.", "error")

    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect(url_for("admin_login"))

@app.route("/admin")
@admin_required
def admin_panel():
    db = get_db()
    users = db.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    assessments = db.execute(
        """SELECT a.*, u.name AS user_name, u.email AS user_email
           FROM assessments a JOIN users u ON a.user_id = u.id
           ORDER BY a.created_at DESC"""
    ).fetchall()
    feedback_rows = db.execute(
        "SELECT * FROM feedback ORDER BY created_at DESC"
    ).fetchall()

    return render_template(
        "admin.html",
        users=users,
        assessments=assessments,
        feedback_rows=feedback_rows,
        total_users=len(users),
        total_assessments=len(assessments),
        total_feedback=len(feedback_rows)
    )

# =======================
init_db()
_migrate_history()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
