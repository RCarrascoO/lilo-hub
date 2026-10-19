from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from src.handlers.common import is_authorized
from src.services.system_service import SystemService

def make_bar(percent: float, length: int = 10) -> str:
    filled = int(round((percent / 100) * length))
    return "█" * filled + "░" * (length - filled)

def format_server_message() -> tuple[str, InlineKeyboardMarkup]:
    metrics = SystemService.get_metrics()

    cpu = metrics["cpu_percent"]
    ram = metrics["ram"]
    ram_bar = make_bar(ram["percent"])

    msg_lines = [
        "🖥️ **ESTADO DEL SERVIDOR (`sanehost`)**",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"**CPU ({metrics['cpu_count']} cores):** `{cpu}%`",
        f"**RAM:** `{ram['used_gb']}G / {ram['total_gb']}G` ({ram['percent']}%)",
        f"`[{ram_bar}]` (Libre: {ram['free_gb']}G)\n",
        "💾 **ALMACENAMIENTO:**"
    ]

    for d in metrics["disks"]:
        disk_bar = make_bar(d["percent"])
        msg_lines.append(f"• `{d['name']}`: `{d['used_gb']}G / {d['total_gb']}G` ({d['percent']}%)")
        msg_lines.append(f"  `[{disk_bar}]` ({d['free_gb']}G libres)")

    msg_lines.append("\n📦 **CONTENEDORES DOCKER:**")
    active_count = 0
    for c in metrics["containers"]:
        status_lower = c["status"].lower()
        is_active = "running" in status_lower or "up" in status_lower
        status_icon = "🟢" if is_active else "🔴"
        if is_active:
            active_count += 1
        msg_lines.append(f"{status_icon} `{c['name']}` ({c['status']})")

    msg_lines.append(f"\n_Total activos: {active_count}/{len(metrics['containers'])}_")

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Actualizar Métricas", callback_data="refresh_server"),
            InlineKeyboardButton("⚡ Encender PC", callback_data="wake_pc_inline")
        ]
    ])

    return "\n".join(msg_lines), keyboard

async def server_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    text, keyboard = format_server_message()
    await update.message.reply_markdown(text, reply_markup=keyboard)

async def server_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Actualizando métricas...")

    text, keyboard = format_server_message()
    try:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
    except Exception:
        # Si las métricas no cambiaron, Telegram lanzará un error leve de 'message not modified'
        pass
