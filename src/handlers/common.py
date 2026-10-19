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
        [KeyboardButton("📓 Última Nota"), KeyboardButton("❓ Ayuda")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("⛔ Acceso denegado. Este es un servidor personal privado.")
        return

    user_name = update.effective_user.first_name or "Renato"
    msg = (
        f"👋 **¡Hola, {user_name}! Bienvenido a Lilo Hub.**\n\n"
        "Soy tu orquestador personal conectado al servidor 24/7 y a tu bóveda de Obsidian.\n\n"
        "⚡ **Accesos Rápidos (Botones):**\n"
        "• Puedes usar los botones de abajo directamente sin escribir comandos.\n"
        "• O si lo prefieres, escribir `/encender_pc`, `/server`, `/help`.\n\n"
        "📥 **Captura Rápida Inteligente:**\n"
        "• **Texto:** Escribe cualquier pensamiento y lo estructuraré en tu Obsidian Inbox.\n"
        "• **Voz:** Mándame un audio caminando o manejando; transcribiré el audio y extraeré tareas y notas automáticamente."
    )
    await update.message.reply_markdown(msg, reply_markup=get_main_keyboard())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_command(update, context)
