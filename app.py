import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
import models
import seed_data

app = Flask(__name__)

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
    {"name": "Prensa de Piernas", "muscle": "Piernas"},
    {"name": "Peso Muerto Rumano", "muscle": "Piernas / Isquios"},
    {"name": "Extensiones de Cuádriceps", "muscle": "Piernas"},
    {"name": "Curl Femoral Tumbado", "muscle": "Piernas"},
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

# Initialize database on startup
with app.app_context():
    models.init_db()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/popular_exercises", methods=["GET"])
def get_popular_exercises():
    with models.get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT exercise_name, muscle_group FROM exercise_logs")
        logged = [{"name": row["exercise_name"], "muscle": row["muscle_group"]} for row in cur.fetchall()]

    # Merge unique exercises
    names_seen = set()
    result = []
    for item in logged + DEFAULT_EXERCISES:
        normalized = item["name"].strip().lower()
        if normalized not in names_seen:
            names_seen.add(normalized)
            result.append(item)

    return jsonify({"exercises": result})

@app.route("/api/workout", methods=["GET"])
def get_workout():
    date_str = request.args.get("date")
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    with models.get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM workouts WHERE date = ?", (date_str,))
        row = cur.fetchone()
        if not row:
            # Return empty skeleton
            return jsonify({
                "workout": {
                    "id": None,
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
    data = request.get_json() or {}
    date_str = data.get("date")
    title = data.get("title", "").strip()
    notes = data.get("notes", "").strip()

    if not date_str:
        return jsonify({"error": "Fecha requerida"}), 400

    with models.get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO workouts (date, title, notes)
            VALUES (?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET title = excluded.title, notes = excluded.notes
        """, (date_str, title, notes))
        conn.commit()

        cur.execute("SELECT * FROM workouts WHERE date = ?", (date_str,))
        row = cur.fetchone()
        workout_data = models.get_workout_details(row, conn)
        return jsonify({"workout": workout_data})

@app.route("/api/exercise", methods=["POST"])
def add_exercise():
    data = request.get_json() or {}
    date_str = data.get("date")
    exercise_name = data.get("exercise_name", "").strip()
    muscle_group = data.get("muscle_group", "General").strip()
    notes = data.get("notes", "").strip()
    sets = data.get("sets", [])

    if not date_str or not exercise_name:
        return jsonify({"error": "Fecha y nombre de ejercicio son requeridos"}), 400

    if not sets or len(sets) == 0:
        return jsonify({"error": "Debes agregar al menos una serie"}), 400

    with models.get_db() as conn:
        cur = conn.cursor()
        # Ensure workout exists for this date
        cur.execute("""
            INSERT INTO workouts (date, title, notes)
            VALUES (?, ?, ?)
            ON CONFLICT(date) DO NOTHING
        """, (date_str, f"Entrenamiento del {date_str}", ""))
        
        cur.execute("SELECT id FROM workouts WHERE date = ?", (date_str,))
        workout_id = cur.fetchone()["id"]

        # Insert exercise log
        cur.execute("""
            INSERT INTO exercise_logs (workout_id, exercise_name, muscle_group, notes)
            VALUES (?, ?, ?, ?)
        """, (workout_id, exercise_name, muscle_group, notes))
        exercise_log_id = cur.lastrowid

        # Insert sets
        for idx, s in enumerate(sets, start=1):
            reps = int(s.get("reps", 0))
            weight = float(s.get("weight", 0) or 0)
            rpe = s.get("rpe")
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
    with models.get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT workout_id FROM exercise_logs WHERE id = ?", (exercise_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "Ejercicio no encontrado"}), 404
        workout_id = row["workout_id"]

        cur.execute("DELETE FROM exercise_logs WHERE id = ?", (exercise_id,))
        conn.commit()

        cur.execute("SELECT * FROM workouts WHERE id = ?", (workout_id,))
        w_row = cur.fetchone()
        workout_data = models.get_workout_details(w_row, conn) if w_row else None
        return jsonify({"workout": workout_data})

@app.route("/api/exercise/last", methods=["GET"])
def get_last_exercise_occurrence():
    exercise_name = request.args.get("name", "").strip()
    before_date = request.args.get("before_date")
    if not exercise_name:
        return jsonify({"last_session": None})

    last_session = models.get_last_session_for_exercise_name(exercise_name, before_date)
    return jsonify({"last_session": last_session})

@app.route("/api/exercise/history", methods=["GET"])
def get_exercise_history():
    name = request.args.get("name", "").strip()
    if not name:
        return jsonify({"history": []})
    history = models.get_exercise_all_history(name)
    return jsonify({"history": history})

@app.route("/api/weekly", methods=["GET"])
def get_weekly():
    date_str = request.args.get("date")
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    report = models.get_weekly_analytics(date_str)
    return jsonify(report)

@app.route("/api/seed", methods=["POST"])
def seed():
    seed_data.populate_seed_data()
    return jsonify({"status": "ok", "message": "Datos de ejemplo cargados exitosamente"})

@app.route("/api/reset", methods=["POST"])
def reset():
    with models.get_db() as conn:
        conn.execute("DELETE FROM set_logs")
        conn.execute("DELETE FROM exercise_logs")
        conn.execute("DELETE FROM workouts")
        conn.commit()
    return jsonify({"status": "ok", "message": "Base de datos reiniciada"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Iniciando servicio de entrenamiento en http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
