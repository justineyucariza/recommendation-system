import os
import re
import ssl
import json
import smtplib
import secrets
import hashlib
import urllib.error
import urllib.request
import base64
from datetime import datetime, timedelta
from email.message import EmailMessage
from flask import Flask, request, jsonify, send_from_directory, abort
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# ------------------------------------------------------------------
# MySQL Configuration — for local XAMPP / phpMyAdmin.
#
# Defaults match a standard XAMPP install:
#   host:     localhost
#   user:     root
#   password: ""
#   database: coursedb
#
# If your local MySQL user has a password, set DB_PASSWORD in your
# environment and the app will use that instead.
# ------------------------------------------------------------------
DB_CONFIG = {
    "host":     os.environ.get("MYSQLHOST") or os.environ.get("DB_HOST", "localhost"),
    "user":     os.environ.get("MYSQLUSER") or os.environ.get("DB_USER", "root"),
    "password": os.environ.get("MYSQLPASSWORD") or os.environ.get("MYSQL_ROOT_PASSWORD") or os.environ.get("DB_PASSWORD", ""),
    "database": os.environ.get("MYSQLDATABASE") or os.environ.get("MYSQL_DATABASE") or os.environ.get("DB_NAME", "coursedb"),
    "port":     int(os.environ.get("MYSQLPORT") or os.environ.get("DB_PORT", "3306")),
    "connection_timeout": 10
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads", "profile-pictures")
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_PROFILE_PICTURE_BYTES = 1 * 1024 * 1024
EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
RESET_CODE_MINUTES = int(os.environ.get("RESET_CODE_MINUTES", "10"))
# Prefer Resend over SMTP on Railway because outbound SMTP can be blocked.
# Resend: RESEND_API_KEY, RESEND_FROM_EMAIL.
# SMTP fallback: SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD.
# Optional: SMTP_FROM_EMAIL, SMTP_USE_TLS, RESET_CODE_MINUTES.
RESEND_CONFIG = {
    "api_key": os.environ.get("RESEND_API_KEY", ""),
    "from_email": os.environ.get("RESEND_FROM_EMAIL", ""),
}
SMTP_CONFIG = {
    "host": os.environ.get("SMTP_HOST", ""),
    "port": int(os.environ.get("SMTP_PORT", "587")),
    "username": os.environ.get("SMTP_USERNAME", ""),
    "password": os.environ.get("SMTP_PASSWORD", ""),
    "from_email": os.environ.get("SMTP_FROM_EMAIL") or os.environ.get("SMTP_USERNAME", ""),
    "use_tls": os.environ.get("SMTP_USE_TLS", "1") != "0",
}
FRONTEND_FILES = {
    "index.html",
    "Homepage.html",
    "course.css",
    "Homepage.css",
    "Homepage.js",
    "Acadsync.jpg"
}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db():
    """Return a fresh MySQL connection, or None if it fails."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"[DB ERROR] {e}")
        return None


def safe_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def safe_int(val, default=0):
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def title_case(value):
    return " ".join(part.capitalize() for part in str(value or "").strip().split())


def format_full_name(first_name, last_name):
    first_name = title_case(first_name)
    last_name = title_case(last_name)
    return f"{first_name} {last_name}".strip()


def profile_picture_path(filename):
    if not filename:
        return ""
    if str(filename).startswith("data:"):
        return filename
    return f"/uploads/profile-pictures/{filename}"


def is_allowed_image(filename):
    if not filename or "." not in filename:
        return False
    extension = filename.rsplit(".", 1)[1].lower()
    return extension in ALLOWED_IMAGE_EXTENSIONS


def is_valid_email(email):
    return bool(EMAIL_PATTERN.fullmatch(email or ""))


def password_validation_errors(password):
    """Return clear requirements missing from a proposed account password."""
    errors = []
    password = password or ""
    if len(password) < 8:
        errors.append("at least 8 characters")
    if not re.search(r"[A-Z]", password):
        errors.append("one uppercase letter")
    if not re.search(r"[a-z]", password):
        errors.append("one lowercase letter")
    if not re.search(r"\d", password):
        errors.append("one number")
    if not re.search(r"[^A-Za-z0-9]", password):
        errors.append("one special character")
    return errors


def password_requirements_message(errors):
    return "Password must include " + ", ".join(errors) + "."


def hash_password(password):
    return generate_password_hash(password)


def verify_password(stored_password, submitted_password):
    if not stored_password:
        return False
    if stored_password.startswith(("pbkdf2:", "scrypt:")):
        return check_password_hash(stored_password, submitted_password)
    return secrets.compare_digest(stored_password, submitted_password)


def code_hash(code):
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def is_email_configured():
    if RESEND_CONFIG["api_key"] and RESEND_CONFIG["from_email"]:
        return True

    return all([
        SMTP_CONFIG["host"],
        SMTP_CONFIG["username"],
        SMTP_CONFIG["password"],
        SMTP_CONFIG["from_email"],
    ])


def email_provider_name():
    if RESEND_CONFIG["api_key"] and RESEND_CONFIG["from_email"]:
        return "resend"
    if is_email_configured():
        return "smtp"
    return "not configured"


def public_email_error_message(error):
    text = str(error)
    if len(text) > 240:
        text = text[:237] + "..."
    return f"Could not send email using {email_provider_name()}: {text}"


def send_email_with_smtp(to_email, subject, body):
    message = EmailMessage()
    message["From"] = SMTP_CONFIG["from_email"]
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    if SMTP_CONFIG["use_tls"]:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_CONFIG["host"], SMTP_CONFIG["port"], timeout=20) as server:
            server.starttls(context=context)
            server.login(SMTP_CONFIG["username"], SMTP_CONFIG["password"])
            server.send_message(message)
    else:
        with smtplib.SMTP_SSL(SMTP_CONFIG["host"], SMTP_CONFIG["port"], timeout=20) as server:
            server.login(SMTP_CONFIG["username"], SMTP_CONFIG["password"])
            server.send_message(message)


def send_email_with_resend(to_email, subject, body):
    payload = json.dumps({
        "from": RESEND_CONFIG["from_email"],
        "to": [to_email],
        "subject": subject,
        "text": body,
    }).encode("utf-8")

    request = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {RESEND_CONFIG['api_key']}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.status >= 300:
                raise RuntimeError(f"Resend returned HTTP {response.status}.")
    except urllib.error.HTTPError as e:
        details = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Resend email error: {details}") from e


def send_email(to_email, subject, body):
    if RESEND_CONFIG["api_key"] and RESEND_CONFIG["from_email"]:
        send_email_with_resend(to_email, subject, body)
        return

    if not is_email_configured():
        raise RuntimeError("Email service is not configured.")

    send_email_with_smtp(to_email, subject, body)


def send_reset_code_email(to_email, code):
    send_email(
        to_email,
        "AcadSync Password Reset Code",
        (
            "Hello,\n\n"
            f"Your AcadSync password reset code is: {code}\n\n"
            f"This code expires in {RESET_CODE_MINUTES} minutes. "
            "If you did not request this reset, you can ignore this email.\n\n"
            "AcadSync"
        )
    )


def send_registration_email(to_email, name):
    send_email(
        to_email,
        "AcadSync Account Created",
        (
            f"Hello {name or 'student'},\n\n"
            "Your AcadSync account has been created successfully. "
            "You can now sign in and use the course recommendation system.\n\n"
            "For your security, this email does not include your password.\n\n"
            "AcadSync"
        )
    )


def send_assessment_result_email(to_email, name, result):
    recommended = result.get("recommended_course_title", "Your recommended course")
    alternative = result.get("alternative_course_title", "Your alternative course")
    alignment = result.get("alignment_score", "")
    pathways = result.get("pathways") or []
    pathway_text = "\n".join(f"- {pathway}" for pathway in pathways) or "- No pathways listed"

    send_email(
        to_email,
        "Your AcadSync Assessment Result",
        (
            f"Hello {name or 'student'},\n\n"
            "Here is your AcadSync assessment result:\n\n"
            f"Top recommendation: {recommended}\n"
            f"Alternative recommendation: {alternative}\n"
            f"Course match: {alignment}\n\n"
            "Suggested career pathways:\n"
            f"{pathway_text}\n\n"
            "This recommendation is based on your interests, skills, grades, "
            "preferences, and assessment answers.\n\n"
            "AcadSync"
        )
    )


def parse_valid_grade(value):
    try:
        grade = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    if 0 <= grade <= 99:
        return grade
    return None


# ------------------------------------------------------------------
# Startup migration — creates / updates all required tables once.
# Safe to re-run every startup (uses IF NOT EXISTS / ALTER IGNORE).
# ------------------------------------------------------------------
def run_startup_migrations():
    conn = get_db()
    if not conn:
        print("[MIGRATION] Skipped — cannot connect to DB.")
        return
    try:
        cur = conn.cursor()

        # strands lookup table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS strands (
                strand_id   INT AUTO_INCREMENT PRIMARY KEY,
                strand_name VARCHAR(50) UNIQUE NOT NULL
            )
        """)

        # users
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                studentID  INT AUTO_INCREMENT PRIMARY KEY,
                first_name VARCHAR(100) NOT NULL,
                last_name  VARCHAR(100) NOT NULL,
                email      VARCHAR(150) UNIQUE NOT NULL,
                password   VARCHAR(255) NOT NULL,
                strand_id  INT,
                section    VARCHAR(100) DEFAULT NULL,
                profile_picture LONGTEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (strand_id) REFERENCES strands(strand_id)
            )
        """)

        # Add `section` column to users if it was created before this migration
        try:
            cur.execute("ALTER TABLE users ADD COLUMN section VARCHAR(100) DEFAULT NULL")
        except Error as e:
            if "Duplicate column" not in str(e):
                print(f"[MIGRATION] section column: {e}")

        try:
            cur.execute("ALTER TABLE users ADD COLUMN profile_picture VARCHAR(255) DEFAULT NULL")
        except Error as e:
            if "Duplicate column" not in str(e):
                print(f"[MIGRATION] profile_picture column: {e}")

        try:
            cur.execute("ALTER TABLE users MODIFY COLUMN profile_picture LONGTEXT DEFAULT NULL")
        except Error as e:
            print(f"[MIGRATION] profile_picture type: {e}")

        # quiz_results — stores one row per quiz attempt
        cur.execute("""
            CREATE TABLE IF NOT EXISTS quiz_results (
                id                 INT AUTO_INCREMENT PRIMARY KEY,
                studentID          INT NOT NULL,
                total_score        FLOAT NOT NULL DEFAULT 0,
                time_taken_seconds INT NOT NULL DEFAULT 0,
                recommended_course VARCHAR(150) DEFAULT NULL,
                alignment_score    VARCHAR(10) DEFAULT NULL,
                created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (studentID) REFERENCES users(studentID)
            )
        """)

        try:
            cur.execute("ALTER TABLE quiz_results ADD COLUMN recommended_course VARCHAR(150) DEFAULT NULL")
        except Error as e:
            if "Duplicate column" not in str(e):
                print(f"[MIGRATION] recommended_course column: {e}")

        try:
            cur.execute("ALTER TABLE quiz_results ADD COLUMN alignment_score VARCHAR(10) DEFAULT NULL")
        except Error as e:
            if "Duplicate column" not in str(e):
                print(f"[MIGRATION] alignment_score column: {e}")

        # recommendations history (existing — keep it)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS recommendations (
                id                 INT AUTO_INCREMENT PRIMARY KEY,
                studentID          VARCHAR(20),
                recommended_course VARCHAR(100),
                alternative_course VARCHAR(100),
                alignment_score    VARCHAR(10),
                created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_codes (
                id         INT AUTO_INCREMENT PRIMARY KEY,
                email      VARCHAR(150) NOT NULL,
                code_hash  VARCHAR(64) NOT NULL,
                expires_at DATETIME NOT NULL,
                used_at    DATETIME DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_password_reset_email (email),
                INDEX idx_password_reset_expiry (expires_at)
            )
        """)

        conn.commit()
        print("[MIGRATION] All tables ready.")
    except Error as e:
        print(f"[MIGRATION ERROR] {e}")
    finally:
        conn.close()


# ------------------------------------------------------------------
# Helper: get or create a strand row and return its id
# ------------------------------------------------------------------
def get_or_create_strand_id(cursor, strand_name):
    cursor.execute("SELECT strand_id FROM strands WHERE strand_name = %s", (strand_name,))
    row = cursor.fetchone()
    if row:
        return row["strand_id"] if isinstance(row, dict) else row[0]
    cursor.execute("INSERT INTO strands (strand_name) VALUES (%s)", (strand_name,))
    return cursor.lastrowid


def get_course_id(cursor, course_code):
    cursor.execute("SELECT course_id FROM courses WHERE course_code = %s", (course_code,))
    row = cursor.fetchone()
    if row:
        return row["course_id"] if isinstance(row, dict) else row[0]
    return None


@app.route("/uploads/profile-pictures/<path:filename>")
def serve_profile_picture(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/")
def serve_index():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/index.html")
def serve_index_html():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/Homepage.html")
def serve_homepage_html():
    return send_from_directory(BASE_DIR, "Homepage.html")


@app.route("/<path:filename>")
def serve_frontend_asset(filename):
    if filename in FRONTEND_FILES:
        return send_from_directory(BASE_DIR, filename)
    abort(404)


@app.route("/api/health", methods=["GET"])
def health_check():
    conn = get_db()
    if not conn:
        return jsonify({
            "success": False,
            "database": "disconnected",
            "host": DB_CONFIG["host"],
            "database_name": DB_CONFIG["database"]
        }), 500

    conn.close()
    return jsonify({
        "success": True,
        "database": "connected",
        "host": DB_CONFIG["host"],
        "database_name": DB_CONFIG["database"],
        "email_provider": email_provider_name(),
        "resend_configured": bool(RESEND_CONFIG["api_key"] and RESEND_CONFIG["from_email"]),
        "smtp_configured": all([
            SMTP_CONFIG["host"],
            SMTP_CONFIG["username"],
            SMTP_CONFIG["password"],
            SMTP_CONFIG["from_email"],
        ])
    })


# ==================================================================
#  AUTH ENDPOINTS
# ==================================================================

# ------------------------------------------------------------------
# LOGIN  —  POST /api/login
# Body: { "email": "...", "password": "..." }
# Returns all fields needed by Homepage (name, strand, section, etc.)
# ------------------------------------------------------------------
@app.route('/api/login', methods=['POST'])
def login():
    data     = request.get_json() or {}
    email    = data.get('email', '').strip()
    password = data.get('password', '').strip()

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password required."}), 400

    conn = get_db()
    if not conn:
        return jsonify({"success": False, "message": "Database connection failed."}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT u.studentID,
                   u.first_name,
                   u.last_name,
                   u.email,
                   u.password,
                   u.section,
                   u.profile_picture,
                   s.strand_name
            FROM   users u
                 LEFT JOIN strands s ON u.strand_id = s.strand_id
            WHERE  u.email = %s
        """, (email,))
        user = cursor.fetchone()
    finally:
        conn.close()

    if not user or not verify_password(user["password"], password):
        return jsonify({"success": False, "message": "Invalid email or password."}), 401

    return jsonify({
        "success":   True,
        "studentID": user["studentID"],
        "firstName": user["first_name"],
        "lastName":  user["last_name"],
            "name":      format_full_name(user["first_name"], user["last_name"]),
        "email":     user["email"],
        "section":   user["section"] or "",
            "strand":    user["strand_name"] or "",
            "profilePictureUrl": profile_picture_path(user["profile_picture"])
    })


# ------------------------------------------------------------------
# REGISTER  —  POST /api/register
# Body: { "firstname", "lastname", "email", "password",
#         "strand", "section" (optional) }
# ------------------------------------------------------------------
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json() or {}

    firstname = data.get('firstname', '').strip()
    lastname  = data.get('lastname', '').strip()
    email     = data.get('email', '').strip()
    password  = data.get('password', '').strip()
    strand    = data.get('strand', '').strip()
    section   = data.get('section', '').strip()

    if not all([firstname, lastname, email, password, strand]):
        return jsonify({"success": False, "message": "Please fill in all fields."}), 400

    if not is_valid_email(email):
        return jsonify({
            "success": False,
            "message": "Please enter a complete email address, such as example@gmail.com."
        }), 400

    password_errors = password_validation_errors(password)
    if password_errors:
        return jsonify({
            "success": False,
            "message": password_requirements_message(password_errors)
        }), 400

    conn = get_db()
    if not conn:
        return jsonify({"success": False, "message": "Database connection failed."}), 500

    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT studentID FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({
                "success": False,
                "message": "This email is already registered. Please log in or use another email."
            }), 409

        strand_id = get_or_create_strand_id(cursor, strand)

        cursor.execute("""
            INSERT INTO users (first_name, last_name, email, password, strand_id, section, profile_picture)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (firstname, lastname, email, hash_password(password), strand_id, section or None, None))
        conn.commit()

        new_id = cursor.lastrowid
        email_notice = ""
        try:
            send_registration_email(email, format_full_name(firstname, lastname))
        except Exception as mail_error:
            email_notice = public_email_error_message(mail_error)
            print(f"[EMAIL REGISTER ERROR] {mail_error}")

        return jsonify({
            "success":   True,
            "studentID": new_id,
            "firstName": firstname,
            "lastName":  lastname,
            "name":      format_full_name(firstname, lastname),
            "email":     email,
            "section":   section,
            "strand":    strand,
            "profilePictureUrl": "",
            "emailNotice": email_notice
        })

    except Error as e:
        print(f"[DB REGISTER ERROR] {e}")
        return jsonify({"success": False, "message": "Registration failed."}), 500
    finally:
        conn.close()


# ------------------------------------------------------------------
# FORGOT PASSWORD CODE  —  POST /api/forgot-password/send-code
# Body: { "email": "..." }
# ------------------------------------------------------------------
@app.route('/api/forgot-password/send-code', methods=['POST'])
def send_forgot_password_code():
    data = request.get_json() or {}
    email = data.get('email', '').strip()

    if not email:
        return jsonify({"success": False, "message": "Email is required."}), 400

    if not is_valid_email(email):
        return jsonify({
            "success": False,
            "message": "Please enter a complete email address, such as example@gmail.com."
        }), 400

    conn = get_db()
    if not conn:
        return jsonify({"success": False, "message": "Database connection failed."}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT studentID FROM users WHERE email = %s", (email,))
        if not cursor.fetchone():
            return jsonify({"success": False, "message": "No account found with that email."}), 404

        reset_code = f"{secrets.randbelow(1000000):06d}"
        expires_at = datetime.utcnow() + timedelta(minutes=RESET_CODE_MINUTES)

        cursor.execute(
            "UPDATE password_reset_codes SET used_at = %s WHERE email = %s AND used_at IS NULL",
            (datetime.utcnow(), email)
        )
        cursor.execute("""
            INSERT INTO password_reset_codes (email, code_hash, expires_at)
            VALUES (%s, %s, %s)
        """, (email, code_hash(reset_code), expires_at))

        try:
            send_reset_code_email(email, reset_code)
        except Exception as mail_error:
            conn.rollback()
            print(f"[EMAIL RESET ERROR] {mail_error}")
            return jsonify({
                "success": False,
                "message": public_email_error_message(mail_error)
            }), 500

        conn.commit()
        return jsonify({
            "success": True,
            "message": f"Verification code sent. It expires in {RESET_CODE_MINUTES} minutes."
        })
    except Error as e:
        print(f"[DB RESET CODE ERROR] {e}")
        return jsonify({"success": False, "message": "Could not create reset code."}), 500
    finally:
        conn.close()


# ------------------------------------------------------------------
# RESET PASSWORD  —  POST /api/reset-password
# Body: { "email": "...", "code": "...", "new_password": "..." }
# ------------------------------------------------------------------
@app.route('/api/reset-password', methods=['POST'])
def reset_password():
    data         = request.get_json() or {}
    email        = data.get('email', '').strip()
    code         = data.get('code', '').strip()
    new_password = data.get('new_password', '').strip()

    if not email or not code or not new_password:
        return jsonify({"success": False, "message": "Email, code, and new password are required."}), 400

    if not is_valid_email(email):
        return jsonify({
            "success": False,
            "message": "Please enter a complete email address, such as example@gmail.com."
        }), 400

    password_errors = password_validation_errors(new_password)
    if password_errors:
        return jsonify({
            "success": False,
            "message": password_requirements_message(password_errors)
        }), 400

    conn = get_db()
    if not conn:
        return jsonify({"success": False, "message": "Database connection failed."}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT studentID FROM users WHERE email = %s", (email,))
        if not cursor.fetchone():
            return jsonify({"success": False, "message": "No account found with that email."}), 404

        cursor.execute("""
            SELECT id, code_hash
            FROM password_reset_codes
            WHERE email = %s AND used_at IS NULL AND expires_at > %s
            ORDER BY created_at DESC, id DESC
            LIMIT 1
        """, (email, datetime.utcnow()))
        reset_row = cursor.fetchone()

        if not reset_row or not secrets.compare_digest(reset_row["code_hash"], code_hash(code)):
            return jsonify({"success": False, "message": "Invalid or expired verification code."}), 400

        cursor.execute("UPDATE users SET password = %s WHERE email = %s", (hash_password(new_password), email))
        cursor.execute(
            "UPDATE password_reset_codes SET used_at = %s WHERE id = %s",
            (datetime.utcnow(), reset_row["id"])
        )
        conn.commit()
        return jsonify({"success": True, "message": "Password updated successfully."})

    except Error as e:
        print(f"[DB RESET ERROR] {e}")
        return jsonify({"success": False, "message": "Could not reset password."}), 500
    finally:
        conn.close()


# ------------------------------------------------------------------
# CHANGE PASSWORD  —  POST /api/change-password
# Body: { "student_id": 1, "current_password": "...", "new_password": "..." }
# ------------------------------------------------------------------
@app.route('/api/change-password', methods=['POST'])
def change_password():
    data = request.get_json() or {}
    student_id = data.get('student_id')
    current_password = data.get('current_password', '').strip()
    new_password = data.get('new_password', '').strip()

    if not student_id or not current_password or not new_password:
        return jsonify({
            "success": False,
            "message": "Student ID, current password, and new password are required."
        }), 400

    password_errors = password_validation_errors(new_password)
    if password_errors:
        return jsonify({
            "success": False,
            "message": password_requirements_message(password_errors)
        }), 400

    conn = get_db()
    if not conn:
        return jsonify({"success": False, "message": "Database connection failed."}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT studentID, password FROM users WHERE studentID = %s", (student_id,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"success": False, "message": "Student not found."}), 404

        if not verify_password(user["password"], current_password):
            return jsonify({"success": False, "message": "Current password is incorrect."}), 401

        cursor.execute(
            "UPDATE users SET password = %s WHERE studentID = %s",
            (hash_password(new_password), student_id)
        )
        conn.commit()
        return jsonify({"success": True, "message": "Password changed successfully."})
    except Error as e:
        print(f"[DB CHANGE PASSWORD ERROR] {e}")
        return jsonify({"success": False, "message": "Could not change password."}), 500
    finally:
        conn.close()


# ==================================================================
#  LEADERBOARD ENDPOINT
# ==================================================================

# ------------------------------------------------------------------
# GET /api/leaderboard
# Returns top 50 students ranked by:
#   1. total_score DESC (highest first)
#   2. time_taken_seconds ASC (fastest first on tie)
# Each student's BEST attempt is shown.
# ------------------------------------------------------------------
@app.route('/api/leaderboard', methods=['GET'])
def leaderboard():
    conn = get_db()
    if not conn:
        return jsonify({"success": False, "message": "Database connection failed."}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT
                u.studentID,
                u.first_name,
                u.last_name,
                u.section,
                u.profile_picture,
                s.strand_name,
                qr.total_score,
                qr.time_taken_seconds,
                qr.recommended_course,
                qr.alignment_score,
                qr.created_at
            FROM quiz_results qr
            JOIN users u ON u.studentID = qr.studentID
            LEFT JOIN strands s ON s.strand_id = u.strand_id
            ORDER BY qr.total_score DESC, qr.time_taken_seconds ASC, qr.created_at ASC
        """)
        rows = cursor.fetchall()

        cursor.execute("SELECT MAX(created_at) AS last_updated FROM quiz_results")
        latest_row = cursor.fetchone() or {}
    finally:
        conn.close()

    board = []
    seen_students = set()
    for row in rows:
        if row["studentID"] in seen_students:
            continue
        seen_students.add(row["studentID"])
        rank = len(board) + 1
        mins = (row["time_taken_seconds"] or 0) // 60
        secs = (row["time_taken_seconds"] or 0) % 60
        board.append({
            "rank":              rank,
            "studentID":         row["studentID"],
            "name":              format_full_name(row["first_name"], row["last_name"]),
            "section":           row["section"] or "—",
            "strand":            row["strand_name"] or "—",
            "total_score":       round(row["total_score"], 2),
            "time_taken_seconds": row["time_taken_seconds"] or 0,
            "time_display":      f"{mins}m {secs:02d}s",
            "recommended_course": row["recommended_course"] or "—",
            "alignment_score":    row["alignment_score"] or "",
            "profilePictureUrl":  profile_picture_path(row["profile_picture"]),
            "created_at":         row["created_at"].isoformat(sep=" ") if row["created_at"] else ""
        })

        if len(board) >= 50:
            break

    last_updated = latest_row.get("last_updated")
    return jsonify({
        "success": True,
        "leaderboard": board,
        "last_updated": last_updated.isoformat(sep=" ") if last_updated else ""
    })


@app.route('/api/profile/<int:student_id>', methods=['GET'])
def profile(student_id):
    conn = get_db()
    if not conn:
        return jsonify({"success": False, "message": "Database connection failed."}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT u.studentID, u.first_name, u.last_name, u.email, u.section, u.profile_picture, s.strand_name
            FROM users u
            LEFT JOIN strands s ON s.strand_id = u.strand_id
            WHERE u.studentID = %s
        """, (student_id,))
        user = cursor.fetchone()
    finally:
        conn.close()

    if not user:
        return jsonify({"success": False, "message": "Student not found."}), 404

    return jsonify({
        "success": True,
        "studentID": user["studentID"],
        "firstName": user["first_name"],
        "lastName": user["last_name"],
        "name": format_full_name(user["first_name"], user["last_name"]),
        "email": user["email"],
        "section": user["section"] or "",
        "strand": user["strand_name"] or "",
        "profilePictureUrl": profile_picture_path(user["profile_picture"])
    })


@app.route('/api/quiz-history/<int:student_id>', methods=['GET'])
def quiz_history(student_id):
    conn = get_db()
    if not conn:
        return jsonify({"success": False, "message": "Database connection failed."}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT
                id,
                total_score,
                time_taken_seconds,
                recommended_course,
                alignment_score,
                created_at
            FROM quiz_results
            WHERE studentID = %s
            ORDER BY created_at DESC, id DESC
        """, (student_id,))
        rows = cursor.fetchall()
    finally:
        conn.close()

    history = []
    for index, row in enumerate(rows, start=1):
        history.append({
            "attempt": index,
            "quiz_score": round(row["total_score"], 2),
            "recommended_course": row["recommended_course"] or "—",
            "course_match": row["alignment_score"] or "",
            "time_taken_seconds": row["time_taken_seconds"] or 0,
            "created_at": row["created_at"].isoformat(sep=" ") if row["created_at"] else ""
        })

    return jsonify({"success": True, "history": history})


@app.route('/api/profile-picture', methods=['POST'])
def upload_profile_picture():
    student_id = request.form.get('student_id', '').strip()
    picture = request.files.get('profile_picture')

    if not student_id:
        return jsonify({"success": False, "message": "Student ID is required."}), 400

    if not picture or not picture.filename:
        return jsonify({"success": False, "message": "Please choose an image to upload."}), 400

    if not is_allowed_image(picture.filename):
        return jsonify({"success": False, "message": "Only PNG, JPG, JPEG, GIF, and WEBP images are allowed."}), 400

    picture_bytes = picture.read()
    if len(picture_bytes) > MAX_PROFILE_PICTURE_BYTES:
        return jsonify({"success": False, "message": "Profile picture must be 1 MB or smaller."}), 400

    if not picture_bytes:
        return jsonify({"success": False, "message": "The uploaded image is empty."}), 400

    conn = get_db()
    if not conn:
        return jsonify({"success": False, "message": "Database connection failed."}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT studentID, profile_picture FROM users WHERE studentID = %s", (student_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"success": False, "message": "Student not found."}), 404

        original_name = secure_filename(picture.filename)
        _, file_ext = os.path.splitext(original_name)
        mime_extension = file_ext.lower().lstrip(".") or "jpeg"
        if mime_extension == "jpg":
            mime_extension = "jpeg"
        mime_type = f"image/{mime_extension}"
        encoded_image = base64.b64encode(picture_bytes).decode("ascii")
        profile_picture_value = f"data:{mime_type};base64,{encoded_image}"

        old_file = user.get("profile_picture")
        if old_file and not str(old_file).startswith("data:"):
            old_path = os.path.join(UPLOAD_FOLDER, old_file)
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except OSError:
                    pass

        cursor.execute(
            "UPDATE users SET profile_picture = %s WHERE studentID = %s",
            (profile_picture_value, student_id)
        )
        conn.commit()

        return jsonify({
            "success": True,
            "message": "Profile picture updated.",
            "profilePictureUrl": profile_picture_path(profile_picture_value)
        })
    except Error as e:
        print(f"[DB PROFILE ERROR] {e}")
        return jsonify({"success": False, "message": "Could not update profile picture."}), 500
    finally:
        conn.close()


@app.route('/api/email-assessment-result', methods=['POST'])
def email_assessment_result():
    data = request.get_json() or {}
    student_id = data.get("student_id")
    result = data.get("result") or {}

    if not student_id:
        return jsonify({"success": False, "message": "Student ID is required."}), 400

    if not result.get("recommended_course_title"):
        return jsonify({"success": False, "message": "Assessment result is required."}), 400

    conn = get_db()
    if not conn:
        return jsonify({"success": False, "message": "Database connection failed."}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT first_name, last_name, email
            FROM users
            WHERE studentID = %s
        """, (student_id,))
        user = cursor.fetchone()
    finally:
        conn.close()

    if not user:
        return jsonify({"success": False, "message": "Student not found."}), 404

    try:
        send_assessment_result_email(
            user["email"],
            format_full_name(user["first_name"], user["last_name"]),
            result
        )
        return jsonify({"success": True, "message": "Assessment result sent to your email."})
    except Exception as e:
        print(f"[EMAIL RESULT ERROR] {e}")
        return jsonify({"success": False, "message": public_email_error_message(e)}), 500


# ==================================================================
#  RECOMMENDATION ENGINE
# ==================================================================

@app.route('/api/recommend', methods=['POST'])
def recommend():
    data = request.get_json() or {}

    interests   = data.get('interests', '').lower()
    skills      = data.get('skills', '').lower()
    career_pref = data.get('career_preference', '').lower()
    preferences = data.get('preferences', '').lower()

    grades = data.get('grades', {})
    math_grade    = parse_valid_grade(grades.get('math',    0))
    english_grade = parse_valid_grade(grades.get('english', 0))
    science_grade = parse_valid_grade(grades.get('science', 0))

    if None in (math_grade, english_grade, science_grade):
        return jsonify({
            "success": False,
            "error": "Grades must be whole numbers from 0 to 99."
        }), 400

    quiz_scores      = data.get('quiz_scores', {})
    student_id       = data.get('student_id')
    time_taken_secs  = safe_int(data.get('time_taken_seconds', 0))

    courses = ["it", "marketing", "tourism", "beed", "bsed", "crim"]
    scores  = {
        c: {"interest": 0, "skill": 0, "career": 0,
            "academic": 0, "preference": 0, "quiz": 0}
        for c in courses
    }

    # ── INTEREST RULES (25%) ─────────────────────────────────────
    interest_weights = {
        "code": {"it": 100}, "computer": {"it": 100},
        "programming": {"it": 100}, "software": {"it": 100}, "gaming": {"it": 80},
        "business": {"marketing": 100}, "selling": {"marketing": 90},
        "entrepreneur": {"marketing": 100}, "social media": {"marketing": 80},
        "travel": {"tourism": 100}, "hotel": {"tourism": 90},
        "hospitality": {"tourism": 100}, "culture": {"tourism": 70},
        "teach": {"beed": 100, "bsed": 100}, "children": {"beed": 100},
        "kids": {"beed": 100}, "reading": {"bsed": 80},
        "law": {"crim": 100}, "police": {"crim": 100},
        "investigate": {"crim": 100}, "justice": {"crim": 90}
    }

    # ── SKILL RULES (20%) ────────────────────────────────────────
    skill_weights = {
        "programming": {"it": 100}, "logic": {"it": 80},
        "problem solving": {"it": 90},
        "finance": {"marketing": 100}, "sales": {"marketing": 90},
        "negotiation": {"marketing": 90},
        "communication": {"tourism": 100}, "customer service": {"tourism": 100},
        "patience": {"beed": 100}, "creativity": {"beed": 80},
        "writing": {"bsed": 100}, "english": {"bsed": 100},
        "public speaking": {"bsed": 90},
        "leadership": {"crim": 90}, "discipline": {"crim": 100}
    }

    # ── CAREER RULES (25%) ───────────────────────────────────────
    career_weights = {
        "developer": {"it": 100}, "programmer": {"it": 100},
        "software engineer": {"it": 100},
        "entrepreneur": {"marketing": 100}, "manager": {"marketing": 90},
        "businessman": {"marketing": 100},
        "flight attendant": {"tourism": 100}, "tour guide": {"tourism": 100},
        "hotel manager": {"tourism": 100},
        "teacher": {"beed": 100, "bsed": 100},
        "educator": {"beed": 100, "bsed": 100}, "professor": {"bsed": 100},
        "police": {"crim": 100}, "investigator": {"crim": 100},
        "criminologist": {"crim": 100}
    }

    # ── PREFERENCE RULES (5%) ────────────────────────────────────
    preference_weights = {
        "technology": {"it": 100}, "business": {"marketing": 100},
        "travel": {"tourism": 100}, "education": {"beed": 100, "bsed": 100},
        "public service": {"crim": 100},
        "ict": {"it": 100},
        "stem": {"it": 70, "bsed": 50, "beed": 35, "crim": 30},
        "abm": {"marketing": 100},
        "humss": {"beed": 80, "bsed": 80, "crim": 65, "marketing": 35},
        "techpro_tourism": {"tourism": 100, "marketing": 35},
        "techpro_culinary": {"tourism": 85, "marketing": 45}
    }

    for keyword, mapping in interest_weights.items():
        if keyword in interests:
            for c, v in mapping.items():
                scores[c]["interest"] += v

    for keyword, mapping in skill_weights.items():
        if keyword in skills:
            for c, v in mapping.items():
                scores[c]["skill"] += v

    for keyword, mapping in career_weights.items():
        if keyword in career_pref:
            for c, v in mapping.items():
                scores[c]["career"] += v

    for keyword, mapping in preference_weights.items():
        if keyword in preferences:
            for c, v in mapping.items():
                scores[c]["preference"] += v

    for c in courses:
        for k in ("interest", "skill", "career", "preference"):
            scores[c][k] = min(scores[c][k], 100)

    # ── ACADEMIC ROUTING (15%) ────────────────────────────────────
    scores["it"]["academic"]        = min((math_grade * 0.7) + (science_grade * 0.3), 100)
    scores["marketing"]["academic"] = min((math_grade * 0.5) + (english_grade * 0.5), 100)
    scores["tourism"]["academic"]   = min(english_grade, 100)
    scores["beed"]["academic"]      = min((english_grade * 0.5) + (science_grade * 0.5), 100)
    scores["bsed"]["academic"]      = min((english_grade * 0.5) + (math_grade * 0.5), 100)
    scores["crim"]["academic"]      = min((science_grade * 0.6) + (english_grade * 0.4), 100)

    # ── QUIZ SCORES (10%) ─────────────────────────────────────────
    quiz_map = {
        "it": "it", "beed": "beed", "bsed": "bsed",
        "marketing": "marketing", "tourism": "tourism", "criminology": "crim"
    }
    for fk, ck in quiz_map.items():
        scores[ck]["quiz"] = min(safe_float(quiz_scores.get(fk, 0)), 100)

    # ── WEIGHTED FINAL SCORE ──────────────────────────────────────
    final_scores = {}
    for c in courses:
        final_scores[c] = round(
            scores[c]["interest"]   * 0.25 +
            scores[c]["skill"]      * 0.20 +
            scores[c]["career"]     * 0.25 +
            scores[c]["academic"]   * 0.15 +
            scores[c]["preference"] * 0.05 +
            scores[c]["quiz"]       * 0.10,
            2
        )

    sorted_courses = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
    winner    = sorted_courses[0][0]
    runner_up = sorted_courses[1][0]

    course_metadata = {
        "it":        {"title": "Bachelor of Science in Information Technology (BSIT)",
                      "pathways": ["Software Engineer", "Web Developer", "Cybersecurity Analyst",
                                   "Network Administrator", "Database Administrator", "UI/UX Designer"]},
        "marketing": {"title": "Bachelor of Science in Marketing Management (BSMM)",
                      "pathways": ["Marketing Manager", "Brand Strategist", "Digital Marketer",
                                   "Sales Executive", "Entrepreneur", "Advertising Specialist"]},
        "tourism":   {"title": "Bachelor of Science in Tourism Management (BSTM)",
                      "pathways": ["Tour Guide", "Hotel Manager", "Flight Attendant",
                                   "Event Planner", "Travel Consultant", "Resort Manager"]},
        "beed":      {"title": "Bachelor of Elementary Education (BEED)",
                      "pathways": ["Elementary School Teacher", "Curriculum Developer",
                                   "School Counselor", "Education Administrator",
                                   "Child Development Specialist", "Literacy Coach"]},
        "bsed":      {"title": "Bachelor of Secondary Education (BSED)",
                      "pathways": ["High School Teacher", "Subject Specialist", "Department Head",
                                   "Education Researcher", "School Principal", "Academic Coordinator"]},
        "crim":      {"title": "Bachelor of Science in Criminology (BSCRIM)",
                      "pathways": ["Police Officer", "Criminologist", "Criminal Investigator",
                                   "Forensic Analyst", "Probation Officer", "Security Consultant"]}
    }

    top_score = sorted_courses[0][1]
    if top_score == 0:
        return jsonify({
            "recommended_course_title": "No strong match found",
            "alternative_course_title": "Please complete more sections",
            "alignment_score": "0%",
            "pathways": [],
            "scores": final_scores,
            "error": "Not enough input to generate a recommendation."
        })

    alignment_score = min(round(top_score), 99)

    # ── SAVE TO DATABASE ─────────────────────────────────────────
    if student_id:
        conn = get_db()
        if conn:
            try:
                cursor = conn.cursor()

                # Save to recommendations history. Newer deployments use course
                # title columns; older local DBs may still use course_id columns.
                try:
                    cursor.execute("""
                        INSERT INTO recommendations
                            (studentID, recommended_course, alternative_course, alignment_score)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        student_id,
                        course_metadata[winner]["title"],
                        course_metadata[runner_up]["title"],
                        f"{alignment_score}%"
                    ))
                except Error as text_insert_error:
                    try:
                        winner_course_id = get_course_id(cursor, winner)
                        runner_up_course_id = get_course_id(cursor, runner_up)
                        cursor.execute("""
                            INSERT INTO recommendations
                                (studentID, recommended_course_id, alternative_course_id, alignment_score)
                            VALUES (%s, %s, %s, %s)
                        """, (
                            student_id,
                            winner_course_id,
                            runner_up_course_id,
                            alignment_score
                        ))
                    except Error as id_insert_error:
                        print(f"[DB RECOMMENDATION SAVE ERROR] {text_insert_error}; {id_insert_error}")

                # Compute a total_score for the leaderboard:
                # average of the 6 per-category quiz percentages (0-100 each)
                quiz_vals   = [safe_float(v) for v in quiz_scores.values()]
                quiz_avg    = (sum(quiz_vals) / len(quiz_vals)) if quiz_vals else 0.0
                total_score = round(
                    (alignment_score * 0.60) + (quiz_avg * 0.40), 2
                )

                cursor.execute("""
                    INSERT INTO quiz_results
                        (studentID, total_score, time_taken_seconds, recommended_course, alignment_score)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    student_id,
                    total_score,
                    time_taken_secs,
                    course_metadata[winner]["title"],
                    f"{alignment_score}%"
                ))

                conn.commit()
            except Error as e:
                print(f"[DB SAVE ERROR] {e}")
            finally:
                conn.close()

    return jsonify({
        "recommended_course_title": course_metadata[winner]["title"],
        "alternative_course_title": course_metadata[runner_up]["title"],
        "alignment_score":          f"{alignment_score}%",
        "pathways":                 course_metadata[winner]["pathways"],
        "scores":                   final_scores,
        "recommended_course_key":   winner,
        "alternative_course_key":   runner_up,
        "category_scores":          scores,
        "weights": {
            "interest": 25,
            "skill": 20,
            "career": 25,
            "academic": 15,
            "preference": 5,
            "quiz": 10
        },
        "course_matches": [
            {
                "key": course_key,
                "title": course_metadata[course_key]["title"],
                "score": score
            }
            for course_key, score in sorted_courses
        ]
    })


if __name__ == "__main__":
    run_startup_migrations()
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
