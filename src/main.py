import os
import sys
import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

# Añadir raíz al sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import settings
from src.database.db import init_db
from src.handlers.common import start_command, help_command
from src.handlers.wol_handlers import encender_pc_command
from src.handlers.system_handlers import server_command
from src.handlers.inbox_handlers import handle_text_inbox, handle_voice_inbox

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("lilo-hub")

async def post_init(application):
    logger.info("Inicializando base de datos SQLite...")
    await init_db()
    logger.info("Base de datos inicializada correctamente.")

def main():
    logger.info("Iniciando Lilo Hub...")
    app = (
        ApplicationBuilder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Registrar Comandos
    app.add_handler(CommandHandler(["start", "inicio"], start_command))
    app.add_handler(CommandHandler(["help", "ayuda"], help_command))
    app.add_handler(CommandHandler(["encender_pc", "wol", "wake"], encender_pc_command))
    app.add_handler(CommandHandler(["server", "servidor", "status"], server_command))

    # Registrar Handlers de Mensajes
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text_inbox))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice_inbox))

    logger.info("Lilo Hub está escuchando eventos...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
