# 🤖 GEMINI.MD — Contexto del Proyecto para Agentes e IAs

## 📌 Visión General
**Lilo Hub** es el centro neurálgico de automatización personal y orquestación para Renato (`saneadmin`).
Conecta un servidor doméstico 24/7 (`sanehost`) con Telegram, la bóveda personal de **Obsidian** y la PC principal de escritorio (CachyOS / Ryzen).

El objetivo del proyecto es eliminar la fricción en la captura de notas, el monitoreo del servidor, el encendido remoto de equipos y el análisis profundo con IAs, operando bajo una filosofía **YAGNI (cero sobreingeniería, mínimo consumo de recursos)**.

---

## 🛠️ Stack Tecnológico
* **Lenguaje:** Python 3.12+ (asíncrono con `asyncio`).
* **Framework Bot:** `python-telegram-bot` >= 21.0 (usando `ApplicationBuilder`).
* **Modelos de IA Integrados:**
  * `gemini-3.5-flash-lite`: Captura rápida de texto y clasificación.
  * `gemini-2.5-flash`: Transcripción multimodal de notas de voz.
  * `gemini-2.5-flash-preview-tts`: Síntesis de voz para respuestas habladas cuando se requiere conversación.
  * `gemini-2.5-pro`: Razonamiento avanzado para análisis complejo y estudio (`/pro`).
* **Telemetría de Tokens:** Módulo mutable `TokenService` que audita cada llamada a la API en la tabla `token_usage` de SQLite.
* **Base de Datos:** SQLite asíncrono con `SQLAlchemy 2.0` + `aiosqlite` + `greenlet`. Almacenada en `data/lilo.db`. Cero sobrecarga de RAM en reposo.
* **Orquestación y Despliegue:** Docker Compose con `network_mode: host` (indispensable para paquetes UDP Wake-on-LAN).
* **Sincronización:** Syncthing (`lscr.io/linuxserver/syncthing`) para mantener sincronizada la bóveda `/vault` entre servidor, PC y móvil.

---

## 🔒 Reglas de Seguridad y Autenticación
1. **Whitelist estricta:** Toda interacción debe pasar por `is_authorized(update)` en `src/handlers/common.py`. Solo los `ALLOWED_CHAT_IDS` configurados en `.env` tienen permitido interactuar.
2. **Cero credenciales en código:** Ni tokens de Telegram, ni API keys de Google deben comitearse al repositorio. Usar siempre `src.config.settings`.
