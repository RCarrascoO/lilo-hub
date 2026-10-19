import io
from telegram import Update
from telegram.ext import ContextTypes
from src.handlers.common import is_authorized
from src.services.gemini_service import GeminiService, StructuredResponse
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

    user_id = update.effective_user.id
    wait_msg = await update.message.reply_text("🧠 Pensando...")

    try:
        parsed = await gemini_service.process_message(text=text, user_id=user_id)

        if parsed.save_to_vault and parsed.title:
            # Guardar nota en Obsidian
            filepath = VaultService.save_note(parsed, source_type="text")

            async with AsyncSessionLocal() as session:
                note_record = CapturedNote(
                    user_id=user_id,
                    title=parsed.title,
                    filepath=filepath,
                    source_type="text",
                    summary=parsed.summary
                )
                session.add(note_record)
                await session.commit()

            tags_str = " ".join([f"#{t}" for t in parsed.tags])
            tasks_preview = ""
            if parsed.tasks:
                tasks_preview = "\n\n**Tareas extraídas:**\n" + "\n".join([f"• [ ] {t}" for t in parsed.tasks])

            reply = (
                f"📥 **Guardado en Obsidian Inbox**\n\n"
                f"📌 **Título:** {parsed.title}\n"
                f"💡 **Resumen:** {parsed.summary}\n"
                f"🏷️ **Tags:** {tags_str}"
                f"{tasks_preview}\n\n"
                f"_Sincronizado en tu bóveda._"
            )
            await wait_msg.edit_text(reply, parse_mode="Markdown")
        else:
            # Es una consulta o conversación (ej. sobre el servidor o estado)
            answer = parsed.text_reply or parsed.spoken_reply or parsed.summary or "Entendido."
            await wait_msg.edit_text(answer, parse_mode="Markdown")

    except Exception as e:
        await wait_msg.edit_text(f"❌ Error al procesar mensaje: {str(e)}")

async def handle_voice_inbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    voice = update.message.voice or update.message.audio
    if not voice:
        return

    user_id = update.effective_user.id
    wait_msg = await update.message.reply_text("🎙️ Escuchando y procesando audio con Gemini...")

    try:
        file_obj = await context.bot.get_file(voice.file_id)
        audio_buffer = io.BytesIO()
        await file_obj.download_to_memory(audio_buffer)
        audio_bytes = audio_buffer.getvalue()

        mime = voice.mime_type or "audio/ogg"

        parsed = await gemini_service.process_message(audio_bytes=audio_bytes, mime_type=mime, user_id=user_id)

        if parsed.save_to_vault and parsed.title:
            filepath = VaultService.save_note(parsed, source_type="voice")

            async with AsyncSessionLocal() as session:
                note_record = CapturedNote(
                    user_id=user_id,
                    title=parsed.title,
                    filepath=filepath,
                    source_type="voice",
                    summary=parsed.summary
                )
                session.add(note_record)
                await session.commit()

            tags_str = " ".join([f"#{t}" for t in parsed.tags])
            tasks_preview = ""
            if parsed.tasks:
                tasks_preview = "\n\n**Tareas extraídas:**\n" + "\n".join([f"• [ ] {t}" for t in parsed.tasks])

            transcription_preview = ""
            if parsed.transcription:
                transcription_preview = f"\n\n_\"{parsed.transcription[:150]}...\"_"

            reply = (
                f"🎙️ **Nota de Voz Guardada en Obsidian**\n\n"
                f"📌 **Título:** {parsed.title}\n"
                f"💡 **Resumen:** {parsed.summary}\n"
                f"🏷️ **Tags:** {tags_str}"
                f"{transcription_preview}"
                f"{tasks_preview}\n\n"
                f"_Guardado en tu Obsidian Inbox._"
            )
            await wait_msg.edit_text(reply, parse_mode="Markdown")
        else:
            # Respuesta a consulta interactiva (no satura Obsidian con notas basura)
            answer_text = parsed.text_reply or parsed.spoken_reply or "Listo."
            await wait_msg.edit_text(answer_text, parse_mode="Markdown")

        # Si requiere respuesta hablada, sintetizar voz con Gemini TTS y enviarla
        if parsed.is_conversational and parsed.spoken_reply:
            try:
                voice_wav = await gemini_service.generate_voice_audio(parsed.spoken_reply, user_id=user_id)
                wav_buffer = io.BytesIO(voice_wav)
                wav_buffer.name = "lilo_reply.wav"
                wav_buffer.seek(0)
                await context.bot.send_voice(
                    chat_id=update.effective_chat.id,
                    voice=wav_buffer,
                    caption=f"🗣️ {parsed.spoken_reply}"
                )
            except Exception as tts_err:
                print(f"Error generando audio TTS: {tts_err}")

    except Exception as e:
        await wait_msg.edit_text(f"❌ Error al procesar audio: {str(e)}")
