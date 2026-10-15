// FitChallenge Application Logic
let currentDate = getTodayDateString();
let currentWeekStart = getMondayOfWeek(new Date());
let currentWorkout = null;
let popularExercises = [];
let lastFetchedPreviousSession = null;
let weeklyChartInstance = null;
let historyChartInstance = null;
let currentModalSets = [];

// Authentication & User State
let currentUser = null;
let currentAuthTab = 'login'; // 'login' or 'register'

function getAuthToken() {
    return localStorage.getItem('fitchallenge_token');
}

function setAuthSession(token, user) {
    localStorage.setItem('fitchallenge_token', token);
    localStorage.setItem('fitchallenge_user', JSON.stringify(user));
    currentUser = user;
    updateUserProfileUI();
}

function clearAuthSession() {
    localStorage.removeItem('fitchallenge_token');
    localStorage.removeItem('fitchallenge_user');
    currentUser = null;
    updateUserProfileUI();
}

function updateUserProfileUI() {
    const profileWidget = document.getElementById("user-profile-widget");
    const profileName = document.getElementById("user-profile-name");
    const loginBtn = document.getElementById("header-login-btn");
    if (currentUser) {
        if (profileWidget) profileWidget.classList.remove("hidden");
        if (profileName) profileName.textContent = currentUser.name || currentUser.username;
        if (loginBtn) loginBtn.classList.add("hidden");
    } else {
        if (profileWidget) profileWidget.classList.add("hidden");
        if (loginBtn) loginBtn.classList.remove("hidden");
    }
}

function showAuthModal(show = true) {
    const modal = document.getElementById("auth-modal");
    if (!modal) return;
    if (show) {
        modal.classList.remove("hidden");
        modal.style.display = "flex";
        setAuthTab(currentAuthTab);
    } else {
        modal.classList.add("hidden");
        modal.style.display = "none";
    }
}

function setAuthTab(tab) {
    currentAuthTab = tab;
    const loginTabBtn = document.getElementById("auth-tab-login");
    const regTabBtn = document.getElementById("auth-tab-register");
    const nameContainer = document.getElementById("auth-name-container");
    const emailContainer = document.getElementById("auth-email-container");
    const usernameLabel = document.getElementById("auth-username-label");
    const usernameInput = document.getElementById("auth-username-input");
    const usernameHint = document.getElementById("auth-username-hint");
    const submitText = document.getElementById("auth-submit-text");
    const errorBox = document.getElementById("auth-error-box");
    if (errorBox) errorBox.classList.add("hidden");

    if (tab === 'login') {
        if (loginTabBtn) loginTabBtn.className = "flex-1 py-2 rounded-lg bg-emerald-500 text-slate-950 font-bold transition shadow-sm";
        if (regTabBtn) regTabBtn.className = "flex-1 py-2 rounded-lg text-slate-400 hover:text-white transition";
        if (nameContainer) nameContainer.classList.add("hidden");
        if (emailContainer) emailContainer.classList.add("hidden");
        if (usernameHint) usernameHint.classList.add("hidden");
        if (usernameLabel) usernameLabel.textContent = "Usuario o Gmail";
        if (usernameInput) {
            usernameInput.placeholder = "Tu usuario o tu@gmail.com";
            usernameInput.removeAttribute("minlength");
        }
        if (submitText) submitText.textContent = "Entrar a mi Gimnasio";
    } else {
        if (regTabBtn) regTabBtn.className = "flex-1 py-2 rounded-lg bg-emerald-500 text-slate-950 font-bold transition shadow-sm";
        if (loginTabBtn) loginTabBtn.className = "flex-1 py-2 rounded-lg text-slate-400 hover:text-white transition";
        if (nameContainer) nameContainer.classList.remove("hidden");
        if (emailContainer) emailContainer.classList.remove("hidden");
        if (usernameHint) usernameHint.classList.remove("hidden");
        if (usernameLabel) usernameLabel.textContent = "Nombre de Usuario (mínimo 5 letras)";
        if (usernameInput) {
            usernameInput.placeholder = "Elige tu usuario (mínimo 5 letras)";
            usernameInput.setAttribute("minlength", "5");
        }
        if (submitText) submitText.textContent = "Crear Mi Cuenta Segura";
    }
    lucide.createIcons();
}

function quickUseGmail() {
    setAuthTab('register');
    const emailInput = document.getElementById("auth-email-input");
    if (emailInput) {
        emailInput.focus();
        emailInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

async function handleGoogleCredentialResponse(response) {
    const errorBox = document.getElementById("auth-error-box");
    const errorText = document.getElementById("auth-error-text");
    if (errorBox) errorBox.classList.add("hidden");

    try {
        const res = await fetch("/api/auth/google", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ credential: response.credential })
        });
        const data = await res.json();
        if (!res.ok) {
            if (errorBox && errorText) {
                errorText.textContent = data.error || "Error al autenticar con Google";
                errorBox.classList.remove("hidden");
            }
            return;
        }

        // Success!
        setAuthSession(data.token, data.user);
        showAuthModal(false);
        showToast(data.message || `¡Bienvenido, ${data.user.name || data.user.username}!`);

        // Load user data
        await fetchPopularExercises();
        await loadWorkoutForDate(currentDate);
        renderWeekStrip();
    } catch (err) {
        console.error("Google sign in error:", err);
        if (errorBox && errorText) {
            errorText.textContent = "No se pudo conectar con el servidor para iniciar sesión con Google";
            errorBox.classList.remove("hidden");
        }
    }
}

function togglePasswordVisibility() {
    const passInput = document.getElementById("auth-password-input");
    const eyeIcon = document.getElementById("auth-password-eye");
    if (!passInput) return;
    if (passInput.type === "password") {
        passInput.type = "text";
        if (eyeIcon) eyeIcon.setAttribute("data-lucide", "eye-off");
    } else {
        passInput.type = "password";
        if (eyeIcon) eyeIcon.setAttribute("data-lucide", "eye");
    }
    lucide.createIcons();
}

async function handleAuthSubmit(e) {
    e.preventDefault();
    const errorBox = document.getElementById("auth-error-box");
    const errorText = document.getElementById("auth-error-text");
    const submitBtn = document.getElementById("auth-submit-btn");
    const usernameInput = document.getElementById("auth-username-input");
    const passwordInput = document.getElementById("auth-password-input");
    const nameInput = document.getElementById("auth-name-input");
    const emailInput = document.getElementById("auth-email-input");

    const username = usernameInput ? usernameInput.value.trim() : "";
    const password = passwordInput ? passwordInput.value.trim() : "";
    const name = nameInput ? nameInput.value.trim() : "";
    const email = emailInput ? emailInput.value.trim() : "";

    if (!username || !password) {
        if (errorBox && errorText) {
            errorText.textContent = "Por favor ingresa usuario y contraseña";
            errorBox.classList.remove("hidden");
        }
        return;
    }

    if (currentAuthTab === "register" && username.length < 5) {
        if (errorBox && errorText) {
            errorText.textContent = "El nombre de usuario debe tener al menos 5 letras o caracteres";
            errorBox.classList.remove("hidden");
        }
        if (usernameInput) usernameInput.focus();
        return;
    }

    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.classList.add("opacity-60");
    }

    try {
        const endpoint = (currentAuthTab === "login") ? "/api/auth/login" : "/api/auth/register";
        const payload = (currentAuthTab === "login") 
            ? { username, password } 
            : { username, password, name, email };

        const res = await fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (!res.ok) {
            if (errorBox && errorText) {
                errorText.textContent = data.error || "Error al procesar la solicitud";
                errorBox.classList.remove("hidden");
            }
            return;
        }

        // Success!
        setAuthSession(data.token, data.user);
        showAuthModal(false);
        showToast(data.message || "¡Sesión iniciada!");

        // Load data
        await fetchPopularExercises();
        await loadWorkoutForDate(currentDate);
        renderWeekStrip();
    } catch (err) {
        console.error("Auth error:", err);
        if (errorBox && errorText) {
            errorText.textContent = "Error de conexión al servidor";
            errorBox.classList.remove("hidden");
        }
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.classList.remove("opacity-60");
        }
    }
}

async function logoutUser() {
    const token = getAuthToken();
    try {
        if (token) {
            await fetch("/api/auth/logout", {
                method: "POST",
                headers: { "Authorization": `Bearer ${token}` }
            });
        }
    } catch (e) {
        console.error("Logout error:", e);
    }
    clearAuthSession();
    showToast("Sesión cerrada");
    showAuthModal(true);
}

// Global authenticated fetch wrapper
async function authFetch(url, options = {}) {
    options.headers = options.headers || {};
    const token = getAuthToken();
    if (token) {
        if (options.headers instanceof Headers) {
            options.headers.set("Authorization", `Bearer ${token}`);
        } else {
            options.headers["Authorization"] = `Bearer ${token}`;
        }
    }
    const res = await fetch(url, options);
    if (res.status === 401) {
        clearAuthSession();
        showAuthModal(true);
        throw new Error("No autenticado");
    }
    return res;
}

// Muscle Group Filter State
const MUSCLE_GROUPS = ["Todos", "Pecho", "Espalda", "Piernas", "Hombros", "Brazos", "Core"];
let dailyMuscleFilter = "Todos";
let weeklyMuscleFilter = "Todos";
let historyMuscleFilter = "Todos";
let currentWeeklyComparisons = [];

// Rest Timer State
let restTimer = {
    totalSeconds: 90,
    remainingSeconds: 90,
    interval: null,
    isRunning: false,
    isPaused: false
};

// Helper functions for date handling
function getTodayDateString() {
    const d = new Date();
    return formatLocalDate(d);
}

function formatLocalDate(d) {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function parseLocalDate(dateStr) {
    const [y, m, d] = dateStr.split('-').map(Number);
    return new Date(y, m - 1, d);
}

function getMondayOfWeek(d) {
    const date = new Date(d);
    const day = date.getDay();
    const diff = date.getDate() - day + (day === 0 ? -6 : 1); // adjust when day is sunday
    const monday = new Date(date.setDate(diff));
    return formatLocalDate(monday);
}

const MONTH_NAMES_ES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
];

const DAY_NAMES_ES = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"];
const DAY_SHORT_ES = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];

// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", async () => {
    // Check saved auth
    const token = getAuthToken();
    const savedUser = localStorage.getItem("fitchallenge_user");
    if (savedUser) {
        try { currentUser = JSON.parse(savedUser); } catch(e){}
    }

    if (!token) {
        showAuthModal(true);
        lucide.createIcons();
        return;
    }

    // Verify token with backend
    try {
        const meRes = await fetch("/api/auth/me", {
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (meRes.ok) {
            const meData = await meRes.json();
            currentUser = meData.user;
            localStorage.setItem("fitchallenge_user", JSON.stringify(currentUser));
            updateUserProfileUI();
            await fetchPopularExercises();
            await loadWorkoutForDate(currentDate);
            renderWeekStrip();
        } else {
            clearAuthSession();
            showAuthModal(true);
        }
    } catch (e) {
        // If offline or network issue, proceed if we have cached user
        if (currentUser) {
            updateUserProfileUI();
            await fetchPopularExercises();
            await loadWorkoutForDate(currentDate);
            renderWeekStrip();
        } else {
            showAuthModal(true);
        }
    }

    lucide.createIcons();

    // Close exercise dropdown when clicking outside
    document.addEventListener("click", (e) => {
        const container = document.getElementById("exercise-dropdown-container");
        if (container && !container.contains(e.target)) {
            closeExerciseDropdown();
        }
    });
});

// Switch Top Tabs
function switchTab(tabName) {
    document.querySelectorAll(".tab-view").forEach(el => el.classList.add("hidden"));
    document.querySelectorAll(".tab-btn").forEach(el => {
        el.classList.remove("active");
        el.classList.remove("bg-emerald-500", "text-slate-950", "font-bold");
        el.classList.add("text-slate-400");
    });
    
    // Mobile tab buttons reset
    const mobBtns = ["daily", "weekly", "history"];
    mobBtns.forEach(b => {
        const btn = document.getElementById(`mob-btn-${b}`);
        if (btn) {
            btn.classList.remove("text-emerald-400");
            btn.classList.add("text-slate-400");
        }
    });

    const activeTab = document.getElementById(`view-${tabName}`);
    if (activeTab) activeTab.classList.remove("hidden");

    const activeBtn = document.getElementById(`tab-btn-${tabName}`);
    if (activeBtn) {
        activeBtn.classList.add("active");
        activeBtn.classList.remove("text-slate-400");
    }

    const activeMobBtn = document.getElementById(`mob-btn-${tabName}`);
    if (activeMobBtn) {
        activeMobBtn.classList.add("text-emerald-400");
        activeMobBtn.classList.remove("text-slate-400");
    }

    if (tabName === "weekly") {
        loadWeeklyReport(currentDate);
    } else if (tabName === "history") {
        initHistoryView();
    }

    lucide.createIcons();
}

// ==========================================
// DAILY WORKOUT LOGIC
// ==========================================

async function loadWorkoutForDate(dateStr) {
    currentDate = dateStr;
    const dateObj = parseLocalDate(dateStr);
    
    // Update labels
    const isToday = (dateStr === getTodayDateString());
    const dayHeadline = document.getElementById("current-day-headline");
    const daySubline = document.getElementById("current-day-subline");
    
    if (isToday) {
        dayHeadline.textContent = "Hoy, " + DAY_NAMES_ES[dateObj.getDay()];
    } else {
        dayHeadline.textContent = DAY_NAMES_ES[dateObj.getDay()];
    }
    daySubline.textContent = `${dateObj.getDate()} de ${MONTH_NAMES_ES[dateObj.getMonth()]}, ${dateObj.getFullYear()}`;

    const datePicker = document.getElementById("native-date-picker");
    if (datePicker) datePicker.value = dateStr;

    try {
        const res = await authFetch(`/api/workout?date=${dateStr}`);
        const data = await res.json();
        currentWorkout = data.workout;

        // Populate session title & notes
        document.getElementById("workout-title-input").value = currentWorkout.title || "";
        document.getElementById("workout-notes-input").value = currentWorkout.notes || "";

        renderExercisesList(currentWorkout.exercises || []);
        renderWeekStrip();
    } catch (err) {
        console.error("Error al cargar entrenamiento:", err);
    }
    lucide.createIcons();
}

function renderWeekStrip() {
    const container = document.getElementById("week-strip");
    if (!container) return;
    container.innerHTML = "";

    const selectedDate = parseLocalDate(currentDate);
    const mondayStr = getMondayOfWeek(selectedDate);
    const monday = parseLocalDate(mondayStr);

    for (let i = 0; i < 7; i++) {
        const d = new Date(monday);
        d.setDate(monday.getDate() + i);
        const dStr = formatLocalDate(d);
        const isSelected = (dStr === currentDate);
        const isToday = (dStr === getTodayDateString());

        const dayBtn = document.createElement("button");
        dayBtn.className = `day-strip-btn flex flex-col items-center justify-center p-2 rounded-xl text-center transition border ${
            isSelected 
                ? "bg-emerald-500/15 border-emerald-500/70 text-emerald-400 font-bold shadow-md shadow-emerald-500/10" 
                : "bg-slate-800/40 border-slate-800/70 text-slate-400 hover:bg-slate-800 hover:text-slate-200"
        }`;
        dayBtn.onclick = () => loadWorkoutForDate(dStr);

        const dayOfWeekIndex = d.getDay();
        const shortName = DAY_SHORT_ES[dayOfWeekIndex];

        dayBtn.innerHTML = `
            <span class="text-[10px] uppercase font-semibold tracking-wider ${isSelected ? 'text-emerald-400' : 'text-slate-400'}">${shortName}</span>
            <span class="text-sm sm:text-base font-extrabold mt-0.5 ${isSelected ? 'text-white' : 'text-slate-300'}">${d.getDate()}</span>
            ${isToday ? '<span class="w-1.5 h-1.5 rounded-full bg-emerald-400 mt-1"></span>' : '<span class="w-1.5 h-1.5 rounded-full bg-transparent mt-1"></span>'}
        `;
        container.appendChild(dayBtn);
    }
}

function shiftDate(deltaDays) {
    const d = parseLocalDate(currentDate);
    d.setDate(d.getDate() + deltaDays);
    loadWorkoutForDate(formatLocalDate(d));
}

function goToToday() {
    loadWorkoutForDate(getTodayDateString());
}

function onDatePicked(newDate) {
    if (newDate) loadWorkoutForDate(newDate);
}

async function saveWorkoutMeta() {
    const title = document.getElementById("workout-title-input").value;
    const notes = document.getElementById("workout-notes-input").value;

    try {
        await authFetch("/api/workout", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                date: currentDate,
                title: title,
                notes: notes
            })
        });
    } catch (e) {
        console.error("Error al guardar notas de sesión:", e);
    }
}

function renderExercisesList(exercises) {
    const container = document.getElementById("exercises-container");
    const emptyState = document.getElementById("empty-workout-state");

    renderDailyMuscleFilters();

    if (!exercises || exercises.length === 0) {
        container.innerHTML = "";
        emptyState.classList.remove("hidden");
        return;
    }

    const filtered = (dailyMuscleFilter === "Todos")
        ? exercises
        : exercises.filter(ex => ex.muscle_group && ex.muscle_group.toLowerCase().includes(dailyMuscleFilter.toLowerCase()));

    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="text-center py-8 text-slate-400 text-xs bg-slate-900/40 rounded-2xl border border-slate-800">
                No hay ejercicios de <strong>${dailyMuscleFilter}</strong> registrados hoy.
            </div>
        `;
        emptyState.classList.add("hidden");
        return;
    }

    emptyState.classList.add("hidden");
    container.innerHTML = "";

    filtered.forEach(ex => {
        const comp = ex.comparison;
        const stats = ex.stats;
        const prevStats = ex.previous_stats;
        const prevDate = ex.previous_date;

        let badgeHtml = "";
        let prevText = "";

        if (comp.status === "mejora") {
            badgeHtml = `
                <div class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                    <i data-lucide="trending-up" class="w-3.5 h-3.5"></i>
                    <span>${comp.headline}</span>
                </div>
            `;
        } else if (comp.status === "mantenimiento") {
            badgeHtml = `
                <div class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">
                    <i data-lucide="minus" class="w-3.5 h-3.5"></i>
                    <span>${comp.headline}</span>
                </div>
            `;
        } else if (comp.status === "descenso") {
            badgeHtml = `
                <div class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30">
                    <i data-lucide="trending-down" class="w-3.5 h-3.5"></i>
                    <span>${comp.headline}</span>
                </div>
            `;
        } else {
            badgeHtml = `
                <div class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-sky-500/15 text-sky-400 border border-sky-500/30">
                    <i data-lucide="sparkles" class="w-3.5 h-3.5"></i>
                    <span>${comp.headline}</span>
                </div>
            `;
        }

        if (prevDate && prevStats) {
            const pObj = parseLocalDate(prevDate);
            const dateFmt = `${pObj.getDate()} ${MONTH_NAMES_ES[pObj.getMonth()]}`;
            const weightPart = prevStats.max_weight > 0 ? ` con ${prevStats.max_weight} kg` : " (peso corporal)";
            prevText = `Última vez (${dateFmt}): ${prevStats.total_sets} series • ${prevStats.total_reps} reps totales${weightPart}`;
        } else {
            prevText = "Primera vez que registras este ejercicio.";
        }

        // Sets table rows
        let setsRowsHtml = "";
        ex.sets.forEach(s => {
            const weightDisplay = (s.weight && s.weight > 0) ? `${s.weight} kg` : "Peso corporal";
            setsRowsHtml += `
                <tr class="border-b border-slate-800/40 text-xs">
                    <td class="py-2.5 px-3 text-slate-400 font-semibold">Serie ${s.set_number}</td>
                    <td class="py-2.5 px-3 font-bold text-white">${s.reps} <span class="text-[11px] text-slate-400 font-normal">reps</span></td>
                    <td class="py-2.5 px-3 font-medium text-slate-200">${weightDisplay}</td>
                </tr>
            `;
        });

        const card = document.createElement("div");
        card.className = "bg-slate-900/80 border border-slate-800/90 rounded-2xl p-4 sm:p-5 shadow-lg backdrop-blur-sm space-y-4 transition hover:border-slate-700";
        card.innerHTML = `
            <!-- Card Header -->
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/60 pb-3">
                <div class="flex items-center gap-3">
                    <div class="w-9 h-9 rounded-xl bg-slate-800 flex items-center justify-center text-emerald-400 border border-slate-700">
                        <i data-lucide="activity" class="w-4 h-4"></i>
                    </div>
                    <div>
                        <div class="flex items-center gap-2">
                            <h4 class="text-base font-bold text-white">${escapeHtml(ex.exercise_name)}</h4>
                            <button type="button" onclick="promptChangeMuscleGroup('${escapeHtml(ex.exercise_name)}', '${escapeHtml(ex.muscle_group)}')" title="Toca para cambiar grupo muscular" class="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-emerald-400 border border-slate-700/60 transition flex items-center gap-1 cursor-pointer">
                                <span>${escapeHtml(ex.muscle_group)}</span>
                                <i data-lucide="edit-2" class="w-2.5 h-2.5 opacity-60"></i>
                            </button>
                        </div>
                        <p class="text-[11px] text-slate-400 mt-0.5">${prevText}</p>
                    </div>
                </div>
                <div class="flex items-center gap-2 self-start sm:self-auto">
                    <!-- Quick Rest Timer Launch Button -->
                    <button onclick="startPresetTimer(90)" title="Iniciar descanso de 90s" class="text-xs px-2.5 py-1 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1 font-semibold transition">
                        <i data-lucide="timer" class="w-3.5 h-3.5"></i>
                        <span>90s Descanso</span>
                    </button>
                    ${badgeHtml}
                    <button onclick="deleteExercise(${ex.id})" title="Eliminar ejercicio" class="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-slate-800 transition">
                        <i data-lucide="trash" class="w-3.5 h-3.5"></i>
                    </button>
                </div>
            </div>

            <!-- Comparison Message / Overload Insight -->
            <div class="p-3 rounded-xl text-xs flex items-center gap-2.5 ${
                comp.status === 'mejora' ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20' :
                comp.status === 'descenso' ? 'bg-rose-500/10 text-rose-300 border border-rose-500/20' :
                comp.status === 'mantenimiento' ? 'bg-amber-500/10 text-amber-300 border border-amber-500/20' :
                'bg-sky-500/10 text-sky-300 border border-sky-500/20'
            }">
                <i data-lucide="${comp.icon}" class="w-4 h-4 shrink-0"></i>
                <span>${escapeHtml(comp.summary)}</span>
            </div>

            <!-- Sets Table -->
            <div class="overflow-x-auto">
                <table class="w-full text-left">
                    <thead>
                        <tr class="text-[10px] font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-800">
                            <th class="py-1 px-3">Serie</th>
                            <th class="py-1 px-3">Reps</th>
                            <th class="py-1 px-3">Carga</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${setsRowsHtml}
                    </tbody>
                </table>
            </div>

            <!-- Card Footer: Stats Pill -->
            <div class="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-800/40 text-xs text-slate-400">
                <div class="flex items-center gap-3">
                    <span><strong class="text-white">${stats.total_sets}</strong> series</span>
                    <span>•</span>
                    <span><strong class="text-white">${stats.total_reps}</strong> reps totales</span>
                    ${stats.max_weight > 0 ? `<span>•</span><span>Máx: <strong class="text-white">${stats.max_weight} kg</strong></span>` : ''}
                </div>
                ${stats.total_volume > 0 && !stats.is_bodyweight ? `
                    <div class="text-slate-300 font-semibold">
                        Volumen: <span class="text-emerald-400">${stats.total_volume} kg</span>
                    </div>
                ` : ''}
            </div>
        `;
        container.appendChild(card);
    });
}

// ==========================================
// MODAL: ADD EXERCISE & LIVE COMPARISON
// ==========================================

async function fetchPopularExercises() {
    try {
        const res = await authFetch("/api/popular_exercises");
        const data = await res.json();
        popularExercises = data.exercises || [];

        const datalist = document.getElementById("popular-exercises-datalist");
        if (datalist) {
            datalist.innerHTML = "";
            popularExercises.forEach(ex => {
                const opt = document.createElement("option");
                opt.value = ex.name;
                datalist.appendChild(opt);
            });
        }
    } catch (e) {
        console.error("Error al obtener ejercicios populares:", e);
    }
}

function openAddExerciseModal() {
    const modal = document.getElementById("add-exercise-modal");
    const dateObj = parseLocalDate(currentDate);
    document.getElementById("modal-date-display").textContent = `Fecha: ${dateObj.getDate()} de ${MONTH_NAMES_ES[dateObj.getMonth()]}`;
    document.getElementById("modal-exercise-input").value = "";
    document.getElementById("modal-exercise-notes").value = "";
    document.getElementById("modal-previous-session-banner").classList.add("hidden");
    lastFetchedPreviousSession = null;
    closeExerciseDropdown();
    updateClearButtonVisibility();

    // Initialize 3 default sets
    currentModalSets = [
        { reps: 10, weight: 0 },
        { reps: 10, weight: 0 },
        { reps: 10, weight: 0 }
    ];
    renderModalSetRows();

    modal.classList.remove("hidden");
    lucide.createIcons();
    setTimeout(() => {
        document.getElementById("modal-exercise-input").focus();
    }, 100);
}

function closeAddExerciseModal() {
    closeExerciseDropdown();
    document.getElementById("add-exercise-modal").classList.add("hidden");
}

// Custom Exercise Dropdown Functions
function renderExerciseDropdownItems(filterText = "") {
    const menu = document.getElementById("exercise-dropdown-menu");
    if (!menu) return;
    menu.innerHTML = "";

    const query = (filterText || "").trim().toLowerCase();
    const filtered = query
        ? popularExercises.filter(ex => ex.name.toLowerCase().includes(query) || (ex.muscle && ex.muscle.toLowerCase().includes(query)))
        : popularExercises;

    if (filtered.length === 0) {
        menu.innerHTML = `
            <div class="px-4 py-3 text-xs text-slate-500 text-center">
                No hay coincidencias predefinidas.<br>
                <span class="text-emerald-400 font-medium">Puedes escribir cualquier ejercicio personalizado.</span>
            </div>
        `;
        return;
    }

    filtered.forEach(ex => {
        const item = document.createElement("div");
        item.className = "px-4 py-2.5 flex items-center justify-between hover:bg-slate-800/80 cursor-pointer transition active:bg-emerald-500/20";
        item.onmousedown = (e) => {
            e.preventDefault(); // Prevent input blur before click finishes
            selectExerciseFromDropdown(ex.name, ex.muscle);
        };
        item.innerHTML = `
            <span class="text-xs sm:text-sm font-semibold text-white">${escapeHtml(ex.name)}</span>
            <span class="text-[10px] px-2 py-0.5 rounded-md bg-slate-800 text-emerald-400 border border-emerald-500/20 font-medium">${escapeHtml(ex.muscle)}</span>
        `;
        menu.appendChild(item);
    });
}

function openExerciseDropdown() {
    const menu = document.getElementById("exercise-dropdown-menu");
    const chevron = document.getElementById("exercise-dropdown-chevron");
    const input = document.getElementById("modal-exercise-input");
    if (!menu) return;

    renderExerciseDropdownItems(input ? input.value : "");
    menu.classList.remove("hidden");
    if (chevron) chevron.classList.add("rotate-180", "text-emerald-400");
}

function closeExerciseDropdown() {
    const menu = document.getElementById("exercise-dropdown-menu");
    const chevron = document.getElementById("exercise-dropdown-chevron");
    if (menu) menu.classList.add("hidden");
    if (chevron) chevron.classList.remove("rotate-180", "text-emerald-400");
}

function toggleExerciseDropdown(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    const menu = document.getElementById("exercise-dropdown-menu");
    if (menu && !menu.classList.contains("hidden")) {
        closeExerciseDropdown();
    } else {
        openExerciseDropdown();
    }
}

function selectExerciseFromDropdown(name, muscle) {
    const input = document.getElementById("modal-exercise-input");
    if (input) input.value = name;

    const select = document.getElementById("modal-muscle-select");
    if (select && muscle) {
        for (let opt of select.options) {
            if (opt.value.toLowerCase().includes(muscle.toLowerCase()) || muscle.toLowerCase().includes(opt.value.toLowerCase())) {
                select.value = opt.value;
                break;
            }
        }
    }

    closeExerciseDropdown();
    updateClearButtonVisibility();
    onModalExerciseInput(name);
}

function updateClearButtonVisibility() {
    const input = document.getElementById("modal-exercise-input");
    const clearBtn = document.getElementById("clear-exercise-input-btn");
    if (!input || !clearBtn) return;
    if (input.value && input.value.trim().length > 0) {
        clearBtn.classList.remove("hidden");
    } else {
        clearBtn.classList.add("hidden");
    }
    lucide.createIcons();
}

function clearExerciseInput(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    const input = document.getElementById("modal-exercise-input");
    if (input) {
        input.value = "";
        input.focus();
    }
    document.getElementById("modal-previous-session-banner").classList.add("hidden");
    lastFetchedPreviousSession = null;
    updateClearButtonVisibility();
    renderExerciseDropdownItems("");
    openExerciseDropdown();
}

let inputDebounceTimer = null;
function onModalExerciseInput(val) {
    updateClearButtonVisibility();
    renderExerciseDropdownItems(val);
    const menu = document.getElementById("exercise-dropdown-menu");
    if (menu && menu.classList.contains("hidden") && val) {
        openExerciseDropdown();
    }
    clearTimeout(inputDebounceTimer);
    inputDebounceTimer = setTimeout(async () => {
        const name = val.trim();
        if (!name) {
            document.getElementById("modal-previous-session-banner").classList.add("hidden");
            return;
        }

        // Auto-match muscle group if known
        const match = popularExercises.find(ex => ex.name.toLowerCase() === name.toLowerCase());
        if (match && match.muscle) {
            const select = document.getElementById("modal-muscle-select");
            for (let opt of select.options) {
                if (opt.value.toLowerCase().includes(match.muscle.toLowerCase()) || match.muscle.toLowerCase().includes(opt.value.toLowerCase())) {
                    select.value = opt.value;
                    break;
                }
            }
        }

        // Query the last occurrence of this exercise before currentDate
        try {
            const res = await authFetch(`/api/exercise/last?name=${encodeURIComponent(name)}&before_date=${currentDate}`);
            const data = await res.json();
            const lastSession = data.last_session;

            const banner = document.getElementById("modal-previous-session-banner");
            const summary = document.getElementById("modal-prev-summary");

            if (lastSession) {
                lastFetchedPreviousSession = lastSession;
                const dObj = parseLocalDate(lastSession.date);
                const dateFmt = `${dObj.getDate()} de ${MONTH_NAMES_ES[dObj.getMonth()]}`;
                const st = lastSession.stats;
                const weightPart = st.max_weight > 0 ? ` con hasta ${st.max_weight} kg` : " (peso corporal)";
                summary.innerHTML = `<strong>${dateFmt}</strong>: ${st.total_sets} series, ${st.total_reps} reps totales${weightPart}. <br><span class="text-emerald-400 font-semibold">¡Supera estas marcas hoy para progresar!</span>`;
                banner.classList.remove("hidden");
                lucide.createIcons();
            } else {
                banner.classList.add("hidden");
                lastFetchedPreviousSession = null;
            }
        } catch (e) {
            console.error("Error al buscar última sesión:", e);
        }
    }, 300);
}

function copyPreviousSetsToModal() {
    if (!lastFetchedPreviousSession || !lastFetchedPreviousSession.sets) return;
    currentModalSets = lastFetchedPreviousSession.sets.map(s => ({
        reps: s.reps,
        weight: s.weight
    }));
    renderModalSetRows();
    showToast("Series anteriores copiadas. ¡Añade 1 rep o sube peso!");
}

function renderModalSetRows() {
    const container = document.getElementById("modal-sets-rows");
    container.innerHTML = "";

    currentModalSets.forEach((s, idx) => {
        const row = document.createElement("div");
        row.className = "grid grid-cols-12 gap-2 px-3 py-2 items-center hover:bg-slate-800/30 transition";
        row.innerHTML = `
            <div class="col-span-2 text-center text-xs font-bold text-slate-400">${idx + 1}</div>
            <div class="col-span-5">
                <input type="number" min="1" max="500" value="${s.reps}" 
                    onchange="updateModalSet(${idx}, 'reps', this.value)" 
                    class="w-full bg-slate-800 border border-slate-700 rounded-lg px-2 py-1.5 text-center text-sm font-bold text-white focus:outline-none focus:border-emerald-500">
            </div>
            <div class="col-span-4">
                <input type="number" step="0.5" min="0" max="1000" value="${s.weight}" 
                    onchange="updateModalSet(${idx}, 'weight', this.value)" 
                    class="w-full bg-slate-800 border border-slate-700 rounded-lg px-2 py-1.5 text-center text-sm font-semibold text-slate-200 focus:outline-none focus:border-emerald-500">
            </div>
            <div class="col-span-1 text-center">
                ${currentModalSets.length > 1 ? `
                    <button type="button" onclick="removeModalSetRow(${idx})" class="text-slate-500 hover:text-rose-400 p-1">
                        <i data-lucide="x" class="w-3.5 h-3.5"></i>
                    </button>
                ` : ''}
            </div>
        `;
        container.appendChild(row);
    });
    lucide.createIcons();
}

function updateModalSet(index, field, value) {
    if (currentModalSets[index]) {
        currentModalSets[index][field] = parseFloat(value) || 0;
    }
}

function addSetRowModal() {
    // Clone values from the last row for convenient progressive entry
    const last = currentModalSets[currentModalSets.length - 1] || { reps: 10, weight: 0 };
    currentModalSets.push({ reps: last.reps, weight: last.weight });
    renderModalSetRows();
}

function removeModalSetRow(index) {
    if (currentModalSets.length > 1) {
        currentModalSets.splice(index, 1);
        renderModalSetRows();
    }
}

async function submitAddExercise() {
    const name = document.getElementById("modal-exercise-input").value.trim();
    const muscle = document.getElementById("modal-muscle-select").value;
    const notes = document.getElementById("modal-exercise-notes").value.trim();

    if (!name) {
        alert("Por favor ingresa o selecciona el nombre del ejercicio.");
        return;
    }

    if (currentModalSets.length === 0) {
        alert("Debes agregar al menos una serie.");
        return;
    }

    try {
        const payload = {
            date: currentDate,
            exercise_name: name,
            muscle_group: muscle,
            notes: notes,
            sets: currentModalSets
        };

        const res = await authFetch("/api/exercise", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (data.error) {
            alert(data.error);
            return;
        }

        closeAddExerciseModal();
        currentWorkout = data.workout;
        renderExercisesList(currentWorkout.exercises || []);
        renderWeekStrip();
        fetchPopularExercises();
        showToast("¡Ejercicio guardado exitosamente!");
    } catch (e) {
        console.error("Error al guardar ejercicio:", e);
        alert("Ocurrió un error al guardar el ejercicio.");
    }
}

async function deleteExercise(exerciseId) {
    if (!confirm("¿Seguro que deseas eliminar este ejercicio de la sesión?")) return;

    try {
        const res = await authFetch(`/api/exercise/${exerciseId}`, { method: "DELETE" });
        const data = await res.json();
        currentWorkout = data.workout;
        renderExercisesList(currentWorkout ? currentWorkout.exercises : []);
        renderWeekStrip();
        fetchPopularExercises();
        showToast("Ejercicio eliminado");
    } catch (e) {
        console.error("Error al eliminar ejercicio:", e);
    }
}

async function promptChangeMuscleGroup(exerciseName, currentGroup) {
    const groups = ["Piernas", "Pecho", "Espalda", "Hombros", "Brazos", "Core", "General"];
    const promptText = `Elige el nuevo grupo muscular para "${exerciseName}":\n\n` + 
        groups.map((g, idx) => `${idx + 1}. ${g}`).join("\n") + 
        `\n\nIngresa el número (1-${groups.length}) o el nombre:`;
    
    const choice = prompt(promptText, "1");
    if (!choice) return;

    let selectedGroup = "";
    const num = parseInt(choice.trim());
    if (!isNaN(num) && num >= 1 && num <= groups.length) {
        selectedGroup = groups[num - 1];
    } else {
        const found = groups.find(g => g.toLowerCase() === choice.trim().toLowerCase());
        selectedGroup = found || choice.trim();
    }

    if (!selectedGroup) return;

    try {
        const res = await authFetch("/api/exercise/update_muscle_group", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ exercise_name: exerciseName, muscle_group: selectedGroup })
        });
        const data = await res.json();
        if (data.status === "ok") {
            showToast(`Grupo de "${exerciseName}" cambiado a ${selectedGroup}`);
            await fetchPopularExercises();
            await loadWorkoutForDate(currentDate);
        }
    } catch (e) {
        console.error("Error al actualizar grupo muscular:", e);
    }
}

async function deleteEntireExercise(exerciseName) {
    if (!confirm(`¿Estás seguro de que deseas eliminar permanentemente el ejercicio "${exerciseName}" y todos sus registros de la app?`)) return;
    try {
        const res = await authFetch("/api/exercise/delete_by_name", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ exercise_name: exerciseName })
        });
        const data = await res.json();
        showToast(data.message || "Ejercicio eliminado");
        await fetchPopularExercises();
        await loadWorkoutForDate(currentDate);
    } catch (e) {
        console.error("Error al eliminar ejercicio:", e);
    }
}

// ==========================================
// TAB 2: WEEKLY SUMMARY & ANALYSIS
// ==========================================

let activeWeeklyDate = currentDate;

function shiftWeek(weeksDelta) {
    const d = parseLocalDate(activeWeeklyDate);
    d.setDate(d.getDate() + (weeksDelta * 7));
    activeWeeklyDate = formatLocalDate(d);
    loadWeeklyReport(activeWeeklyDate);
}

function goToCurrentWeek() {
    activeWeeklyDate = getTodayDateString();
    loadWeeklyReport(activeWeeklyDate);
}

async function loadWeeklyReport(dateStr) {
    try {
        const res = await authFetch(`/api/weekly?date=${dateStr}`);
        const report = await res.json();

        // Label
        const startObj = parseLocalDate(report.week_start);
        const endObj = parseLocalDate(report.week_end);
        document.getElementById("weekly-range-label").textContent = 
            `Semana del ${startObj.getDate()} de ${MONTH_NAMES_ES[startObj.getMonth()]} al ${endObj.getDate()} de ${MONTH_NAMES_ES[endObj.getMonth()]}`;

        // Big Verdict Card
        const verdictCard = document.getElementById("weekly-verdict-card");
        verdictCard.className = `rounded-2xl p-5 sm:p-6 border transition-all ${report.verdict_badge}`;
        verdictCard.innerHTML = `
            <div class="flex items-start gap-4">
                <div class="w-12 h-12 rounded-2xl bg-slate-900/80 flex items-center justify-center shrink-0 border border-slate-700/50">
                    <i data-lucide="${report.verdict_icon}" class="w-6 h-6"></i>
                </div>
                <div class="flex-1">
                    <div class="flex flex-wrap items-center gap-3">
                        <h3 class="text-lg sm:text-xl font-extrabold text-white">${report.verdict}</h3>
                        <div class="flex items-center gap-1.5 text-xs font-bold">
                            <span class="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">${report.improvements_count} Mejoras</span>
                            <span class="px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30">${report.maintenance_count} Mantenimiento</span>
                            ${report.drops_count > 0 ? `<span class="px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-400 border border-rose-500/30">${report.drops_count} Descensos</span>` : ''}
                        </div>
                    </div>
                    <p class="text-xs sm:text-sm text-slate-300 mt-1">${report.verdict_desc}</p>
                </div>
            </div>
        `;

        // 4 KPI Cards
        document.getElementById("metric-workouts").textContent = `${report.total_workouts} días`;
        document.getElementById("metric-sets").textContent = `${report.total_sets} series`;
        document.getElementById("metric-reps").textContent = `${report.total_reps} reps`;
        
        const volText = report.total_volume.toLocaleString("es-ES") + " kg";
        document.getElementById("metric-volume").textContent = volText;

        const volDiffEl = document.getElementById("metric-vol-diff");
        if (report.prev_week_volume > 0) {
            const isPos = report.vol_diff_pct >= 0;
            volDiffEl.innerHTML = `
                <span class="${isPos ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}">
                    ${isPos ? '+' : ''}${report.vol_diff_pct}%
                </span> vs sem. anterior (${report.prev_week_volume.toLocaleString("es-ES")} kg)
            `;
        } else {
            volDiffEl.textContent = "Primera semana con registros";
        }

        // Render Bar Chart
        renderWeeklyChart(report.days_distribution);

        // Store and Render Exercise Breakdown Table with Muscle Filters
        currentWeeklyComparisons = report.exercise_comparisons || [];
        renderWeeklyMuscleFilters();
        renderWeeklyExercisesTable(currentWeeklyComparisons);

        lucide.createIcons();
    } catch (e) {
        console.error("Error al cargar reporte semanal:", e);
    }
}

function renderWeeklyChart(days) {
    const ctx = document.getElementById("weeklyBarChart");
    if (!ctx) return;

    const labels = days.map(d => d.day_name);
    const volumes = days.map(d => d.volume);
    const reps = days.map(d => d.reps);

    if (weeklyChartInstance) {
        weeklyChartInstance.destroy();
    }

    weeklyChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Carga / Volumen (kg)',
                    data: volumes,
                    backgroundColor: 'rgba(16, 185, 129, 0.75)',
                    borderRadius: 8,
                    yAxisID: 'y'
                },
                {
                    label: 'Repeticiones',
                    data: reps,
                    backgroundColor: 'rgba(56, 189, 248, 0.45)',
                    borderRadius: 8,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    labels: { color: '#94a3b8', font: { family: 'Inter', size: 11 } }
                },
                tooltip: {
                    backgroundColor: '#0f172a',
                    borderColor: '#334155',
                    borderWidth: 1,
                    titleFont: { family: 'Inter', weight: 'bold' },
                    bodyFont: { family: 'Inter' }
                }
            },
            scales: {
                x: {
                    grid: { color: '#1e293b' },
                    ticks: { color: '#94a3b8', font: { family: 'Inter' } }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    grid: { color: '#1e293b' },
                    ticks: { color: '#10b981', font: { family: 'Inter' } }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    grid: { drawOnChartArea: false },
                    ticks: { color: '#38bdf8', font: { family: 'Inter' } }
                }
            }
        }
    });
}

function renderWeeklyExercisesTable(comparisons) {
    const container = document.getElementById("weekly-exercises-table-container");
    container.innerHTML = "";

    renderWeeklyMuscleFilters();

    const data = comparisons || currentWeeklyComparisons || [];
    const filtered = (weeklyMuscleFilter === "Todos")
        ? data
        : data.filter(c => c.muscle_group && c.muscle_group.toLowerCase().includes(weeklyMuscleFilter.toLowerCase()));

    if (!filtered || filtered.length === 0) {
        container.innerHTML = `
            <div class="text-center py-8 text-slate-500 text-xs bg-slate-950/40 rounded-xl border border-slate-800">
                No hay ejercicios de <strong>${weeklyMuscleFilter}</strong> completados en esta semana.
            </div>
        `;
        return;
    }

    filtered.forEach(c => {
        const comp = c.comparison;
        const stats = c.stats;
        const prev = c.previous_stats;
        const dateObj = parseLocalDate(c.workout_date);
        const dayLabel = `${DAY_NAMES_ES[dateObj.getDay()]} ${dateObj.getDate()}`;

        let statusBadge = "";
        if (comp.status === "mejora") {
            statusBadge = `<span class="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 flex items-center gap-1"><i data-lucide="trending-up" class="w-3 h-3"></i> Mejora</span>`;
        } else if (comp.status === "mantenimiento") {
            statusBadge = `<span class="px-2.5 py-1 rounded-full text-xs font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30 flex items-center gap-1"><i data-lucide="minus" class="w-3 h-3"></i> Mantenimiento</span>`;
        } else if (comp.status === "descenso") {
            statusBadge = `<span class="px-2.5 py-1 rounded-full text-xs font-bold bg-rose-500/15 text-rose-400 border border-rose-500/30 flex items-center gap-1"><i data-lucide="trending-down" class="w-3 h-3"></i> Descenso</span>`;
        } else {
            statusBadge = `<span class="px-2.5 py-1 rounded-full text-xs font-bold bg-sky-500/15 text-sky-400 border border-sky-500/30 flex items-center gap-1"><i data-lucide="sparkles" class="w-3 h-3"></i> Nuevo</span>`;
        }

        const prevSummary = prev 
            ? `${prev.total_sets} series • ${prev.total_reps} reps${prev.max_weight > 0 ? ` @ ${prev.max_weight}kg` : ''} (Vol: ${prev.total_volume}kg)` 
            : "Sin registro anterior";

        const currentSummary = `${stats.total_sets} series • ${stats.total_reps} reps${stats.max_weight > 0 ? ` @ ${stats.max_weight}kg` : ''} (Vol: ${stats.total_volume}kg)`;

        const card = document.createElement("div");
        card.className = "bg-slate-950/50 border border-slate-800/80 rounded-xl p-3.5 flex flex-col md:flex-row md:items-center justify-between gap-3";
        card.innerHTML = `
            <div class="flex items-center gap-3">
                <div class="w-2 self-stretch rounded-full ${
                    comp.status === 'mejora' ? 'bg-emerald-500' :
                    comp.status === 'mantenimiento' ? 'bg-amber-500' :
                    comp.status === 'descenso' ? 'bg-rose-500' : 'bg-sky-500'
                }"></div>
                <div>
                    <div class="flex items-center gap-2">
                        <span class="text-xs font-semibold text-slate-400">${dayLabel}</span>
                        <span class="text-xs text-slate-600">•</span>
                        <span class="text-sm font-bold text-white">${escapeHtml(c.exercise_name)}</span>
                        <span class="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400">${escapeHtml(c.muscle_group)}</span>
                    </div>
                    <div class="text-xs text-slate-300 mt-1">
                        <strong>Esta semana:</strong> ${currentSummary}
                    </div>
                    <div class="text-xs text-slate-500 mt-0.5">
                        <strong>Sesión anterior:</strong> ${prevSummary}
                    </div>
                </div>
            </div>
            <div class="flex items-center justify-between md:justify-end gap-3 border-t md:border-t-0 pt-2 md:pt-0 border-slate-800/60">
                <div class="text-right">
                    <span class="text-xs block text-slate-400 font-medium">${escapeHtml(comp.summary)}</span>
                </div>
                ${statusBadge}
            </div>
        `;
        container.appendChild(card);
    });
}

// ==========================================
// TAB 3: EXERCISE HISTORY & CURVES
// ==========================================

async function initHistoryView() {
    await fetchPopularExercises();
    renderHistoryMuscleFilters();
    populateHistoryExerciseSelect();
}

function populateHistoryExerciseSelect() {
    const select = document.getElementById("history-exercise-select");
    if (!select) return;

    const filtered = (historyMuscleFilter === "Todos")
        ? popularExercises
        : popularExercises.filter(ex => ex.muscle && ex.muscle.toLowerCase().includes(historyMuscleFilter.toLowerCase()));

    select.innerHTML = "";
    if (filtered.length === 0) {
        const opt = document.createElement("option");
        opt.value = "";
        opt.textContent = `No hay ejercicios en ${historyMuscleFilter}`;
        select.appendChild(opt);
        renderHistoryChart([]);
        renderHistoryTimeline([]);
        return;
    }

    filtered.forEach((ex, idx) => {
        const opt = document.createElement("option");
        opt.value = ex.name;
        opt.textContent = `${ex.name} (${ex.muscle})`;
        if (idx === 0) opt.selected = true;
        select.appendChild(opt);
    });

    loadExerciseHistory(filtered[0].name);
}

function onHistoryExerciseChanged(name) {
    if (name) loadExerciseHistory(name);
}

async function loadExerciseHistory(exerciseName) {
    try {
        const res = await authFetch(`/api/exercise/history?name=${encodeURIComponent(exerciseName)}`);
        const data = await res.json();
        const history = data.history || [];

        document.getElementById("history-chart-title").textContent = `Progresión de ${exerciseName}`;
        document.getElementById("history-total-sessions").textContent = `${history.length} sesiones registradas`;

        renderHistoryChart(history);
        renderHistoryTimeline(history);
        lucide.createIcons();
    } catch (e) {
        console.error("Error al cargar historial:", e);
    }
}

function renderHistoryChart(history) {
    const ctx = document.getElementById("exerciseHistoryChart");
    if (!ctx) return;

    const labels = history.map(h => {
        const d = parseLocalDate(h.date);
        return `${d.getDate()}/${d.getMonth()+1}`;
    });
    const maxWeights = history.map(h => h.stats.max_weight);
    const volumes = history.map(h => h.stats.total_volume);

    if (historyChartInstance) {
        historyChartInstance.destroy();
    }

    historyChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Peso Máximo (kg)',
                    data: maxWeights,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.3,
                    pointBackgroundColor: '#10b981',
                    pointRadius: 5
                },
                {
                    label: 'Volumen Total (kg)',
                    data: volumes,
                    borderColor: '#6366f1',
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    tension: 0.3,
                    pointRadius: 3,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#94a3b8', font: { family: 'Inter', size: 11 } } },
                tooltip: {
                    backgroundColor: '#0f172a',
                    borderColor: '#334155',
                    borderWidth: 1
                }
            },
            scales: {
                x: { grid: { color: '#1e293b' }, ticks: { color: '#94a3b8' } },
                y: { grid: { color: '#1e293b' }, ticks: { color: '#10b981' }, title: { display: true, text: 'Kg Máx', color: '#10b981' } },
                y1: { position: 'right', grid: { drawOnChartArea: false }, ticks: { color: '#818cf8' }, title: { display: true, text: 'Volumen', color: '#818cf8' } }
            }
        }
    });
}

function renderHistoryTimeline(history) {
    const container = document.getElementById("history-timeline-container");
    container.innerHTML = "";

    if (!history || history.length === 0) {
        container.innerHTML = `<div class="text-center py-6 text-slate-500 text-xs">Sin registros previos de este ejercicio.</div>`;
        return;
    }

    // Render newest first
    const reversed = [...history].reverse();

    reversed.forEach(item => {
        const dObj = parseLocalDate(item.date);
        const dateFmt = `${DAY_NAMES_ES[dObj.getDay()]}, ${dObj.getDate()} de ${MONTH_NAMES_ES[dObj.getMonth()]}, ${dObj.getFullYear()}`;
        const comp = item.comparison;
        const stats = item.stats;

        const row = document.createElement("div");
        row.className = "bg-slate-950/60 border border-slate-800 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3";
        row.innerHTML = `
            <div>
                <div class="flex items-center gap-2">
                    <span class="text-xs font-bold text-white">${dateFmt}</span>
                    <span class="text-[11px] px-2 py-0.5 rounded-full ${comp.badge_class}">${comp.headline}</span>
                </div>
                <div class="text-xs text-slate-300 mt-1.5 flex flex-wrap gap-2">
                    <span>${stats.total_sets} series</span>
                    <span>•</span>
                    <span>${stats.total_reps} reps totales</span>
                    ${stats.max_weight > 0 ? `<span>•</span><span>Máx: ${stats.max_weight} kg</span>` : ''}
                    <span>•</span>
                    <span class="text-emerald-400">Volumen: ${stats.total_volume} kg</span>
                </div>
            </div>
            <div class="text-xs text-slate-400">
                ${escapeHtml(comp.summary)}
            </div>
        `;
        container.appendChild(row);
    });
}

// ==========================================
// SAMPLE DATA & RESET UTILITIES
// ==========================================

async function loadSampleData() {
    if (!confirm("¿Deseas cargar datos de prueba para esta semana y la anterior? Verás comparativas reales al instante.")) return;
    try {
        const res = await authFetch("/api/seed", { method: "POST" });
        const data = await res.json();
        showToast(data.message || "Datos de ejemplo cargados");
        await loadWorkoutForDate(currentDate);
        await fetchPopularExercises();
    } catch (e) {
        console.error("Error al cargar datos de muestra:", e);
    }
}

async function confirmResetData() {
    if (!confirm("⚠️ ¿Estás seguro de que deseas borrar tus entrenamientos registrados en tu cuenta?")) return;
    try {
        const res = await authFetch("/api/reset", { method: "POST" });
        const data = await res.json();
        showToast("Tus datos han sido reiniciados");
        await loadWorkoutForDate(currentDate);
    } catch (e) {
        console.error("Error al reiniciar datos:", e);
    }
}

// Toast notification helper
function showToast(message) {
    const toast = document.getElementById("toast");
    const msg = document.getElementById("toast-message");
    msg.textContent = message;
    toast.classList.remove("opacity-0", "translate-y-20", "pointer-events-none");
    toast.classList.add("opacity-100", "translate-y-0");

    setTimeout(() => {
        toast.classList.remove("opacity-100", "translate-y-0");
        toast.classList.add("opacity-0", "translate-y-20", "pointer-events-none");
    }, 3000);
}

function escapeHtml(text) {
    if (!text) return "";
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// ==========================================
// MUSCLE GROUP FILTERS
// ==========================================

function renderDailyMuscleFilters() {
    const container = document.getElementById("daily-muscle-filters");
    if (!container) return;
    container.innerHTML = "";

    MUSCLE_GROUPS.forEach(muscle => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = `muscle-filter-pill ${dailyMuscleFilter === muscle ? 'active' : ''}`;
        btn.textContent = muscle;
        btn.onclick = () => setDailyMuscleFilter(muscle);
        container.appendChild(btn);
    });
}

function setDailyMuscleFilter(muscle) {
    dailyMuscleFilter = muscle;
    renderDailyMuscleFilters();
    renderExercisesList(currentWorkout ? currentWorkout.exercises : []);
}

function renderWeeklyMuscleFilters() {
    const container = document.getElementById("weekly-muscle-filters");
    if (!container) return;
    container.innerHTML = "";

    MUSCLE_GROUPS.forEach(muscle => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = `muscle-filter-pill ${weeklyMuscleFilter === muscle ? 'active' : ''}`;
        btn.textContent = muscle;
        btn.onclick = () => setWeeklyMuscleFilter(muscle);
        container.appendChild(btn);
    });
}

function setWeeklyMuscleFilter(muscle) {
    weeklyMuscleFilter = muscle;
    renderWeeklyMuscleFilters();
    renderWeeklyExercisesTable(currentWeeklyComparisons);
}

function renderHistoryMuscleFilters() {
    const container = document.getElementById("history-muscle-filters");
    if (!container) return;
    container.innerHTML = "";

    MUSCLE_GROUPS.forEach(muscle => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = `muscle-filter-pill ${historyMuscleFilter === muscle ? 'active' : ''}`;
        btn.textContent = muscle;
        btn.onclick = () => setHistoryMuscleFilter(muscle);
        container.appendChild(btn);
    });
}

function setHistoryMuscleFilter(muscle) {
    historyMuscleFilter = muscle;
    renderHistoryMuscleFilters();
    populateHistoryExerciseSelect();
}

// ==========================================
// REST TIMER (AUDIO SYNTH & ENGINE)
// ==========================================

let audioCtx = null;
function getAudioContext() {
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioCtx.state === 'suspended') {
        audioCtx.resume();
    }
    return audioCtx;
}

function playTimerBeep(freq = 800, duration = 0.12) {
    try {
        const ctx = getAudioContext();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(freq, ctx.currentTime);
        gain.gain.setValueAtTime(0.35, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + duration);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();
        osc.stop(ctx.currentTime + duration);
    } catch (e) {
        console.warn('Audio feedback failed:', e);
    }
}

function playTimerFinishedChime() {
    try {
        const ctx = getAudioContext();
        const now = ctx.currentTime;
        [880, 1174, 1480].forEach((freq, idx) => {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = 'triangle';
            osc.frequency.setValueAtTime(freq, now + idx * 0.14);
            gain.gain.setValueAtTime(0.4, now + idx * 0.14);
            gain.gain.exponentialRampToValueAtTime(0.01, now + idx * 0.14 + 0.45);
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start(now + idx * 0.14);
            osc.stop(now + idx * 0.14 + 0.45);
        });
    } catch (e) {
        console.warn('Audio chime failed:', e);
    }
}

function triggerVibration() {
    if ('vibrate' in navigator) {
        try {
            navigator.vibrate([200, 100, 200, 100, 350]);
        } catch (e) {}
    }
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

function updateTimerDisplay() {
    const formatted = formatTime(restTimer.remainingSeconds);

    // Floating widget
    const floatingCountdown = document.getElementById("floating-timer-countdown");
    if (floatingCountdown) floatingCountdown.textContent = formatted;

    // Header button text
    const headerText = document.getElementById("header-timer-text");
    if (headerText) {
        headerText.textContent = restTimer.isRunning ? formatted : "Descanso";
    }

    // Modal display
    const modalDigits = document.getElementById("modal-timer-digits");
    if (modalDigits) modalDigits.textContent = formatted;

    const modalStatus = document.getElementById("modal-timer-status");
    if (modalStatus) {
        if (!restTimer.isRunning && restTimer.remainingSeconds === restTimer.totalSeconds) {
            modalStatus.textContent = "Listo para iniciar";
        } else if (restTimer.isPaused) {
            modalStatus.textContent = "En pausa";
        } else if (restTimer.isRunning) {
            modalStatus.textContent = "Descansando...";
        } else {
            modalStatus.textContent = "¡Tiempo completado!";
        }
    }

    // Modal progress bar
    const progressBar = document.getElementById("modal-timer-progress-bar");
    if (progressBar) {
        const pct = restTimer.totalSeconds > 0
            ? (restTimer.remainingSeconds / restTimer.totalSeconds) * 100
            : 0;
        progressBar.style.width = `${pct}%`;
        if (pct <= 20) {
            progressBar.className = "bg-gradient-to-r from-rose-500 to-amber-400 h-full transition-all duration-300";
        } else {
            progressBar.className = "bg-gradient-to-r from-emerald-500 to-teal-400 h-full transition-all duration-300";
        }
    }

    // Modal start/pause button
    const modalPlayText = document.getElementById("modal-start-pause-text");
    if (modalPlayText) {
        modalPlayText.textContent = (restTimer.isRunning && !restTimer.isPaused) ? "Pausar" : "Iniciar";
    }

    // Floating pause button
    const floatingPauseBtn = document.getElementById("floating-pause-btn");
    if (floatingPauseBtn) {
        floatingPauseBtn.innerHTML = (restTimer.isRunning && !restTimer.isPaused)
            ? '<i data-lucide="pause" class="w-3.5 h-3.5"></i>'
            : '<i data-lucide="play" class="w-3.5 h-3.5"></i>';
        lucide.createIcons();
    }
}

function startPresetTimer(seconds) {
    stopRestTimer(false);
    restTimer.totalSeconds = seconds;
    restTimer.remainingSeconds = seconds;
    restTimer.isRunning = true;
    restTimer.isPaused = false;

    // Show floating widget
    const floating = document.getElementById("floating-rest-timer");
    if (floating) floating.classList.remove("hidden");

    updateTimerDisplay();

    restTimer.interval = setInterval(() => {
        if (restTimer.isPaused) return;

        restTimer.remainingSeconds--;
        updateTimerDisplay();

        // 3-2-1 Warning beeps
        if (restTimer.remainingSeconds >= 1 && restTimer.remainingSeconds <= 3) {
            playTimerBeep(750, 0.1);
        }

        // Finished!
        if (restTimer.remainingSeconds <= 0) {
            clearInterval(restTimer.interval);
            restTimer.interval = null;
            restTimer.isRunning = false;
            restTimer.isPaused = false;

            updateTimerDisplay();
            playTimerFinishedChime();
            triggerVibration();
            showToast("🔔 ¡Tiempo de descanso terminado! Siguiente serie 💪");
        }
    }, 1000);

    lucide.createIcons();
}

function toggleTimerPause() {
    if (!restTimer.isRunning && restTimer.remainingSeconds > 0) {
        startPresetTimer(restTimer.remainingSeconds);
        return;
    }
    restTimer.isPaused = !restTimer.isPaused;
    updateTimerDisplay();
}

function addSecondsToTimer(delta) {
    restTimer.remainingSeconds = Math.max(5, restTimer.remainingSeconds + delta);
    if (restTimer.remainingSeconds > restTimer.totalSeconds) {
        restTimer.totalSeconds = restTimer.remainingSeconds;
    }
    updateTimerDisplay();
}

function stopRestTimer(hideFloating = true) {
    if (restTimer.interval) {
        clearInterval(restTimer.interval);
        restTimer.interval = null;
    }
    restTimer.isRunning = false;
    restTimer.isPaused = false;
    restTimer.remainingSeconds = restTimer.totalSeconds;
    updateTimerDisplay();

    if (hideFloating) {
        const floating = document.getElementById("floating-rest-timer");
        if (floating) floating.classList.add("hidden");
    }
}

function openRestTimerModal() {
    updateTimerDisplay();
    document.getElementById("rest-timer-modal").classList.remove("hidden");
    lucide.createIcons();
}

function closeRestTimerModal() {
    document.getElementById("rest-timer-modal").classList.add("hidden");
}
