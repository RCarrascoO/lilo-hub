# ⚡ Lilo Hub

> **Centro de automatización personal, orquestación de servidor y sincronización inteligente con Obsidian.**

Lilo Hub es un bot modular asíncrono para Telegram conectado 24/7 a tu servidor personal. Permite capturar pensamientos y notas de voz con **Gemini 2.5 Flash**, encender tu PC mediante **Wake-on-LAN**, monitorear los recursos del servidor y mantener tus notas sincronizadas en tiempo real en todos tus dispositivos mediante **Syncthing**.

---

## 🚀 Características Principales

* 🎙️ **Captura Inteligente (Voz y Texto):** Envía audios o mensajes de texto. Gemini transcribe, genera títulos limpios, tags y listas de tareas, y guarda la nota en tu carpeta de Obsidian Inbox.
* ⚡ **Wake-on-LAN:** Comando `/encender_pc` para encender tu equipo principal de forma remota.
* 🖥️ **Monitor de Servidor:** Comando `/server` con métricas en tiempo real de CPU, RAM, almacenamiento y contenedores Docker activos.
* 🔄 **Sincronización Multiplataforma:** Integración con Syncthing para sincronizar la bóveda entre tu servidor, PC de escritorio, netbook y teléfono móvil.
* 🔒 **Seguridad y Privacidad:** Whitelist estricta basada en `chat_id` de Telegram. Nadie ajeno puede interactuar con el bot.
* 🪶 **Arquitectura Ligera:** Base de datos SQLite asíncrona con SQLAlchemy (0 MB de sobrecarga de RAM en reposo).

---

## 🛠️ Tecnologías

* **Lenguaje:** Python 3.12 (asíncrono)
* **Framework:** `python-telegram-bot` 21+
* **Inteligencia Artificial:** Google GenAI SDK (`gemini-2.5-flash`)
* **Base de Datos:** SQLite (`aiosqlite` + SQLAlchemy 2.0)
* **Despliegue:** Docker & Docker Compose

---

## 📦 Despliegue con Docker Compose

1. Clonar el repositorio:
   ```bash
   git clone git@github.com:RCarrascoO/lilo-hub.git
   cd lilo-hub
   ```
2. Configurar variables de entorno:
   ```bash
   cp .env.example .env
   nano .env
   ```
3. Iniciar los servicios:
   ```bash
   docker compose up -d --build
   ```

---

## 📱 Comandos del Bot

* `/start` o `/help` — Menú de bienvenida y ayuda.
* `/encender_pc` — Envía paquete mágico WOL y comprueba respuesta de red.
* `/server` — Reporte visual de salud del servidor y estado de Docker.
