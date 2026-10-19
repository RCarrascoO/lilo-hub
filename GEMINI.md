# 🤖 GEMINI.MD — Contexto del Proyecto para Agentes e IAs

## 📌 Visión General
**Lilo Hub** es el centro neurálgico de automatización personal y orquestación para Renato (`saneadmin`).
Conecta un servidor doméstico 24/7 (`sanehost`) con Telegram, la bóveda personal de **Obsidian** y la PC principal de escritorio (CachyOS / Ryzen).

El objetivo del proyecto es eliminar la fricción en la captura de notas, el monitoreo del servidor y el encendido remoto de equipos, operando bajo una filosofía **YAGNI (cero sobreingeniería, mínimo consumo de recursos)**.

---

## 🛠️ Stack Tecnológico
* **Lenguaje:** Python 3.12+ (asíncrono con `asyncio`).
* **Framework Bot:** `python-telegram-bot` >= 21.0 (usando `ApplicationBuilder`).
* **Modelos de IA:** Google GenAI SDK (`google-genai`):
  * `gemini-3.5-flash-lite`: Para procesamiento de texto simple, categorización, resúmenes rápidos y clasificación (costo y latencia casi cero).
  * `gemini-2.5-flash`: Para audio multimodal (transcripción de notas de voz en `.ogg`, parsing de documentos y fotos).
  * `gemini-2.5-pro`: Reservado para tareas complejas de razonamiento o síntesis masiva.
* **Base de Datos:** SQLite asíncrono con `SQLAlchemy 2.0` + `aiosqlite` + `greenlet`. Almacenada en `data/lilo.db`. Cero sobrecarga de RAM en reposo.
* **Orquestación y Despliegue:** Docker Compose con `network_mode: host` (indispensable para paquetes UDP Wake-on-LAN).
* **Sincronización:** Syncthing (`lscr.io/linuxserver/syncthing`) para mantener sincronizada la bóveda `/vault` entre servidor, PC y móvil.

---

## 📂 Estructura del Código

```text
lilo-hub/
├── .env.example              # Plantilla de variables de entorno requeridas
├── Dockerfile                # Imagen optimizada en python:3.12-slim
├── docker-compose.yml        # Servicios lilo_hub y syncthing
├── requirements.txt          # Dependencias fijadas
├── GEMINI.md                 # Este documento de contexto para asistentes IA
├── README.md                 # Documentación para humanos
└── src/
    ├── config.py             # Configuración Pydantic validada
    ├── main.py               # Entrypoint y registro de handlers
    ├── database/
    │   ├── db.py             # Engine asíncrono y sesión de SQLite
    │   └── models.py         # Tablas ActivityLog y CapturedNote
    ├── services/
    │   ├── gemini_service.py # Interacción con Google GenAI y Model Tiering
    │   ├── system_service.py # Monitoreo de CPU, RAM, Discos y Docker
    │   ├── vault_service.py  # Creación de notas Markdown con YAML frontmatter
    │   └── wol_service.py    # Envío de paquetes Wake-on-LAN y test de ping
    └── handlers/
        ├── common.py         # Filtro de autorización (whitelist) y /start
        ├── inbox_handlers.py # Captura de texto y audio hacia Obsidian
        ├── system_handlers.py# Comando /server
        └── wol_handlers.py   # Comando /encender_pc
```

---

## 🔒 Reglas de Seguridad y Autenticación
1. **Whitelist estricta:** Toda interacción debe pasar por `is_authorized(update)` en `src/handlers/common.py`. Solo los `ALLOWED_CHAT_IDS` configurados en `.env` tienen permitido interactuar.
2. **Cero credenciales en código:** Ni tokens de Telegram, ni API keys de Google deben comitearse al repositorio. Usar siempre `src.config.settings`.

---

## 💡 Guía para Agregar Nuevas Funciones
* **Nuevos Comandos:** Crear el handler en `src/handlers/` y registrarlo en `src/main.py`.
* **Nuevos Servicios:** Desacoplar la lógica de Telegram encapsulándola en una clase dentro de `src/services/`.
* **Nuevas Tablas:** Heredar de `Base` en `src/database/models.py`. Se crearán automáticamente en el arranque en `init_db()`.
* **Model Tiering:** Usar siempre el modelo de menor costo capaz de resolver la tarea con alta calidad (preferir `-flash-lite` sobre `-flash` a menos que se requiera multimodalidad o razonamiento profundo).
