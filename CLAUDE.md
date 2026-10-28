# CLAUDE.md — Directrices de Desarrollo para Claude y Claude Code

Guía técnica para que cualquier instancia de Claude comprenda la arquitectura, convenciones y flujo de desarrollo de **Lilo Hub**.

---

## 🛠️ Comandos de Desarrollo y Testing

```bash
# Correr suite de pruebas unitarias
uv run --with pytest --with python-telegram-bot --with google-genai --with wakeonlan --with psutil --with docker --with pydantic --with pydantic-settings --with python-dotenv --with "SQLAlchemy[asyncio]" --with greenlet --with aiosqlite pytest

# Verificación de sintaxis de todo el proyecto
uv run --with python-telegram-bot --with google-genai --with wakeonlan --with psutil --with docker --with pydantic --with pydantic-settings --with python-dotenv --with "SQLAlchemy[asyncio]" --with greenlet --with aiosqlite python -m py_compile src/main.py

# Construir y levantar con Docker Compose
docker compose up -d --build

# Ver logs en tiempo real
docker compose logs -f lilo_hub

# Reiniciar servicio
docker compose restart lilo_hub
```

---

## 📐 Estilo de Código y Estabilización

* **Asincronía Obligatoria:** Todo handler y llamada a base de datos usa `async/await`.
* **SQLite en Modo WAL:** Se configura `PRAGMA journal_mode=WAL` y `busy_timeout=5000` para eliminar bloqueos de concurrencia.
* **Respaldos Automáticos:** Job diario programado a las 04:00 AM mediante `BackupService.create_backup()` hacia `/backups/` con retención de 7 días.
* **Manejo Global de Errores:** Errores no capturados pasan por `error_handler` y se auditan en la tabla `ActivityLog`.
* **Límites de Recursos:** El contenedor tiene un tope de 512MB de RAM en `docker-compose.yml` para garantizar la estabilidad del servidor y otros servicios concurrentes.
* **Model Tiering y Cascada:**
  * Texto $\rightarrow$ `gemini-3.5-flash-lite`.
  * Audio $\rightarrow$ `gemini-flash-latest` con cascada ante 429 hacia `gemini-3.5-flash` y `gemini-2.5-flash`.
  * Razonamiento profundo $\rightarrow$ `gemini-2.5-pro` (`/pro`).
  * Voz TTS $\rightarrow$ `gemini-2.5-flash-preview-tts` (solo si `is_conversational=True`).

---

## 📂 Mapa de Arquitectura

* `src/config.py`: Fuente única de configuración (lee de `.env`).
* `src/main.py`: Entrypoint, jobs programados, error_handler y registro de handlers.
* `src/handlers/`:
  * `common.py`: Whitelist y teclados rápidos.
  * `inbox_handlers.py`: Captura de texto y audio (con discriminación de voz y guardado).
  * `system_handlers.py`: Comando `/server` e inline buttons.
  * `wol_handlers.py`: Comando `/encender_pc`.
  * `token_handlers.py`: Monitor `/tokens` y cuotas diarias.
  * `pro_handlers.py`: Comando `/pro` con Gemini Pro.
  * `notes_handlers.py`: Visor de `/ultima_nota`.
* `src/services/`: Lógica desacoplada (`gemini_service.py`, `token_service.py`, `backup_service.py`, `conversation_service.py`, `system_service.py`, `vault_service.py`, `wol_service.py`).
* `src/database/`: SQLite asíncrono (`db.py` y `models.py`).
* `tests/`: Pruebas automatizadas con `pytest`.
