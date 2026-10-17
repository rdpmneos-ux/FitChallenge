from datetime import datetime, timedelta
import models

DEFAULT_EXERCISES_DATA = [
    # ==================== PIERNAS / GLÚTEOS ====================
    {"name": "Sentadilla con Barra", "muscle": "Piernas"},
    {"name": "Sentadilla Hack (Hacka)", "muscle": "Piernas"},
    {"name": "Sentadilla Hack Inversa", "muscle": "Piernas"},
    {"name": "Sentadilla Frontal", "muscle": "Piernas"},
    {"name": "Sentadilla Goblet", "muscle": "Piernas"},
    {"name": "Sentadilla Búlgara", "muscle": "Piernas"},
    {"name": "Sentadilla en Máquina Smith", "muscle": "Piernas"},
    {"name": "Sentadilla Sissy", "muscle": "Piernas"},
    {"name": "Prensa de Piernas", "muscle": "Piernas"},
    {"name": "Prensa de Piernas (Prensa 45°)", "muscle": "Piernas"},
    {"name": "Prensa Horizontal", "muscle": "Piernas"},
    {"name": "Extensiones de Cuádriceps", "muscle": "Piernas"},
    {"name": "Peso Muerto Convencional", "muscle": "Piernas"},
    {"name": "Peso Muerto Sumo", "muscle": "Piernas"},
    {"name": "Peso Muerto Rumano", "muscle": "Piernas"},
    {"name": "Peso Muerto Rumano con Mancuernas", "muscle": "Piernas"},
    {"name": "Curl Femoral Tumbado", "muscle": "Piernas"},
    {"name": "Curl Femoral Sentado", "muscle": "Piernas"},
    {"name": "Curl Femoral de Pie", "muscle": "Piernas"},
    {"name": "Hip Thrust", "muscle": "Piernas"},
    {"name": "Hip Thrust en Máquina", "muscle": "Piernas"},
    {"name": "Puente de Glúteos", "muscle": "Piernas"},
    {"name": "Zancadas / Lunges", "muscle": "Piernas"},
    {"name": "Zancadas Caminando con Mancuernas", "muscle": "Piernas"},
    {"name": "Step Ups (Subidas al Cajón)", "muscle": "Piernas"},
    {"name": "Patada de Glúteo en Polea", "muscle": "Piernas"},
    {"name": "Patada de Glúteo en Máquina", "muscle": "Piernas"},
    {"name": "Abductores en Máquina", "muscle": "Piernas"},
    {"name": "Aductores en Máquina", "muscle": "Piernas"},
    {"name": "Elevación de Talones (Gemelos)", "muscle": "Piernas"},
    {"name": "Elevación de Talones Sentado (Sóleo)", "muscle": "Piernas"},
    {"name": "Elevación de Talones en Prensa", "muscle": "Piernas"},
    {"name": "Buenos Días (Good Mornings)", "muscle": "Piernas"},

    # ==================== PECHO ====================
    {"name": "Press de Banca", "muscle": "Pecho"},
    {"name": "Press de Banca con Mancuernas", "muscle": "Pecho"},
    {"name": "Press Inclinado con Barra", "muscle": "Pecho"},
    {"name": "Press Inclinado con Mancuernas", "muscle": "Pecho"},
    {"name": "Press Declinado con Barra", "muscle": "Pecho"},
    {"name": "Press Declinado con Mancuernas", "muscle": "Pecho"},
    {"name": "Press de Pecho en Máquina", "muscle": "Pecho"},
    {"name": "Press Inclinado en Máquina", "muscle": "Pecho"},
    {"name": "Press en Máquina Smith (Pecho)", "muscle": "Pecho"},
    {"name": "Aperturas con Mancuernas", "muscle": "Pecho"},
    {"name": "Aperturas Inclinadas con Mancuernas", "muscle": "Pecho"},
    {"name": "Aperturas en Polea", "muscle": "Pecho"},
    {"name": "Cruces en Polea Alta a Baja", "muscle": "Pecho"},
    {"name": "Cruces en Polea Baja a Alta", "muscle": "Pecho"},
    {"name": "Pec Deck / Contractora", "muscle": "Pecho"},
    {"name": "Fondos en Paralelas", "muscle": "Pecho"},
    {"name": "Fondos en Paralelas (Pecho)", "muscle": "Pecho"},
    {"name": "Flexiones de Pecho (Push-ups)", "muscle": "Pecho"},
    {"name": "Flexiones Declinadas", "muscle": "Pecho"},
    {"name": "Pullover con Mancuerna", "muscle": "Pecho"},
    {"name": "Svend Press", "muscle": "Pecho"},

    # ==================== ESPALDA ====================
    {"name": "Dominadas", "muscle": "Espalda"},
    {"name": "Dominadas Neutras", "muscle": "Espalda"},
    {"name": "Dominadas Supinas (Chin-ups)", "muscle": "Espalda"},
    {"name": "Dominadas Asistidas", "muscle": "Espalda"},
    {"name": "Jalón al Pecho", "muscle": "Espalda"},
    {"name": "Jalón al Pecho Agarre Neutro / Estrecho", "muscle": "Espalda"},
    {"name": "Jalón Trasnuca", "muscle": "Espalda"},
    {"name": "Jalón Unilateral en Polea", "muscle": "Espalda"},
    {"name": "Remo con Barra", "muscle": "Espalda"},
    {"name": "Remo Pendlay", "muscle": "Espalda"},
    {"name": "Remo con Mancuerna (Serrucho)", "muscle": "Espalda"},
    {"name": "Remo con Mancuernas en Banco Inclinado", "muscle": "Espalda"},
    {"name": "Remo en Barra T", "muscle": "Espalda"},
    {"name": "Remo en Barra T con Apoyo al Pecho", "muscle": "Espalda"},
    {"name": "Remo Gironda", "muscle": "Espalda"},
    {"name": "Remo en Máquina", "muscle": "Espalda"},
    {"name": "Pullover en Polea Alta", "muscle": "Espalda"},
    {"name": "Encogimientos con Barra (Trapecio)", "muscle": "Espalda"},
    {"name": "Encogimientos con Mancuernas (Trapecio)", "muscle": "Espalda"},
    {"name": "Hiperextensiones Lumbares", "muscle": "Espalda"},
    {"name": "Rack Pull (Peso Muerto Parcial)", "muscle": "Espalda"},

    # ==================== HOMBROS ====================
    {"name": "Press Militar con Barra", "muscle": "Hombros"},
    {"name": "Press Militar Mancuernas", "muscle": "Hombros"},
    {"name": "Press Arnold", "muscle": "Hombros"},
    {"name": "Press de Hombros en Máquina", "muscle": "Hombros"},
    {"name": "Press Militar en Máquina Smith", "muscle": "Hombros"},
    {"name": "Elevaciones Laterales", "muscle": "Hombros"},
    {"name": "Elevaciones Laterales en Polea", "muscle": "Hombros"},
    {"name": "Elevaciones Laterales en Máquina", "muscle": "Hombros"},
    {"name": "Pájaros con Mancuerna", "muscle": "Hombros"},
    {"name": "Pájaros en Polea / Cruces Inversos", "muscle": "Hombros"},
    {"name": "Deltoides Posterior en Máquina (Pec Deck Invertido)", "muscle": "Hombros"},
    {"name": "Face Pull en Polea", "muscle": "Hombros"},
    {"name": "Elevaciones Frontales con Mancuernas", "muscle": "Hombros"},
    {"name": "Elevaciones Frontales con Disco", "muscle": "Hombros"},
    {"name": "Elevaciones Frontales en Polea", "muscle": "Hombros"},
    {"name": "Remo al Mentón con Barra", "muscle": "Hombros"},
    {"name": "Remo al Mentón en Polea", "muscle": "Hombros"},
    {"name": "Rotaciones Externas en Polea (Manguito Rotador)", "muscle": "Hombros"},
    {"name": "Y-Raises en Banco Inclinado", "muscle": "Hombros"},

    # ==================== BRAZOS ====================
    {"name": "Curl con Barra Recta", "muscle": "Brazos"},
    {"name": "Curl con Barra Z", "muscle": "Brazos"},
    {"name": "Curl con Mancuernas (Alterno)", "muscle": "Brazos"},
    {"name": "Curl Martillo con Mancuernas", "muscle": "Brazos"},
    {"name": "Curl Inclinado con Mancuernas", "muscle": "Brazos"},
    {"name": "Curl Concentrado con Mancuerna", "muscle": "Brazos"},
    {"name": "Curl Predicador / Banco Scott", "muscle": "Brazos"},
    {"name": "Curl Predicador en Máquina", "muscle": "Brazos"},
    {"name": "Curl Araña (Spider Curl)", "muscle": "Brazos"},
    {"name": "Curl en Polea Baja", "muscle": "Brazos"},
    {"name": "Curl en Polea Alta (Doble Bíceps)", "muscle": "Brazos"},
    {"name": "Curl Bayesiano en Polea", "muscle": "Brazos"},
    {"name": "Extensiones de Tríceps en Polea", "muscle": "Brazos"},
    {"name": "Extensiones de Tríceps con Cuerda", "muscle": "Brazos"},
    {"name": "Extensiones sobre la Cabeza en Polea", "muscle": "Brazos"},
    {"name": "Press Francés", "muscle": "Brazos"},
    {"name": "Copa a Dos Manos con Mancuerna", "muscle": "Brazos"},
    {"name": "Patada de Tríceps con Mancuerna", "muscle": "Brazos"},
    {"name": "Patada de Tríceps en Polea", "muscle": "Brazos"},
    {"name": "Extensiones Katana en Polea", "muscle": "Brazos"},
    {"name": "Press de Banca Agarre Estrecho", "muscle": "Brazos"},
    {"name": "Fondos en Banco", "muscle": "Brazos"},
    {"name": "Fondos en Paralelas (Tríceps)", "muscle": "Brazos"},
    {"name": "Curl de Muñeca (Antebrazo)", "muscle": "Brazos"},
    {"name": "Curl de Muñeca Invertido", "muscle": "Brazos"},
    {"name": "Paseo del Granjero (Farmer's Walk)", "muscle": "Brazos"},

    # ==================== CORE ====================
    {"name": "Plancha Abdominal", "muscle": "Core"},
    {"name": "Plancha Lateral", "muscle": "Core"},
    {"name": "Elevaciones de Piernas Colgado", "muscle": "Core"},
    {"name": "Elevaciones de Piernas en Paralelas", "muscle": "Core"},
    {"name": "Elevaciones de Piernas en Suelo", "muscle": "Core"},
    {"name": "Crunch Abdominal en Suelo", "muscle": "Core"},
    {"name": "Crunch en Polea Alta (Cable Crunch)", "muscle": "Core"},
    {"name": "Crunch en Máquina", "muscle": "Core"},
    {"name": "Rueda Abdominal (Ab Wheel)", "muscle": "Core"},
    {"name": "Giros Rusos (Russian Twists)", "muscle": "Core"},
    {"name": "Vacío Abdominal (Stomach Vacuum)", "muscle": "Core"},
    {"name": "Bicicleta Abdominal (Bicycle Crunch)", "muscle": "Core"},
    {"name": "Toques de Talón (Heel Touches)", "muscle": "Core"},
    {"name": "Dead Bug", "muscle": "Core"},
    {"name": "Bird Dog", "muscle": "Core"},
    {"name": "Leñador en Polea (Woodchoppers)", "muscle": "Core"},
    {"name": "Hiperextensiones Laterales para Oblicuos", "muscle": "Core"}
]

DEFAULT_POPULAR_EXERCISES = [
    {"name": item["name"], "muscle_group": item["muscle"]}
    for item in DEFAULT_EXERCISES_DATA
]

def populate_seed_data(db_path=models.DB_PATH, user_id=1):
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
            # Upsert workout for this user
            cur.execute("""
                INSERT INTO workouts (user_id, date, title, notes)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, date) DO UPDATE SET title=excluded.title, notes=excluded.notes
            """, (user_id, w["date"], w["title"], w["notes"]))
            cur.execute("SELECT id FROM workouts WHERE user_id = ? AND date = ?", (user_id, w["date"]))
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
