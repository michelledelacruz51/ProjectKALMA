from flask import Flask, render_template, request, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random

app = Flask(__name__)
app.secret_key = "supersecretkey"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///kalma.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# ---------------------------
# DATABASE MODELS
# ---------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(200))
    name = db.Column(db.String(100))


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    title = db.Column(db.String(150))
    category = db.Column(db.String(100))
    due_date = db.Column(db.String(50))
    is_completed = db.Column(db.Boolean, default=False)


# ---------------------------
# ROUTES
# ---------------------------

@app.route("/")
def intro():
    return render_template("intro.html")


# ---------------------------
# REGISTER
# ---------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["fullname"]
        email = request.form["email"]
        password = request.form["password"]
        confirm = request.form["confirm_password"]

        if password != confirm:
            return render_template("register.html", error="Passwords do not match")

        hashed = generate_password_hash(password)

        user = User(name=name, email=email, password=hashed)
        db.session.add(user)
        db.session.commit()

        return redirect("/login")

    return render_template("register.html")


# ---------------------------
# LOGIN
# ---------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["user_name"] = user.name
            return redirect("/dashboard")

        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")


# ---------------------------
# LOGOUT
# ---------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ---------------------------
# DASHBOARD
# ---------------------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    tasks = Task.query.filter_by(user_id=user_id).all()

    motivations = [
        {"message": "You are stronger than you think."},
        {"message": "Small steps every day still move you forward."},
        {"message": "Your feelings are valid."},
        {"message": "Breathe. You’re doing your best."},
        {"message": "You’ve survived every hard day so far—you can handle this one too."},
        {'message': "Small victories count. Celebrate them."},
        {'message': "Your mental health matters more than the expectations of others."},
        {'message': "It’s okay to feel lost. Healing often begins in the dark."},
    ]

    return render_template(
        "dashboard.html",
        user=session["user_name"],
        tasks=tasks,
        motivation=random.choice(motivations),
    )


# ---------------------------
# ADD TASK
# ---------------------------
@app.route("/add_task", methods=["POST"])
def add_task():
    if "user_id" not in session:
        return redirect("/login")

    title = request.form["title"]
    category = request.form["category"]
    due = request.form["due_date"]

    task = Task(
        user_id=session["user_id"],
        title=title,
        category=category,
        due_date=due,
    )
    db.session.add(task)
    db.session.commit()

    return redirect("/dashboard")


# ---------------------------
# COMPLETE TASK
# ---------------------------
@app.route("/complete_task/<int:id>")
def complete_task(id):
    task = Task.query.get(id)
    task.is_completed = True
    db.session.commit()
    return redirect("/dashboard")


# ---------------------------
# DELETE TASK
# ---------------------------
@app.route("/delete_task/<int:id>")
def delete_task(id):
    task = Task.query.get(id)
    db.session.delete(task)
    db.session.commit()
    return redirect("/dashboard")


# ---------------------------
# EDIT TASK
# ---------------------------
@app.route("/edit_task/<int:id>", methods=["GET", "POST"])
def edit_task(id):
    task = Task.query.get(id)

    if request.method == "POST":
        task.title = request.form["title"]
        task.category = request.form["category"]
        task.due_date = request.form["due_date"]
        db.session.commit()
        return redirect("/dashboard")

    return render_template("edit_task.html", task=task)


# ---------------------------
# TASK STATS API (for dashboard chart)
# ---------------------------
@app.route("/api/task_stats")
def task_stats():
    if "user_id" not in session:
        return jsonify({"total": 0, "done": 0, "pending": 0})

    user_id = session["user_id"]
    tasks = Task.query.filter_by(user_id=user_id).all()

    total = len(tasks)
    done = len([t for t in tasks if t.is_completed])
    pending = total - done

    return jsonify({"total": total, "done": done, "pending": pending})


# ---------------------------
# RUN APP
# ---------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
