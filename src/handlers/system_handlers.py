from telegram import Update
from telegram.ext import ContextTypes
from src.handlers.common import is_authorized
from src.services.system_service import SystemService

def make_bar(percent: float, length: int = 10) -> str:
    filled = int(round((percent / 100) * length))
    return "█" * filled + "░" * (length - filled)

async def server_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    wait_msg = await update.message.reply_text("⏳ Consultando métricas del servidor...")

    metrics = SystemService.get_metrics()

    # Formatear CPU y RAM
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
        msg_lines.append(f"• `{d['path']}`: `{d['used_gb']}G / {d['total_gb']}G` ({d['percent']}%)")
        msg_lines.append(f"  `[{disk_bar}]` ({d['free_gb']}G libres)")

    msg_lines.append("\n📦 **CONTENEDORES DOCKER:**")
    active_count = 0
    for c in metrics["containers"]:
        status_icon = "🟢" if "up" in c["status"].lower() else "🔴"
        if status_icon == "🟢":
            active_count += 1
        msg_lines.append(f"{status_icon} `{c['name']}` ({c['status']})")

    msg_lines.append(f"\n_Total activos: {active_count}/{len(metrics['containers'])}_")

    await wait_msg.edit_text("\n".join(msg_lines), parse_mode="Markdown")
