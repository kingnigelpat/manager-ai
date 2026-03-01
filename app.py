from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, send_from_directory, Response, abort
import sqlite3
import random
import os
import json
import time
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps

import firebase_admin
from firebase_admin import credentials, auth

import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import timedelta
from flask_talisman import Talisman
from dotenv import load_dotenv

# Load environment variables at the very beginning
load_dotenv()

# Universal Project Root (For VPS absolute paths)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
# Security: Session & Cookies
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SESSION_COOKIE_HTTPONLY'] = True
# Detect if we should use secure cookies (default True in production)
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'True').lower() == 'true'
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Security Headers (Talisman)
# Note: inclusive CSP to allow Firebase, Cloudinary and external fonts/scripts
csp = {
    'default-src': '\'self\'',
    'script-src': [
        '\'self\'',
        'https://cdn.jsdelivr.net',
        'https://cdnjs.cloudflare.com',
        'https://www.gstatic.com',
        'https://apis.google.com',
        '\'unsafe-inline\'',
        '\'unsafe-eval\''
    ],
    'style-src': [
        '\'self\'',
        'https://fonts.googleapis.com',
        'https://cdnjs.cloudflare.com',
        'https://cdn.jsdelivr.net',
        '\'unsafe-inline\''
    ],
    'font-src': [
        '\'self\'',
        'https://fonts.gstatic.com',
        'https://cdnjs.cloudflare.com'
    ],
    'img-src': [
        '\'self\'',
        'data:',
        'https://res.cloudinary.com',
        'https://www.gstatic.com',
        'https://*.firebaseapp.com'
    ],
    'connect-src': [
        '\'self\'',
        'https://*.googleapis.com',
        'https://*.firebaseapp.com',
        'https://*.firebasestorage.app',
        'https://ipapi.co',
        'https://res.cloudinary.com',
        'https://openrouter.ai'
    ],
    'frame-src': [
        '\'self\'',
        'https://*.firebaseapp.com'
    ]
}
# VPS Ready: Detect if HTTPS should be forced (off for local testing, on for VPS with SSL)
force_https = os.getenv('FORCE_HTTPS', 'False').lower() == 'true'
Talisman(app, content_security_policy=csp, force_https=force_https)

# Rate Limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Cloudinary Configuration
cloudinary.config(
    cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key = os.getenv('CLOUDINARY_API_KEY'),
    api_secret = os.getenv('CLOUDINARY_API_SECRET'),
    secure = True
)
# app.secret_key set below
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize Firebase (Using Absolute Path)
service_account_path = os.path.join(BASE_DIR, 'serviceAccountKey.json')
cred = credentials.Certificate(service_account_path)
firebase_admin.initialize_app(cred)

# Database setup (Using Absolute Path)
DB_NAME = os.path.join(BASE_DIR, 'content_ideas.db')

def init_db():
    print(f"Initializing database: {DB_NAME}...")
    conn = sqlite3.connect(DB_NAME, timeout=10)
    c = conn.cursor()
    # User table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password_hash TEXT NOT NULL)''')
    
    # Table to store generated ideas
    c.execute('''CREATE TABLE IF NOT EXISTS ideas
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  business_type TEXT,
                  idea_content TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')

    # Submissions table for payments
    c.execute('''CREATE TABLE IF NOT EXISTS submissions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  username TEXT,
                  full_name TEXT,
                  plan_type TEXT,
                  screenshot_path TEXT,
                  status TEXT DEFAULT 'pending',
                  admin_note TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')
                  
    # Check if user_id column exists in ideas table (for migration)
    c.execute("PRAGMA table_info(ideas)")
    columns = [column[1] for column in c.fetchall()]
    if 'user_id' not in columns:
        try:
            c.execute("ALTER TABLE ideas ADD COLUMN user_id INTEGER REFERENCES users(id)")
        except Exception as e:
            print(f"Migration warning: {e}")

    # Check for columns in users table
    c.execute("PRAGMA table_info(users)")
    user_columns = [column[1] for column in c.fetchall()]
    
    if 'is_subscribed' not in user_columns:
        try:
            c.execute("ALTER TABLE users ADD COLUMN is_subscribed BOOLEAN DEFAULT 0")
        except Exception as e:
            print(f"Migration warning (users - is_subscribed): {e}")

    if 'is_admin' not in user_columns:
        try:
            c.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0")
        except Exception as e:
            print(f"Migration warning (users - is_admin): {e}")

    if 'subscription_start' not in user_columns:
        try:
            c.execute("ALTER TABLE users ADD COLUMN subscription_start DATETIME")
        except Exception as e:
            print(f"Migration warning (users - subscription_start): {e}")

    if 'plan_type' not in user_columns:
        try:
            c.execute("ALTER TABLE users ADD COLUMN plan_type TEXT DEFAULT 'free'")
        except Exception as e:
            print(f"Migration warning (users - plan_type): {e}")

    if 'brand_tone' not in user_columns:
        try:
            c.execute("ALTER TABLE users ADD COLUMN brand_tone TEXT")
        except Exception as e:
            print(f"Migration warning (users - brand_tone): {e}")

    # Table for preferred payment requests (Can't pay with bank)
    c.execute('''CREATE TABLE IF NOT EXISTS payment_requests
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  username TEXT,
                  plan_type TEXT,
                  preferred_method TEXT,
                  contact_method TEXT,
                  contact_info TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')

    # Migration for payment_requests (ensure ALL columns exist)
    c.execute("PRAGMA table_info(payment_requests)")
    pr_columns = [column[1] for column in c.fetchall()]
    
    # Check for missing columns in payment_requests
    migrations = [
        ('plan_type', "ALTER TABLE payment_requests ADD COLUMN plan_type TEXT"),
        ('contact_method', "ALTER TABLE payment_requests ADD COLUMN contact_method TEXT"),
        ('contact_info', "ALTER TABLE payment_requests ADD COLUMN contact_info TEXT")
    ]
    
    for col_name, alter_stmt in migrations:
        if col_name not in pr_columns:
            try:
                c.execute(alter_stmt)
            except Exception as e:
                print(f"Migration warning (payment_requests - {col_name}): {e}")

    conn.commit()
    conn.close()

from openai import OpenAI
# load_dotenv() moved to top

# --- REAL AI INTEGRATION ---
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENAI_API_KEY")
)

class AI_Engine:
    def generate(self, business_type, platform, mood, goal, people, language, existing_ideas, location=None, refinement=None, previous_idea=None, brand_tone=None):
        # Determine language style
        lang_instruction = "SPEAK IN VERY SIMPLE, BEGINNER ENGLISH (A1/A2 level). Use short sentences. Use simple words. No big grammar."
        if language == 'pidgin':
            lang_instruction = "SPEAK IN NIGERIAN PIDGIN ENGLISH. Make it sound authentic, street-smart, and relatable to Nigerians. Use words like 'abeg', 'wetin', 'na so', 'ginger'."
        elif language == 'standard':
            lang_instruction = "SPEAK IN STANDARD PROFESSIONAL ENGLISH. Be clear, concise, and business-appropriate, but still engaging."

        # Universal Strategist Persona
        system_prompt = (
            "You are a world-class Global Content Strategist and Growth Marketer. "
            "You possess 'Cultural Intelligence'—the ability to identify and leverage regional trends, "
            "slang, and psychological triggers for any location while maintaining a professional standard. "
            "Your goal is to create viral, high-converting content that turns casual viewers into loyal customers. "
            f"{lang_instruction} "
            "Always be practical, trend-aware, and laser-focused on growth. Do not be generic."
        )
        
        if brand_tone:
            system_prompt += f"\n\nIMPORTANT BRAND TONE GUIDELINE: {brand_tone}. Always ensure the content matches this specific style and voice."

        base_prompt = f"""
        Business Type: {business_type}
        Platform: {platform}
        Target Location/Audience: {location or 'Global'}
        Tone/Mood: {mood}
        Campaign Objective: {goal}
        Personnel in video: {people}
        """

        if refinement and previous_idea:
            user_prompt = f"""
            {base_prompt}

            PREVIOUS IDEA GENERATED:
            {previous_idea}

            USER FEEDBACK / REQUEST:
            "{refinement}"

            TASK:
            Generate a REFINED video/content idea that addresses the user's feedback.
            Do NOT simply repeat the previous idea. Make the specific changes requested.
            
            Format your answer using Markdown with clear headers (###):

            ### 👑 THE BIG IDEA
            (Write 1 sentence about the video).

            ### 📋 STEP-BY-STEP (How do I do it?)
            1. [Step 1]
            2. [Step 2]
            3. [Step 3]
            4. [Step 4]

            ### 💡 PRO TIP (To make it sweet)
            (One simple advice).

            ### ✍️ CAPTION
            (Write a catchy caption).

            ### #️⃣ HASHTAGS
            (5-10 hashtags).

            ### ⏰ BEST TIME TO POST
            (Best time to post).

            Remember: {lang_instruction}
            """
        else:
            user_prompt = f"""
            {base_prompt}

            Give me ONE video/content idea optimized for {platform}.

            Format your answer using Markdown with clear headers (###):

            ### 👑 THE BIG IDEA
            (Write 1 sentence about the video).

            ### 📋 STEP-BY-STEP (How do I do it?)
            1. [Step 1]
            2. [Step 2]
            3. [Step 3]
            4. [Step 4]

            ### 💡 PRO TIP (To make it sweet)
            (One simple advice).

            ### ✍️ CAPTION
            (Write a catchy caption).

            ### #️⃣ HASHTAGS
            (5-10 hashtags).

            ### ⏰ BEST TIME TO POST
            (Best time to post).

            Remember: {lang_instruction}
            AVOID these ideas: {json.dumps(existing_ideas)}
            """
        
        try:
            response = client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "http://localhost:5000",
                    "X-Title": "ContentIdeaApp",
                },
                model="google/gemini-2.0-flash-001",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"AI API Error: {e}")
            import traceback
            traceback.print_exc()
            return f"A {mood} video showcasing your {business_type} to help {goal}. (Backup: AI service temporarily unavailable)"

    def generate_weekly_plan(self, business_type, platform, language, location=None, brand_tone=None):
        lang_instruction = "Use simple English."
        if language == 'pidgin':
            lang_instruction = "Use Naija Pidgin Style."
        elif language == 'standard':
            lang_instruction = "Use Standard Professional English."

        system_prompt = f"You are a Senior Strategic Planner. Create a 7-day social media roadmap. Target Location: {location or 'Global'}. {lang_instruction}"
        if brand_tone:
            system_prompt += f" Brand Voice Guide: {brand_tone}"

        user_prompt = f"""
    Create a 7-day content plan for a {business_type} on {platform} targeting an audience in {location or 'a Global market'}. 
    
    FORMAT REQUIREMENT:
    Return a Markdown TABLE with headers: | Day | Content Type | The Big Idea | Why it works |
    
    Make each day different (e.g. Tutorial, Behind the scenes, Educational, Promotion, etc.).
    Under the table, add a brief 1-sentence strategic summary for the week.
    """
        
        try:
            response = client.chat.completions.create(
                model="google/gemini-2.0-flash-001",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return "Unable to generate weekly plan right now."

    def optimize_cta(self, current_content, platform, language, brand_tone=None):
        system_prompt = f"You are a Copywriting Expert. Your job is to rewrite the Call to Action (CTA) of a post to increase sales. Use {language}."
        if brand_tone:
            system_prompt += f" Brand Tone: {brand_tone}"

        user_prompt = f"Here is the content: '{current_content}'. Platform: {platform}. Give me 3 high-converting versions of a CTA for this. Format as a clean bulleted list using Markdown."
        
        try:
            response = client.chat.completions.create(
                model="google/gemini-2.0-flash-001",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return "Unable to optimize CTA right now."

    def rewrite_hook(self, current_content, platform, language, brand_tone=None):
        system_prompt = f"You are a Viral Content Specialist. Rewrite the 'Hook' (first 3 seconds/lines) of this content to stop people from scrolling. Use {language}."
        if brand_tone:
            system_prompt += f" Brand Tone: {brand_tone}"

        user_prompt = f"Content: '{current_content}'. Platform: {platform}. Give me 3 viral hooks for this. Format as a clean numbered list using Markdown."
        
        try:
            response = client.chat.completions.create(
                model="google/gemini-2.0-flash-001",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return "Unable to rewrite hooks right now."

    def support_chat(self, user_question, history=None):
        system_prompt = """
        You are 'Rae', the official Support AI for Manager AI.
        Manager AI is an AI-powered content strategist tool for social media growth.
        
        KEY INFO:
        - 3 Plans: 
          1. Starter: 5,000 Naira/month (10 generations per week).
          2. Pro: 25,000 Naira/month (Unlimited generations, Pro tools).
          3. Business: 75,000 Naira/month (Priority, Brand Tone memory).
        - Features: Big Idea generation, 7-Day Content Plan, CTA Optimizer, Hook Rewriter.
        - Payment: Users pay via GTB (Bank Transfer or Card) then upload a receipt screenshot in the 'Billing' section. An admin verifies it.
        - Alternative Payments: If a user can't pay via GTB, they can click 'Request Another Method' in the pricing modal.
        - Redirection: If you cannot solve the user's problem or they explicitly want to speak to a human, tell them to click the 'Talk to Human' button in the chat interface.
        - The 'Talk to Human' button will redirect them to our Instagram: https://www.instagram.com/rae__hub
        
        GUIDELINES:
        - Be friendly, professional, and concise. 
        - Use a helpful, encouraging tone.
        - If the user asks about something unrelated to Manager AI, politely bring them back to the topic.
        """
        
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            # history should be a list of {"role": "user/assistant", "content": "..."}
            messages.extend(history[-10:]) # Keep last 10 messages for context
        messages.append({"role": "user", "content": user_question})
        
        try:
            response = client.chat.completions.create(
                model="google/gemini-2.0-flash-001",
                messages=messages
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Support AI Error: {e}")
            return "Hi there! I'm having a small technical issue. Please try again or head over to our Instagram @rae__hub and send us a DM if you need urgent help!"

ai_engine = AI_Engine()

# Login Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

app.secret_key = os.getenv('SECRET_KEY', 'default_dev_key')
# app.config['UPLOAD_FOLDER'] already set at top

# PIN Rate Limiter
PIN_ATTEMPTS = {}  # {user_id: [timestamp, count]}
PIN_LOCKOUT_TIME = 300  # 5 minutes
MAX_PIN_ATTEMPTS = 5

# Admin Decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            flash('Access denied. Admins only.')
            return redirect(url_for('dashboard'))
        
        # Check if admin is authenticated with PIN
        if not session.get('admin_authenticated'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def admin_login():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('dashboard'))
        
    user_id = session['user_id']
    current_time = time.time()
    
    # Check lockout
    if user_id in PIN_ATTEMPTS:
        last_time, count = PIN_ATTEMPTS[user_id]
        if count >= MAX_PIN_ATTEMPTS:
            if current_time - last_time < PIN_LOCKOUT_TIME:
                flash(f'Too many attempts. Please wait {int((PIN_LOCKOUT_TIME - (current_time - last_time)) / 60)} minutes.')
                return render_template('admin_login.html')
            else:
                # Reset after lockout expires
                PIN_ATTEMPTS[user_id] = [current_time, 0]

    if request.method == 'POST':
        pin = request.form.get('pin', '').strip()
        # Hardcode fallback for online reliability
        correct_pin = os.getenv('ADMIN_PIN', 'Olyviamywife2324').strip()
        
        if pin == correct_pin:
            session['admin_authenticated'] = True
            # Clear attempts on success
            if user_id in PIN_ATTEMPTS:
                del PIN_ATTEMPTS[user_id]
            return redirect(url_for('admin_dashboard'))
        else:
            # Increment attempts
            if user_id in PIN_ATTEMPTS:
                PIN_ATTEMPTS[user_id] = [current_time, PIN_ATTEMPTS[user_id][1] + 1]
            else:
                PIN_ATTEMPTS[user_id] = [current_time, 1]
                
            flash('Incorrect Admin PIN')
            
    return render_template('admin_login.html')

@app.route('/')
def intro():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('intro.html')

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if request.method == 'POST':
        # FIREBASE LOGIN LOGIC
        data = request.get_json(silent=True) or {}
        id_token = data.get('idToken')
        if not id_token:
            return jsonify({"error": "No token provided"}), 400
        
        try:
            # Verify Firebase Token with Retry for network issues
            decoded_token = None
            for attempt in range(3):
                try:
                    # check_revoked=False is faster and avoids one extra network call
                    decoded_token = auth.verify_id_token(id_token, check_revoked=False)
                    break
                except Exception as e:
                    if attempt == 2: raise e
                    print(f"Auth attempt {attempt+1} failed: {e}. Retrying...")
                    time.sleep(1)
            
            uid = decoded_token['uid']
            email = decoded_token.get('email')
            # Extract username from email or metadata if possible, else default
            # For now, we will use the email prefix as username if not set
            username = email.split('@')[0] if email else f"user_{uid[:6]}"
            
            # Sync with Local DB
            conn = sqlite3.connect(DB_NAME, timeout=10)
            c = conn.cursor()
            
            c.execute("SELECT id, is_subscribed, is_admin FROM users WHERE username = ?", (username,))
            user_row = c.fetchone()
            
            if not user_row:
                # First time login = Register in local DB
                # Password hash is not needed anymore, can be empty or 'firebase'
                c.execute("INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)", 
                          (username, 'firebase_managed', 0))
                conn.commit()
                # Fetch new ID
                c.execute("SELECT id, is_subscribed, is_admin FROM users WHERE username = ?", (username,))
                user_row = c.fetchone()
            
            conn.close()
            
            # Set Session
            session['user_id'] = user_row[0]
            session['username'] = username
            session['is_subscribed'] = bool(user_row[1])
            
            # GOD MODE ADMIN CHECK: Grant patricknigel33@gmail.com full privileges
            is_god_admin = (email == 'patricknigel33@gmail.com')
            session['is_admin'] = is_god_admin
            
            # Always ensure God Admin is subscribed and on Business Plan in the Session
            if is_god_admin:
                session['is_subscribed'] = True
                session['plan_type'] = 'business'
            
            # Ensure DB reflects this (self-correcting security & access)
            conn = sqlite3.connect(DB_NAME, timeout=10)
            c = conn.cursor()
            
            # 1. Update Admin status
            if is_god_admin != bool(user_row[2]):
                c.execute("UPDATE users SET is_admin = ? WHERE id = ?", (1 if is_god_admin else 0, user_row[0]))
            
            # 2. Grant God Admin the Business Plan if they don't have it
            if is_god_admin:
                c.execute("UPDATE users SET is_subscribed = 1, plan_type = 'business' WHERE id = ?", (user_row[0],))
                
            conn.commit()
            conn.close()

            session['firebase_uid'] = uid # Store Firebase UID for future reference
            
            # If Admin, let frontend know so it can ask which dashboard to go to
            return jsonify({
                "success": True, 
                "redirect": url_for('dashboard'),
                "is_admin": is_god_admin
            })
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Firebase Auth Error: {e}\nDetailed Traceback:\n{error_details}")
            
            # If it's a network issue specifically (RemoteDisconnected/ConnectionError)
            if 'Connection' in str(e) or 'Remote' in str(e):
                return jsonify({"error": "AUTH_NETWORK_ERROR", "message": "The server had trouble connecting to Google's authentication service. Please try again or check your ISP/Firewall."}), 503
                
            return jsonify({"error": "Invalid token", "message": str(e)}), 401
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Registration is now handled primarily on client side via Firebase
    # This route just serves the page or handles redirects
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('intro'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    conn = sqlite3.connect(DB_NAME, timeout=10)
    c = conn.cursor()
    c.execute("SELECT plan_type, brand_tone FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    
    plan_type = row[0] if row else 'free'
    brand_tone = row[1] if row else ''
    
    return render_template('index.html', 
                           username=session.get('username'), 
                           is_subscribed=session.get('is_subscribed'),
                           plan_type=plan_type,
                           brand_tone=brand_tone)

@app.route('/pricing')
@login_required
def pricing():
    return render_template('pricing.html')

@app.route('/plan/<plan_name>')
@login_required
def choose_plan(plan_name):
    currency = request.args.get('currency', '₦')
    amount = request.args.get('amount')
    
    # Mapping plan URL parts to display names and default prices
    plans = {
        'starter': {'name': 'Starter Plan', 'price': '₦5,000'},
        'pro': {'name': 'Pro Plan', 'price': '₦25,000'},
        'business': {'name': 'Business Plan', 'price': '₦75,000'}
    }
    
    plan_info = plans.get(plan_name.lower())
    if not plan_info:
        flash("Invalid plan selected")
        return redirect(url_for('pricing'))
    
    # Use dynamic price if provided
    display_price = f"{currency}{amount}" if amount else plan_info['price']
        
    return render_template('payment.html', plan=plan_info['name'], plan_id=plan_name.lower(), price=display_price, username=session.get('username'))

@app.route('/submit_payment', methods=['POST'])
@login_required
@limiter.limit("3 per minute")
def submit_payment():
    # Security: Limit file size to 5MB
    if request.content_length > 5 * 1024 * 1024:
        flash('File too large. Maximum size is 5MB.')
        return redirect(request.url)

    if 'screenshot' not in request.files:
        flash('No file part')
        return redirect(request.url)
    
    file = request.files['screenshot']
    full_name = request.form.get('full_name')
    app_username = request.form.get('app_username')
    plan_id = request.form.get('plan_id', 'starter') # Default to starter
    
    plan_names = {
        'starter': 'Starter Plan',
        'pro': 'Pro Plan',
        'business': 'Business Plan'
    }
    plan_display_name = plan_names.get(plan_id, 'Starter Plan')

    if not full_name:
         flash('Please enter your full name')
         return redirect(request.url)

    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)

    if file:
        try:
            # Upload to Cloudinary
            upload_result = cloudinary.uploader.upload(
                file,
                folder="manager_ai_payments/",
                resource_type="image"
            )
            screenshot_url = upload_result.get('secure_url')
            
            target_user_id = session['user_id']
            
            conn = sqlite3.connect(DB_NAME, timeout=10)
            c = conn.cursor()
            c.execute('''INSERT INTO submissions (user_id, username, full_name, plan_type, screenshot_path)
                         VALUES (?, ?, ?, ?, ?)''', 
                      (target_user_id, app_username, full_name, plan_id, screenshot_url))
            conn.commit()
            conn.close()
            
            return render_template('payment_success.html')
        except Exception as e:
            flash(f"Upload failed: {str(e)}")
            return redirect(request.url)

@app.route('/uploads/<filename>')
@login_required 
def uploaded_file(filename):
    if not session.get('is_admin'):
         return "Access Denied", 403
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/admin')
@admin_required
def admin_dashboard():
    conn = sqlite3.connect(DB_NAME, timeout=10)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT id, username, full_name, plan_type, screenshot_path, timestamp, status FROM submissions WHERE status = 'pending' ORDER BY timestamp DESC")
    submissions = c.fetchall()
    
    c.execute("SELECT id, username, full_name, plan_type, status, timestamp FROM submissions WHERE status != 'pending' ORDER BY timestamp DESC LIMIT 20")
    history = c.fetchall()
    
    # Get all users with subscription details
    c.execute("SELECT id, username, is_subscribed, subscription_start, plan_type FROM users")
    users = c.fetchall()
    
    # Get preferred payment requests
    c.execute("SELECT id, username, plan_type, preferred_method, contact_method, contact_info, timestamp FROM payment_requests ORDER BY timestamp DESC")
    payment_requests = c.fetchall()
    
    conn.close()
    return render_template('admin.html', submissions=submissions, history=history, users=users, payment_requests=payment_requests)

@app.route('/admin/approve/<int:submission_id>')
@admin_required
def approve_submission(submission_id):
    conn = sqlite3.connect(DB_NAME, timeout=10)
    c = conn.cursor()
    
    c.execute("SELECT user_id, plan_type FROM submissions WHERE id = ?", (submission_id,))
    sub = c.fetchone()
    
    if sub:
        user_id = sub[0]
        plan_type = sub[1]
        c.execute("UPDATE submissions SET status = 'approved' WHERE id = ?", (submission_id,))
        # Set is_subscribed = 1, set start date to now, and set the plan_type
        c.execute("""UPDATE users 
                     SET is_subscribed = 1, 
                         subscription_start = CURRENT_TIMESTAMP, 
                         plan_type = ? 
                     WHERE id = ?""", (plan_type, user_id))
        conn.commit()
        flash(f'Submission {submission_id} approved and user {user_id} credited with {plan_type}.')
    else:
        flash('Submission not found.')
        
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/api/save_brand_tone', methods=['POST'])
@login_required
def save_brand_tone():
    user_id = session['user_id']
    data = request.get_json(silent=True) or {}
    brand_tone = data.get('brandTone', '').strip()
    
    if not brand_tone:
        return jsonify({"error": "Brand tone description is required"}), 400
        
    conn = sqlite3.connect(DB_NAME, timeout=10)
    try:
        c = conn.cursor()
        # Check if user is on Business plan
        c.execute("SELECT plan_type FROM users WHERE id = ?", (user_id,))
        row = c.fetchone()
        plan_type = row[0] if row else 'free'
        
        if plan_type != 'business':
            return jsonify({"error": "Business plan required to save brand tone"}), 403
            
        c.execute("UPDATE users SET brand_tone = ? WHERE id = ?", (brand_tone, user_id))
        conn.commit()
        return jsonify({"success": True, "message": "Brand tone saved!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/notify_payment_method', methods=['POST'])
@login_required
def notify_payment_method():
    user_id = session['user_id']
    username = session.get('username')
    data = request.get_json(silent=True) or {}
    method = data.get('method', '').strip()
    contact_method = data.get('contact_method', 'email').strip()
    contact_info = data.get('contact_info', '').strip()
    plan = data.get('plan', 'starter').strip()
    
    if not method or not contact_info:
        return jsonify({"success": False, "error": "All fields required"}), 400
        
    conn = sqlite3.connect(DB_NAME, timeout=10)
    try:
        c = conn.cursor()
        c.execute("INSERT INTO payment_requests (user_id, username, plan_type, preferred_method, contact_method, contact_info) VALUES (?, ?, ?, ?, ?, ?)",
                  (user_id, username, plan, method, contact_method, contact_info))
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error saving payment request: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()

@app.route('/admin/reject/<int:submission_id>')
@admin_required
def reject_submission(submission_id):
    conn = sqlite3.connect(DB_NAME, timeout=10)
    c = conn.cursor()
    c.execute("UPDATE submissions SET status = 'rejected' WHERE id = ?", (submission_id,))
    conn.commit()
    conn.close()
    flash(f'Submission {submission_id} rejected.')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/terminate/<int:user_id>')
@admin_required
def terminate_plan(user_id):
    conn = sqlite3.connect(DB_NAME, timeout=10)
    c = conn.cursor()
    c.execute("UPDATE users SET is_subscribed = 0, subscription_start = NULL, plan_type = 'free' WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    flash(f'Plan terminated for User ID {user_id}.')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_user/<int:user_id>')
@admin_required
def delete_user(user_id):
    if user_id == session.get('user_id'):
         flash('You cannot delete your own admin account.')
         return redirect(url_for('admin_dashboard'))

    conn = sqlite3.connect(DB_NAME, timeout=10)
    c = conn.cursor()
    # Delete related data first
    c.execute("DELETE FROM ideas WHERE user_id = ?", (user_id,))
    c.execute("DELETE FROM submissions WHERE user_id = ?", (user_id,))
    # Delete user
    c.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    flash(f'User ID {user_id} and all their data have been permanently deleted.')
    return redirect(url_for('admin_dashboard'))

@app.route('/api/check_status', methods=['GET'])
def check_status():
    is_subscribed = session.get('is_subscribed', False)
    
    trial_used = False
    if 'user_id' in session and not is_subscribed:
        try:
            conn = sqlite3.connect(DB_NAME, timeout=10)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM ideas WHERE user_id = ?", (session['user_id'],))
            count = c.fetchone()[0]
            conn.close()
            if count >= 1:
                trial_used = True
        except Exception as e:
            print(f"Error check_status: {e}")
            
    return jsonify({"subscribed": is_subscribed, "trial_used": trial_used})

@app.route('/api/subscribe', methods=['POST'])
@login_required
def subscribe():
    return jsonify({"redirect": url_for('pricing')})

@app.route('/api/generate', methods=['POST'])
@login_required
@limiter.limit("5 per minute")
def generate_idea():
    data = request.get_json(silent=True) or {}
    business_type = data.get('businessType', '').strip()
    platform = data.get('platform', 'instagram').strip()
    if platform == 'instagram_tiktok':
        platform = 'Instagram and TikTok'
        
    mood = data.get('mood', 'neutral').strip()
    goal = data.get('goal', 'engage').strip()
    people = data.get('people', 'solo').strip()
    language = data.get('language', 'simple').strip()
    location = data.get('location', 'Global').strip()
    refinement = data.get('refinement', '').strip()
    previous_idea = data.get('previous_idea', '').strip()
    
    # New Pro tools fields
    mode = data.get('mode', 'idea') # 'idea', 'weekly_plan', 'cta', 'hook'
    content_to_optimize = data.get('content', '').strip()

    if mode == 'idea' and not business_type:
        return jsonify({"error": "Business type is required"}), 400

    user_id = session['user_id']
    conn = sqlite3.connect(DB_NAME, timeout=10)
    try:
        c = conn.cursor()
        
        # Get user plan and brand tone
        c.execute("SELECT is_subscribed, plan_type, brand_tone, is_admin FROM users WHERE id = ?", (user_id,))
        user_info = c.fetchone()
        is_subscribed = user_info[0]
        plan_type = user_info[1] or 'free'
        brand_tone = user_info[2]
        is_admin = bool(user_info[3])

        # Check limits (Bypassed for Admins)
        if not is_admin:
            if not is_subscribed:
                c.execute("SELECT COUNT(*) FROM ideas WHERE user_id = ?", (user_id,))
                usage_count = c.fetchone()[0]
                if usage_count >= 1 and not refinement:
                    return jsonify({"error": "LIMIT_REACHED", "message": "Free trial expired. Please upgrade to the Starter Plan."}), 403
            
            elif plan_type == 'starter':
                # 10 generations per week
                c.execute("SELECT COUNT(*) FROM ideas WHERE user_id = ? AND timestamp > datetime('now', '-7 days')", (user_id,))
                usage_count = c.fetchone()[0]
                if usage_count >= 10 and not refinement:
                    return jsonify({"error": "LIMIT_REACHED", "message": "You've reached your 10 generations limit for the week. Upgrade to Pro for unlimited!"}), 403
            
            # Pro/Business tools restriction
            if mode in ['weekly_plan', 'cta', 'hook'] and plan_type not in ['pro', 'business']:
                 return jsonify({"error": "UPGRADE_REQUIRED", "message": "This tool is only available on Pro and Business plans."}), 403

        result = ""
        if mode == 'idea':
            c.execute("SELECT idea_content FROM ideas WHERE business_type = ? AND user_id = ?", (business_type, user_id))
            past_ideas = [row[0] for row in c.fetchall()]
            result = ai_engine.generate(business_type, platform, mood, goal, people, language, past_ideas, location, refinement, previous_idea, brand_tone)
            # Store generation only for 'idea' mode
            c.execute("INSERT INTO ideas (user_id, business_type, idea_content) VALUES (?, ?, ?)", (user_id, business_type, result))
            conn.commit()
        elif mode == 'weekly_plan':
            result = ai_engine.generate_weekly_plan(business_type, platform, language, location, brand_tone)
        elif mode == 'cta':
            result = ai_engine.optimize_cta(content_to_optimize, platform, language, brand_tone)
        elif mode == 'hook':
            result = ai_engine.rewrite_hook(content_to_optimize, platform, language, brand_tone)
        
        return jsonify({"idea": result})
    except Exception as e:
        print(f"Error generating content: {e}")
        return jsonify({"error": "Server Error", "message": str(e)}), 500
    finally:
        conn.close()

# Error Handlers to prevent information leakage
@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({"error": "TOO_MANY_REQUESTS", "message": "Slow down! You're making requests too fast."}), 429

@app.errorhandler(500)
def internal_error(e):
    original_exception = getattr(e, 'original_exception', e)
    print(f"CRITICAL 500 ERROR: {original_exception}")
    return jsonify({
        "error": "SERVER_ERROR", 
        "message": f"Something went wrong on our end. Error: {str(original_exception)[:200]}"
    }), 500

@app.route('/api/support', methods=['POST'])
def support_api():
    try:
        data = request.get_json()
        user_question = data.get('question')
        history = data.get('history', [])
        
        if not user_question:
            return jsonify({"error": "Question is required"}), 400
            
        answer = ai_engine.support_chat(user_question, history)
        return jsonify({"answer": answer})
    except Exception as e:
        print(f"Support API Error: {e}")
        return jsonify({"error": "Internal Server Error", "message": str(e)}), 500

@app.route('/robots.txt')
def robots():
    return send_from_directory(app.config.root_path, 'static/robots.txt')

@app.route('/manifest.json')
def manifest():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'manifest.json')

@app.route('/sw.js')
def service_worker():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'sw.js')

@app.route('/sitemap.xml')
def sitemap():
    sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url><loc>https://manager.raehub.live/</loc><priority>1.0</priority></url>
    <url><loc>https://manager.raehub.live/pricing</loc><priority>0.8</priority></url>
    <url><loc>https://manager.raehub.live/login</loc><priority>0.5</priority></url>
    <url><loc>https://manager.raehub.live/register</loc><priority>0.5</priority></url>
</urlset>"""
    return Response(sitemap_xml, mimetype='application/xml')

# Initialize DB on startup
with app.app_context():
    init_db()

if __name__ == '__main__':
    # VPS Ready Run Configuration
    host = os.getenv('FLASK_HOST', '127.0.0.1')  # Use 0.0.0.0 for VPS access
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # SECURITY: Disable debug mode in production to prevent crashes/hacks
    app.run(host=host, port=port, debug=debug)
