import os
import re
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

def detect_ai_provider(api_key):
    """Detects provider based on API key prefix."""
    if not api_key:
        return None
    k = api_key.strip()
    if k.startswith("gsk_"):
        return "groq"
    if k.startswith("sk-or-"):
        return "openrouter"
    if k.startswith("sk-"):
        return "openai"
    return "gemini"

def get_ai_api_key(client_key=None):
    """Retrieve API key from client header, environment, or database setting."""
    if client_key and isinstance(client_key, str) and client_key.strip():
        k = client_key.strip()
        return k, detect_ai_provider(k)

    for env_var in ["GEMINI_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY", "AI_API_KEY"]:
        val = os.environ.get(env_var, "").strip()
        if val:
            return val, detect_ai_provider(val)

    try:
        import models
        db_key = models.get_app_setting("ai_api_key") or models.get_app_setting("gemini_api_key")
        if db_key and isinstance(db_key, str) and db_key.strip():
            k = db_key.strip()
            return k, detect_ai_provider(k)
    except Exception:
        pass

    return "", None

def get_gemini_api_key(client_key=None):
    """Backwards compatibility alias."""
    key, _ = get_ai_api_key(client_key)
    return key

def _format_weight_label(w):
    if w <= 0:
        return "peso corporal"
    return f"{w:g} kg"

def calculate_progressive_overload(exercise_name, muscle_group, last_sets):
    """
    Implements evidence-based Double Progression Model respecting individual set loads:
    1. If user reached the ceiling of their rep range in all sets (e.g. >= 12 reps or >= 10 reps),
       increase weight (2.5% to 5%) and reset reps to the floor of the range (e.g. 8-10 reps).
    2. If user is within the range but hasn't maxed out all sets (e.g. 11, 9, 8 reps),
       maintain each set's individual weight and aim for +1 or +2 reps in the later sets.
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

    # Extract metrics per set
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

    # Check if all sets had identical weight or variable weights (e.g. ramp / pyramid)
    unique_weights = list(dict.fromkeys(weights))
    is_single_weight = (len(unique_weights) <= 1)

    # Detailed representation of each set from previous session
    set_details = [
        f"S{idx+1}: {reps[idx]} reps con {_format_weight_label(weights[idx])}"
        for idx in range(num_sets)
    ]
    detailed_breakdown = ", ".join(set_details)

    suggested_sets = []
    overload_type = "maintain_add_reps"
    summary = ""
    explanation = ""

    # Case 1: Bodyweight exercise (e.g., dominadas, fondos, planchas)
    if is_bodyweight:
        if avg_reps >= 12:
            overload_type = "add_ballast"
            summary = f"Añadir lastre de +{weight_step:g} kg o aumentar a {min_reps + 2} reps"
            explanation = f"Completaste un promedio de {avg_reps:.0f} reps con peso corporal. Tu cuerpo ya se adaptó: puedes empezar a lastrarte con {weight_step:g} kg o buscar más repeticiones."
            for idx in range(num_sets):
                suggested_sets.append({
                    "set_number": idx + 1,
                    "reps": max(8, reps[idx] - 2),
                    "weight": weight_step
                })
        else:
            overload_type = "add_reps"
            summary = f"Intentar +1 repetición en cada serie (objetivo: {min_reps + 1}+ reps)"
            explanation = f"La sesión anterior hiciste: {detailed_breakdown}. La sobrecarga progresiva hoy se logra sumando repeticiones totales."
            for idx in range(num_sets):
                suggested_sets.append({
                    "set_number": idx + 1,
                    "reps": reps[idx] + 1,
                    "weight": 0.0
                })

    # Case 2: User hit the top of the rep range in all sets (e.g., all sets >= 12 reps, or all >= 10 with 3+ sets)
    elif all(r >= 12 for r in reps) or (all(r >= 10 for r in reps) and num_sets >= 3):
        overload_type = "increase_weight"
        if is_single_weight:
            new_weight = round(max_weight + weight_step, 2)
            summary = f"Subir a {_format_weight_label(new_weight)} (+{weight_step:g} kg) en rango de 8 a 10 reps"
            explanation = f"¡Dominaste los {_format_weight_label(max_weight)} en todas tus series ({min_reps}+ reps)! Corresponde aplicar sobrecarga por intensidad aumentando {weight_step:g} kg."
            for idx in range(num_sets):
                suggested_sets.append({
                    "set_number": idx + 1,
                    "reps": max(8, min(10, reps[idx] - 2)),
                    "weight": new_weight
                })
        else:
            summary = f"Aumentar carga (+{weight_step:g} kg) en tus series de trabajo"
            explanation = f"La sesión anterior registraste: {detailed_breakdown}. Al dominar el rango de repeticiones, puedes subir {weight_step:g} kg en tus series de trabajo."
            for idx in range(num_sets):
                suggested_sets.append({
                    "set_number": idx + 1,
                    "reps": max(8, min(10, reps[idx] - 2)),
                    "weight": round(weights[idx] + weight_step, 2)
                })

    # Case 3: In the middle of rep range -> Maintain each set's base load, aim for +1-2 reps on weaker sets
    else:
        overload_type = "increase_reps"
        if is_single_weight:
            summary = f"Mantener {_format_weight_label(max_weight)} y superar las {sum(reps)} reps totales (+1 rep en cada serie)"
            explanation = f"La sesión anterior lograste series de {', '.join(str(r) for r in reps)} reps con {_format_weight_label(max_weight)}. La meta de hoy es ganar 1 o 2 repeticiones en las series intermedias antes de subir peso."
        else:
            summary = f"Superar las {sum(reps)} reps totales manteniendo tus cargas ({detailed_breakdown})"
            explanation = f"La sesión anterior registraste: {detailed_breakdown} (peso máximo: {_format_weight_label(max_weight)}). La meta de hoy es mantener tus pesos de trabajo y buscar ganar 1 o 2 repeticiones en tus series para acumular mayor volumen efectivo."

        for idx in range(num_sets):
            # Target +1 rep on sets that haven't hit ceiling (12 reps)
            r = reps[idx]
            target_r = r + 1 if (idx > 0 or r < 12) else r
            suggested_sets.append({
                "set_number": idx + 1,
                "reps": target_r,
                "weight": weights[idx]  # Preserve each set's actual weight!
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

def _query_openai_compatible(url, api_key, model, fallback_model, system_prompt, user_message, chat_history=None):
    """Generic client for OpenAI, Groq, and OpenRouter chat completions."""
    messages = [{"role": "system", "content": system_prompt}]
    if chat_history and isinstance(chat_history, list):
        for msg in chat_history[-8:]:
            role = "user" if msg.get("role") in ["user", "human"] else "assistant"
            txt = (msg.get("content") or "").strip()
            if txt:
                messages.append({"role": role, "content": txt})
    messages.append({"role": "user", "content": user_message})

    models_to_try = [model]
    if fallback_model and fallback_model != model:
        models_to_try.append(fallback_model)

    last_error = ""
    for m in models_to_try:
        payload = {
            "model": m,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1200
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        try:
            req = urllib.request.Request(
                url,
                data=body_bytes,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=14) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                choices = data.get("choices", [])
                if choices and "message" in choices[0]:
                    content = choices[0]["message"].get("content", "")
                    if content:
                        return content, None
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            last_error = f"HTTP {e.code}: {err_body}"
            continue
        except Exception as e:
            last_error = str(e)
            continue

    return None, f"Error en proveedor OpenAI/Groq ({last_error})"

def _query_gemini(api_key, system_prompt, user_message, chat_history=None):
    """Client for Google Gemini REST API."""
    contents = []
    if chat_history and isinstance(chat_history, list):
        for msg in chat_history[-8:]:
            role = "user" if msg.get("role") in ["user", "human"] else "model"
            text = (msg.get("content") or "").strip()
            if text:
                contents.append({"role": role, "parts": [{"text": text}]})

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
            continue
        except Exception as e:
            last_error = str(e)
            continue

    return None, f"Error al consultar Gemini ({last_error})"

def query_llm_api(api_key, system_prompt, user_message, chat_history=None):
    """
    Unified entry point for AI providers: Gemini, Groq, OpenAI, or OpenRouter.
    """
    if not api_key:
        return None, "No se proporcionó API Key"

    provider = detect_ai_provider(api_key)

    if provider == "groq":
        return _query_openai_compatible(
            url="https://api.groq.com/openai/v1/chat/completions",
            api_key=api_key,
            model="llama-3.3-70b-versatile",
            fallback_model="llama-3.1-8b-instant",
            system_prompt=system_prompt,
            user_message=user_message,
            chat_history=chat_history
        )
    elif provider == "openrouter":
        return _query_openai_compatible(
            url="https://openrouter.ai/api/v1/chat/completions",
            api_key=api_key,
            model="google/gemini-2.0-flash-exp:free",
            fallback_model="meta-llama/llama-3.3-70b-instruct:free",
            system_prompt=system_prompt,
            user_message=user_message,
            chat_history=chat_history
        )
    elif provider == "openai":
        return _query_openai_compatible(
            url="https://api.openai.com/v1/chat/completions",
            api_key=api_key,
            model="gpt-4o-mini",
            fallback_model="gpt-3.5-turbo",
            system_prompt=system_prompt,
            user_message=user_message,
            chat_history=chat_history
        )
    else:
        return _query_gemini(api_key, system_prompt, user_message, chat_history)

def query_gemini_api(api_key, system_prompt, user_message, chat_history=None):
    """Compatibility alias for query_llm_api."""
    return query_llm_api(api_key, system_prompt, user_message, chat_history)

def _guess_muscle_group(name):
    low = name.lower()
    if any(w in low for w in ['sentadilla', 'prensa', 'cuadriceps', 'cuádriceps', 'femoral', 'pierna', 'gemelo', 'zancada', 'hack', 'bulgara', 'búlgara', 'aductores', 'isquio']):
        return 'Piernas'
    if any(w in low for w in ['banca', 'pecho', 'apertura', 'flexion', 'flexión', 'inclinado', 'declinado', 'cruces', 'chest', 'fondos']):
        return 'Pecho'
    if any(w in low for w in ['espalda', 'dominada', 'jalon', 'jalón', 'remo', 'dorsal', 'pullover', 'trapecio', 'peso muerto', 'deadlift']):
        return 'Espalda'
    if any(w in low for w in ['militar', 'hombro', 'lateral', 'pajaro', 'pájaro', 'arnold', 'frontal', 'deltoides', 'face pull']):
        return 'Hombros'
    if any(w in low for w in ['curl', 'triceps', 'tríceps', 'biceps', 'bíceps', 'martillo', 'frances', 'francés', 'copa', 'antebrazo', 'brazo']):
        return 'Brazos'
    if any(w in low for w in ['plancha', 'crunch', 'abdominal', 'core', 'rueda', 'elevacion de piernas', 'oblicuo']):
        return 'Core'
    return 'General'

def _normalize_routine_exercises(exercise_list):
    res = []
    if not isinstance(exercise_list, list):
        return None
    for ex in exercise_list[:15]:
        if not isinstance(ex, dict):
            continue
        name = str(ex.get("name", "")).strip()
        if not name:
            continue
        muscle = str(ex.get("muscle", "")).strip() or _guess_muscle_group(name)
        try:
            sets = max(1, min(int(ex.get("sets", 3) or 3), 10))
        except Exception:
            sets = 3
        try:
            target_reps = max(1, min(int(ex.get("target_reps", ex.get("reps", 10)) or 10), 100))
        except Exception:
            target_reps = 10
        try:
            weight = max(0.0, min(float(ex.get("weight", 0) or 0), 1000.0))
        except Exception:
            weight = 0.0
        res.append({
            "name": name,
            "muscle": muscle,
            "sets": sets,
            "target_reps": target_reps,
            "weight": weight
        })
    return res if len(res) > 0 else None

def extract_routine_from_text(text):
    """
    Intelligently extracts routine exercises from AI responses across multiple formats:
    1. ```json routine ... ```
    2. ```json ... ``` (with array or object containing exercises/routine)
    3. Standalone JSON array [ { "name": ... } ]
    4. Text list fallback (e.g. "1. Press de Banca: 4 series x 8-10 reps (60 kg)")
    """
    if not text or not isinstance(text, str):
        return None

    # Strategy 1 & 2: Markdown code blocks with json
    code_blocks = re.findall(r'```(?:json)?(?:\s*routine)?\s*([\s\S]*?)```', text, re.IGNORECASE)
    for block in code_blocks:
        b = block.strip()
        try:
            parsed = json.loads(b)
            if isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict) and 'name' in parsed[0]:
                norm = _normalize_routine_exercises(parsed)
                if norm:
                    return norm
            if isinstance(parsed, dict):
                for k in ['routine', 'exercises', 'rutina', 'ejercicios']:
                    if k in parsed and isinstance(parsed[k], list) and len(parsed[k]) > 0:
                        norm = _normalize_routine_exercises(parsed[k])
                        if norm:
                            return norm
        except Exception:
            pass

    # Strategy 3: Naked JSON array in text
    arr_matches = re.findall(r'(\[\s*\{[\s\S]*?"name"[\s\S]*?\}\s*\])', text)
    for m in arr_matches:
        try:
            parsed = json.loads(m.strip())
            norm = _normalize_routine_exercises(parsed)
            if norm:
                return norm
        except Exception:
            pass

    # Strategy 4: Parse bullet/numbered lists of exercises
    lines = text.split('\n')
    extracted = []
    exercise_line_re = re.compile(
        r'^(?:\d+[\.\)]|\-|\*)\s+\*?\*?([A-Za-zÁÉÍÓÚáéíóúñÑ0-9\s\/\(\)]+?)\*?\*?\s*(?:\(([^)]+)\))?\s*[:\-–]\s*(\d+)\s*(?:series|sets)\s*(?:x|de)?\s*(\d+(?:-\d+)?)\s*(?:reps?|repeticiones)?(?:\s*(?:con|@|\()\s*([\d\.]+)\s*(?:kg)?)?',
        re.IGNORECASE
    )

    for line in lines:
        line_clean = line.strip()
        match = exercise_line_re.search(line_clean)
        if match:
            raw_name = match.group(1).strip(' *:-\t')
            paren_muscle = match.group(2)
            sets = int(match.group(3))
            reps_raw = match.group(4)
            if '-' in reps_raw:
                try:
                    target_reps = int(reps_raw.split('-')[0])
                except Exception:
                    target_reps = 10
            else:
                target_reps = int(reps_raw)
            weight = float(match.group(5)) if match.group(5) else 0.0
            muscle = paren_muscle.strip() if paren_muscle else _guess_muscle_group(raw_name)

            extracted.append({
                'name': raw_name,
                'muscle': muscle,
                'sets': sets,
                'target_reps': target_reps,
                'weight': weight
            })

    if len(extracted) >= 2:
        return _normalize_routine_exercises(extracted)

    return None

def clean_routine_markdown(text):
    """Cleans up raw json blocks from markdown text so chat message looks pristine."""
    if not text:
        return ""
    cleaned = re.sub(r'```(?:json)?(?:\s*routine)?\s*\[[\s\S]*?\]\s*```', '', text, flags=re.IGNORECASE)
    cleaned = re.sub(r'```(?:json)?(?:\s*routine)?\s*\{[\s\S]*?\}\s*```', '', text, flags=re.IGNORECASE)
    return cleaned.strip()

def _get_user_exercise_load(name, default_weight, default_sets, default_reps, catalog):
    """
    Finds the user's logged metrics for an exercise to avoid generic placeholders.
    """
    if not catalog or not isinstance(catalog, list):
        return default_weight, default_sets, default_reps

    clean_target = name.strip().lower()
    best_match = None
    for ex in catalog:
        c_name = ex.get("name", "").strip().lower()
        if c_name == clean_target or clean_target in c_name or c_name in clean_target:
            best_match = ex
            break

    if best_match:
        logged_max = float(best_match.get("max_weight", 0) or 0)
        w = logged_max if logged_max > 0 else default_weight
        s_count = int(best_match.get("total_sets", 0) or default_sets)
        s_count = max(2, min(s_count, 5))
        logged_reps = [int(s.get("reps", 10) or 10) for s in best_match.get("sets", [])]
        avg_r = int(sum(logged_reps) / len(logged_reps)) if logged_reps else default_reps
        return w, s_count, avg_r

    return default_weight, default_sets, default_reps

def generate_local_coach_response(user_message, user_context):
    """
    Expanded sports science knowledge base covering routines, nutrition,
    biomechanics, injuries, supplements, and progressive overload.
    Routines are dynamically customized with the user's actual weights and history.
    """
    msg = (user_message or "").lower()
    user_name = user_context.get("name", "Campeón")
    catalog = user_context.get("exercise_catalog", [])

    # 1. SUPPLEMENTS: Creatina, Cafeína, Suplementos (Check first to avoid false positives)
    if any(w in msg for w in ["creatina", "suplemento", "suplementos", "cafeina", "cafeína", "whey", "preentreno", "pre-entreno"]):
        return f"""Aquí tienes la evidencia científica sobre suplementación, {user_name}:

1. **Monohidrato de Creatina (El rey de los suplementos)**:
   - **Dosis**: 3 a 5 gramos diarios todos los días (incluso los días de descanso).
   - **Momento**: A cualquier hora, la clave es la acumulación diaria en el músculo.
   - **Mitos**: No requiere fase de carga, no causa calvicie y el agua que retiene es **intracelular** (hace al músculo verse más lleno y fuerte).
2. **Proteína en Polvo (Whey)**:
   - Es simplemente comida en polvo práctica. Úsala si te cuesta llegar a tu meta de proteína con alimentos enteros.
3. **Cafeína**:
   - Dosis efectiva: 3 a 6 mg por kg de peso corporal tomada 30-45 minutos antes de entrenar. Aumenta la fuerza y reduce la percepción del esfuerzo."""

    # 2. NUTRITION: Proteína / Dieta / Calorías
    if any(w in msg for w in ["proteina", "proteína", "comer", "dieta", "caloria", "caloría", "volumen", "definicion", "definición", "deficit", "déficit", "grasa", "macronutriente"]):
        return f"""Hola {user_name}. En nutrición deportiva basada en evidencia, los puntos clave son:

1. **Requerimiento de Proteína**:
   - Para ganar masa muscular o preservar músculo en definición: **1.6 a 2.2 gramos de proteína por kilogramo de peso corporal** al día.
   - Fuentes recomendadas: Pechuga de pollo, huevos, pescado, carne magra, lácteos desnatados, tofu y proteína whey.
2. **Balance Calórico**:
   - **Volumen (Ganar músculo)**: Superávit ligero de **+200 a +300 kcal** sobre tu mantenimiento. Subir más rápido solo añade grasa.
   - **Definición (Perder grasa)**: Déficit moderado de **-300 a -500 kcal**. Te permite perder 0.5 a 1% de peso corporal semanal sin perder fuerza.
3. **Nutrición Pre y Post Entrenamiento**:
   - Come carbohidratos complejos + 20-30g de proteína 1.5 a 2 horas antes de entrenar para tener glucógeno muscular lleno.
   - La ventana anabólica dura varias horas: lo crucial es cumplir tu total diario de proteínas."""

    # 3. ROUTINE: Piernas / Cuádriceps / Femorales
    if any(w in msg for w in ["pierna", "cuadriceps", "femoral", "sentadilla", "legs", "hacka"]):
        w_hack, s_hack, r_hack = _get_user_exercise_load("Sentadilla Hack (Hacka)", 80.0, 4, 8, catalog)
        w_pren, s_pren, r_pren = _get_user_exercise_load("Prensa de Piernas", 120.0, 3, 10, catalog)
        w_fem, s_fem, r_fem = _get_user_exercise_load("Curl Femoral Tumbado", 40.0, 4, 10, catalog)
        w_ext, s_ext, r_ext = _get_user_exercise_load("Extensiones de Cuádriceps", 45.0, 3, 12, catalog)
        w_gem, s_gem, r_gem = _get_user_exercise_load("Elevación de Talones", 50.0, 4, 15, catalog)

        return f"""¡Excelente día de piernas, {user_name}! He preparado esta rutina adaptada a tus marcas registradas para máximo estímulo:

### 🦵 Rutina de Piernas (Basada en tu Historial)
1. **Sentadilla Hack (Hacka)** (Piernas) - {s_hack} series x {r_hack} reps ({_format_weight_label(w_hack)}, Descanso: 3 min)
2. **Prensa de Piernas** (Piernas) - {s_pren} series x {r_pren} reps ({_format_weight_label(w_pren)})
3. **Curl Femoral Tumbado** (Piernas) - {s_fem} series x {r_fem} reps ({_format_weight_label(w_fem)})
4. **Extensiones de Cuádriceps** (Piernas) - {s_ext} series x {r_ext} reps ({_format_weight_label(w_ext)})
5. **Elevación de Talones** (Piernas) - {s_gem} series x {r_gem} reps ({_format_weight_label(w_gem)})

```json routine
[
  {{"name": "Sentadilla Hack (Hacka)", "muscle": "Piernas", "sets": {s_hack}, "target_reps": {r_hack}, "weight": {w_hack}}},
  {{"name": "Prensa de Piernas", "muscle": "Piernas", "sets": {s_pren}, "target_reps": {r_pren}, "weight": {w_pren}}},
  {{"name": "Curl Femoral Tumbado", "muscle": "Piernas", "sets": {s_fem}, "target_reps": {r_fem}, "weight": {w_fem}}},
  {{"name": "Extensiones de Cuádriceps", "muscle": "Piernas", "sets": {s_ext}, "target_reps": {r_ext}, "weight": {w_ext}}},
  {{"name": "Elevación de Talones", "muscle": "Piernas", "sets": {s_gem}, "target_reps": {r_gem}, "weight": {w_gem}}}
]
```

💡 *Pulsa el botón de abajo para sumarla directamente a tu día de hoy.*"""

    # 4. ROUTINE: Espalda / Pull / Tirón
    if any(w in msg for w in ["espalda", "pull", "tiron", "tirón", "dorsal", "remo", "dominada"]):
        w_jal, s_jal, r_jal = _get_user_exercise_load("Jalón al Pecho en Polea", 55.0, 4, 8, catalog)
        w_rem, s_rem, r_rem = _get_user_exercise_load("Remo con Barra", 60.0, 4, 8, catalog)
        w_gir, s_gir, r_gir = _get_user_exercise_load("Remo en Polea Baja", 50.0, 3, 10, catalog)
        w_pul, s_pul, r_pul = _get_user_exercise_load("Pullover en Polea Alta", 25.0, 3, 12, catalog)
        w_fac, s_fac, r_fac = _get_user_exercise_load("Face Pulls", 20.0, 3, 15, catalog)
        w_cur, s_cur, r_cur = _get_user_exercise_load("Curl con Barra Z", 25.0, 3, 10, catalog)

        return f"""¡A construir una espalda densa y ancha, {user_name}! Aquí tienes tu rutina de tirón ajustada a tus pesos de trabajo:

### 🦅 Rutina de Espalda y Bíceps (Pull)
1. **Jalón al Pecho en Polea** (Espalda) - {s_jal} series x {r_jal} reps ({_format_weight_label(w_jal)})
2. **Remo con Barra** (Espalda) - {s_rem} series x {r_rem} reps ({_format_weight_label(w_rem)})
3. **Remo en Polea Baja** (Espalda) - {s_gir} series x {r_gir} reps ({_format_weight_label(w_gir)})
4. **Pullover en Polea Alta** (Espalda) - {s_pul} series x {r_pul} reps ({_format_weight_label(w_pul)})
5. **Face Pulls** (Hombros) - {s_fac} series x {r_fac} reps ({_format_weight_label(w_fac)})
6. **Curl con Barra Z** (Brazos) - {s_cur} series x {r_cur} reps ({_format_weight_label(w_cur)})

```json routine
[
  {{"name": "Jalón al Pecho en Polea", "muscle": "Espalda", "sets": {s_jal}, "target_reps": {r_jal}, "weight": {w_jal}}},
  {{"name": "Remo con Barra", "muscle": "Espalda", "sets": {s_rem}, "target_reps": {r_rem}, "weight": {w_rem}}},
  {{"name": "Remo en Polea Baja", "muscle": "Espalda", "sets": {s_gir}, "target_reps": {r_gir}, "weight": {w_gir}}},
  {{"name": "Pullover en Polea Alta", "muscle": "Espalda", "sets": {s_pul}, "target_reps": {r_pul}, "weight": {w_pul}}},
  {{"name": "Face Pulls", "muscle": "Hombros", "sets": {s_fac}, "target_reps": {r_fac}, "weight": {w_fac}}},
  {{"name": "Curl con Barra Z", "muscle": "Brazos", "sets": {s_cur}, "target_reps": {r_cur}, "weight": {w_cur}}}
]
```

💡 *Pulsa el botón de abajo para sumarla directamente a tu día de hoy.*"""

    # 5. ROUTINE: Brazos / Bíceps / Tríceps
    if any(w in msg for w in ["brazo", "brazos", "bicep", "bícep", "tricep", "trícep"]):
        w_fra, s_fra, r_fra = _get_user_exercise_load("Press Francés con Barra Z", 25.0, 4, 10, catalog)
        w_curz, s_curz, r_curz = _get_user_exercise_load("Curl con Barra Z", 25.0, 4, 8, catalog)
        w_tri, s_tri, r_tri = _get_user_exercise_load("Extensiones de Tríceps con Cuerda", 20.0, 3, 12, catalog)
        w_mar, s_mar, r_mar = _get_user_exercise_load("Curl Martillo con Mancuernas", 14.0, 3, 10, catalog)
        w_fon, s_fon, r_fon = _get_user_exercise_load("Fondos en Paralelas", 0.0, 3, 10, catalog)

        return f"""¡Sesión de brazos, {user_name}! Ajustada a tus marcas de trabajo para congestión e hipertrofia:

### 💪 Rutina de Brazos (Bíceps + Tríceps)
1. **Press Francés con Barra Z** (Brazos) - {s_fra} series x {r_fra} reps ({_format_weight_label(w_fra)})
2. **Curl con Barra Z** (Brazos) - {s_curz} series x {r_curz} reps ({_format_weight_label(w_curz)})
3. **Extensiones de Tríceps con Cuerda** (Brazos) - {s_tri} series x {r_tri} reps ({_format_weight_label(w_tri)})
4. **Curl Martillo con Mancuernas** (Brazos) - {s_mar} series x {r_mar} reps ({_format_weight_label(w_mar)})
5. **Fondos en Paralelas** (Brazos) - {s_fon} series x {r_fon} reps ({_format_weight_label(w_fon)})

```json routine
[
  {{"name": "Press Francés con Barra Z", "muscle": "Brazos", "sets": {s_fra}, "target_reps": {r_fra}, "weight": {w_fra}}},
  {{"name": "Curl con Barra Z", "muscle": "Brazos", "sets": {s_curz}, "target_reps": {r_curz}, "weight": {w_curz}}},
  {{"name": "Extensiones de Tríceps con Cuerda", "muscle": "Brazos", "sets": {s_tri}, "target_reps": {r_tri}, "weight": {w_tri}}},
  {{"name": "Curl Martillo con Mancuernas", "muscle": "Brazos", "sets": {s_mar}, "target_reps": {r_mar}, "weight": {w_mar}}},
  {{"name": "Fondos en Paralelas", "muscle": "Brazos", "sets": {s_fon}, "target_reps": {r_fon}, "weight": {w_fon}}}
]
```

💡 *Pulsa el botón de abajo para sumarla directamente a tu día de hoy.*"""

    # 6. ROUTINE: General Torso / Pecho / Push / Rutina para hoy
    if any(w in msg for w in ["rutina", "entrenar", "push", "empuje", "pecho", "hoy", "crear", "diseñ"]):
        w_ban, s_ban, r_ban = _get_user_exercise_load("Press de Banca", 60.0, 4, 8, catalog)
        w_inc, s_inc, r_inc = _get_user_exercise_load("Press Inclinado con Mancuernas", 40.0, 3, 10, catalog)
        w_mil, s_mil, r_mil = _get_user_exercise_load("Press Militar con Barra", 40.0, 3, 8, catalog)
        w_lat, s_lat, r_lat = _get_user_exercise_load("Elevaciones Laterales", 8.0, 4, 12, catalog)
        w_trie, s_trie, r_trie = _get_user_exercise_load("Extensiones de Tríceps con Cuerda", 20.0, 3, 12, catalog)
        w_fond, s_fond, r_fond = _get_user_exercise_load("Fondos en Paralelas", 0.0, 3, 10, catalog)

        return f"""¡Excelente, {user_name}! He diseñado esta rutina de empuje y torso basada en tus sesiones previas y pesos reales:

### 🏋️ Rutina de Torso (Basada en tus Marcas Reales)
1. **Press de Banca** (Pecho) - {s_ban} series x {r_ban} reps ({_format_weight_label(w_ban)}, Descanso: 2 min)
2. **Press Inclinado con Mancuernas** (Pecho) - {s_inc} series x {r_inc} reps ({_format_weight_label(w_inc)})
3. **Press Militar con Barra** (Hombros) - {s_mil} series x {r_mil} reps ({_format_weight_label(w_mil)})
4. **Elevaciones Laterales** (Hombros) - {s_lat} series x {r_lat} reps ({_format_weight_label(w_lat)})
5. **Extensiones de Tríceps con Cuerda** (Brazos) - {s_trie} series x {r_trie} reps ({_format_weight_label(w_trie)})
6. **Fondos en Paralelas** (Pecho) - {s_fond} series x {r_fond} reps ({_format_weight_label(w_fond)})

```json routine
[
  {{"name": "Press de Banca", "muscle": "Pecho", "sets": {s_ban}, "target_reps": {r_ban}, "weight": {w_ban}}},
  {{"name": "Press Inclinado con Mancuernas", "muscle": "Pecho", "sets": {s_inc}, "target_reps": {r_inc}, "weight": {w_inc}}},
  {{"name": "Press Militar con Barra", "muscle": "Hombros", "sets": {s_mil}, "target_reps": {r_mil}, "weight": {w_mil}}},
  {{"name": "Elevaciones Laterales", "muscle": "Hombros", "sets": {s_lat}, "target_reps": {r_lat}, "weight": {w_lat}}},
  {{"name": "Extensiones de Tríceps con Cuerda", "muscle": "Brazos", "sets": {s_trie}, "target_reps": {r_trie}, "weight": {w_trie}}},
  {{"name": "Fondos en Paralelas", "muscle": "Pecho", "sets": {s_fond}, "target_reps": {r_fond}, "weight": {w_fond}}}
]
```

💡 *Pulsa el botón de abajo para cargar estos ejercicios directamente en tu día de hoy.*"""

    # 7. EXERCISE TECHNIQUE & BIOMECHANICS: Hack, Búlgara, Banca, Inclinado, Peso Muerto, Dominadas, Laterales
    if any(w in msg for w in ["como hacer", "cómo hacer", "tecnica", "técnica", "posicion", "posición", "postura", "forma correcta"]):
        if any(w in msg for w in ["hack", "hacka"]):
            return f"""Aquí tienes la técnica correcta y biomecánica para la **Sentadilla Hack**, {user_name}:

1. **Colocación de los pies**:
   - Apoya los pies en el tercio medio-alto de la plataforma, separados a la anchura de tus hombros.
   - Puntas de los pies ligeramente abiertas hacia afuera (15° a 30°).
   - **Clave**: Nunca despegues los talones de la base durante el movimiento.
2. **Posición de la espalda**:
   - Pega firmemente la zona lumbar y la espalda alta contra el respaldo acolchado. No permitas que la pelvis se despegue o rote hacia adelante en el punto bajo.
3. **Profundidad y recorrido**:
   - Desciende de forma controlada (2-3 segundos) hasta que tus muslos queden al menos paralelos o por debajo de la plataforma (flexión de rodilla a 90°-110°).
   - Empuja con toda la planta del pie, haciendo foco en los cuádriceps, y no bloquees bruscamente las rodillas arriba."""

        if any(w in msg for w in ["bulgara", "búlgara"]):
            return f"""Técnica de la **Sentadilla Búlgara** para máximo estímulo y equilibrio, {user_name}:

1. **Distancia y apoyo**:
   - Apoya el empeine del pie trasero en un banco a la altura de tu rodilla.
   - Da un paso hacia adelante con la pierna delantera (al descender, la rodilla debe quedar alineada sobre el empeine o mediopié).
2. **Énfasis muscular según inclinación del torso**:
   - **Para Glúteos**: Inclina el torso hacia adelante unos 20-30° manteniendo la columna neutra y da un paso ligeramente más largo.
   - **Para Cuádriceps**: Mantén el torso vertical y permite que la rodilla avance sobre la punta del pie.
3. **Descenso**:
   - Baja verticalmente hasta que la rodilla trasera quede a 2-3 cm del suelo. Empuja con el talón y mediopié delantero."""

        if any(w in msg for w in ["inclinado", "pecho superior"]):
            return f"""Técnica del **Press Inclinado con Mancuernas**, {user_name}:

1. **Inclinación del banco**:
   - El ángulo ideal es de **30 grados** (a lo sumo 45°). Si lo subes a 60°, la mayor parte del trabajo se desplaza a los deltoides anteriores en lugar del pectoral superior.
2. **Alineación de brazos y muñecas**:
   - Mantén los codos en un ángulo de **45 a 60 grados** respecto a tu torso (forma de flecha, nunca abiertos a 90° para proteger el manguito rotador).
   - Muñecas firmes y alineadas sobre los codos.
3. **Retracción escapular**:
   - Saca pecho y junta los omóplatos contra el banco durante toda la serie. Baja las mancuernas controladas hasta el nivel de la parte superior del pecho."""

        if any(w in msg for w in ["peso muerto", "deadlift"]):
            return f"""Técnica segura para el **Peso Muerto**, {user_name}:

1. **Posición de partida**:
   - Barra sobre la mitad de tus pies (pegada a unos 2-3 cm de tus espinillas).
   - Agarre por fuera de las piernas, brazos totalmente rectos como cuerdas.
2. **Bisagra de cadera y columna neutra**:
   - Lleva la cadera hacia atrás (*hip hinge*). No redondees la espalda baja ni hiper-extiendas el cuello.
   - Activa el *bracing*: llena el abdomen de aire y aprieta como un cinturón natural.
3. **Empuje**:
   - Piensa en **empujar el suelo con las piernas**, no en tirar con los brazos. La barra debe subir rozando tus espinillas y muslos."""

        if any(w in msg for w in ["lateral", "laterales", "pajaro", "pájaro"]):
            return f"""Técnica para **Elevaciones Laterales** (Deltoides Lateral), {user_name}:

1. **Plano escapular**:
   - No eleves los brazos exactamente en línea recta hacia los lados (plano frontal). Elévalos unos **20-30° hacia adelante** (en el plano escapular natural del hombro).
2. **Flexión de codos**:
   - Mantén una ligerísima flexión de codos (10-15°) fija durante todo el recorrido.
3. **Altura y control**:
   - Sube hasta la altura de los hombros. No utilices inercia con las piernas ni te balancees; una pausa de medio segundo arriba garantiza máxima tensión mecánica."""

    # 8. TRAINING SCIENCE: RIR, RPE, Fallo, Frecuencia, Series semanales
    if any(w in msg for w in ["rpe", "rir", "fallo", "frecuencia", "series semanales", "volumen de entrenamiento"]):
        return f"""Claves sobre intensidad y volumen de entrenamiento, {user_name}:

1. **¿Qué es RPE y RIR?**:
   - **RIR (Repeticiones en Recámara)**: Cuántas repeticiones te faltaban para llegar al fallo absoluto.
   - **RIR 1-2 (RPE 8-9)**: Es la zona óptima para ganar músculo. Te deja a 1 o 2 repeticiones de no poder levantar la barra, logrando el 95% del estímulo con la mitad de fatiga y riesgo articular.
2. **¿Llegar al fallo muscular?**:
   - En **ejercicios analíticos o en máquinas** (ej. curl de bíceps, elevaciones laterales, extensiones): Puedes ir al fallo técnico en la última serie.
   - En **ejercicios pesados con barra libre** (ej. sentadilla, peso muerto, banca pesada): Mantén siempre **RIR 1 o 2** por seguridad.
3. **Frecuencia óptima**:
   - **Frecuencia 2**: Entrenar cada grupo muscular 2 veces por semana genera picos de síntesis proteica repetidos y mayor progreso que machacarlo una sola vez.
4. **Volumen semanal**:
   - Apunta a entre **10 y 20 series efectivas semanales** por grupo muscular."""

    # 9. NUTRITION SPECIFICS: Comer de noche, Ayuno, Horarios, Mitos
    if any(w in msg for w in ["de noche", "engorda", "ayuno", "ayunar", "horario", "arroz", "carbohidrato"]):
        return f"""Derribando mitos sobre horarios y comidas, {user_name}:

1. **¿Comer carbohidratos de noche engorda?**:
   - **No**. El cuerpo no almacena grasa automáticamente después de cierta hora. Lo que determina si ganas músculo, pierdes grasa o subes de peso es el **balance calórico total de las 24 horas**.
   - De hecho, cenar carbohidratos complejos ayuda a producir serotonina y melatonina, mejorando la calidad del sueño y la recuperación muscular.
2. **¿Entrenar en ayunas quema más grasa?**:
   - Aunque oxida más ácidos grasos durante la sesión, al final del día el balance calórico manda. Si entrenar en ayunas te resta fuerza o energía para levantar pesado, es mejor comer carbohidratos unas 1-2 horas antes.
3. **Ayuno intermitente**:
   - Es una estrategia cómoda para controlar el apetito reduciendo la ventana de comidas, pero no tiene ventajas anabólicas superiores frente a una distribución regular de comidas con suficiente proteína."""

    # 10. INJURIES, PAIN, TIREDNESS: Dolor, Hombro, Rodilla, Molestia
    if any(w in msg for w in ["dolor", "duele", "hombro", "rodilla", "lumbar", "lesion", "lesión", "molestia", "calentar"]):
        return f"""Mucho cuidado con las molestias articulares, {user_name}. Distingue entre agujetas musculares (DOMS) y dolor articular:

1. **Dolor de Hombro en Presses**:
   - Suele deberse a falta de retracción escapular o codos muy abiertos (a 90°). Mantén los codos a unos 45-60° de tu torso en banca o usa mancuernas con agarre neutro. Calienta el manguito rotador con rotaciones externas en polea.
2. **Dolor de Rodilla en Sentadillas / Prensa**:
   - Verifica que las rodillas sigan la línea de la punta de tus pies y no colapsen hacia adentro (valgo). No rebotes bruscamente en el punto más profundo y calienta cuádriceps e isquios previamente.
3. **Molestia Lumbar**:
   - Mantén la columna neutra y activa el *bracing* (aprieta el abdomen como si fueras a recibir un golpe) antes de cada repetición pesada.
4. **Calentamiento recomendado**:
   - 5 minutos de movilidad articular dinámica + 2 o 3 series de aproximación con cargas piramidales livianas antes de tus series efectivas de trabajo."""

    # 11. REST & RECOVERY: Descanso, Sueño, Deload
    if any(w in msg for w in ["descanso", "tiempo", "segundo", "sueño", "dormir", "deload", "descarga"]):
        return f"""Sobre el descanso y recuperación, {user_name}:

* **Entre series de fuerza o ejercicios pesados** (Sentadilla, Peso Muerto, Press Banca): **2 a 3 minutos**. Permite que el ATP y el sistema nervioso central se recuperen al 95%.
* **Entre series de aislamiento** (Bíceps, tríceps, laterales): **60 a 90 segundos**.
* **Sueño**: El 80% de la hormona del crecimiento y la síntesis proteica ocurre mientras duermes. Apunta a 7-8 horas de sueño de calidad.
* **Semana de Descarga (Deload)**: Si llevas 6-8 semanas consecutivas progresando y notas fatiga articular o estancamiento, entrena una semana al 50% de series."""

    # 12. STAGNATION & PROGRESSION: Sobrecarga, Estancado, No subo, Cuanto peso
    if any(w in msg for w in ["sobrecarga", "estanc", "no subo", "meseta", "progresar", "progresiva", "peso", "cuanto subir", "cuándo subir"]):
        return f"""Hola {user_name}. La **sobrecarga progresiva** es el principio fundamental del crecimiento muscular.

Hay 3 formas principales de aplicarla en **FitChallenge**:
1. **Doble Progresión (La más recomendada)**: Establece un rango (ej: 8 a 12 reps). Mantén el peso hasta que logres 12 reps en todas tus series. En la siguiente sesión, sube de 2.5 kg a 5 kg y vuelve a empezar en 8 reps.
2. **Sobrecarga por Repeticiones**: Mismo peso, pero sumar 1 repetición más en cualquiera de tus series respecto a la semana pasada.
3. **Micro-cargas**: Si no puedes saltar 5 kg, utiliza discos fraccionados de 1.25 kg (+2.5 kg total).

👉 *Tip: Al anotar o modificar cualquier ejercicio en la app, verás automáticamente tu objetivo sugerido para hoy.*"""

    # 13. MUSIC & PLAYLIST: Música, Canciones, Playlist, Escuchar
    if any(w in msg for w in ["musica", "música", "cancion", "canción", "canciones", "playlist", "escuchar", "tema"]):
        return f"""Aquí tienes la evidencia científica y recomendaciones sobre **música para entrenar**, {user_name}:

1. **El Tempo Ideal (BPM - Golpes por Minuto)**:
   - **Para Fuerza e Hipertrofia pesada (Sentadillas, Presses, Remos)**: Entre **125 y 145 BPM**. Ayuda a sincronizar el reclutamiento de unidades motoras y activa el sistema nervioso simpático (adrenalina).
   - **Para Cardio intenso o circuitos (HIIT)**: Entre **140 y 160+ BPM**.
2. **Impacto en el RPE (Percepción del esfuerzo)**:
   - Escuchar música que te guste reduce el esfuerzo percibido (RPE) hasta en un **10%** y retrasa la fatiga mental.
3. **Géneros más efectivos según tu objetivo**:
   - 🎸 **Metal / Hard Rock / Industrial** (Slipknot, Rammstein, Doom OST de Mick Gordon): Ideal para series de máxima sobrecarga o récords personales por la agresividad controlada y los graves potentes.
   - ⚡ **Phonk / Hardstyle / Electronic / D&B**: Bombo continuo y ritmo constante, excelente para mantener el *flow* y entrenar con descansos cronometrados.
   - 🎤 **Hip-Hop / Rap con bajos marcados / Trap** (Eminem, 50 Cent, rap noventero o actual): Perfecto para concentración, cadencia constante y aislamiento muscular.
   - 🎬 **Bandas Sonoras Épicas / Synthwave** (Hans Zimmer, Two Steps from Hell): Si las letras te distraen y buscas concentración técnica absoluta.
4. **Consejo táctico**:
   - No gastes tu canción favorita en el calentamiento: resérvala para tu serie más pesada o cuando vayas a buscar la sobrecarga progresiva."""

    # 14. MOTIVATION & MINDSET: Ganas, Pereza, Cansado, Desmotivado
    if any(w in msg for w in ["ganas", "pereza", "cansado", "desmotivado", "motivacion", "motivación", "flojera"]):
        return f"""¡Te entiendo perfectamente, {user_name}! La motivación es una emoción pasajera, la disciplina es un hábito que construye resultados:

1. **La regla de los 5 minutos**:
   - Ponte la ropa de entrenamiento, ve al gimnasio y haz solo el calentamiento y la primera serie. El 90% de las veces la inercia mental se rompe y terminas completando una sesión brutal.
2. **Los días difíciles valen el doble**:
   - Los días en que entrenas sin ganas son exactamente los que forjan tu carácter y te diferencian de quienes abandonan.
3. **Ajuste de sesión**:
   - Si tu cuerpo acumula fatiga real, baja un 10% el peso y enfócate en la técnica y las sensaciones. Moverte siempre es mejor que quedarte quieto."""

    # General fallback response
    return f"""¡Hola {user_name}! Soy tu **FitCoach IA** en FitChallenge.

Estoy completamente disponible de forma libre y gratuita para cualquier consulta deportiva:
* 📋 **Diseño y carga de rutinas**: Pídeme una rutina de piernas, torso, espalda o brazos y la sumaremos con un clic a tu día con tus pesos reales.
* 🏋️ **Biomecánica y técnica**: Pregúntame cómo hacer sentadilla hack, sentadilla búlgara, press inclinado, dominadas o peso muerto.
* 🎯 **Sobrecarga progresiva**: Analizo tus cargas previas y te sugiero el peso exacto para hoy.
* 🥗 **Nutrición y suplementación**: Dudas sobre proteínas, creatina, déficit calórico o volumen.
* ⏱️ **Recuperación**: Tiempos de descanso, dolores articulares y cómo evitar lesiones.

¿Qué consulta o entrenamiento tienes en mente hoy?"""

