import os
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
import models
import seed_data

app = Flask(__name__)
# Restrict request payload size to 1MB to prevent memory exhaustion / DoS
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024

# Security: In-memory rate limiting trackers (IP -> list of timestamps)
_login_failures = defaultdict(list)
_register_attempts = defaultdict(list)
_general_requests = defaultdict(list)

def get_client_ip():
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "127.0.0.1"

def is_rate_limited(ip, tracker, limit, window_seconds):
    now = time.time()
    timestamps = tracker.get(ip, [])
    valid_ts = [ts for ts in timestamps if now - ts < window_seconds]
    tracker[ip] = valid_ts
    return len(valid_ts) >= limit

def record_attempt(ip, tracker):
    if ip not in tracker:
        tracker[ip] = []
    tracker[ip].append(time.time())

def clear_failures(ip, tracker):
    if ip in tracker:
        del tracker[ip]

DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")

def validate_date(date_str):
    if not date_str or not isinstance(date_str, str) or not DATE_REGEX.match(date_str.strip()):
        return None
    try:
        datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return date_str.strip()
    except ValueError:
        return None

def sanitize_str(val, max_len=80, default=""):
    if not val or not isinstance(val, str):
        return default
    cleaned = "".join(ch for ch in val if ch.isprintable()).strip()
    return cleaned[:max_len]

# Predefined popular exercises for quick selection & autocomplete
DEFAULT_EXERCISES = [
    {"name": "Press de Banca", "muscle": "Pecho"},
    {"name": "Press Inclinado con Mancuernas", "muscle": "Pecho"},
    {"name": "Aperturas en Polea", "muscle": "Pecho"},
    {"name": "Fondos en Paralelas", "muscle": "Tríceps / Pecho"},
    {"name": "Dominadas", "muscle": "Espalda"},
    {"name": "Remo con Barra", "muscle": "Espalda"},
    {"name": "Jalón al Pecho", "muscle": "Espalda"},
    {"name": "Remo Gironda", "muscle": "Espalda"},
    {"name": "Sentadilla con Barra", "muscle": "Piernas"},
    {"name": "Hip Thrust", "muscle": "Piernas"},
    {"name": "Prensa de Piernas", "muscle": "Piernas"},
    {"name": "Peso Muerto Rumano", "muscle": "Piernas / Isquios"},
    {"name": "Sentadilla Búlgara", "muscle": "Piernas"},
    {"name": "Zancadas / Lunges", "muscle": "Piernas"},
    {"name": "Extensiones de Cuádriceps", "muscle": "Piernas"},
    {"name": "Curl Femoral Tumbado", "muscle": "Piernas"},
    {"name": "Puente de Glúteos", "muscle": "Piernas"},
    {"name": "Abductores en Máquina", "muscle": "Piernas"},
    {"name": "Elevación de Talones (Gemelos)", "muscle": "Piernas"},
    {"name": "Press Militar con Barra", "muscle": "Hombros"},
    {"name": "Press Militar Mancuernas", "muscle": "Hombros"},
    {"name": "Elevaciones Laterales", "muscle": "Hombros"},
    {"name": "Pájaros con Mancuerna", "muscle": "Hombros"},
    {"name": "Curl con Barra Z", "muscle": "Bíceps"},
    {"name": "Curl Martillo con Mancuernas", "muscle": "Bíceps"},
    {"name": "Extensiones de Tríceps en Polea", "muscle": "Tríceps"},
    {"name": "Press Francés", "muscle": "Tríceps"},
    {"name": "Plancha Abdominal", "muscle": "Core"},
    {"name": "Elevaciones de Piernas Colgado", "muscle": "Core"}
]

# Initialize database and execute auto-migrations on startup
with app.app_context():
    models.init_db()
    try:
        with models.get_db() as conn:
            # Fix any mistakenly assigned muscle groups
            conn.execute("UPDATE exercise_logs SET muscle_group = 'Piernas' WHERE LOWER(TRIM(exercise_name)) LIKE '%hip thrust%'")
            conn.commit()
    except Exception as e:
        print("Migration notice:", e)

BLOCKED_PATH_PATTERNS = [
    r"\.\.",                                                 # Path traversal
    r"\.(git|env|db|sqlite|py|sh|yaml|yml|bak|log|ini|cfg)$", # Forbidden file extensions
    r"^/(\.env|\.git|proc|sys|etc|database\.db)",             # Sensitive roots
]

@app.before_request
def security_shield():
    path = request.path.lower()
    raw_query = request.query_string.decode("utf-8", errors="ignore").lower()

    for pattern in BLOCKED_PATH_PATTERNS:
        if re.search(pattern, path) or re.search(pattern, raw_query):
            return jsonify({"error": "Acceso denegado. Recurso no permitido."}), 403

    # Prevent general DoS abuse (max 150 requests per minute per IP, skip in tests)
    if not app.config.get("TESTING", False):
        ip = get_client_ip()
        if is_rate_limited(ip, _general_requests, limit=150, window_seconds=60):
            return jsonify({"error": "Demasiadas solicitudes. Por favor espera un momento."}), 429
        record_attempt(ip, _general_requests)

@app.after_request
def add_security_headers(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://accounts.google.com https://unpkg.com https://cdn.tailwindcss.com https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://accounts.google.com https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://accounts.google.com; "
        "frame-src https://accounts.google.com; "
        "object-src 'none'; "
        "base-uri 'self';"
    )
    response.headers["Server"] = "FitChallenge-Protegido"
    return response

@app.errorhandler(413)
def request_entity_too_large(e):
    return jsonify({"error": "La solicitud enviada es demasiado grande (máximo 1MB)"}), 413

@app.errorhandler(403)
def forbidden(e):
    return jsonify({"error": "Acceso denegado"}), 403

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Recurso no encontrado"}), 404
    return render_template("index.html", google_client_id=os.environ.get("GOOGLE_CLIENT_ID", "")), 200

@app.errorhandler(500)
def internal_server_error(e):
    return jsonify({"error": "Error interno del servidor. Tu información está protegida."}), 500

def get_auth_token():
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return request.args.get("token", "").strip() or None

def get_current_user():
    token = get_auth_token()
    if not token:
        return None
    return models.get_user_by_token(token)

def require_auth():
    user = get_current_user()
    if not user:
        return None, (jsonify({"error": "No autorizado. Inicia sesión para continuar."}), 401)
    return user, None

@app.route("/")
def index():
    google_client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    return render_template("index.html", google_client_id=google_client_id)

# ==========================================
# AUTHENTICATION ENDPOINTS
# ==========================================

@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    ip = get_client_ip()
    if not app.config.get("TESTING", False) and is_rate_limited(ip, _register_attempts, limit=5, window_seconds=600):
        return jsonify({"error": "Demasiados registros desde tu dirección. Espera 10 minutos."}), 429

    data = request.get_json(silent=True) or {}
    username = sanitize_str(data.get("username", ""), max_len=50)
    password = str(data.get("password", "")).strip()
    name = sanitize_str(data.get("name", ""), max_len=60)
    email = sanitize_str(data.get("email", ""), max_len=120)

    user, err = models.create_user(username, password, name=name, email=email)
    if err:
        return jsonify({"error": err}), 400

    record_attempt(ip, _register_attempts)
    token = models.create_session(user["id"])
    return jsonify({
        "status": "ok",
        "message": f"¡Bienvenido a FitChallenge, {user['name']}!",
        "token": token,
        "user": user
    })

@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    ip = get_client_ip()
    if not app.config.get("TESTING", False) and is_rate_limited(ip, _login_failures, limit=5, window_seconds=300):
        return jsonify({"error": "Demasiados intentos fallidos. Por seguridad, espera 5 minutos."}), 429

    data = request.get_json(silent=True) or {}
    username = sanitize_str(data.get("username", ""), max_len=120)
    password = str(data.get("password", "")).strip()

    user, err = models.authenticate_user(username, password)
    if err:
        record_attempt(ip, _login_failures)
        return jsonify({"error": err}), 401

    clear_failures(ip, _login_failures)
    token = models.create_session(user["id"])
    return jsonify({
        "status": "ok",
        "message": f"¡Hola de nuevo, {user['name']}!",
        "token": token,
        "user": user
    })

@app.route("/api/auth/google", methods=["POST"])
def auth_google():
    import urllib.request
    import json
    data = request.get_json() or {}
    credential = data.get("credential", "").strip()
    if not credential:
        return jsonify({"error": "Credencial de Google no recibida"}), 400

    try:
        verify_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={credential}"
        req = urllib.request.Request(verify_url, headers={"User-Agent": "FitChallenge-App"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            google_info = json.loads(resp.read().decode())
    except Exception as e:
        print("Google token verification failed:", e)
        return jsonify({"error": "No se pudo verificar la cuenta de Google con los servidores de Google"}), 400

    email = google_info.get("email")
    name = google_info.get("name") or google_info.get("given_name")
    if not email:
        return jsonify({"error": "No se obtuvo un correo válido de Google"}), 400

    user, err = models.find_or_create_google_user(email, name=name)
    if err:
        return jsonify({"error": err}), 400

    token = models.create_session(user["id"])
    return jsonify({
        "status": "ok",
        "message": f"¡Bienvenido, {user['name']}!",
        "token": token,
        "user": user
    })

@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    user, err = require_auth()
    if err:
        return err
    return jsonify({"user": user})

@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    token = get_auth_token()
    if token:
        models.delete_session(token)
    return jsonify({"status": "ok", "message": "Sesión cerrada correctamente"})

# ==========================================
# WORKOUT AND EXERCISE ENDPOINTS
# ==========================================

@app.route("/api/popular_exercises", methods=["GET"])
def get_popular_exercises():
    user = get_current_user()
    logged = []
    if user:
        with models.get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT DISTINCT el.exercise_name, el.muscle_group 
                FROM exercise_logs el
                JOIN workouts w ON el.workout_id = w.id
                WHERE w.user_id = ?
            """, (user["id"],))
            logged = [{"name": row["exercise_name"], "muscle": row["muscle_group"]} for row in cur.fetchall()]

    # Merge unique exercises - prioritize DEFAULT_EXERCISES
    names_seen = set()
    result = []
    for item in DEFAULT_EXERCISES:
        normalized = item["name"].strip().lower()
        if normalized not in names_seen:
            names_seen.add(normalized)
            result.append(item)

    for item in logged:
        normalized = item["name"].strip().lower()
        if normalized not in names_seen:
            names_seen.add(normalized)
            result.append(item)

    return jsonify({"exercises": result})

@app.route("/api/workout", methods=["GET"])
def get_workout():
    user, err = require_auth()
    if err:
        return err
    date_str = validate_date(request.args.get("date"))
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    with models.get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM workouts WHERE user_id = ? AND date = ?", (user["id"], date_str))
        row = cur.fetchone()
        if not row:
            # Return empty skeleton
            return jsonify({
                "workout": {
                    "id": None,
                    "user_id": user["id"],
                    "date": date_str,
                    "title": "",
                    "notes": "",
                    "exercises": []
                }
            })
        
        workout_data = models.get_workout_details(row, conn)
        return jsonify({"workout": workout_data})

@app.route("/api/workout", methods=["POST"])
def save_workout_meta():
    user, err = require_auth()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    date_str = validate_date(data.get("date"))
    if not date_str:
        return jsonify({"error": "Fecha requerida (formato YYYY-MM-DD)"}), 400

    title = sanitize_str(data.get("title", ""), max_len=100)
    notes = sanitize_str(data.get("notes", ""), max_len=500)

    with models.get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO workouts (user_id, date, title, notes)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, date) DO UPDATE SET title = excluded.title, notes = excluded.notes
        """, (user["id"], date_str, title, notes))
        conn.commit()

        cur.execute("SELECT * FROM workouts WHERE user_id = ? AND date = ?", (user["id"], date_str))
        row = cur.fetchone()
        workout_data = models.get_workout_details(row, conn)
        return jsonify({"workout": workout_data})

@app.route("/api/exercise", methods=["POST"])
def add_exercise():
    user, err = require_auth()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    date_str = validate_date(data.get("date"))
    if not date_str:
        return jsonify({"error": "Fecha requerida (formato YYYY-MM-DD)"}), 400

    exercise_name = sanitize_str(data.get("exercise_name", ""), max_len=80)
    muscle_group = sanitize_str(data.get("muscle_group", "General"), max_len=40, default="General")
    notes = sanitize_str(data.get("notes", ""), max_len=500, default="")
    sets = data.get("sets", [])

    if not exercise_name:
        return jsonify({"error": "Nombre de ejercicio requerido"}), 400

    if not isinstance(sets, list) or len(sets) == 0:
        return jsonify({"error": "Debes agregar al menos una serie"}), 400

    with models.get_db() as conn:
        cur = conn.cursor()
        # Ensure workout exists for this user and date
        cur.execute("""
            INSERT INTO workouts (user_id, date, title, notes)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, date) DO NOTHING
        """, (user["id"], date_str, f"Entrenamiento del {date_str}", ""))
        
        cur.execute("SELECT id FROM workouts WHERE user_id = ? AND date = ?", (user["id"], date_str))
        workout_id = cur.fetchone()["id"]

        # Insert exercise log
        cur.execute("""
            INSERT INTO exercise_logs (workout_id, exercise_name, muscle_group, notes)
            VALUES (?, ?, ?, ?)
        """, (workout_id, exercise_name, muscle_group, notes))
        exercise_log_id = cur.lastrowid

        # Insert bounded sets (max 50 sets to prevent abuse)
        for idx, s in enumerate(sets[:50], start=1):
            try:
                reps = max(1, min(int(s.get("reps", 0)), 500))
                weight = max(0.0, min(float(s.get("weight", 0) or 0), 1000.0))
                rpe_raw = s.get("rpe")
                rpe = max(1.0, min(float(rpe_raw), 10.0)) if rpe_raw is not None and str(rpe_raw).strip() != "" else None
            except (ValueError, TypeError):
                reps = 10
                weight = 0.0
                rpe = None

            cur.execute("""
                INSERT INTO set_logs (exercise_log_id, set_number, reps, weight, rpe)
                VALUES (?, ?, ?, ?, ?)
            """, (exercise_log_id, idx, reps, weight, rpe))

        conn.commit()

        # Return full updated workout
        cur.execute("SELECT * FROM workouts WHERE id = ?", (workout_id,))
        row = cur.fetchone()
        workout_data = models.get_workout_details(row, conn)
        return jsonify({"workout": workout_data})

@app.route("/api/exercise/<int:exercise_id>", methods=["DELETE"])
def delete_exercise(exercise_id):
    user, err = require_auth()
    if err:
        return err
    with models.get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT el.workout_id 
            FROM exercise_logs el
            JOIN workouts w ON el.workout_id = w.id
            WHERE el.id = ? AND w.user_id = ?
        """, (exercise_id, user["id"]))
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "Ejercicio no encontrado o no autorizado"}), 404
        workout_id = row["workout_id"]

        cur.execute("DELETE FROM exercise_logs WHERE id = ?", (exercise_id,))
        conn.commit()

        cur.execute("SELECT * FROM workouts WHERE id = ?", (workout_id,))
        w_row = cur.fetchone()
        workout_data = models.get_workout_details(w_row, conn) if w_row else None
        return jsonify({"workout": workout_data})

@app.route("/api/exercise/last", methods=["GET"])
def get_last_exercise_occurrence():
    user, err = require_auth()
    if err:
        return err
    exercise_name = sanitize_str(request.args.get("name", ""), max_len=80)
    before_date = validate_date(request.args.get("before_date"))
    if not exercise_name:
        return jsonify({"last_session": None})

    last_session = models.get_last_session_for_exercise_name(exercise_name, user["id"], before_date)
    return jsonify({"last_session": last_session})

@app.route("/api/exercise/history", methods=["GET"])
def get_exercise_history():
    user, err = require_auth()
    if err:
        return err
    name = sanitize_str(request.args.get("name", ""), max_len=80)
    if not name:
        return jsonify({"history": []})
    history = models.get_exercise_all_history(name, user["id"])
    return jsonify({"history": history})

@app.route("/api/exercise/update_muscle_group", methods=["POST"])
def update_exercise_muscle_group():
    user, err = require_auth()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    exercise_name = sanitize_str(data.get("exercise_name", ""), max_len=80)
    new_muscle = sanitize_str(data.get("muscle_group", "Piernas"), max_len=40, default="Piernas")
    if not exercise_name:
        return jsonify({"error": "Nombre de ejercicio requerido"}), 400
    with models.get_db() as conn:
        conn.execute("""
            UPDATE exercise_logs 
            SET muscle_group = ? 
            WHERE LOWER(TRIM(exercise_name)) = LOWER(TRIM(?))
              AND workout_id IN (SELECT id FROM workouts WHERE user_id = ?)
        """, (new_muscle, exercise_name, user["id"]))
        conn.commit()
    return jsonify({"status": "ok", "message": f"Grupo de '{exercise_name}' actualizado a '{new_muscle}'"})

@app.route("/api/exercise/delete_by_name", methods=["POST"])
def delete_exercise_by_name():
    user, err = require_auth()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    exercise_name = sanitize_str(data.get("exercise_name", ""), max_len=80)
    if not exercise_name:
        return jsonify({"error": "Nombre de ejercicio requerido"}), 400
    with models.get_db() as conn:
        conn.execute("""
            DELETE FROM exercise_logs 
            WHERE LOWER(TRIM(exercise_name)) = LOWER(TRIM(?))
              AND workout_id IN (SELECT id FROM workouts WHERE user_id = ?)
        """, (exercise_name, user["id"]))
        conn.commit()
    return jsonify({"status": "ok", "message": f"Ejercicio '{exercise_name}' eliminado completamente"})

@app.route("/api/weekly", methods=["GET"])
def get_weekly():
    user, err = require_auth()
    if err:
        return err
    date_str = validate_date(request.args.get("date"))
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    report = models.get_weekly_analytics(date_str, user["id"])
    return jsonify(report)

@app.route("/api/seed", methods=["POST"])
def seed():
    user, err = require_auth()
    if err:
        return err
    seed_data.populate_seed_data(user_id=user["id"])
    return jsonify({"status": "ok", "message": "Datos de ejemplo cargados exitosamente"})

@app.route("/api/reset", methods=["POST"])
def reset():
    user, err = require_auth()
    if err:
        return err
    with models.get_db() as conn:
        conn.execute("DELETE FROM workouts WHERE user_id = ?", (user["id"],))
        conn.commit()
    return jsonify({"status": "ok", "message": "Tus datos de entrenamiento han sido reiniciados"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Iniciando servicio de entrenamiento seguro en http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
