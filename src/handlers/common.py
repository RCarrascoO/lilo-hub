from telegram import Update
from telegram.ext import ContextTypes
from src.config import settings

def is_authorized(update: Update) -> bool:
    if not update.effective_user:
        return False
    return update.effective_user.id in settings.ALLOWED_CHAT_IDS

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("⛔ Acceso denegado. Este es un servidor personal privado.")
        return

    user_name = update.effective_user.first_name or "Renato"
    msg = (
        f"👋 **¡Hola, {user_name}! Bienvenido a Lilo Hub.**\n\n"
        "Soy tu orquestador personal conectado al servidor 24/7 y a tu bóveda de Obsidian.\n\n"
        "⚡ **Comandos disponibles:**\n"
        "• `/encender_pc` — Enviar paquete mágico Wake-on-LAN a tu PC de escritorio.\n"
        "• `/server` — Ver métricas del servidor (CPU, RAM, Disco y Contenedores).\n"
        "• `/help` — Ver esta guía de ayuda.\n\n"
        "📥 **Captura Rápida Inteligente:**\n"
        "• **Texto:** Escribe cualquier idea, nota o tarea suelta y la estructuraré en tu Obsidian Inbox.\n"
        "• **Voz:** Mándame un audio caminando o manejando; transcribiré el audio y extraeré tareas y notas automáticamente."
    )
    await update.message.reply_markdown(msg)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_command(update, context)
