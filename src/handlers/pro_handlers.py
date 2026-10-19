from telegram import Update
from telegram.ext import ContextTypes
from src.handlers.common import is_authorized
from src.services.gemini_service import GeminiService

gemini_service = GeminiService()

async def pro_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    # Extraer el texto de la consulta
    query = " ".join(context.args) if context.args else ""
    if not query:
        await update.message.reply_markdown(
            "🧠 **Modo Gemini 2.5 Pro (Razonamiento Profundo)**\n\n"
            "Uso: `/pro <tu pregunta o tema complejo>`\n\n"
            "Ejemplo:\n"
            "`/pro Explica la diferencia entre cálculo vectorial y álgebra lineal aplicado a redes neuronales`"
        )
        return

    wait_msg = await update.message.reply_text("🤔 Analizando con Gemini 2.5 Pro (Razonamiento profundo)...")

    try:
        response_text = await gemini_service.query_pro_model(query, user_id=update.effective_user.id)
        # Dividir mensaje si supera el límite de Telegram (4096 caracteres)
        if len(response_text) > 4000:
            for i in range(0, len(response_text), 4000):
                await update.message.reply_markdown(response_text[i:i+4000])
            await wait_msg.delete()
        else:
            await wait_msg.edit_text(response_text, parse_mode="Markdown")
    except Exception as e:
        await wait_msg.edit_text(f"❌ Error al consultar Gemini 2.5 Pro: {str(e)}")
