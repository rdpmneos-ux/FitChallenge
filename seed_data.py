from datetime import datetime, timedelta
import models

def populate_seed_data(db_path=models.DB_PATH):
    models.init_db(db_path)
    today = datetime.now()
    # Find Monday of current week
    curr_monday = today - timedelta(days=today.weekday())
    prev_monday = curr_monday - timedelta(days=7)

    sample_plan = [
        # PREVIOUS WEEK
        {
            "date": (prev_monday + timedelta(days=0)).strftime("%Y-%m-%d"),
            "title": "Torso / Empuje (Semana Anterior)",
            "notes": "Buena sesión de inicio",
            "exercises": [
                {
                    "name": "Press de Banca",
                    "muscle": "Pecho",
                    "sets": [
                        {"reps": 10, "weight": 60.0},
                        {"reps": 10, "weight": 60.0},
                        {"reps": 10, "weight": 60.0},
                        {"reps": 8, "weight": 60.0}
                    ]
                },
                {
                    "name": "Fondos en Paralelas",
                    "muscle": "Tríceps / Pecho",
                    "sets": [
                        {"reps": 10, "weight": 0.0},
                        {"reps": 10, "weight": 0.0},
                        {"reps": 8, "weight": 0.0}
                    ]
                },
                {
                    "name": "Press Militar Mancuernas",
                    "muscle": "Hombros",
                    "sets": [
                        {"reps": 12, "weight": 18.0},
                        {"reps": 10, "weight": 18.0},
                        {"reps": 10, "weight": 18.0}
                    ]
                }
            ]
        },
        {
            "date": (prev_monday + timedelta(days=2)).strftime("%Y-%m-%d"),
            "title": "Espalda y Bíceps (Semana Anterior)",
            "notes": "Enfoque en técnica estricta",
            "exercises": [
                {
                    "name": "Dominadas",
                    "muscle": "Espalda",
                    "sets": [
                        {"reps": 8, "weight": 0.0},
                        {"reps": 8, "weight": 0.0},
                        {"reps": 7, "weight": 0.0},
                        {"reps": 6, "weight": 0.0}
                    ]
                },
                {
                    "name": "Remo con Barra",
                    "muscle": "Espalda",
                    "sets": [
                        {"reps": 10, "weight": 50.0},
                        {"reps": 10, "weight": 50.0},
                        {"reps": 10, "weight": 50.0},
                        {"reps": 10, "weight": 50.0}
                    ]
                },
                {
                    "name": "Curl con Barra Z",
                    "muscle": "Bíceps",
                    "sets": [
                        {"reps": 12, "weight": 25.0},
                        {"reps": 10, "weight": 25.0},
                        {"reps": 10, "weight": 25.0}
                    ]
                }
            ]
        },
        {
            "date": (prev_monday + timedelta(days=4)).strftime("%Y-%m-%d"),
            "title": "Pierna Completa (Semana Anterior)",
            "notes": "Día pesado",
            "exercises": [
                {
                    "name": "Sentadilla con Barra",
                    "muscle": "Pierna",
                    "sets": [
                        {"reps": 10, "weight": 80.0},
                        {"reps": 10, "weight": 80.0},
                        {"reps": 8, "weight": 80.0},
                        {"reps": 8, "weight": 80.0}
                    ]
                },
                {
                    "name": "Prensa de Piernas",
                    "muscle": "Pierna",
                    "sets": [
                        {"reps": 12, "weight": 140.0},
                        {"reps": 12, "weight": 140.0},
                        {"reps": 10, "weight": 140.0}
                    ]
                }
            ]
        },

        # CURRENT WEEK (Progressions & Improvements!)
        {
            "date": (curr_monday + timedelta(days=0)).strftime("%Y-%m-%d"),
            "title": "Torso / Empuje (Esta Semana)",
            "notes": "¡Subí 2.5kg en banca y más reps en fondos!",
            "exercises": [
                {
                    "name": "Press de Banca",
                    "muscle": "Pecho",
                    "sets": [
                        {"reps": 10, "weight": 62.5},
                        {"reps": 10, "weight": 62.5},
                        {"reps": 10, "weight": 62.5},
                        {"reps": 9, "weight": 62.5}
                    ]
                },
                {
                    "name": "Fondos en Paralelas",
                    "muscle": "Tríceps / Pecho",
                    "sets": [
                        {"reps": 12, "weight": 0.0},
                        {"reps": 11, "weight": 0.0},
                        {"reps": 10, "weight": 0.0}
                    ]
                },
                {
                    "name": "Press Militar Mancuernas",
                    "muscle": "Hombros",
                    "sets": [
                        {"reps": 12, "weight": 18.0},
                        {"reps": 10, "weight": 18.0},
                        {"reps": 10, "weight": 18.0}
                    ]
                }
            ]
        },
        {
            "date": (curr_monday + timedelta(days=2)).strftime("%Y-%m-%d"),
            "title": "Espalda y Bíceps (Esta Semana)",
            "notes": "Sobrecarga progresiva lograda en dominadas y remo",
            "exercises": [
                {
                    "name": "Dominadas",
                    "muscle": "Espalda",
                    "sets": [
                        {"reps": 9, "weight": 0.0},
                        {"reps": 9, "weight": 0.0},
                        {"reps": 8, "weight": 0.0},
                        {"reps": 7, "weight": 0.0}
                    ]
                },
                {
                    "name": "Remo con Barra",
                    "muscle": "Espalda",
                    "sets": [
                        {"reps": 10, "weight": 52.5},
                        {"reps": 10, "weight": 52.5},
                        {"reps": 10, "weight": 52.5},
                        {"reps": 9, "weight": 52.5}
                    ]
                },
                {
                    "name": "Curl con Barra Z",
                    "muscle": "Bíceps",
                    "sets": [
                        {"reps": 12, "weight": 25.0},
                        {"reps": 11, "weight": 25.0},
                        {"reps": 10, "weight": 25.0}
                    ]
                }
            ]
        }
    ]

    with models.get_db(db_path) as conn:
        cur = conn.cursor()
        for w in sample_plan:
            # Upsert workout
            cur.execute("""
                INSERT INTO workouts (date, title, notes)
                VALUES (?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET title=excluded.title, notes=excluded.notes
            """, (w["date"], w["title"], w["notes"]))
            cur.execute("SELECT id FROM workouts WHERE date = ?", (w["date"],))
            w_id = cur.fetchone()["id"]

            # Remove existing exercises for this day if re-seeding
            cur.execute("DELETE FROM exercise_logs WHERE workout_id = ?", (w_id,))

            for ex in w["exercises"]:
                cur.execute("""
                    INSERT INTO exercise_logs (workout_id, exercise_name, muscle_group)
                    VALUES (?, ?, ?)
                """, (w_id, ex["name"], ex["muscle"]))
                ex_id = cur.lastrowid

                for idx, s in enumerate(ex["sets"], start=1):
                    cur.execute("""
                        INSERT INTO set_logs (exercise_log_id, set_number, reps, weight)
                        VALUES (?, ?, ?, ?)
                    """, (ex_id, idx, s["reps"], s.get("weight", 0.0)))
        conn.commit()
    print("Seed data loaded successfully!")

if __name__ == "__main__":
    populate_seed_data()
