import os
import sys
import logging
import traceback
from datetime import time
import datetime
from zoneinfo import ZoneInfo
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# Añadir raíz al sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import settings
from src.database.db import init_db, AsyncSessionLocal
from src.database.models import ActivityLog
from src.services.backup_service import BackupService
from src.services.alarm_service import alarm_service
from src.handlers.common import start_command, help_command, is_authorized
from src.handlers.wol_handlers import encender_pc_command, wol_callback_handler
from src.handlers.system_handlers import server_command, server_callback_handler
from src.handlers.notes_handlers import ultima_nota_command
from src.handlers.token_handlers import tokens_command, tokens_callback_handler
from src.handlers.pro_handlers import pro_command
from src.handlers.inbox_handlers import handle_text_inbox, handle_voice_inbox
from src.handlers.assistant_handlers import (
    agenda_command,
    correos_command,
    alarma_command,
    test_alarma_command,
    alarm_callback_handler,
    fire_morning_alarm
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("lilo-hub")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manejador global de excepciones para registrar errores y no silenciar fallos."""
    logger.error("Excepción no controlada:", exc_info=context.error)

    # Registrar en base de datos
    try:
        user_id = 0
        if isinstance(update, Update) and update.effective_user:
            user_id = update.effective_user.id

        tb_str = "".join(traceback.format_exception(None, context.error, context.error.__traceback__))
        async with AsyncSessionLocal() as session:
            log = ActivityLog(
                user_id=user_id,
                action="UNHANDLED_ERROR",
                details=f"{str(context.error)[:200]}\n{tb_str[-500:]}"
            )
            session.add(log)
            await session.commit()
    except Exception as db_err:
        logger.error(f"Error registrando fallo en DB: {db_err}")

    # Notificar al usuario si ocurrió durante una interacción
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ Ocurrió un error inesperado al procesar tu solicitud. El equipo técnico ha registrado el incidente."
            )
        except Exception:
            pass

async def scheduled_backup_job(context: ContextTypes.DEFAULT_TYPE):
    """Tarea programada diaria para respaldo de la base de datos."""
    res = BackupService.create_backup()
    if res["success"]:
        logger.info(f"Respaldo automático completado: {res['filename']} ({res['size_kb']} KB)")
    else:
        logger.error(f"Fallo en respaldo automático: {res.get('error')}")

async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando manual para crear un respaldo instantáneo."""
    if not is_authorized(update):
        return

    wait_msg = await update.message.reply_text("💾 Creando copia de seguridad de la base de datos...")
    res = BackupService.create_backup()
    if res["success"]:
        await wait_msg.edit_text(
            f"✅ **Copia de seguridad completada**\n\n"
            f"📁 **Archivo:** `{res['filename']}`\n"
            f"📊 **Tamaño:** `{res['size_kb']} KB`\n"
            f"🗄️ **Ruta:** `{res['filepath']}`\n\n"
            f"_Retención activa: 7 días automáticos._",
            parse_mode="Markdown"
        )
    else:
        await wait_msg.edit_text(f"❌ Error al crear respaldo: {res.get('error')}")

_last_alarm_fired_date: datetime.date | None = None

async def check_alarm_job(context: ContextTypes.DEFAULT_TYPE):
    """Verifica cada minuto si es hora de disparar la alarma matutina según el horario base u override."""
    global _last_alarm_fired_date
    tz = ZoneInfo(settings.TIMEZONE)
    now = datetime.datetime.now(tz)
    today = now.date()

    if _last_alarm_fired_date == today:
        return

    alarm_time = alarm_service.get_alarm_time_for_date(today)
    if not alarm_time:
        return

    h, m = alarm_time
    if now.hour == h and now.minute == m:
        _last_alarm_fired_date = today
        logger.info(f"¡Disparando alarma matutina programada ({h:02d}:{m:02d})!")
        target_chat = settings.ALLOWED_CHAT_IDS[0] if settings.ALLOWED_CHAT_IDS else None
        if target_chat:
            await fire_morning_alarm(context, target_chat)

async def post_init(application):
    logger.info("Inicializando base de datos SQLite con modo WAL y tablas...")
    await init_db()
    logger.info("Base de datos y tablas de telemetría inicializadas correctamente.")

    # Programar respaldo diario a las 04:00 AM (hora de Santiago)
    if application.job_queue:
        application.job_queue.run_daily(
            scheduled_backup_job,
            time=time(hour=4, minute=0)
        )
        logger.info("Job de respaldo diario programado para las 04:00 AM.")

        # Monitor de alarma matutina cada 60 segundos
        application.job_queue.run_repeating(
            check_alarm_job,
            interval=60,
            first=10
        )
        logger.info("Monitor de alarma matutina y Morning Briefing activado.")

def main():
    logger.info("Iniciando Lilo Hub...")
    app = (
        ApplicationBuilder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # 0. Manejador Global de Errores
    app.add_error_handler(error_handler)

    # 1. Comandos con barra diagonal (/)
    app.add_handler(CommandHandler(["start", "inicio"], start_command))
    app.add_handler(CommandHandler(["help", "ayuda"], help_command))
    app.add_handler(CommandHandler(["encender_pc", "wol", "wake"], encender_pc_command))
    app.add_handler(CommandHandler(["server", "servidor", "status"], server_command))
    app.add_handler(CommandHandler(["agenda", "calendario", "clases"], agenda_command))
    app.add_handler(CommandHandler(["correos", "gmail", "inbox_mail"], correos_command))
    app.add_handler(CommandHandler(["alarma", "despertador"], alarma_command))
    app.add_handler(CommandHandler(["test_alarma", "probar_alarma"], test_alarma_command))
    app.add_handler(CommandHandler(["nota", "ultima_nota"], ultima_nota_command))
    app.add_handler(CommandHandler(["tokens", "consumo"], tokens_command))
    app.add_handler(CommandHandler(["pro", "gemini_pro"], pro_command))
    app.add_handler(CommandHandler(["backup", "respaldo"], backup_command))

    # 2. Handlers para Botones del Teclado Inferior
    app.add_handler(MessageHandler(filters.Regex(r"^⚡ Encender PC$"), encender_pc_command))
    app.add_handler(MessageHandler(filters.Regex(r"^🖥️ Servidor$"), server_command))
    app.add_handler(MessageHandler(filters.Regex(r"^📅 Agenda$"), agenda_command))
    app.add_handler(MessageHandler(filters.Regex(r"^✉️ Correos$"), correos_command))
    app.add_handler(MessageHandler(filters.Regex(r"^⏰ Alarma$"), alarma_command))
    app.add_handler(MessageHandler(filters.Regex(r"^📓 Última Nota$"), ultima_nota_command))
    app.add_handler(MessageHandler(filters.Regex(r"^📊 Tokens IA$"), tokens_command))
    app.add_handler(MessageHandler(filters.Regex(r"^❓ Ayuda$"), help_command))

    # 3. Callbacks para Botones Inline (Bajo los mensajes)
    app.add_handler(CallbackQueryHandler(server_callback_handler, pattern=r"^refresh_server$"))
    app.add_handler(CallbackQueryHandler(wol_callback_handler, pattern=r"^wake_pc_inline$"))
    app.add_handler(CallbackQueryHandler(tokens_callback_handler, pattern=r"^refresh_tokens$"))
    app.add_handler(CallbackQueryHandler(alarm_callback_handler, pattern=r"^(alarm_ack|alarm_snooze|test_alarm_inline|refresh_emails)$"))

    # 4. Captura inteligente de Inbox (Texto y Audio)
    app.add_handler(MessageHandler(
        filters.TEXT & (~filters.COMMAND) & (~filters.Regex(r"^(⚡ Encender PC|🖥️ Servidor|📅 Agenda|✉️ Correos|⏰ Alarma|📓 Última Nota|📊 Tokens IA|❓ Ayuda)$")),
        handle_text_inbox
    ))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice_inbox))

    logger.info("Lilo Hub está escuchando eventos...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
