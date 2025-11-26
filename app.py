from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # change to a secure secret in production
DB = 'kalma.db'

# -----------------------------
# DATABASE HELPERS
# -----------------------------
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    # create tables
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    security_question TEXT,
                    security_answer TEXT
                )''')

    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    title TEXT,
                    category TEXT,
                    due_date TEXT,
                    is_completed INTEGER DEFAULT 0,
                    created_at TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )''')

    c.execute('''CREATE TABLE IF NOT EXISTS motivations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message TEXT
                )''')

    # insert initial motivational messages if empty
    c.execute('SELECT COUNT(*) as cnt FROM motivations')
    row = c.fetchone()
    if not row or row['cnt'] == 0:
        c.executemany('INSERT INTO motivations (message) VALUES (?)',
                      [("Breathe. You’re doing your best.",),
                       ("Progress, not perfection.",),
                       ("One step at a time.",)])
    conn.commit()
    conn.close()

# -----------------------------
# INTRO (landing)
# -----------------------------
@app.route('/')
def intro():
    return render_template('intro.html')

# alternative home redirect (keeps route if desired)
@app.route('/home')
def home():
    return redirect(url_for('login'))

# -----------------------------
# AUTH ROUTES
# -----------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email','').strip()
        password = request.form.get('password','')
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email=?", (email,))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            flash("Logged in!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials", "danger")
    return render_template('login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email','').strip()
        password = request.form.get('password','')
        confirm = request.form.get('confirm','')
        question = request.form.get('security_question','').strip()
        answer = request.form.get('security_answer','').strip()

        if password != confirm:
            flash("Passwords don't match", "danger")
            return redirect(url_for('register'))

        hashed = generate_password_hash(password)
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (email, password, security_question, security_answer) VALUES (?,?,?,?)",
                      (email, hashed, question, answer))
            conn.commit()
            flash("Registration successful — you can now log in", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Email already exists", "danger")
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for('login'))

# -----------------------------
# FORGOT / RESET PASSWORD
# -----------------------------
@app.route('/forgot', methods=['GET','POST'])
def forgot():
    if request.method == 'POST':
        email = request.form.get('email','').strip()
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, security_question FROM users WHERE email=?", (email,))
        row = c.fetchone()
        conn.close()
        if row:
            return render_template('forgot_step2.html', user_id=row['id'], question=row['security_question'], email=email)
        else:
            flash("Email not found", "danger")
            return redirect(url_for('forgot'))
    return render_template('forgot.html')

@app.route('/reset_password', methods=['POST'])
def reset_password():
    user_id = request.form.get('user_id')
    answer = request.form.get('security_answer','').strip()
    newpw = request.form.get('new_password','')
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT security_answer FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    if row and row['security_answer'] and row['security_answer'].strip().lower() == answer.strip().lower():
        hashed = generate_password_hash(newpw)
        c.execute("UPDATE users SET password=? WHERE id=?", (hashed, user_id))
        conn.commit()
        conn.close()
        flash("Password reset successful — please login", "success")
        return redirect(url_for('login'))
    else:
        conn.close()
        flash("Security answer incorrect", "danger")
        return redirect(url_for('forgot'))

# -----------------------------
# DASHBOARD & TASKS
# -----------------------------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT email FROM users WHERE id=?", (user_id,))
    user_row = c.fetchone()
    user = user_row['email'] if user_row else "User"
    c.execute("SELECT id, title, category, due_date, is_completed FROM tasks WHERE user_id=? ORDER BY due_date ASC", (user_id,))
    tasks = c.fetchall()
    c.execute("SELECT message FROM motivations ORDER BY RANDOM() LIMIT 1")
    motivation = c.fetchone()
    conn.close()
    return render_template('dashboard.html', user=user, tasks=tasks, motivation=motivation)

@app.route('/add_task', methods=['POST'])
def add_task():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    title = request.form.get('title','').strip()
    category = request.form.get('category','').strip()
    due_date = request.form.get('due_date','')
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO tasks (user_id, title, category, due_date, created_at) VALUES (?,?,?,?,?)",
              (session['user_id'], title, category, due_date, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    flash("Task added", "success")
    return redirect(url_for('dashboard'))

@app.route('/edit_task/<int:task_id>', methods=['GET','POST'])
def edit_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    c = conn.cursor()
    if request.method == 'POST':
        title = request.form.get('title','').strip()
        category = request.form.get('category','').strip()
        due_date = request.form.get('due_date','')
        c.execute("UPDATE tasks SET title=?, category=?, due_date=? WHERE id=? AND user_id=?",
                  (title, category, due_date, task_id, session['user_id']))
        conn.commit()
        conn.close()
        flash("Task updated", "success")
        return redirect(url_for('dashboard'))
    c.execute("SELECT * FROM tasks WHERE id=? AND user_id=?", (task_id, session['user_id']))
    task = c.fetchone()
    conn.close()
    if not task:
        flash("Task not found", "danger")
        return redirect(url_for('dashboard'))
    return render_template('edit_task.html', task=task)

@app.route('/delete_task/<int:task_id>')
def delete_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id=? AND user_id=?", (task_id, session['user_id']))
    conn.commit()
    conn.close()
    flash("Task deleted", "info")
    return redirect(url_for('dashboard'))

@app.route('/complete_task/<int:task_id>')
def complete_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE tasks SET is_completed=1 WHERE id=? AND user_id=?", (task_id, session['user_id']))
    conn.commit()
    conn.close()
    flash("Task marked complete", "success")
    return redirect(url_for('dashboard'))

# API for chart
@app.route('/api/task_stats')
def task_stats():
    if 'user_id' not in session:
        return jsonify({"error":"unauthenticated"}), 401
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as total FROM tasks WHERE user_id=?", (session['user_id'],))
    total_row = c.fetchone()
    total = total_row['total'] if total_row else 0
    c.execute("SELECT COUNT(*) as done FROM tasks WHERE user_id=? AND is_completed=1", (session['user_id'],))
    done_row = c.fetchone()
    done = done_row['done'] if done_row else 0
    conn.close()
    pending = total - (done or 0)
    return jsonify({"total": total or 0, "done": done or 0, "pending": pending or 0})

# -----------------------------
# SELF-ASSESSMENT
# -----------------------------
@app.route('/self_assessment', methods=['GET','POST'])
def self_assessment():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            q1 = int(request.form.get('q1', 5))
            q2 = int(request.form.get('q2', 5))
            q3 = int(request.form.get('q3', 5))
        except ValueError:
            q1 = q2 = q3 = 5

        try:
            emoji_score = int(request.form.get('emoji_score', 3))
        except ValueError:
            emoji_score = 3

        stress_q3 = 11 - q3
        raw = q1 + q2 + stress_q3
        emoji_offset = (3 - emoji_score) * 2
        combined = raw + emoji_offset

        if combined <= 10:
            mood = 'calm'
            bg_class = 'bg-calm'
            emoji = "😊"
            headline = "You're doing well — keep it up!"
            result_text = "Your answers show a calm and steady mood."
        elif combined <= 18:
            mood = 'neutral'
            bg_class = 'bg-neutral'
            emoji = "🙂"
            headline = "A mixed day — that's okay"
            result_text = "You feel some stress but also stability."
        elif combined <= 24:
            mood = 'stressed'
            bg_class = 'bg-stressed'
            emoji = "😟"
            headline = "You're feeling stressed — be kind to yourself"
            result_text = "A short break or breathing exercise may help."
        else:
            mood = 'anxious'
            bg_class = 'bg-anxious'
            emoji = "😣"
            headline = "High stress detected — reach out if needed"
            result_text = "Talking to a friend or counselor may help."

        return render_template('assessment_result.html',
                               result_text=result_text,
                               headline=headline,
                               emoji=emoji,
                               bg_class=bg_class)

    return render_template('self_assessment.html')

# -----------------------------
# PROFILE
# -----------------------------
@app.route('/profile', methods=['GET','POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    c = conn.cursor()
    if request.method == 'POST':
        new_email = request.form.get('email','').strip()
        new_password = request.form.get('password','')
        try:
            if new_email:
                c.execute("UPDATE users SET email=? WHERE id=?", (new_email, session['user_id']))
            if new_password:
                c.execute("UPDATE users SET password=? WHERE id=?", (generate_password_hash(new_password), session['user_id']))
            conn.commit()
            flash("Profile updated", "success")
        except sqlite3.IntegrityError:
            flash("Email already taken", "danger")
        finally:
            conn.close()
        return redirect(url_for('profile'))
    c.execute("SELECT email, security_question FROM users WHERE id=?", (session['user_id'],))
    user = c.fetchone()
    conn.close()
    return render_template('profile.html', user=user)

# -----------------------------
# SAMPLE TASKS
# -----------------------------
@app.route('/add_sample_tasks')
def add_sample_tasks():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    c = conn.cursor()
    sample = [
        ("Finish IT project", "School", "2025-12-01"),
        ("Meditation", "Wellness", "2025-11-20"),
        ("Group meeting", "School", "2025-11-22"),
    ]
    for s in sample:
        c.execute("INSERT INTO tasks (user_id, title, category, due_date, created_at) VALUES (?,?,?,?,?)",
                  (session['user_id'], s[0], s[1], s[2], datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
