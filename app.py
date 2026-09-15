from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os
from functools import wraps

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-secret-key")
DB_PATH = os.getenv("DB_PATH", "college.db")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('staff','student'))
    );
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reg_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT NOT NULL,
        department TEXT NOT NULL,
        year INTEGER NOT NULL,
        section TEXT NOT NULL,
        dob TEXT,
        gender TEXT,
        address TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS marks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        subject_code TEXT NOT NULL,
        subject_name TEXT NOT NULL,
        credits INTEGER NOT NULL,
        mark REAL NOT NULL,
        grade TEXT NOT NULL,
        FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
        UNIQUE(student_id, subject_code)
    );
    """)
    # Demo staff login
    if not conn.execute("SELECT 1 FROM users WHERE username='admin'").fetchone():
        conn.execute("INSERT INTO users(username,password,role) VALUES(?,?,?)",
                     ("admin", generate_password_hash("admin123"), "staff"))
    conn.commit()
    conn.close()

def login_required(role=None):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                flash("You don't have permission to access that page.", "error")
                return redirect(url_for("dashboard"))
            return fn(*args, **kwargs)
        return wrapper
    return deco

def grade_for(mark):
    if mark >= 90: return "O", 10
    if mark >= 80: return "A+", 9
    if mark >= 70: return "A", 8
    if mark >= 60: return "B+", 7
    if mark >= 50: return "B", 6
    if mark >= 40: return "C", 5
    return "F", 0

def student_cgpa(student_id):
    conn = db()
    rows = conn.execute("SELECT credits, mark FROM marks WHERE student_id=?", (student_id,)).fetchall()
    conn.close()
    if not rows: return 0.0
    total_credits = sum(r["credits"] for r in rows)
    points = sum(grade_for(r["mark"])[1] * r["credits"] for r in rows)
    return round(points / total_credits, 2) if total_credits else 0.0

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        conn = db()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required()
def dashboard():
    conn = db()
    students = conn.execute("SELECT * FROM students ORDER BY id DESC").fetchall()
    enriched = []
    for s in students:
        enriched.append({**dict(s), "cgpa": student_cgpa(s["id"])})
    conn.close()
    return render_template("dashboard.html", students=enriched, role=session["role"])

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        data = {k: request.form.get(k, "").strip() for k in
                ["reg_id","name","email","phone","department","year","section","dob","gender","address"]}
        if not all(data[k] for k in ["reg_id","name","email","phone","department","year","section"]):
            flash("Please complete all mandatory fields.", "error")
            return render_template("register.html", data=data)
        conn = db()
        try:
            conn.execute("""INSERT INTO students
                (reg_id,name,email,phone,department,year,section,dob,gender,address)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                tuple(data.values()))
            conn.commit()
            flash("Student registered successfully.", "success")
            return redirect(url_for("dashboard"))
        except sqlite3.IntegrityError:
            flash("Registration ID or email already exists.", "error")
        finally:
            conn.close()
    return render_template("register.html", data={})

@app.route("/student/<int:student_id>")
@login_required()
def student_profile(student_id):
    conn = db()
    student = conn.execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone()
    marks = conn.execute("SELECT * FROM marks WHERE student_id=? ORDER BY subject_code", (student_id,)).fetchall()
    conn.close()
    if not student:
        return "Student not found", 404
    cgpa = student_cgpa(student_id)
    return render_template("student_profile.html", student=student, marks=marks, cgpa=cgpa)

@app.route("/staff/marks", methods=["GET","POST"])
@login_required("staff")
def marks():
    conn = db()
    if request.method == "POST":
        student_id = request.form["student_id"]
        subject_code = request.form["subject_code"].strip().upper()
        subject_name = request.form["subject_name"].strip()
        credits = int(request.form["credits"])
        mark = float(request.form["mark"])
        if not subject_code or not subject_name or not 0 <= mark <= 100 or credits <= 0:
            flash("Enter valid subject, credits and marks.", "error")
        else:
            grade, _ = grade_for(mark)
            conn.execute("""INSERT INTO marks(student_id,subject_code,subject_name,credits,mark,grade)
                            VALUES(?,?,?,?,?,?)
                            ON CONFLICT(student_id,subject_code) DO UPDATE SET
                            subject_name=excluded.subject_name, credits=excluded.credits,
                            mark=excluded.mark, grade=excluded.grade""",
                         (student_id,subject_code,subject_name,credits,mark,grade))
            conn.commit()
            flash("Marks saved and CGPA recalculated.", "success")
    students = conn.execute("SELECT * FROM students ORDER BY name").fetchall()
    all_marks = conn.execute("""SELECT m.*, s.name, s.reg_id FROM marks m
                                JOIN students s ON s.id=m.student_id
                                ORDER BY s.name,m.subject_code""").fetchall()
    conn.close()
    return render_template("marks.html", students=students, marks=all_marks)

@app.route("/api/students")
@login_required()
def api_students():
    conn = db()
    rows = conn.execute("SELECT id,reg_id,name,department,year,section FROM students ORDER BY name").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
