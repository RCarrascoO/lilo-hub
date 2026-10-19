from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from src.handlers.common import is_authorized
from src.services.token_service import TokenService

async def format_tokens_message() -> tuple[str, InlineKeyboardMarkup]:
    summary = await TokenService.get_summary()

    today_k = round(summary["tokens_today"] / 1000, 2)
    month_k = round(summary["tokens_month"] / 1000, 2)
    total_k = round(summary["tokens_total"] / 1000, 2)

    msg_lines = [
        "📊 **MONITOR DE CONSUMO DE TOKENS (IA)**",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"📅 **Hoy:** `{today_k}k tokens` ({summary['tokens_today']} exactos)",
        f"📆 **Este Mes:** `{month_k}k tokens` ({summary['tokens_month']} exactos)",
        f"📈 **Total Histórico:** `{total_k}k tokens`\n",
        "🤖 **DESGLOSE POR MODELO (ESTE MES):**"
    ]

    if not summary["models"]:
        msg_lines.append("_Aún no se registran llamadas con telemetría este mes._")
    else:
        for m in summary["models"]:
            m_tokens_k = round(m["tokens"] / 1000, 2)
            # Limpiar nombre del modelo para visualización
            display_name = m["model"].replace("gemini-", "").replace("models/", "")
            msg_lines.append(f"• `{display_name}`: `{m_tokens_k}k tokens` ({m['calls']} llamadas)")

    msg_lines.append("\n💡 _Estrategia activa: Tiering inteligente con Flash-Lite para ahorro máximo._")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Actualizar Tokens", callback_data="refresh_tokens")]
    ])

    return "\n".join(msg_lines), keyboard

async def tokens_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    text, keyboard = await format_tokens_message()
    await update.message.reply_markdown(text, reply_markup=keyboard)

async def tokens_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Actualizando métricas de tokens...")

    text, keyboard = await format_tokens_message()
    try:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
    except Exception:
        pass
