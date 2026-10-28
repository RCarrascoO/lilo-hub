# ⚡ Lilo Hub

> **Centro de automatización personal, orquestación de servidor y sincronización inteligente con Obsidian.**

Lilo Hub es un bot modular asíncrono para Telegram conectado 24/7 a tu servidor personal. Permite capturar pensamientos y notas de voz con **Gemini Flash**, encender tu PC mediante **Wake-on-LAN**, monitorear los recursos del servidor, gestionar tu agenda matutina con síntesis de voz (TTS) y mantener tus notas sincronizadas en tiempo real en todos tus dispositivos mediante **WebDAV**.

---

## 🚀 Características Principales

* 🎙️ **Captura Inteligente (Voz y Texto):** Envía audios o mensajes de texto. Gemini transcribe, genera títulos estructurados, etiquetas y listas de tareas, guardando la nota en tu carpeta Obsidian Inbox.
* ⚡ **Wake-on-LAN:** Comando `/encender_pc` para encender tu equipo principal de forma remota y verificar su conexión en red.
* ⏰ **Alarma & Morning Briefing:** Despertador inteligente con síntesis de voz (TTS) de Gemini, resumen de agenda y correos del día con confirmación de despertar y watchdog.
* 📅 **Google Workspace:** Consulta en vivo de tu Google Calendar (`/agenda`) y correos no leídos de Gmail (`/correos`).
* 🖥️ **Monitor de Servidor:** Comando `/server` con métricas en tiempo real de CPU, RAM, almacenamiento y contenedores Docker activos.
* 📊 **Telemetría y Control de Cuota:** Comando `/tokens` para monitorear el consumo de tokens y cuotas de Google AI Studio en tiempo real.
* 🧠 **Modo Razonamiento Profundo:** Comando `/pro` potenciado por Gemini 2.5 Pro.
* 🔄 **Sincronización de Bóveda:** Servidor WebDAV integrado con soporte CORS para sincronizar Obsidian mediante plugins como Remotely Save.
* 🔒 **Seguridad y Privacidad:** Whitelist estricta basada en `chat_id` de Telegram. Ningún usuario no autorizado puede interactuar con el bot.
* 🪶 **Arquitectura Ligera & Resiliente:** Base de datos SQLite asíncrona en modo WAL con SQLAlchemy, copias de seguridad automáticas diarias y cascada de modelos ante límites de cuota (429).

---

## 🛠️ Tecnologías

* **Lenguaje:** Python 3.12+ (asíncrono con `asyncio`)
* **Framework Bot:** `python-telegram-bot` 21+
* **Inteligencia Artificial:** Google GenAI SDK (`gemini-2.5-flash`, `gemini-3.5-flash-lite`, `gemini-2.5-pro`, `gemini-2.5-flash-preview-tts`)
* **Base de Datos:** SQLite (`aiosqlite` + SQLAlchemy 2.0 en modo WAL)
* **Despliegue:** Docker & Docker Compose

---

## 📦 Despliegue con Docker Compose

1. Clonar el repositorio:
   ```bash
   git clone https://github.com/RCarrascoO/lilo-hub.git
   cd lilo-hub
   ```
2. Configurar variables de entorno:
   ```bash
   cp .env.example .env
   nano .env
   ```
3. Configurar credenciales de WebDAV en `webdav.yaml` si utilizas la sincronización con Obsidian.
4. (Opcional) Autenticar Google Workspace para Calendar y Gmail:
   ```bash
   python scripts/auth_google.py
   ```
5. Iniciar los servicios:
   ```bash
   docker compose up -d --build
   ```

---

## 📱 Comandos del Bot

* `/start` o `/help` — Menú de bienvenida y teclado interactivo.
* `/encender_pc` — Envía paquete mágico Wake-on-LAN y verifica estado.
* `/server` — Métricas de salud del servidor (CPU, RAM, discos, contenedores Docker).
* `/agenda` — Visualiza tus próximos eventos en Google Calendar.
* `/correos` — Resumen de correos recientes no leídos en Gmail.
* `/alarma` — Configura y consulta la alarma matutina / Morning Briefing.
* `/test_alarma` — Ejecuta de inmediato la rutina de despertador con síntesis de voz.
* `/tokens` — Métricas y consumo de tokens de los modelos de IA.
* `/pro <consulta>` — Consulta al modelo de razonamiento profundo (Gemini Pro).
* `/nota` — Muestra la última nota capturada en Obsidian Inbox.
* `/backup` — Genera un respaldo instantáneo en caliente de la base de datos.
