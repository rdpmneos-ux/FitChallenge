# ⚡ FitPulse - Control Semanal de Entrenamiento y Progresión

Servicio web en Python con interfaz responsive, moderna y elegante para el registro diario de tus entrenamientos (series, repeticiones y peso), con **comparativa automática inmediata contra tu última sesión** de cada ejercicio y un **balance semanal inteligente** que evalúa tus mejoras o mantenimiento.

---

## 🌟 Características Principales

1. **Registro Diario Intuitivo**:
   - Anota series y repeticiones día a día con soporte para peso o peso corporal.
   - Navegación ágil por días de la semana con barra de días rápida y selector de fecha.
   - Autocompletado de ejercicios populares por grupo muscular (Pecho, Espalda, Piernas, Hombros, Brazos, Core).
   - Botón *"Copiar series anteriores"* para no tener que tipear todo desde cero.

2. **Comparativa Día a Día (Sobrecarga Progresiva)**:
   - Al abrir o registrar un ejercicio, FitPulse localiza automáticamente la **última vez que lo realizaste** (incluso si fue hace días o semanas).
   - Insignias visuales instantáneas:
     - 🟢 **Mejora**: Has subido peso, agregado repeticiones o incrementado el volumen total de trabajo.
     - 🟡 **Mantenimiento**: Mantuviste el estímulo consolidado con el mismo volumen/repeticiones.
     - 🔴 **Descenso**: Sesión de menor rendimiento o descarga.
     - 🔷 **Línea Base**: Primera vez que registras el ejercicio.

3. **Reporte y Veredicto Semanal**:
   - **Veredicto Inteligente**: Evalúa la semana completa con un balance claro (*"¡Semana de Progreso y Sobrecarga!"*, *"Semana de Mantenimiento y Solidez"*, etc.).
   - Métricas clave: Días entrenados, Series totales, Repeticiones totales, y Volumen total (kg) con porcentaje de variación respecto a la semana anterior.
   - **Gráfico de Esfuerzo**: Visualiza el volumen y repeticiones distribuidas por cada día de la semana (Lunes a Domingo) con Chart.js.
   - **Tabla Comparativa Detallada**: Muestra cada ejercicio realizado durante la semana confrontado directamente con su marca anterior.

4. **Historial y Curvas de Evolución**:
   - Pestaña para consultar la progresión histórica de cualquier ejercicio.
   - Gráfico de evolución temporal del peso máximo alcanzado y el volumen total.

5. **Diseño Moderno & Responsive**:
   - Interfaz en Modo Oscuro inspirada en aplicaciones fitness de alto nivel (Linear / Hevy / Fitbod).
   - Totalmente adaptable a teléfonos móviles (con barra de navegación inferior) y computadoras de escritorio.

---

## 🚀 Cómo Iniciar el Servicio

### 1. Requisitos
- Python 3.10+
- Flask

### 2. Instalación de dependencias
```bash
pip install -r requirements.txt
```

### 3. Ejecutar la aplicación
```bash
python app.py
```
El servidor se iniciará en:
👉 **http://localhost:5000**

---

## 📁 Estructura del Proyecto

```
workout_tracker/
├── app.py                 # Servidor Flask y API REST
├── models.py              # Lógica de base de datos SQLite y algoritmos de comparativa
├── seed_data.py           # Generador de datos de ejemplo (Semana actual y previa)
├── test_app.py            # Suite de pruebas automatizadas
├── requirements.txt       # Dependencias Python
├── database.db            # Base de datos local SQLite (se crea automáticamente)
├── templates/
│   └── index.html         # Interfaz web responsive
└── static/
    ├── css/style.css      # Estilos personalizados y animaciones
    └── js/app.js          # Lógica interactiva del cliente (fetch API, Chart.js)
```

---

## 💡 Pruebas Rápidas con Datos de Ejemplo
En la esquina superior derecha de la interfaz encontrarás el botón **"Ejemplo"**:
- Carga 2 semanas completas de entrenamientos realistas (Press de Banca, Dominadas, Sentadilla, Fondos, Remo, etc.).
- Te permite ver de inmediato el balance semanal, las insignias de progreso (+2.5 kg, +2 reps, etc.) y las gráficas interactivas sin tener que cargar datos manualmente.
- Puedes reiniciar los datos en cualquier momento con el botón del cesto de basura.
