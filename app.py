from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, send_from_directory
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

app = Flask(__name__)
# app.secret_key set below
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize Firebase
cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred)

# Database setup
DB_NAME = 'content_ideas.db'

def init_db():
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

    conn.commit()
    conn.close()

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# --- REAL AI INTEGRATION ---
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENAI_API_KEY")
)

class AI_Engine:
    def generate(self, business_type, platform, mood, goal, people, language, existing_ideas, refinement=None, previous_idea=None):
        # Determine language style
        lang_instruction = "SPEAK IN VERY SIMPLE, BEGINNER ENGLISH (A1/A2 level). Use short sentences. Use simple words. No big grammar."
        if language == 'pidgin':
            lang_instruction = "SPEAK IN NIGERIAN PIDGIN ENGLISH. Make it sound authentic, street-smart, and relatable to Nigerians. Use words like 'abeg', 'wetin', 'na so', 'ginger'."
        elif language == 'standard':
            lang_instruction = "SPEAK IN STANDARD PROFESSIONAL ENGLISH. Be clear, concise, and business-appropriate, but still engaging."

        # Construct prompt
        system_prompt = (
            f"You are a world-class Social Media Manager and Content Strategist specializing in African small businesses. "
            f"You understand the local market, cultural nuances, and how to turn viewers into loyal customers with zero budget. "
            f"Your goal is to create viral, high-converting video content that feels authentic. "
            f"{lang_instruction} "
            f"Be practical, encouraging, and laser-focused on growth. Do not be generic."
        )

        base_prompt = f"""
        I have a {business_type}.
        Platform: {platform}
        Video feeling: {mood}.
        Goal: {goal}.
        People in video: {people}.
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
            
            Format your answer exactly like this:

            THE BIG IDEA
            (Write 1 sentence about the video).

            STEP-BY-STEP (How do I do it?)
            1. [Step 1]
            2. [Step 2]
            3. [Step 3]
            4. [Step 4]

            PRO TIP (To make it sweet)
            (One simple advice).

            CAPTION
            (Write a catchy caption).

            HASHTAGS
            (5-10 hashtags).

            BEST TIME TO POST
            (Best time to post).

            Remember: {lang_instruction}
            """
        else:
            user_prompt = f"""
            {base_prompt}

            Give me ONE video/content idea optimized for {platform}.

            Format your answer exactly like this:

            THE BIG IDEA
            (Write 1 sentence about the video).

            STEP-BY-STEP (How do I do it?)
            1. [Step 1]
            2. [Step 2]
            3. [Step 3]
            4. [Step 4]

            PRO TIP (To make it sweet)
            (One simple advice).

            CAPTION
            (Write a catchy caption).

            HASHTAGS
            (5-10 hashtags).

            BEST TIME TO POST
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
def login():
    if request.method == 'POST':
        # FIREBASE LOGIN LOGIC
        id_token = request.json.get('idToken')
        if not id_token:
            return jsonify({"error": "No token provided"}), 400
        
        try:
            # Verify Firebase Token
            decoded_token = auth.verify_id_token(id_token, check_revoked=True)
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
            
            # STRICT ADMIN CHECK: Only patricknigel33@gmail.com can be admin
            is_admin_email = (email == 'patricknigel33@gmail.com')
            session['is_admin'] = is_admin_email
            
            # Ensure DB reflects this (self-correcting security)
            if is_admin_email != bool(user_row[2]):
                conn = sqlite3.connect(DB_NAME, timeout=10)
                c = conn.cursor()
                c.execute("UPDATE users SET is_admin = ? WHERE id = ?", (1 if is_admin_email else 0, user_row[0]))
                conn.commit()
                conn.close()

            session['firebase_uid'] = uid # Store Firebase UID for future reference
            
            # If Admin, let frontend know so it can ask which dashboard to go to
            return jsonify({
                "success": True, 
                "redirect": url_for('dashboard'),
                "is_admin": is_admin_email
            })
            
        except Exception as e:
            print(f"Firebase Auth Error: {e}")
            return jsonify({"error": "Invalid token"}), 401
            
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
    return render_template('index.html', username=session.get('username'), is_subscribed=session.get('is_subscribed'))

@app.route('/pricing')
@login_required
def pricing():
    return render_template('pricing.html')

@app.route('/plan/5k')
@login_required
def plan_5k():
    return render_template('payment.html', plan='5k Content Plan', price='₦5,000', username=session.get('username'))

@app.route('/submit_payment', methods=['POST'])
@login_required
def submit_payment():
    if 'screenshot' not in request.files:
        flash('No file part')
        return redirect(request.url)
    
    file = request.files['screenshot']
    full_name = request.form.get('full_name')
    app_username = request.form.get('app_username')
    
    if not full_name:
         flash('Please enter your full name')
         return redirect(request.url)

    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)

    if file:
        filename = secure_filename(f"{int(time.time())}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        target_user_id = session['user_id']
        
        conn = sqlite3.connect(DB_NAME, timeout=10)
        c = conn.cursor()
        c.execute('''INSERT INTO submissions (user_id, username, full_name, plan_type, screenshot_path)
                     VALUES (?, ?, ?, ?, ?)''', 
                  (target_user_id, app_username, full_name, '5k Content Plan', filename))
        conn.commit()
        conn.close()
        
        return render_template('payment_success.html')

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
    c = conn.cursor()
    
    c.execute("SELECT id, username, full_name, plan_type, screenshot_path, timestamp, status FROM submissions WHERE status = 'pending' ORDER BY timestamp DESC")
    submissions = c.fetchall()
    
    c.execute("SELECT id, username, full_name, plan_type, status, timestamp FROM submissions WHERE status != 'pending' ORDER BY timestamp DESC LIMIT 20")
    history = c.fetchall()
    
    # Get all users with subscription details
    c.execute("SELECT id, username, is_subscribed, subscription_start FROM users")
    users = c.fetchall()
    
    conn.close()
    return render_template('admin.html', submissions=submissions, history=history, users=users)

@app.route('/admin/approve/<int:submission_id>')
@admin_required
def approve_submission(submission_id):
    conn = sqlite3.connect(DB_NAME, timeout=10)
    c = conn.cursor()
    
    c.execute("SELECT user_id, plan_type FROM submissions WHERE id = ?", (submission_id,))
    sub = c.fetchone()
    
    if sub:
        user_id = sub[0]
        c.execute("UPDATE submissions SET status = 'approved' WHERE id = ?", (submission_id,))
        # Set is_subscribed = 1 and set start date to now
        c.execute("UPDATE users SET is_subscribed = 1, subscription_start = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))
        conn.commit()
        flash(f'Submission {submission_id} approved and user {user_id} credited.')
    else:
        flash('Submission not found.')
        
    conn.close()
    return redirect(url_for('admin_dashboard'))

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
    c.execute("UPDATE users SET is_subscribed = 0, subscription_start = NULL WHERE id = ?", (user_id,))
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
def generate_idea():
    data = request.json
    business_type = data.get('businessType', '').strip()
    platform = data.get('platform', 'instagram').strip()
    if platform == 'instagram_tiktok':
        platform = 'Instagram and TikTok'
        
    mood = data.get('mood', 'neutral').strip()
    goal = data.get('goal', 'engage').strip()
    people = data.get('people', 'solo').strip()
    language = data.get('language', 'simple').strip()
    refinement = data.get('refinement', '').strip()
    previous_idea = data.get('previous_idea', '').strip()
    
    if not business_type:
        return jsonify({"error": "Business type is required"}), 400

    user_id = session['user_id']
    conn = sqlite3.connect(DB_NAME, timeout=10)
    try:
        c = conn.cursor()
        
        c.execute("SELECT idea_content FROM ideas WHERE business_type = ? AND user_id = ?", (business_type, user_id))
        past_ideas = [row[0] for row in c.fetchall()]

        c.execute("SELECT COUNT(*) FROM ideas WHERE user_id = ?", (user_id,))
        usage_count = c.fetchone()[0]
        
        is_subscribed = session.get('is_subscribed', False)
        
        # Only check limit if it's a fresh generation, not a refinement
        if not is_subscribed and usage_count >= 1 and not refinement:
            return jsonify({"error": "LIMIT_REACHED", "message": "Free trial expired. Please upgrade to the 5k Plan."}), 403
        
        new_idea = ai_engine.generate(business_type, platform, mood, goal, people, language, past_ideas, refinement, previous_idea)
        
        c.execute("INSERT INTO ideas (user_id, business_type, idea_content) VALUES (?, ?, ?)", (user_id, business_type, new_idea))
        conn.commit()
        
        return jsonify({"idea": new_idea})
    except Exception as e:
        print(f"Error generating idea: {e}")
        return jsonify({"error": "Server Error", "message": str(e)}), 500
    finally:
        conn.close()

# Initialize DB on startup
with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
