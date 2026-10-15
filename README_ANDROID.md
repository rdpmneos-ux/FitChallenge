# 📱 Guía para tener FitPulse en Android (PWA o APK)

Tienes **3 alternativas principales** para usar esta aplicación en tu teléfono Android:

---

## ⚡ Opción 1: Instalación Directa como App (PWA) — *La más rápida y recomendada*
La aplicación ya cuenta con `manifest.json`, iconos y Service Worker listos. No necesitas compilar nada.

1. Asegúrate de que el servidor esté corriendo (`python app.py`).
2. Abre **Google Chrome** en tu teléfono móvil (conectado a la misma red Wi-Fi).
3. Entra a: `http://192.168.0.233:5000` *(o tu IP local / URL en la nube)*.
4. Toca el menú de Chrome (los 3 puntos verticales `⋮` arriba a la derecha).
5. Selecciona **"Instalar aplicación"** o **"Añadir a la pantalla de inicio"**.
6. ¡Listo! Se creará el icono de **FitPulse** en tu menú de apps de Android. Se abre a pantalla completa, sin barra de navegador, con la misma experiencia que un APK nativo.

---

## 📦 Opción 2: Generar el archivo `.apk` con PWABuilder
Si necesitas el archivo instalable `.apk` para compartirlo o instalarlo manualmente:

1. Aloja tu servidor Flask en un servicio gratuito en la nube (como [Render.com](https://render.com) o [PythonAnywhere](https://www.pythonanywhere.com)) para tener una URL pública segura (`https://...`).
2. Ingresa a **[PWABuilder.com](https://www.pwabuilder.com)** (herramienta oficial de Microsoft para empaquetar PWAs a Android).
3. Pega tu URL pública y haz clic en **Start**.
4. Pulsa **Package for Android** y descarga el archivo `.apk` firmado listo para instalar en cualquier móvil Android.

---

## 🛠️ Opción 3: Compilar con Android Studio
Ya dejamos generado un proyecto base de Android en la carpeta `android_app/`:

1. Abre **Android Studio**.
2. Selecciona **Open** y elige la carpeta:
   `C:\Users\ruben\.gemini\antigravity\scratch\workout_tracker\android_app`
3. En `MainActivity.kt`, verifica que la variable `APP_URL` apunte a la dirección de tu servidor.
4. Ve al menú superior: **Build > Build Bundle(s) / APK(s) > Build APK(s)**.
5. Android Studio compilará el archivo `.apk` en `android_app/app/build/outputs/apk/debug/app-debug.apk`.
