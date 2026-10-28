from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from src.config import settings

def is_authorized(update: Update) -> bool:
    if not update.effective_user:
        return False
    return update.effective_user.id in settings.ALLOWED_CHAT_IDS

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Retorna el teclado rápido persistente en la parte inferior del chat."""
    keyboard = [
        [KeyboardButton("⚡ Encender PC"), KeyboardButton("🖥️ Servidor")],
        [KeyboardButton("📅 Agenda"), KeyboardButton("✉️ Correos")],
        [KeyboardButton("⏰ Alarma"), KeyboardButton("📊 Tokens IA")],
        [KeyboardButton("📓 Última Nota"), KeyboardButton("❓ Ayuda")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("⛔ Acceso denegado. Este es un servidor personal privado.")
        return

    user_name = update.effective_user.first_name or settings.USER_NAME
    msg = (
        f"👋 **¡Hola, {user_name}! Bienvenido a Lilo Hub.**\n\n"
        "Soy tu orquestador personal conectado a tu servidor 24/7, tu bóveda de Obsidian y tu Google Workspace.\n\n"
        "⚡ **Accesos Rápidos (Botones):**\n"
        "• `⚡ Encender PC` / `🖥️ Servidor`: Control de hardware y contenedores.\n"
        "• `📅 Agenda` / `✉️ Correos`: Google Calendar y Gmail en tiempo real.\n"
        "• `⏰ Alarma`: Morning Briefing matutino con voz y despertador.\n"
        "• `📊 Tokens IA`: Telemetría y cuota de modelos de Gemini.\n\n"
        "🤖 **Modelos de IA:**\n"
        "• **Flash-Lite (Texto):** Captura notas e ideas ultra rápido.\n"
        "• **Flash Multimodal (Voz):** Transcribe audios y responde por voz cuando haces preguntas.\n"
        "• **Gemini Pro:** Modo razonamiento avanzado usando `/pro <consulta>`.\n\n"
        "📥 **Captura Rápida:**\n"
        "• Escribe cualquier texto o manda una nota de voz directamente."
    )
    await update.message.reply_markdown(msg, reply_markup=get_main_keyboard())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_command(update, context)
