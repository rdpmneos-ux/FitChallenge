import os
import json
import urllib.request
import urllib.error
import random

# Default fallback models in Google AI Studio / Gemini API
GEMINI_MODELS = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]

MOTIVATIONAL_MISSED_MESSAGES = [
    "¡Cabeza alta! El progreso biológico no es una línea recta. Los días difíciles son los que más fortalecen tu disciplina y tu sistema nervioso.",
    "Dormir, el estrés o la hidratación hacen fluctuar la fuerza hasta un 10%. Lo verdaderamente importante es que hoy te presentaste y diste el 100% de lo que tenías.",
    "Construir masa muscular es una maratón de meses, no una carrera de una sola sesión. Tu cuerpo ya inició el proceso de adaptación para la próxima vez.",
    "¡Gran esfuerzo! Cada repetición al fallo o cercana genera tensión mecánica. Analiza si necesitas 60 segundos más de descanso entre series.",
    "Los levantadores profesionales tienen días donde los pesos pesan el doble. Lo que te hace avanzar es la constancia, no la perfección.",
    "No te desanimes: mantener la carga o rozar el objetivo sigue siendo una victoria de volumen. ¡A descansar, comer bien y la próxima semana lo revientas!",
    "La fatiga acumulada es real. Si sientes que te costó más de lo normal, tu cuerpo quizás te esté pidiendo más proteína y horas de sueño. ¡Mañana más fuerte!"
]

MOTIVATIONAL_ACHIEVED_MESSAGES = [
    "🔥 ¡Sobrecarga progresiva conseguida! Has obligado a tus fibras musculares a adaptarse a un nuevo nivel de tensión.",
    "⚡ ¡Brutal! Nuevo récord personal en el ejercicio. La disciplina silenciosa da sus frutos.",
    "💪 ¡Objetivo superado! El estímulo de hoy ha sido perfecto para hipertrofia y fuerza. ¡Sigue con ese impulso!",
    "🚀 ¡Imparable! Has superado tu marca anterior. Tu cuerpo no tiene más opción que crecer y volverse más fuerte."
]

def get_gemini_api_key(client_key=None):
    """Retrieve API key from request, environment, or None."""
    if client_key and isinstance(client_key, str) and client_key.strip():
        return client_key.strip()
    return os.environ.get("GEMINI_API_KEY", "").strip()

def calculate_progressive_overload(exercise_name, muscle_group, last_sets):
    """
    Implements evidence-based Double Progression Model:
    1. If user reached the ceiling of their rep range in all sets (e.g. >= 12 reps or >= 10 reps),
       increase weight (2.5% to 5%) and reset reps to the floor of the range (e.g. 8-10 reps).
    2. If user is within the range but hasn't maxed out all sets (e.g. 11, 9, 8 reps),
       maintain the same weight and aim for +1 or +2 reps in the later sets.
    3. If user is lifting bodyweight (0 kg), recommend +1-2 reps or adding light weight (2.5-5 kg).
    4. If strength range (<6 reps), recommend microloading +1.25 to +2.5 kg.
    """
    if not last_sets or not isinstance(last_sets, list):
        # Default starting template
        return {
            "type": "new_exercise",
            "summary": "Establecer marca base (3 series x 8-12 reps)",
            "explanation": "Es tu primera vez con este ejercicio. Busca un peso con el que puedas hacer entre 8 y 12 repeticiones sintiendo que te quedan 1 o 2 en recámara (RPE 8).",
            "suggested_sets": [
                {"set_number": 1, "reps": 10, "weight": 0.0},
                {"set_number": 2, "reps": 10, "weight": 0.0},
                {"set_number": 3, "reps": 10, "weight": 0.0}
            ],
            "scientific_tip": "Prioriza siempre el rango de recorrido completo y el control del descenso (2-3 segundos)."
        }

    # Extract metrics
    weights = [float(s.get("weight", 0) or 0) for s in last_sets]
    reps = [int(s.get("reps", 0) or 0) for s in last_sets]
    num_sets = len(last_sets)
    max_weight = max(weights) if weights else 0.0
    min_reps = min(reps) if reps else 0
    avg_reps = sum(reps) / max(len(reps), 1)

    is_legs = (muscle_group or "").lower() in ["piernas", "legs", "gluteos", "cuadriceps"]
    is_bodyweight = max_weight <= 0.0

    # Weight increments based on movement type
    weight_step = 5.0 if is_legs else 2.5
    if max_weight >= 100:
        weight_step = 5.0
    elif max_weight <= 20 and not is_bodyweight:
        weight_step = 1.25

    suggested_sets = []
    overload_type = "maintain_add_reps"
    summary = ""
    explanation = ""

    # Case 1: Bodyweight exercise (e.g., dominadas, fondos, planchas)
    if is_bodyweight:
        if avg_reps >= 12:
            overload_type = "add_ballast"
            summary = f"Añadir lastre de +{weight_step} kg o aumentar a {min_reps + 2} reps"
            explanation = f"Completaste un promedio de {avg_reps:.0f} reps con peso corporal. Tu cuerpo ya se adaptó: puedes empezar a lastrarte con {weight_step} kg o buscar más repeticiones."
            for idx in range(num_sets):
                suggested_sets.append({
                    "set_number": idx + 1,
                    "reps": max(8, reps[idx] - 2),
                    "weight": weight_step
                })
        else:
            overload_type = "add_reps"
            summary = f"Intentar +1 repetición en cada serie (objetivo: {min_reps + 1}+ reps)"
            explanation = f"La sesión anterior hiciste entre {min_reps} y {max(reps)} reps. La sobrecarga progresiva hoy se logra sumando repeticiones totales."
            for idx in range(num_sets):
                suggested_sets.append({
                    "set_number": idx + 1,
                    "reps": reps[idx] + 1,
                    "weight": 0.0
                })

    # Case 2: User hit the top of the rep range in all sets (e.g., all sets >= 12 reps, or all >= 10)
    elif all(r >= 12 for r in reps) or (all(r >= 10 for r in reps) and num_sets >= 3):
        overload_type = "increase_weight"
        new_weight = round(max_weight + weight_step, 2)
        summary = f"Subir a {new_weight} kg (+{weight_step} kg) en rango de 8 a 10 reps"
        explanation = f"¡Dominaste los {max_weight} kg en todas tus series ({min_reps}+ reps)! Corresponde aplicar sobrecarga por intensidad mecánica aumentando {weight_step} kg."
        for idx in range(num_sets):
            # When jumping in weight, drop rep target to bottom of hypertrophy bracket (8-10)
            suggested_sets.append({
                "set_number": idx + 1,
                "reps": max(8, min(10, reps[idx] - 2)),
                "weight": new_weight
            })

    # Case 3: In the middle of rep range -> Keep weight, aim for +1-2 reps on weaker sets
    else:
        overload_type = "increase_reps"
        summary = f"Mantener {max_weight} kg y superar las {sum(reps)} reps totales (+1 rep en cada serie)"
        explanation = f"La sesión anterior lograste series de {', '.join(str(r) for r in reps)} reps con {max_weight} kg. La meta de hoy es ganar 1 o 2 repeticiones en las series intermedias antes de subir peso."
        for idx in range(num_sets):
            target_r = reps[idx] + (1 if idx > 0 or reps[idx] < 12 else 0)
            suggested_sets.append({
                "set_number": idx + 1,
                "reps": target_r,
                "weight": max_weight
            })

    scientific_tip = (
        "El descanso óptimo entre series de sobrecarga es de 2 a 3 minutos para restaurar el ATP muscular."
        if not is_legs else
        "En ejercicios de pierna, asegúrate de mantener la misma profundidad en cada repetición para que la sobrecarga sea real."
    )

    return {
        "type": overload_type,
        "summary": summary,
        "explanation": explanation,
        "suggested_sets": suggested_sets,
        "previous_max_weight": max_weight,
        "previous_total_reps": sum(reps),
        "scientific_tip": scientific_tip
    }

def evaluate_performance(current_sets, last_sets, exercise_name=""):
    """
    Compares today's performance vs last session:
    Calculates total tonnage (reps * weight) or total reps for bodyweight.
    Returns:
      is_success (bool)
      message (str)
    """
    if not last_sets:
        return True, "¡Primer registro de este ejercicio guardado con éxito! Esta será tu base para la sobrecarga progresiva."

    curr_tonnage = sum(float(s.get("weight", 0) or 0) * int(s.get("reps", 0) or 0) for s in current_sets)
    last_tonnage = sum(float(s.get("weight", 0) or 0) * int(s.get("reps", 0) or 0) for s in last_sets)

    curr_reps = sum(int(s.get("reps", 0) or 0) for s in current_sets)
    last_reps = sum(int(s.get("reps", 0) or 0) for s in last_sets)

    curr_max_w = max([float(s.get("weight", 0) or 0) for s in current_sets] or [0])
    last_max_w = max([float(s.get("weight", 0) or 0) for s in last_sets] or [0])

    # Bodyweight evaluation
    if last_max_w <= 0 and curr_max_w <= 0:
        if curr_reps >= last_reps:
            return True, random.choice(MOTIVATIONAL_ACHIEVED_MESSAGES)
        else:
            return False, random.choice(MOTIVATIONAL_MISSED_MESSAGES)

    # Weight evaluation
    # Success if max weight increased or tonnage equal/higher
    if curr_max_w > last_max_w or curr_tonnage >= last_tonnage:
        return True, random.choice(MOTIVATIONAL_ACHIEVED_MESSAGES)
    else:
        return False, random.choice(MOTIVATIONAL_MISSED_MESSAGES)

def query_gemini_api(api_key, system_prompt, user_message, chat_history=None):
    """
    Calls the Google Gemini REST API using Python standard library urllib.
    Tries gemini-2.0-flash first, then fallbacks to gemini-1.5-flash.
    """
    if not api_key:
        return None, "No se proporcionó API Key de Gemini"

    # Build contents array
    contents = []
    if chat_history and isinstance(chat_history, list):
        for msg in chat_history[-8:]:  # keep last 8 messages for context
            role = "user" if msg.get("role") in ["user", "human"] else "model"
            text = msg.get("content", "").strip()
            if text:
                contents.append({"role": role, "parts": [{"text": text}]})

    # Add current user prompt
    contents.append({"role": "user", "parts": [{"text": user_message}]})

    payload = {
        "system_instruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1200
        }
    }

    body_bytes = json.dumps(payload).encode("utf-8")
    last_error = ""

    for model in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            req = urllib.request.Request(
                url,
                data=body_bytes,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=14) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    if parts and "text" in parts[0]:
                        return parts[0]["text"], None
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            last_error = f"HTTP {e.code}: {err_body}"
            # If 404 or 400 with model not found, try next fallback model
            continue
        except Exception as e:
            last_error = str(e)
            continue

    return None, f"Error al consultar Gemini ({last_error})"

def generate_local_coach_response(user_message, user_context):
    """
    Intelligent local sports science fallback when no Gemini API key is configured.
    Provides instant, high-quality answers for common queries.
    """
    msg = (user_message or "").lower()
    user_name = user_context.get("name", "Campeón")
    recent_workouts = user_context.get("recent_workouts", [])

    if "sobrecarga" in msg or "peso" in msg or "progresar" in msg or "progresiva" in msg:
        return f"""Hola {user_name}. La **sobrecarga progresiva** es el principio fundamental del crecimiento muscular. Significa aumentar gradualmente la demanda impuesta a tu sistema musculoesquelético.

Hay 3 formas principales de aplicarla en **FitChallenge**:
1. **Doble Progresión (La más recomendada)**: Establece un rango (ej: 8 a 12 reps). Mantén el peso hasta que logres 12 reps en todas tus series. En la siguiente sesión, sube de 2.5 kg a 5 kg y vuelve a empezar en 8 reps.
2. **Sobrecarga por Repeticiones**: Mismo peso, pero sumar 1 repetición más en cualquiera de tus series respecto a la semana pasada.
3. **Calidad de Ejecución**: Mismo peso y reps, pero haciendo una fase excéntrica (bajada) más lenta y controlada (2-3 segundos).

👉 *Tip: Al anotar cualquier ejercicio en la app, verás automáticamente tu objetivo sugerido para hoy.*"""

    if "rutina" in msg or "entrenar" in msg or "push" in msg or "pull" in msg or "pierna" in msg or "crea" in msg:
        return f"""¡Excelente iniciativa, {user_name}! Aquí tienes una propuesta de rutina equilibrada de hipertrofia y fuerza:

### 🏋️ Rutina Recomendada de Hoy (Torso / Empuje + Tríceps)
1. **Press de Banca** (Pecho) - 4 series x 8-10 reps (Descanso: 2 min)
2. **Press Inclinado con Mancuernas** (Pecho) - 3 series x 10-12 reps
3. **Press Militar con Barra** (Hombros) - 3 series x 8-10 reps
4. **Elevaciones Laterales en Polea** (Hombros) - 4 series x 12-15 reps
5. **Extensiones de Tríceps con Cuerda** (Brazos) - 3 series x 12-15 reps
6. **Fondos en Paralelas** (Pecho / Tríceps) - 3 series al fallo técnico

```json routine
[
  {{"name": "Press de Banca", "muscle": "Pecho", "sets": 4, "target_reps": 8, "weight": 60.0}},
  {{"name": "Press Inclinado con Mancuernas", "muscle": "Pecho", "sets": 3, "target_reps": 10, "weight": 22.0}},
  {{"name": "Press Militar con Barra", "muscle": "Hombros", "sets": 3, "target_reps": 8, "weight": 40.0}},
  {{"name": "Elevaciones Laterales en Polea", "muscle": "Hombros", "sets": 4, "target_reps": 12, "weight": 7.5}},
  {{"name": "Extensiones de Tríceps con Cuerda", "muscle": "Brazos", "sets": 3, "target_reps": 12, "weight": 20.0}},
  {{"name": "Fondos en Paralelas", "muscle": "Pecho", "sets": 3, "target_reps": 10, "weight": 0.0}}
]
```

💡 *Puedes pulsar el botón de abajo para cargar estos ejercicios directamente en tu día de hoy.*"""

    if "descanso" in msg or "tiempo" in msg or "segundos" in msg:
        return f"""Sobre los tiempos de descanso entre series, {user_name}:

* **Ejercicios multiarticulares pesados** (Sentadilla, Peso Muerto, Press Banca): **2 a 3 minutos**. Permite la resíntesis completa de fosfocreatina (ATP) para que la siguiente serie sea igual de efectiva.
* **Ejercicios de aislamiento o máquinas** (Curls de bíceps, elevaciones laterales, extensiones): **60 a 90 segundos** es suficiente.
* Recuerda que descansar muy poco reduce el volumen total y la tensión mecánica, que son los principales motores de la hipertrofia."""

    if "estanc" in msg or "no subo" in msg or "meseta" in msg:
        return f"""Si sientes que te has estancado en un ejercicio, {user_name}, aplica esta estrategia en 3 pasos:

1. **Micro-carga**: En lugar de saltar 5 kg, utiliza discos fraccionados de 1.25 kg (+2.5 kg en total).
2. **Descarga Estratégica (Deload)**: Si llevas más de 6-8 semanas entrenando duro, reduce las series un 50% y el peso un 20% durante una semana. El sistema nervioso se recuperará y volverás más fuerte.
3. **Revisión de Sueño y Nutrición**: Si duermes menos de 7 horas o estás en déficit calórico sin suficiente proteína (1.6 a 2.0g por kg de peso), la fuerza se resiente primero."""

    # General welcome response
    return f"""¡Hola {user_name}! Soy tu **FitCoach con IA** en FitChallenge.

Estoy aquí para ayudarte a sacar el máximo provecho de tus entrenamientos:
* 🎯 **Sobrecarga Progresiva**: Analizo tu última sesión y te digo qué peso y reps intentar hoy.
* 📋 **Diseño de Rutinas**: Pídeme cualquier rutina y la cargaré directamente en tu día.
* 💡 **Consejos de Técnica y Recuperación**: Pregúntame sobre descansos, nutrición o cómo romper estancamientos.

¿Qué te gustaría entrenar o consultar hoy?"""
