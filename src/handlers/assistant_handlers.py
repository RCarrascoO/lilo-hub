import logging
import datetime
from zoneinfo import ZoneInfo
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from src.config import settings
from src.handlers.common import is_authorized
from src.services.google_service import google_service
from src.services.alarm_service import alarm_service
from src.services.gemini_service import gemini_service
from src.services.wol_service import WOLService

logger = logging.getLogger("lilo-hub")


async def agenda_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra los eventos y clases de Google Calendar para hoy y los próximos días."""
    if not is_authorized(update):
        return

    if not google_service.is_authenticated():
        await update.message.reply_text(
            "⚠️ Google Calendar no está autenticado aún. Por favor verifica las credenciales de Google."
        )
        return

    wait_msg = await update.message.reply_text("📅 Consultando tu Google Calendar...")
    events = google_service.get_calendar_events(days=3, max_results=8)

    if not events:
        await wait_msg.edit_text("📅 **Google Calendar:**\nNo tienes eventos programados para los próximos 3 días. ¡Días libres!")
        return

    tz = ZoneInfo(settings.TIMEZONE)
    now = datetime.datetime.now(tz)
    today = now.date()
    tomorrow = today + datetime.timedelta(days=1)

    lines = ["📅 **Tu Agenda (Google Calendar):**\n"]
    for ev in events:
        raw_start = ev["start"]
        summary = ev["summary"]
        loc = f" 📍 _{ev['location']}_" if ev["location"] else ""

        if ev["is_all_day"]:
            date_str = raw_start
            header = "🌟 **Hoy:**" if date_str == today.isoformat() else f"📌 **{date_str}:**"
            lines.append(f"{header} {summary} (Todo el día){loc}")
        else:
            try:
                dt = datetime.datetime.fromisoformat(raw_start).astimezone(tz)
                time_str = dt.strftime("%H:%M")
                if dt.date() == today:
                    prefix = "🕒 **Hoy a las**"
                elif dt.date() == tomorrow:
                    prefix = "🌅 **Mañana a las**"
                else:
                    prefix = f"📆 **{dt.strftime('%d/%m')} a las**"
                lines.append(f"{prefix} `{time_str}`: **{summary}**{loc}")
            except Exception:
                lines.append(f"• `{raw_start}`: **{summary}**{loc}")

    await wait_msg.edit_text("\n".join(lines), parse_mode="Markdown")


async def correos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra y resume los correos recientes no leídos de Gmail."""
    if not is_authorized(update):
        return

    if not google_service.is_authenticated():
        await update.message.reply_text(
            "⚠️ Gmail no está autenticado aún. Por favor verifica las credenciales de Google."
        )
        return

    wait_msg = await update.message.reply_text("✉️ Revisando bandeja de entrada de Gmail...")
    emails = google_service.get_unread_emails(max_results=5)

    if not emails:
        await wait_msg.edit_text("✉️ **Gmail:**\nTu bandeja de entrada está al día. ¡Cero correos no leídos!")
        return

    lines = [f"✉️ **Correos no leídos recientes ({len(emails)}):**\n"]
    for em in emails:
        sender_clean = em["sender"].split("<")[0].replace('"', '').strip()
        lines.append(f"👤 **{sender_clean}**\n📌 `{em['subject']}`\n📝 _{em['snippet'][:120]}..._\n")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Actualizar correos", callback_data="refresh_emails")]
    ])
    await wait_msg.edit_text("\n".join(lines), parse_mode="Markdown", reply_markup=keyboard)


async def alarma_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Configura o muestra el estado de la alarma / Morning Briefing."""
    if not is_authorized(update):
        return

    tz = ZoneInfo(settings.TIMEZONE)
    today = datetime.datetime.now(tz).date()

    # Si pasaron argumentos: ej. /alarma 07:00 o /alarma off
    if context.args:
        arg = context.args[0].lower().strip()
        if arg in ["off", "desactivar", "cancelar"]:
            alarm_service.set_manual_alarm(today, None)
            tomorrow = today + datetime.timedelta(days=1)
            alarm_service.set_manual_alarm(tomorrow, None)
            await update.message.reply_text("🔕 **Alarma desactivada** para hoy y mañana.")
            return
        elif ":" in arg:
            try:
                h, m = map(int, arg.split(":"))
                if 0 <= h <= 23 and 0 <= m <= 59:
                    time_fmt = f"{h:02d}:{m:02d}"
                    # Si ya pasó la hora hoy, la configuramos para mañana
                    now = datetime.datetime.now(tz)
                    target = today if (now.hour < h or (now.hour == h and now.minute < m)) else today + datetime.timedelta(days=1)
                    alarm_service.set_manual_alarm(target, time_fmt)
                    day_name = "hoy" if target == today else "mañana"
                    await update.message.reply_text(f"⏰ **Alarma configurada para {day_name} a las `{time_fmt}`**.", parse_mode="Markdown")
                    return
            except ValueError:
                pass
        await update.message.reply_text("Formato inválido. Usa: `/alarma HH:MM` (ej. `/alarma 06:45`) o `/alarma off`.", parse_mode="Markdown")
        return

    # Si no pasaron argumentos, mostramos estado
    next_alarm = alarm_service.get_next_alarm()
    status_text = f"`{next_alarm.strftime('%A %d/%m a las %H:%M')}`" if next_alarm else "_Apagada_"

    msg = (
        "⏰ **Configuración de Alarma & Morning Briefing**\n\n"
        f"🎯 **Próxima alarma programada:** {status_text}\n\n"
        "📅 **Horario base semanal:**\n"
        "• Lunes: `07:40`\n"
        "• Martes y Jueves: `06:20`\n"
        "• Miércoles: `08:20`\n"
        "• Viernes: `10:00`\n"
        "• Sábado: `09:00`\n"
        "• Domingo: _Libre_\n\n"
        "💡 **Comandos rápidos:**\n"
        "• `/alarma 07:00` $\\rightarrow$ Cambiar hora para la próxima alarma\n"
        "• `/alarma off` $\\rightarrow$ Desactivar próxima alarma\n"
        "• `/test_alarma` $\\rightarrow$ Probar el despertar con audio ahora mismo"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔔 Probar Despertador Ahora", callback_data="test_alarm_inline")],
        [InlineKeyboardButton("💻 Encender PC", callback_data="wake_pc_inline")]
    ])
    await update.message.reply_markdown(msg, reply_markup=keyboard)


async def fire_morning_alarm(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Ejecuta la alarma matutina completa (Texto + Audio TTS + Botones + Watchdog)."""
    try:
        text_card, spoken_script, audio_bytes = await alarm_service.generate_briefing()

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⏰ ¡Ya desperté!", callback_data="alarm_ack")],
            [InlineKeyboardButton("💤 10 min más", callback_data="alarm_snooze")],
            [InlineKeyboardButton("⚡ Encender PC", callback_data="wake_pc_inline")]
        ])

        # 1. Enviar nota de voz si se generó
        if audio_bytes:
            await context.bot.send_voice(
                chat_id=chat_id,
                voice=audio_bytes,
                caption="🎙️ **Buenos días, Renato.** Aquí tienes tu informe de hoy."
            )

        # 2. Enviar ficha de texto con botones
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⏰ **¡ALARMA MATUTINA ACTIVADA!**\n\n{text_card}",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

        # 3. Programar Watchdog de seguridad (5 minutos)
        alarm_service.pending_acknowledgment = datetime.datetime.now().isoformat()
        if context.job_queue:
            context.job_queue.run_once(
                alarm_watchdog_timeout,
                when=300,  # 5 minutos
                chat_id=chat_id,
                name="alarm_watchdog"
            )

    except Exception as e:
        logger.error(f"Error disparando alarma matutina: {e}", exc_info=True)
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Error al disparar alarma: {e}")


async def test_alarma_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando para probar la rutina matutina completa de inmediato."""
    if not is_authorized(update):
        return

    wait_msg = await update.message.reply_text("🎙️ Generando informe matutino y sintetizando voz con Gemini TTS...")
    chat_id = update.effective_chat.id
    await fire_morning_alarm(context, chat_id)
    try:
        await wait_msg.delete()
    except Exception:
        pass


async def alarm_watchdog_timeout(context: ContextTypes.DEFAULT_TYPE):
    """Se ejecuta si pasaron 5 minutos sin confirmar el despertar."""
    if alarm_service.pending_acknowledgment:
        chat_id = context.job.chat_id
        logger.warning(f"Watchdog de alarma activado para chat {chat_id}: Renato aún no confirma que despertó.")

        # Re-enviar alerta ruidosa e insistente a Telegram
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⏰ ¡YA DESPERTÉ!", callback_data="alarm_ack")]
        ])
        await context.bot.send_message(
            chat_id=chat_id,
            text="🚨 **¡ATENCIÓN! HAN PASADO 5 MINUTOS Y NO HAS CONFIRMADO.**\n\n"
                 "¡Renato, levántate! Tienes clases y actividades programadas.",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )


async def alarm_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja las interacciones con los botones de la alarma."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "alarm_ack":
        alarm_service.pending_acknowledgment = None
        # Cancelar jobs de watchdog pendientes
        if context.job_queue:
            current_jobs = context.job_queue.get_jobs_by_name("alarm_watchdog")
            for job in current_jobs:
                job.schedule_removal()

        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("✅ **¡Alarma apagada!** Excelente, que tengas una jornada muy productiva hoy. 🚀")

    elif data == "alarm_snooze":
        alarm_service.pending_acknowledgment = None
        if context.job_queue:
            context.job_queue.run_once(
                lambda ctx: fire_morning_alarm(ctx, query.message.chat_id),
                when=600,  # 10 minutos
                name="alarm_snooze"
            )
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("💤 Alarma pospuesta por 10 minutos. Te volveré a llamar a las "
                                      f"{(datetime.datetime.now(ZoneInfo(settings.TIMEZONE)) + datetime.timedelta(minutes=10)).strftime('%H:%M')}.")

    elif data == "test_alarm_inline":
        await query.message.reply_text("🎙️ Disparando simulación de despertador matutino...")
        await fire_morning_alarm(context, query.message.chat_id)

    elif data == "refresh_emails":
        await correos_command(update, context)
