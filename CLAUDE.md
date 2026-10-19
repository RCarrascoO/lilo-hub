# CLAUDE.md — Directrices de Desarrollo para Claude y Claude Code

Guía técnica para que cualquier instancia de Claude comprenda la arquitectura, convenciones y flujo de desarrollo de **Lilo Hub**.

---

## 🛠️ Comandos de Desarrollo

```bash
# Ejecutar verificación de tipos / sintaxis con uv
uv run --with python-telegram-bot --with google-genai --with wakeonlan --with psutil --with docker --with pydantic --with pydantic-settings --with python-dotenv --with "SQLAlchemy[asyncio]" --with greenlet --with aiosqlite python -m py_compile src/main.py

# Construir y levantar localmente con Docker Compose
docker compose up -d --build

# Ver logs en tiempo real
docker compose logs -f lilo_hub

# Reiniciar solo el servicio del bot
docker compose restart lilo_hub
```

---

## 📐 Estilo de Código y Convenciones

* **Lenguaje:** Python 3.12+ asíncrono. Usar siempre `async/await` en handlers de Telegram y llamadas a base de datos.
* **Tipado:** Tipado estático con `typing` y validación estricta en `src/config.py` con `pydantic-settings`.
* **Filosofía YAGNI:** Cero sobreingeniería. Si algo se puede resolver con SQLite y funciones limpias, no agregar Redis ni servicios pesados.
* **Seguridad:** Ningún handler puede responder sin validar `is_authorized(update)` contra `settings.ALLOWED_CHAT_IDS`.
* **Model Tiering con Google GenAI:**
  * Texto simple / clasificación $\rightarrow$ `gemini-3.5-flash-lite` (máximo ahorro y velocidad).
  * Audio multimodal / fotos / boletas $\rightarrow$ `gemini-2.5-flash`.
  * Razonamiento analítico pesado $\rightarrow$ `gemini-2.5-pro`.

---

## 📂 Mapa de Arquitectura

* `src/config.py`: Fuente única de configuración (lee de `.env`).
* `src/main.py`: Entrypoint, inicialización asíncrona de base de datos y registro de handlers.
* `src/handlers/`: Capa de interfaz con Telegram (comandos, mensajes, botones e inline callbacks).
* `src/services/`: Lógica de negocio desacoplada de Telegram (`gemini_service.py`, `system_service.py`, `vault_service.py`, `wol_service.py`).
* `src/database/`: SQLite asíncrono con SQLAlchemy (`db.py` y `models.py`).
