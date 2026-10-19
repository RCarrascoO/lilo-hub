import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from src.handlers.common import is_authorized
from src.services.wol_service import WOLService
from src.database.db import AsyncSessionLocal
from src.database.models import ActivityLog

async def encender_pc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    status_msg = await update.message.reply_text("📡 Enviando paquete mágico Wake-on-LAN a tu PC...")

    # Registrar en DB
    async with AsyncSessionLocal() as session:
        log = ActivityLog(
            user_id=update.effective_user.id,
            action="WAKE_ON_LAN",
            details="Solicitud de encendido de PC"
        )
        session.add(log)
        await session.commit()

    result = WOLService.wake_pc()
    if not result["success"]:
        await status_msg.edit_text(f"❌ Error al enviar paquete Wake-on-LAN: {result.get('error')}")
        return

    # Esperar unos segundos y chequear si responde a ping
    await status_msg.edit_text("⚡ Paquete Wake-on-LAN enviado. Esperando inicio de red (10s)...")
    await asyncio.sleep(10)

    is_online = await WOLService.is_pc_online(timeout=2)
    if is_online:
        await status_msg.edit_text("✅ **¡Tu PC ya está encendida y respondiendo en la red!** 🟢", parse_mode="Markdown")
    else:
        await status_msg.edit_text(
            "⚡ **Paquete enviado con éxito.**\n"
            "La PC está arrancando o el sistema aún está iniciando la interfaz de red. Estará lista en breves instantes.",
            parse_mode="Markdown"
        )
