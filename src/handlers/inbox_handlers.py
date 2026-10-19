import io
from telegram import Update
from telegram.ext import ContextTypes
from src.handlers.common import is_authorized
from src.services.gemini_service import GeminiService
from src.services.vault_service import VaultService
from src.database.db import AsyncSessionLocal
from src.database.models import CapturedNote

gemini_service = GeminiService()

async def handle_text_inbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    text = update.message.text
    if not text:
        return

    wait_msg = await update.message.reply_text("🧠 Analizando pensamiento y estructurando nota...")

    try:
        structured_note = gemini_service.process_text(text)
        filepath = VaultService.save_note(structured_note, source_type="text")

        # Registrar en la base de datos
        async with AsyncSessionLocal() as session:
            note_record = CapturedNote(
                user_id=update.effective_user.id,
                title=structured_note.title,
                filepath=filepath,
                source_type="text",
                summary=structured_note.summary
            )
            session.add(note_record)
            await session.commit()

        # Responder al usuario con un resumen estilizado
        tags_str = " ".join([f"#{t}" for t in structured_note.tags])
        tasks_preview = ""
        if structured_note.tasks:
            tasks_preview = "\n\n**Tareas extraídas:**\n" + "\n".join([f"• [ ] {t}" for t in structured_note.tasks])

        reply = (
            f"📥 **Guardado en Obsidian Inbox**\n\n"
            f"📌 **Título:** {structured_note.title}\n"
            f"💡 **Resumen:** {structured_note.summary}\n"
            f"🏷️ **Tags:** {tags_str}"
            f"{tasks_preview}\n\n"
            f"_Sincronizado en tu bóveda._"
        )
        await wait_msg.edit_text(reply, parse_mode="Markdown")

    except Exception as e:
        await wait_msg.edit_text(f"❌ Error al procesar la nota: {str(e)}")

async def handle_voice_inbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    voice = update.message.voice or update.message.audio
    if not voice:
        return

    wait_msg = await update.message.reply_text("🎙️ Transcribiendo nota de voz con Gemini 2.5 Flash...")

    try:
        file_obj = await context.bot.get_file(voice.file_id)
        audio_buffer = io.BytesIO()
        await file_obj.download_to_memory(audio_buffer)
        audio_bytes = audio_buffer.getvalue()

        # Determinar mime_type (Telegram voice suele ser audio/ogg)
        mime = voice.mime_type or "audio/ogg"

        await wait_msg.edit_text("🧠 Audio transcrito. Estructurando nota de Obsidian...")
        structured_note = gemini_service.process_audio(audio_bytes, mime_type=mime)
        filepath = VaultService.save_note(structured_note, source_type="voice")

        # Registrar en la base de datos
        async with AsyncSessionLocal() as session:
            note_record = CapturedNote(
                user_id=update.effective_user.id,
                title=structured_note.title,
                filepath=filepath,
                source_type="voice",
                summary=structured_note.summary
            )
            session.add(note_record)
            await session.commit()

        tags_str = " ".join([f"#{t}" for t in structured_note.tags])
        tasks_preview = ""
        if structured_note.tasks:
            tasks_preview = "\n\n**Tareas extraídas:**\n" + "\n".join([f"• [ ] {t}" for t in structured_note.tasks])

        transcription_preview = ""
        if structured_note.transcription:
            transcription_preview = f"\n\n_\"{structured_note.transcription[:150]}...\"_"

        reply = (
            f"🎙️ **Nota de Voz Procesada y Guardada**\n\n"
            f"📌 **Título:** {structured_note.title}\n"
            f"💡 **Resumen:** {structured_note.summary}\n"
            f"🏷️ **Tags:** {tags_str}"
            f"{transcription_preview}"
            f"{tasks_preview}\n\n"
            f"_Guardado en tu Obsidian Inbox._"
        )
        await wait_msg.edit_text(reply, parse_mode="Markdown")

    except Exception as e:
        await wait_msg.edit_text(f"❌ Error al procesar audio: {str(e)}")
