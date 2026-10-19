import os
import sys
import logging
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

# Añadir raíz al sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import settings
from src.database.db import init_db
from src.handlers.common import start_command, help_command
from src.handlers.wol_handlers import encender_pc_command, wol_callback_handler
from src.handlers.system_handlers import server_command, server_callback_handler
from src.handlers.notes_handlers import ultima_nota_command
from src.handlers.token_handlers import tokens_command, tokens_callback_handler
from src.handlers.pro_handlers import pro_command
from src.handlers.inbox_handlers import handle_text_inbox, handle_voice_inbox

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("lilo-hub")

async def post_init(application):
    logger.info("Inicializando base de datos SQLite y tablas...")
    await init_db()
    logger.info("Base de datos y tablas de telemetría inicializadas correctamente.")

def main():
    logger.info("Iniciando Lilo Hub...")
    app = (
        ApplicationBuilder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # 1. Comandos con barra diagonal (/)
    app.add_handler(CommandHandler(["start", "inicio"], start_command))
    app.add_handler(CommandHandler(["help", "ayuda"], help_command))
    app.add_handler(CommandHandler(["encender_pc", "wol", "wake"], encender_pc_command))
    app.add_handler(CommandHandler(["server", "servidor", "status"], server_command))
    app.add_handler(CommandHandler(["nota", "ultima_nota"], ultima_nota_command))
    app.add_handler(CommandHandler(["tokens", "consumo"], tokens_command))
    app.add_handler(CommandHandler(["pro", "gemini_pro"], pro_command))

    # 2. Handlers para Botones del Teclado Inferior
    app.add_handler(MessageHandler(filters.Regex(r"^⚡ Encender PC$"), encender_pc_command))
    app.add_handler(MessageHandler(filters.Regex(r"^🖥️ Servidor$"), server_command))
    app.add_handler(MessageHandler(filters.Regex(r"^📓 Última Nota$"), ultima_nota_command))
    app.add_handler(MessageHandler(filters.Regex(r"^📊 Tokens IA$"), tokens_command))
    app.add_handler(MessageHandler(filters.Regex(r"^❓ Ayuda$"), help_command))

    # 3. Callbacks para Botones Inline (Bajo los mensajes)
    app.add_handler(CallbackQueryHandler(server_callback_handler, pattern=r"^refresh_server$"))
    app.add_handler(CallbackQueryHandler(wol_callback_handler, pattern=r"^wake_pc_inline$"))
    app.add_handler(CallbackQueryHandler(tokens_callback_handler, pattern=r"^refresh_tokens$"))

    # 4. Captura inteligente de Inbox (Texto y Audio)
    # Excluye los textos que coinciden con los botones rápidos
    app.add_handler(MessageHandler(
        filters.TEXT & (~filters.COMMAND) & (~filters.Regex(r"^(⚡ Encender PC|🖥️ Servidor|📓 Última Nota|📊 Tokens IA|❓ Ayuda)$")),
        handle_text_inbox
    ))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice_inbox))

    logger.info("Lilo Hub está escuchando eventos...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
