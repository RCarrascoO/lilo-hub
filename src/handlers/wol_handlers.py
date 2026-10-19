import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from src.handlers.common import is_authorized
from src.services.wol_service import WOLService
from src.database.db import AsyncSessionLocal
from src.database.models import ActivityLog

async def trigger_wake_on_lan(user_id: int) -> tuple[bool, str]:
    # Registrar en DB
    async with AsyncSessionLocal() as session:
        log = ActivityLog(
            user_id=user_id,
            action="WAKE_ON_LAN",
            details="Solicitud de encendido de PC"
        )
        session.add(log)
        await session.commit()

    result = WOLService.wake_pc()
    if not result["success"]:
        return False, f"❌ Error al enviar paquete Wake-on-LAN: {result.get('error')}"

    return True, "⚡ Paquete Wake-on-LAN enviado."

async def encender_pc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    status_msg = await update.message.reply_text("📡 Enviando paquete mágico Wake-on-LAN a tu PC...")
    success, msg = await trigger_wake_on_lan(update.effective_user.id)
    if not success:
        await status_msg.edit_text(msg)
        return

    await status_msg.edit_text("⚡ Paquete enviado con éxito. Esperando respuesta de red (10s)...")
    await asyncio.sleep(10)

    is_online = await WOLService.is_pc_online(timeout=2)
    if is_online:
        await status_msg.edit_text("✅ **¡Tu PC ya está encendida y respondiendo en la red!** 🟢", parse_mode="Markdown")
    else:
        await status_msg.edit_text(
            "⚡ **Paquete enviado con éxito.**\n"
            "La PC está arrancando o el sistema aún está iniciando la interfaz de red.",
            parse_mode="Markdown"
        )

async def wol_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Enviando paquete Wake-on-LAN...")
    await query.message.reply_text("📡 Enviando paquete Wake-on-LAN desde botón...")
    await encender_pc_command(query, context)
