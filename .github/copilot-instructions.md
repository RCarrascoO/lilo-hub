# GitHub Copilot Instructions for Lilo Hub

You are assisting with the development of **Lilo Hub**, a Python 3.12+ asynchronous Telegram bot and personal server orchestrator.

## Architectural Guidelines
1. **Always use asynchronous code**: Use `async/await` for all Telegram handlers, database operations (`aiosqlite` with `SQLAlchemy`), and network requests.
2. **Strict Security**: Every handler must check `is_authorized(update)` from `src.handlers.common`. Never expose API keys or tokens.
3. **Model Tiering**:
   - For quick text parsing or classification: use `gemini-3.5-flash-lite`.
   - For audio/voice/images: use `gemini-2.5-flash`.
4. **YAGNI**: Keep dependencies minimal. Prefer SQLite over PostgreSQL unless explicitly requested. Do not add background queue servers (Redis/Celery) if APScheduler or asyncio tasks suffice.
5. **Obsidian Output**: Ensure all notes saved via `VaultService` include standard YAML frontmatter with tags and date.
