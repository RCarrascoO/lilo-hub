from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select
from src.handlers.common import is_authorized
from src.database.db import AsyncSessionLocal
from src.database.models import CapturedNote

async def ultima_nota_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    async with AsyncSessionLocal() as session:
        query = select(CapturedNote).order_by(CapturedNote.created_at.desc()).limit(1)
        result = await session.execute(query)
        note = result.scalar_one_or_none()

    if not note:
        await update.message.reply_text("📭 Aún no has registrado ninguna nota en tu Obsidian Inbox.")
        return

    icon = "🎙️" if note.source_type == "voice" else "📝"
    date_str = note.created_at.strftime("%Y-%m-%d %H:%M")

    msg = (
        f"{icon} **ÚLTIMA NOTA CAPTURADA**\n\n"
        f"📌 **Título:** {note.title}\n"
        f"📅 **Fecha:** `{date_str}`\n"
        f"💡 **Resumen:** {note.summary or 'Sin resumen'}\n"
        f"📂 **Ruta:** `{note.filepath}`\n\n"
        f"_Disponible en tu app de Obsidian vía Syncthing._"
    )
    await update.message.reply_markdown(msg)
