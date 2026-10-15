import sqlite3
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash, check_password_hash

try:
    import psycopg2
    import psycopg2.extras
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")

def get_database_url():
    url = os.environ.get("DATABASE_URL", "").strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url or None

class PostgresCursorWrapper:
    def __init__(self, pg_cursor):
        self.cur = pg_cursor
        self._last_id = None

    def execute(self, query, params=None):
        converted_query = re.sub(r'\?', '%s', query)
        if converted_query.strip().upper().startswith("PRAGMA"):
            return self

        is_insert = converted_query.strip().upper().startswith("INSERT INTO")
        has_returning = "RETURNING" in converted_query.upper()
        if is_insert and not has_returning:
            converted_query += " RETURNING id"

        if params is not None:
            self.cur.execute(converted_query, params)
        else:
            self.cur.execute(converted_query)

        if is_insert:
            try:
                row = self.cur.fetchone()
                if row:
                    if isinstance(row, dict) and "id" in row:
                        self._last_id = row["id"]
                    elif hasattr(row, "__getitem__"):
                        self._last_id = row[0]
            except Exception:
                pass
        return self

    def executemany(self, query, params_list):
        converted_query = re.sub(r'\?', '%s', query)
        return self.cur.executemany(converted_query, params_list)

    def fetchone(self):
        return self.cur.fetchone()

    def fetchall(self):
        return self.cur.fetchall()

    @property
    def lastrowid(self):
        return self._last_id

    def __iter__(self):
        return iter(self.cur)

class PostgresConnectionWrapper:
    def __init__(self, pg_conn):
        self.conn = pg_conn

    def cursor(self):
        return PostgresCursorWrapper(self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor))

    def execute(self, query, params=None):
        cur = self.cursor()
        cur.execute(query, params)
        return cur

    def executescript(self, script):
        with self.conn.cursor() as cur:
            cur.execute(script)
        self.conn.commit()

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()

def init_postgres_db(db_url):
    import seed_data
    with psycopg2.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                name VARCHAR(100),
                email VARCHAR(150) UNIQUE,
                recovery_question TEXT,
                recovery_answer_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS user_sessions (
                token VARCHAR(100) PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS workouts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                date VARCHAR(20) NOT NULL,
                title TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, date)
            );

            CREATE TABLE IF NOT EXISTS exercise_logs (
                id SERIAL PRIMARY KEY,
                workout_id INTEGER NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
                exercise_name VARCHAR(100) NOT NULL,
                muscle_group VARCHAR(50),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS set_logs (
                id SERIAL PRIMARY KEY,
                exercise_log_id INTEGER NOT NULL REFERENCES exercise_logs(id) ON DELETE CASCADE,
                set_number INTEGER NOT NULL,
                reps INTEGER NOT NULL,
                weight NUMERIC NOT NULL,
                rpe NUMERIC,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS password_resets (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                reset_code VARCHAR(20) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                used INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS popular_exercises (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                muscle_group VARCHAR(50) NOT NULL
            );
            """)

            cur.execute("SELECT COUNT(*) FROM popular_exercises")
            count = cur.fetchone()[0]
            if count == 0:
                for item in seed_data.DEFAULT_POPULAR_EXERCISES:
                    cur.execute(
                        "INSERT INTO popular_exercises (name, muscle_group) VALUES (%s, %s) ON CONFLICT (name) DO NOTHING",
                        (item["name"], item["muscle_group"])
                    )
        conn.commit()

def get_db(db_path=None):
    db_url = get_database_url()
    if db_url and PSYCOPG2_AVAILABLE and db_path is None:
        conn = psycopg2.connect(db_url)
        return PostgresConnectionWrapper(conn)

    if db_path is None:
        db_path = DB_PATH
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db(db_path=None):
    db_url = get_database_url()
    if db_url and PSYCOPG2_AVAILABLE and db_path is None:
        init_postgres_db(db_url)
        return

    with get_db(db_path) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            name TEXT,
            email TEXT UNIQUE COLLATE NOCASE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS user_sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)

        # Migration check: check if users table lacks email or recovery fields
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(users)")
        u_columns = [row[1] for row in cur.fetchall()]
        if "email" not in u_columns:
            conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        if "recovery_question" not in u_columns:
            conn.execute("ALTER TABLE users ADD COLUMN recovery_question TEXT")
        if "recovery_answer_hash" not in u_columns:
            conn.execute("ALTER TABLE users ADD COLUMN recovery_answer_hash TEXT")

        conn.executescript("""
        CREATE TABLE IF NOT EXISTS password_resets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            reset_code TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            used INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_password_resets_user ON password_resets(user_id, reset_code);
        """)

        # Check workouts table
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='workouts'")
        workouts_exists = cur.fetchone() is not None

        if not workouts_exists:
            conn.executescript("""
            CREATE TABLE workouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                date TEXT NOT NULL, -- YYYY-MM-DD
                title TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id, date)
            );
            """)
        else:
            cur.execute("PRAGMA table_info(workouts)")
            columns = [row[1] for row in cur.fetchall()]
            if "user_id" not in columns:
                conn.execute("PRAGMA foreign_keys = OFF")
                cur.execute("SELECT id FROM users LIMIT 1")
                default_user = cur.fetchone()
                if not default_user:
                    secure_pwd = secrets.token_urlsafe(32)
                    cur.execute(
                        "INSERT INTO users (username, password_hash, name) VALUES (?, ?, ?)",
                        ("admin", generate_password_hash(secure_pwd), "Administrador")
                    )
                    default_user_id = cur.lastrowid
                else:
                    default_user_id = default_user[0]

                cur.executescript(f"""
                CREATE TABLE workouts_migrated (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL DEFAULT {default_user_id},
                    date TEXT NOT NULL,
                    title TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(user_id, date)
                );
                INSERT INTO workouts_migrated (id, user_id, date, title, notes, created_at)
                SELECT id, {default_user_id}, date, title, notes, created_at FROM workouts;

                DROP TABLE workouts;
                ALTER TABLE workouts_migrated RENAME TO workouts;
                """)
                conn.execute("PRAGMA foreign_keys = ON")

        conn.executescript("""
        CREATE TABLE IF NOT EXISTS exercise_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_id INTEGER NOT NULL,
            exercise_name TEXT NOT NULL,
            muscle_group TEXT DEFAULT 'General',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (workout_id) REFERENCES workouts(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS set_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exercise_log_id INTEGER NOT NULL,
            set_number INTEGER NOT NULL,
            reps INTEGER NOT NULL,
            weight REAL DEFAULT 0,
            rpe REAL,
            FOREIGN KEY (exercise_log_id) REFERENCES exercise_logs(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_workouts_user_date ON workouts(user_id, date);
        CREATE INDEX IF NOT EXISTS idx_exercise_name ON exercise_logs(exercise_name);
        CREATE INDEX IF NOT EXISTS idx_exercise_workout ON exercise_logs(workout_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id);
        """)

        # Security cleanup: Remove any legacy admin account with insecure default password
        try:
            cur.execute("SELECT id, password_hash FROM users WHERE username = 'admin'")
            admin_row = cur.fetchone()
            if admin_row and check_password_hash(admin_row["password_hash"], "admin123"):
                cur.execute("DELETE FROM users WHERE id = ?", (admin_row["id"],))
        except Exception:
            pass

        conn.commit()

def create_user(username, password, name=None, email=None, recovery_question=None, recovery_answer=None, db_path=None):
    import re
    if db_path is None:
        db_path = DB_PATH
    username = (username or "").strip().lower()
    name = (name or "").strip() or username
    password = (password or "").strip()
    email = (email or "").strip().lower() or None
    recovery_question = (recovery_question or "").strip() or "¿Cuál es tu palabra o frase secreta de recuperación?"
    recovery_answer = (recovery_answer or "").strip().lower()

    if not username or len(username) < 5:
        return None, "El nombre de usuario debe tener al menos 5 letras o caracteres"
    if len(username) > 50:
        return None, "El nombre de usuario no puede exceder 50 caracteres"
    if not re.match(r'^[a-zA-Z0-9_.-]+$', username):
        return None, "El nombre de usuario solo puede contener letras, números, puntos o guiones"
    if not password or len(password) < 4:
        return None, "La contraseña debe tener al menos 4 caracteres"
    if len(password) > 128:
        return None, "La contraseña no puede exceder 128 caracteres"
    if len(name) > 60:
        name = name[:60]
    if email:
        if len(email) > 120 or "@" not in email or "." not in email:
            return None, "El correo electrónico ingresado no es válido"
        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            return None, "El formato del correo electrónico no es válido"

    pwd_hash = generate_password_hash(password)
    rec_hash = generate_password_hash(recovery_answer) if recovery_answer else None

    with get_db(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cur.fetchone():
            return None, "El nombre de usuario ya está registrado. Elige otro o inicia sesión."
        
        if email:
            cur.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cur.fetchone():
                return None, "Ese correo ya está registrado con otra cuenta. Inicia sesión directamente."

        cur.execute(
            "INSERT INTO users (username, password_hash, name, email, recovery_question, recovery_answer_hash) VALUES (?, ?, ?, ?, ?, ?)",
            (username, pwd_hash, name, email, recovery_question, rec_hash)
        )
        user_id = cur.lastrowid
        conn.commit()
        return {"id": user_id, "username": username, "name": name, "email": email}, None

def authenticate_user(username_or_email, password, db_path=None):
    if db_path is None:
        db_path = DB_PATH
    ident = (username_or_email or "").strip().lower()
    password = (password or "").strip()
    if not ident or not password:
        return None, "Usuario/correo y contraseña requeridos"
    if len(ident) > 120 or len(password) > 128:
        return None, "Usuario o contraseña incorrectos"

    with get_db(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ? OR email = ?", (ident, ident))
        row = cur.fetchone()
        if not row:
            return None, "Usuario o contraseña incorrectos"
        if not check_password_hash(row["password_hash"], password):
            return None, "Usuario o contraseña incorrectos"

        return {"id": row["id"], "username": row["username"], "name": row["name"], "email": row["email"]}, None

def find_or_create_google_user(email, name=None, db_path=None):
    """Finds an existing user by email or creates a new one for Google Sign-In."""
    import re
    if db_path is None:
        db_path = DB_PATH
    email = (email or "").strip().lower()
    if not email or "@" not in email:
        return None, "Correo de Google inválido"
    
    name = (name or "").strip() or email.split("@")[0]
    with get_db(db_path) as conn:
        cur = conn.cursor()
        # 1. Existing user by email
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cur.fetchone()
        if row:
            return {"id": row["id"], "username": row["username"], "name": row["name"], "email": row["email"]}, None

        # 2. Derive unique username with at least 5 chars
        base_username = email.split("@")[0].lower()
        base_username = re.sub(r'[^a-z0-9_]', '', base_username)
        if len(base_username) < 5:
            base_username = base_username.ljust(5, '0')
        
        candidate_username = base_username
        counter = 1
        while True:
            cur.execute("SELECT id FROM users WHERE username = ?", (candidate_username,))
            if not cur.fetchone():
                break
            candidate_username = f"{base_username[:10]}_{counter}"
            counter += 1

        random_pwd = secrets.token_urlsafe(24)
        pwd_hash = generate_password_hash(random_pwd)

        cur.execute(
            "INSERT INTO users (username, password_hash, name, email) VALUES (?, ?, ?, ?)",
            (candidate_username, pwd_hash, name, email)
        )
        user_id = cur.lastrowid
        conn.commit()
        return {"id": user_id, "username": candidate_username, "name": name, "email": email}, None

def create_session(user_id, db_path=None):
    if db_path is None:
        db_path = DB_PATH
    token = secrets.token_hex(32)
    # 1 year session expiration for mobile convenience
    expires_at = datetime.now(timezone.utc) + timedelta(days=365)
    with get_db(db_path) as conn:
        conn.execute(
            "INSERT INTO user_sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires_at.isoformat())
        )
        conn.commit()
    return token

def get_user_by_token(token, db_path=None):
    if not token:
        return None
    if db_path is None:
        db_path = DB_PATH
    with get_db(db_path) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT u.id, u.username, u.name, u.email, s.expires_at
            FROM user_sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token = ?
        """, (token,))
        row = cur.fetchone()
        if not row:
            return None
        
        if row["expires_at"]:
            try:
                exp = datetime.fromisoformat(row["expires_at"])
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if exp < datetime.now(timezone.utc):
                    conn.execute("DELETE FROM user_sessions WHERE token = ?", (token,))
                    conn.commit()
                    return None
            except Exception:
                pass

        return {"id": row["id"], "username": row["username"], "name": row["name"], "email": row["email"]}

def delete_session(token, db_path=None):
    if not token:
        return
    if db_path is None:
        db_path = DB_PATH
    with get_db(db_path) as conn:
        conn.execute("DELETE FROM user_sessions WHERE token = ?", (token,))
        conn.commit()

# ==========================================
# PASSWORD RECOVERY HELPERS
# ==========================================

def mask_email(email):
    if not email or "@" not in email:
        return ""
    parts = email.split("@")
    user_part = parts[0]
    domain_part = parts[1]
    if len(user_part) <= 2:
        masked_user = user_part[0] + "***"
    else:
        masked_user = user_part[0] + "***" + user_part[-1]
    return f"{masked_user}@{domain_part}"

def find_user_for_recovery(username_or_email, db_path=None):
    if db_path is None:
        db_path = DB_PATH
    ident = (username_or_email or "").strip().lower()
    if not ident:
        return None, "Debes ingresar tu usuario o correo electrónico"

    with get_db(db_path) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, username, name, email, recovery_question, recovery_answer_hash
            FROM users
            WHERE username = ? OR email = ?
        """, (ident, ident))
        row = cur.fetchone()
        if not row:
            return None, "No se encontró ninguna cuenta asociada a ese usuario o correo"

        return {
            "id": row["id"],
            "username": row["username"],
            "name": row["name"],
            "has_email": bool(row["email"]),
            "email": row["email"],
            "masked_email": mask_email(row["email"]) if row["email"] else None,
            "has_recovery_question": bool(row["recovery_answer_hash"]),
            "recovery_question": row["recovery_question"] or "¿Cuál es tu palabra secreta de recuperación?"
        }, None

def create_password_reset_code(user_id, db_path=None):
    if db_path is None:
        db_path = DB_PATH
    import random
    reset_code = f"{random.randint(100000, 999999)}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    with get_db(db_path) as conn:
        conn.execute(
            "INSERT INTO password_resets (user_id, reset_code, expires_at) VALUES (?, ?, ?)",
            (user_id, reset_code, expires_at.isoformat())
        )
        conn.commit()
    return reset_code

def reset_password(user_id, new_password, db_path=None):
    if db_path is None:
        db_path = DB_PATH
    new_password = (new_password or "").strip()
    if not new_password or len(new_password) < 4:
        return False, "La nueva contraseña debe tener al menos 4 caracteres"
    if len(new_password) > 128:
        return False, "La nueva contraseña no puede exceder 128 caracteres"

    new_hash = generate_password_hash(new_password)
    with get_db(db_path) as conn:
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
        # Clear pending reset codes
        conn.execute("UPDATE password_resets SET used = 1 WHERE user_id = ?", (user_id,))
        # Invalidate old sessions for safety
        conn.execute("DELETE FROM user_sessions WHERE user_id = ?", (user_id,))
        conn.commit()
    return True, None

def verify_and_reset_password(ident, verification_type, verification_value, new_password, db_path=None):
    """
    verification_type:
    - 'secret_word': checks recovery_answer_hash
    - 'email_match': checks that entered email matches stored email
    - 'otp_code': checks 6-digit code in password_resets table
    """
    if db_path is None:
        db_path = DB_PATH
    user_info, err = find_user_for_recovery(ident, db_path=db_path)
    if err:
        return None, err

    user_id = user_info["id"]
    val = (verification_value or "").strip()
    if not val:
        return None, "Debes ingresar el dato de verificación"

    with get_db(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        if not row:
            return None, "Usuario no encontrado"

        if verification_type == "secret_word":
            if not row["recovery_answer_hash"]:
                return None, "Esta cuenta no tiene configurada una palabra secreta. Usa la confirmación por correo."
            if not check_password_hash(row["recovery_answer_hash"], val.lower()):
                return None, "La palabra secreta no coincide. Intenta de nuevo."

        elif verification_type == "email_match":
            if not row["email"]:
                return None, "Esta cuenta no tiene un correo registrado asociado."
            if val.lower() != row["email"].lower():
                return None, "El correo electrónico no coincide con el registrado en esta cuenta."

        elif verification_type == "otp_code":
            cur.execute("""
                SELECT id, expires_at, used FROM password_resets
                WHERE user_id = ? AND reset_code = ? AND used = 0
                ORDER BY id DESC LIMIT 1
            """, (user_id, val))
            reset_row = cur.fetchone()
            if not reset_row:
                return None, "El código de 6 dígitos es inválido o ya fue utilizado."
            
            exp_str = reset_row["expires_at"].replace("Z", "+00:00")
            exp = datetime.fromisoformat(exp_str)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > exp:
                return None, "El código de recuperación ha expirado. Solicita uno nuevo."
        else:
            return None, "Tipo de verificación no reconocido"

    ok, reset_err = reset_password(user_id, new_password, db_path=db_path)
    if not ok:
        return None, reset_err

    return {
        "id": user_info["id"],
        "username": user_info["username"],
        "name": user_info["name"],
        "email": user_info["email"]
    }, None

def set_user_recovery_secret(user_id, secret_answer, question=None, db_path=None):
    if db_path is None:
        db_path = DB_PATH
    secret_answer = (secret_answer or "").strip().lower()
    if not secret_answer or len(secret_answer) < 2:
        return False, "La palabra secreta debe tener al menos 2 caracteres"
    if len(secret_answer) > 100:
        return False, "La palabra secreta no puede superar 100 caracteres"
    
    question = (question or "").strip() or "¿Cuál es tu palabra o frase secreta de recuperación?"
    answer_hash = generate_password_hash(secret_answer)
    with get_db(db_path) as conn:
        conn.execute(
            "UPDATE users SET recovery_question = ?, recovery_answer_hash = ? WHERE id = ?",
            (question, answer_hash, user_id)
        )
        conn.commit()
    return True, None


def compute_exercise_stats(sets):
    """
    Given a list of set dicts with 'reps' and 'weight', computes:
    - total_sets
    - total_reps
    - max_weight
    - total_volume (reps * weight, or reps if all weights are 0)
    - avg_reps
    - sets_formatted
    """
    if not sets:
        return {
            "total_sets": 0,
            "total_reps": 0,
            "max_weight": 0.0,
            "total_volume": 0.0,
            "avg_reps": 0.0,
            "is_bodyweight": True,
            "sets_formatted": "0 series"
        }
    
    total_sets = len(sets)
    total_reps = sum(s.get("reps", 0) for s in sets)
    max_weight = max((float(s.get("weight", 0) or 0) for s in sets), default=0.0)
    
    has_weights = any(float(s.get("weight", 0) or 0) > 0 for s in sets)
    if has_weights:
        total_volume = sum((float(s.get("weight", 0) or 0) * int(s.get("reps", 0))) for s in sets)
        is_bodyweight = False
    else:
        total_volume = float(total_reps)
        is_bodyweight = True

    avg_reps = round(total_reps / total_sets, 1) if total_sets > 0 else 0

    return {
        "total_sets": total_sets,
        "total_reps": total_reps,
        "max_weight": round(max_weight, 2),
        "total_volume": round(total_volume, 1),
        "avg_reps": avg_reps,
        "is_bodyweight": is_bodyweight
    }

def compare_exercise_sessions(current_stats, previous_stats):
    """
    Compares current exercise session with previous session.
    Returns status: 'mejora', 'mantenimiento', 'descenso', or 'nuevo'
    and descriptive pills/text.
    """
    if not previous_stats:
        return {
            "status": "nuevo",
            "badge_class": "bg-sky-500/10 text-sky-400 border-sky-500/20",
            "icon": "sparkles",
            "headline": "Línea base registrada",
            "delta_volume_pct": 0,
            "reps_diff": 0,
            "weight_diff": 0,
            "sets_diff": 0,
            "summary": "Primera vez registrado. Servirá de referencia para tu próxima sesión."
        }
    
    prev_vol = previous_stats["total_volume"]
    curr_vol = current_stats["total_volume"]
    reps_diff = current_stats["total_reps"] - previous_stats["total_reps"]
    weight_diff = round(current_stats["max_weight"] - previous_stats["max_weight"], 2)
    sets_diff = current_stats["total_sets"] - previous_stats["total_sets"]

    # Calculate percentage change in volume
    if prev_vol > 0:
        vol_change_pct = round(((curr_vol - prev_vol) / prev_vol) * 100, 1)
    else:
        vol_change_pct = 0.0

    # Decision logic
    # Mejora:
    # 1. Volume increased by at least 1.5%
    # 2. Or Max weight increased with at least same/close total reps
    # 3. Or Reps increased with same or higher weight
    is_mejora = False
    is_descenso = False

    if vol_change_pct >= 1.5 or (weight_diff > 0 and reps_diff >= 0) or (reps_diff > 0 and weight_diff >= 0):
        is_mejora = True
    elif vol_change_pct <= -1.5 or reps_diff < 0 or weight_diff < -1:
        is_descenso = True

    details_parts = []
    if weight_diff > 0:
        details_parts.append(f"+{weight_diff} kg máx")
    elif weight_diff < 0:
        details_parts.append(f"{weight_diff} kg máx")

    if reps_diff > 0:
        details_parts.append(f"+{reps_diff} reps")
    elif reps_diff < 0:
        details_parts.append(f"{reps_diff} reps")

    if sets_diff != 0:
        details_parts.append(f"{'+' if sets_diff > 0 else ''}{sets_diff} series")

    if not details_parts:
        details_text = "Mismo rendimiento exacto"
    else:
        details_text = ", ".join(details_parts)

    if is_mejora:
        status = "mejora"
        badge_class = "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
        icon = "trending-up"
        vol_str = f"+{vol_change_pct}%" if vol_change_pct > 0 else ""
        headline = f"¡Mejora! {vol_str}".strip()
        summary = f"Superaste la sesión anterior: {details_text}."
    elif is_descenso:
        status = "descenso"
        badge_class = "bg-rose-500/10 text-rose-400 border-rose-500/30"
        icon = "trending-down"
        vol_str = f"{vol_change_pct}%"
        headline = f"Descenso ({vol_str})"
        summary = f"Menor rendimiento que la última vez: {details_text}."
    else:
        status = "mantenimiento"
        badge_class = "bg-amber-500/10 text-amber-400 border-amber-500/30"
        icon = "minus"
        headline = "Mantenimiento"
        summary = f"Mantuviste el estímulo: {details_text}."

    return {
        "status": status,
        "badge_class": badge_class,
        "icon": icon,
        "headline": headline,
        "delta_volume_pct": vol_change_pct,
        "reps_diff": reps_diff,
        "weight_diff": weight_diff,
        "sets_diff": sets_diff,
        "summary": summary
    }

def get_workout_details(workout_row, conn):
    """Fetches all exercises and sets for a workout, enriched with previous comparisons for this user."""
    workout_id = workout_row["id"]
    workout_date = workout_row["date"]
    user_id = workout_row["user_id"] if "user_id" in workout_row.keys() else 1

    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM exercise_logs 
        WHERE workout_id = ? 
        ORDER BY id ASC
    """, (workout_id,))
    exercises_raw = cur.fetchall()

    exercises = []
    for ex in exercises_raw:
        ex_id = ex["id"]
        ex_name = ex["exercise_name"]

        # Fetch sets
        cur.execute("""
            SELECT * FROM set_logs 
            WHERE exercise_log_id = ? 
            ORDER BY set_number ASC
        """, (ex_id,))
        sets_raw = [dict(s) for s in cur.fetchall()]
        current_stats = compute_exercise_stats(sets_raw)

        # Find the most recent previous exercise before this workout date for this user
        cur.execute("""
            SELECT el.id, el.workout_id, w.date, el.exercise_name
            FROM exercise_logs el
            JOIN workouts w ON el.workout_id = w.id
            WHERE w.user_id = ?
              AND LOWER(TRIM(el.exercise_name)) = LOWER(TRIM(?))
              AND w.date < ?
            ORDER BY w.date DESC, el.id DESC
            LIMIT 1
        """, (user_id, ex_name, workout_date))
        prev_ex = cur.fetchone()

        prev_stats = None
        prev_date = None
        prev_sets = []

        if prev_ex:
            prev_date = prev_ex["date"]
            cur.execute("""
                SELECT * FROM set_logs 
                WHERE exercise_log_id = ? 
                ORDER BY set_number ASC
            """, (prev_ex["id"],))
            prev_sets = [dict(s) for s in cur.fetchall()]
            prev_stats = compute_exercise_stats(prev_sets)

        comparison = compare_exercise_sessions(current_stats, prev_stats)

        exercises.append({
            "id": ex["id"],
            "exercise_name": ex["exercise_name"],
            "muscle_group": ex["muscle_group"],
            "notes": ex["notes"] or "",
            "sets": sets_raw,
            "stats": current_stats,
            "previous_date": prev_date,
            "previous_stats": prev_stats,
            "previous_sets": prev_sets,
            "comparison": comparison
        })

    return {
        "id": workout_row["id"],
        "user_id": user_id,
        "date": workout_row["date"],
        "title": workout_row["title"] or "",
        "notes": workout_row["notes"] or "",
        "exercises": exercises
    }

def get_last_session_for_exercise_name(exercise_name, user_id=1, before_date=None, db_path=None):
    """Returns the stats of the last time this exercise was performed by this user."""
    if db_path is None:
        db_path = DB_PATH
    with get_db(db_path) as conn:
        cur = conn.cursor()
        query = """
            SELECT el.id, w.date, el.exercise_name, el.muscle_group
            FROM exercise_logs el
            JOIN workouts w ON el.workout_id = w.id
            WHERE w.user_id = ? AND LOWER(TRIM(el.exercise_name)) = LOWER(TRIM(?))
        """
        params = [user_id, exercise_name]
        if before_date:
            query += " AND w.date <= ?"
            params.append(before_date)
        
        query += " ORDER BY w.date DESC, el.id DESC LIMIT 1"
        cur.execute(query, params)
        row = cur.fetchone()
        if not row:
            return None

        cur.execute("SELECT * FROM set_logs WHERE exercise_log_id = ? ORDER BY set_number ASC", (row["id"],))
        sets = [dict(s) for s in cur.fetchall()]
        stats = compute_exercise_stats(sets)
        return {
            "date": row["date"],
            "exercise_name": row["exercise_name"],
            "muscle_group": row["muscle_group"],
            "sets": sets,
            "stats": stats
        }

def get_weekly_analytics(week_start_date_str, user_id=1, db_path=None):
    """
    Computes weekly summary from Monday (week_start_date) to Sunday for this user.
    Compares exercises performed this week against their last previous session.
    """
    if db_path is None:
        db_path = DB_PATH
    start_dt = datetime.strptime(week_start_date_str, "%Y-%m-%d")
    # Ensure start_dt is Monday of that week
    start_dt = start_dt - timedelta(days=start_dt.weekday())
    end_dt = start_dt + timedelta(days=6)

    start_str = start_dt.strftime("%Y-%m-%d")
    end_str = end_dt.strftime("%Y-%m-%d")

    # Also compute previous week range for general totals comparison
    prev_week_start = (start_dt - timedelta(days=7)).strftime("%Y-%m-%d")
    prev_week_end = (start_dt - timedelta(days=1)).strftime("%Y-%m-%d")

    with get_db(db_path) as conn:
        cur = conn.cursor()

        # Workouts in this week for this user
        cur.execute("""
            SELECT * FROM workouts 
            WHERE user_id = ? AND date >= ? AND date <= ? 
            ORDER BY date ASC
        """, (user_id, start_str, end_str))
        workout_rows = cur.fetchall()

        week_workouts = [get_workout_details(w, conn) for w in workout_rows]

        # Previous week workouts for volume/reps delta for this user
        cur.execute("""
            SELECT w.id, w.date 
            FROM workouts w 
            WHERE w.user_id = ? AND w.date >= ? AND w.date <= ?
        """, (user_id, prev_week_start, prev_week_end))
        prev_workout_rows = cur.fetchall()
        
        prev_week_volume = 0.0
        prev_week_reps = 0
        prev_week_sets = 0
        for pw in prev_workout_rows:
            cur.execute("""
                SELECT sl.reps, sl.weight 
                FROM set_logs sl 
                JOIN exercise_logs el ON sl.exercise_log_id = el.id
                WHERE el.workout_id = ?
            """, (pw["id"],))
            p_sets = [dict(s) for s in cur.fetchall()]
            stats = compute_exercise_stats(p_sets)
            prev_week_volume += stats["total_volume"]
            prev_week_reps += stats["total_reps"]
            prev_week_sets += stats["total_sets"]

        # Aggregate current week metrics
        total_workouts = len(week_workouts)
        total_sets = 0
        total_reps = 0
        total_volume = 0.0
        
        # Collect exercise comparisons
        exercise_comparisons = []
        improvements_count = 0
        maintenance_count = 0
        drops_count = 0
        new_count = 0

        # Day-by-day distribution
        days_map = {}
        for d in range(7):
            day_date = (start_dt + timedelta(days=d)).strftime("%Y-%m-%d")
            day_name = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][d]
            days_map[day_date] = {
                "date": day_date,
                "day_name": day_name,
                "workouts_count": 0,
                "sets": 0,
                "reps": 0,
                "volume": 0.0,
                "exercises": []
            }

        for w in week_workouts:
            w_date = w["date"]
            for ex in w["exercises"]:
                stats = ex["stats"]
                total_sets += stats["total_sets"]
                total_reps += stats["total_reps"]
                total_volume += stats["total_volume"]

                comp = ex["comparison"]
                status = comp["status"]
                if status == "mejora":
                    improvements_count += 1
                elif status == "mantenimiento":
                    maintenance_count += 1
                elif status == "descenso":
                    drops_count += 1
                elif status == "nuevo":
                    new_count += 1

                exercise_comparisons.append({
                    "workout_date": w_date,
                    "exercise_name": ex["exercise_name"],
                    "muscle_group": ex["muscle_group"],
                    "stats": stats,
                    "previous_date": ex["previous_date"],
                    "previous_stats": ex["previous_stats"],
                    "comparison": comp
                })

                if w_date in days_map:
                    days_map[w_date]["workouts_count"] += 1
                    days_map[w_date]["sets"] += stats["total_sets"]
                    days_map[w_date]["reps"] += stats["total_reps"]
                    days_map[w_date]["volume"] += stats["total_volume"]
                    days_map[w_date]["exercises"].append(ex["exercise_name"])

        # Weekly verdict calculation
        total_evaluated = improvements_count + maintenance_count + drops_count
        if total_evaluated == 0 and new_count > 0:
            verdict = "Línea Base Establecida"
            verdict_desc = f"Registraste {new_count} ejercicio(s) nuevos esta semana. ¡La próxima semana veremos tu progreso!"
            verdict_badge = "bg-sky-500/20 text-sky-400 border-sky-500/30"
            verdict_icon = "compass"
        elif total_evaluated == 0:
            verdict = "Sin Registros Aún"
            verdict_desc = "No hay entrenamientos registrados para esta semana."
            verdict_badge = "bg-slate-700/50 text-slate-400 border-slate-600/30"
            verdict_icon = "calendar"
        else:
            improvement_ratio = improvements_count / total_evaluated
            if improvement_ratio >= 0.5:
                verdict = "¡Semana de Progreso y Sobrecarga!"
                verdict_desc = f"Superaste tus marcas en {improvements_count} de {total_evaluated} ejercicios comparables ({round(improvement_ratio*100)}%)."
                verdict_badge = "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
                verdict_icon = "flame"
            elif (improvements_count + maintenance_count) / total_evaluated >= 0.7:
                verdict = "Semana de Mantenimiento y Solidez"
                verdict_desc = f"Consolidaste tus cargas ({maintenance_count} mantenimiento, {improvements_count} mejoras) manteniendo la consistencia."
                verdict_badge = "bg-amber-500/20 text-amber-400 border-amber-500/30"
                verdict_icon = "shield-check"
            else:
                verdict = "Semana de Descarga o Adaptación"
                verdict_desc = f"Hubo descensos en {drops_count} ejercicios. Puede ser momento de descanso o recuperación planificada."
                verdict_badge = "bg-rose-500/20 text-rose-400 border-rose-500/30"
                verdict_icon = "battery-charging"

        # Delta vs previous week volume
        vol_diff_pct = 0.0
        if prev_week_volume > 0:
            vol_diff_pct = round(((total_volume - prev_week_volume) / prev_week_volume) * 100, 1)

        return {
            "week_start": start_str,
            "week_end": end_str,
            "prev_week_start": prev_week_start,
            "prev_week_end": prev_week_end,
            "total_workouts": total_workouts,
            "total_sets": total_sets,
            "total_reps": total_reps,
            "total_volume": round(total_volume, 1),
            "prev_week_volume": round(prev_week_volume, 1),
            "prev_week_sets": prev_week_sets,
            "prev_week_reps": prev_week_reps,
            "vol_diff_pct": vol_diff_pct,
            "improvements_count": improvements_count,
            "maintenance_count": maintenance_count,
            "drops_count": drops_count,
            "new_count": new_count,
            "verdict": verdict,
            "verdict_desc": verdict_desc,
            "verdict_badge": verdict_badge,
            "verdict_icon": verdict_icon,
            "days_distribution": list(days_map.values()),
            "exercise_comparisons": exercise_comparisons,
            "workouts": week_workouts
        }

def get_exercise_all_history(exercise_name, user_id=1, db_path=None):
    """Returns chronological timeline for a specific exercise for this user."""
    if db_path is None:
        db_path = DB_PATH
    with get_db(db_path) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT el.id, w.date, el.notes, w.title as workout_title
            FROM exercise_logs el
            JOIN workouts w ON el.workout_id = w.id
            WHERE w.user_id = ? AND LOWER(TRIM(el.exercise_name)) = LOWER(TRIM(?))
            ORDER BY w.date ASC, el.id ASC
        """, (user_id, exercise_name,))
        entries = cur.fetchall()

        history = []
        prev_stats = None
        for row in entries:
            cur.execute("""
                SELECT * FROM set_logs 
                WHERE exercise_log_id = ? 
                ORDER BY set_number ASC
            """, (row["id"],))
            sets = [dict(s) for s in cur.fetchall()]
            stats = compute_exercise_stats(sets)
            comp = compare_exercise_sessions(stats, prev_stats)
            history.append({
                "exercise_log_id": row["id"],
                "date": row["date"],
                "workout_title": row["workout_title"],
                "notes": row["notes"],
                "sets": sets,
                "stats": stats,
                "comparison": comp
            })
            prev_stats = stats

        return history
