from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import sqlite3
import random
import os
import json
import time
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_demo'  # Needed for sessions

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
    # Check if user_id column exists, if not, we might need to migrate manually or just create table if not exists
    # For simplicity in this dev environment, we'll create it if it doesn't exist. 
    # If it exists without user_id, we will alter it.
    c.execute('''CREATE TABLE IF NOT EXISTS ideas
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  business_type TEXT,
                  idea_content TEXT,
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

    # Check if is_subscribed column exists in users table
    c.execute("PRAGMA table_info(users)")
    user_columns = [column[1] for column in c.fetchall()]
    if 'is_subscribed' not in user_columns:
        try:
            c.execute("ALTER TABLE users ADD COLUMN is_subscribed BOOLEAN DEFAULT 0")
        except Exception as e:
            print(f"Migration warning (users): {e}")

    conn.commit()
    conn.close()

init_db()

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# --- REAL AI INTEGRATION ---
# using OpenRouter (compatible with OpenAI SDK)
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENAI_API_KEY")
)

class AI_Engine:
    def generate(self, business_type, platform, mood, goal, people, language, existing_ideas):
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
        user_prompt = f"""
        I have a {business_type}.
        Platform: {platform}
        Video feeling: {mood}.
        Goal: {goal}.
        People in video: {people}.

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

@app.route('/')
def intro():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('intro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect(DB_NAME, timeout=10)
        c = conn.cursor()
        c.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()
        
        if user and check_password_hash(user[1], password):
            # Check subscription status
            conn = sqlite3.connect(DB_NAME, timeout=10)
            c = conn.cursor()
            c.execute("SELECT is_subscribed FROM users WHERE id = ?", (user[0],))
            sub_status = c.fetchone()[0]
            conn.close()

            session['user_id'] = user[0]
            session['username'] = username
            session['is_subscribed'] = bool(sub_status)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if not username or not password:
            flash('Username and password are required')
            return render_template('register.html')
            
        hashed_password = generate_password_hash(password)
        
        try:
            conn = sqlite3.connect(DB_NAME, timeout=10)
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
            conn.close()
            flash('Registration successful! Please login.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists.')
            
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('intro'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('index.html', username=session.get('username'))

@app.route('/api/check_status', methods=['GET'])
def check_status():
    # Check if user has "paid" (stored in session for demo)
    is_subscribed = session.get('is_subscribed', False)
    
    # Check trial status
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
    # Simulate payment processing
    time.sleep(1.5)
    
    user_id = session['user_id']
    try:
        conn = sqlite3.connect(DB_NAME, timeout=10)
        c = conn.cursor()
        c.execute("UPDATE users SET is_subscribed = 1 WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        
        session['is_subscribed'] = True
        return jsonify({"status": "success", "message": "Subscription active! You have unlimited access."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
    
    if not business_type:
        return jsonify({"error": "Business type is required"}), 400

    user_id = session['user_id']
    conn = sqlite3.connect(DB_NAME, timeout=10)
    try:
        c = conn.cursor()
        
        # Get past ideas for this business type AND user to avoid duplicates
        c.execute("SELECT idea_content FROM ideas WHERE business_type = ? AND user_id = ?", (business_type, user_id))
        past_ideas = [row[0] for row in c.fetchall()]

        # Check Usage Limit
        c.execute("SELECT COUNT(*) FROM ideas WHERE user_id = ?", (user_id,))
        usage_count = c.fetchone()[0]
        
        is_subscribed = session.get('is_subscribed', False)
        
        # If not subscribed and used 1 or more times, BLOCK.
        if not is_subscribed and usage_count >= 1:
            return jsonify({"error": "LIMIT_REACHED", "message": "Free trial expired. Please upgrade for ₦3,000/month."}), 403
        
        # Generate new idea
        new_idea = ai_engine.generate(business_type, platform, mood, goal, people, language, past_ideas)
        
        # Save to history with user_id
        c.execute("INSERT INTO ideas (user_id, business_type, idea_content) VALUES (?, ?, ?)", (user_id, business_type, new_idea))
        conn.commit()
        
        return jsonify({"idea": new_idea})
    except Exception as e:
        print(f"Error generating idea: {e}")
        return jsonify({"error": "Server Error", "message": str(e)}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
