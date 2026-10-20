# 🤖 GEMINI.MD — Contexto del Proyecto para Agentes e IAs

## 📌 Visión General
**Lilo Hub** es el centro neurálgico de automatización personal y orquestación para Renato (`saneadmin`).
Conecta un servidor doméstico 24/7 (`sanehost`) con Telegram, la bóveda personal de **Obsidian** y la PC principal de escritorio (CachyOS / Ryzen).

El proyecto opera bajo una filosofía **YAGNI (cero sobreingeniería, mínimo consumo de recursos)** con una base técnica altamente estabilizada (SQLite en modo WAL, respaldos automáticos, cascada anti-429 y límites de RAM).

---

## 🛠️ Stack Tecnológico
* **Lenguaje:** Python 3.12+ (asíncrono con `asyncio`).
* **Framework Bot:** `python-telegram-bot` >= 21.0 (usando `ApplicationBuilder`).
* **Base de Datos:** SQLite asíncrono en **Modo WAL** (`PRAGMA journal_mode=WAL`, `busy_timeout=5000`) con `SQLAlchemy 2.0` + `aiosqlite`.
* **Respaldos:** Copias en caliente diarias automáticas a las 04:00 AM en `/mnt/disco_1tb/backups/lilo_hub` con retención de 7 días.
* **Modelos de IA Integrados:**
  * `gemini-3.5-flash-lite`: Captura rápida de texto y clasificación.
  * Cascada de Audio: `gemini-flash-latest` $\rightarrow$ `gemini-3.5-flash` $\rightarrow$ `gemini-2.5-flash`.
  * `gemini-2.5-flash-preview-tts`: Síntesis de voz interactiva para respuestas habladas.
  * `gemini-2.5-pro`: Razonamiento avanzado (`/pro`).
* **Telemetría de Tokens:** Módulo mutable `TokenService` con registro en `token_usage` y cálculo de recarga de cuotas.
* **Orquestación y Despliegue:** Docker Compose con `network_mode: host`, límite estricto de `512M` de RAM y `healthcheck`.
* **Sincronización:** Syncthing (`:8384`) para sincronizar la bóveda `/vault` entre servidor, PC y móvil.

---

## 🔒 Reglas de Seguridad y Autenticación
1. **Whitelist estricta:** Toda interacción debe pasar por `is_authorized(update)` en `src/handlers/common.py`. Solo los `ALLOWED_CHAT_IDS` configurados en `.env` tienen permitido interactuar.
2. **Cero credenciales en código:** Ni tokens de Telegram, ni API keys de Google deben comitearse al repositorio. Usar siempre `src.config.settings`.
3. **Manejo de Errores:** Errores globales no capturados pasan por `error_handler` y se auditan en `ActivityLog`.
