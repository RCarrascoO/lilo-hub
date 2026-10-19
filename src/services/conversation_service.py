from datetime import datetime, timedelta
from sqlalchemy import select
from src.database.db import AsyncSessionLocal
from src.database.models import ChatMessage

class ConversationService:
    @staticmethod
    async def add_message(user_id: int, role: str, content: str):
        """Almacena un mensaje en el historial conversacional."""
        async with AsyncSessionLocal() as session:
            msg = ChatMessage(
                user_id=user_id,
                role=role,
                content=content
            )
            session.add(msg)
            await session.commit()

    @staticmethod
    async def get_recent_history(user_id: int, limit: int = 6, max_age_minutes: int = 25) -> list[dict]:
        """Recupera los últimos turnos de conversación recientes para mantener contexto."""
        cutoff = datetime.utcnow() - timedelta(minutes=max_age_minutes)
        async with AsyncSessionLocal() as session:
            q = (
                select(ChatMessage)
                .where(ChatMessage.user_id == user_id, ChatMessage.created_at >= cutoff)
                .order_by(ChatMessage.created_at.desc())
                .limit(limit)
            )
            results = (await session.execute(q)).scalars().all()

        # Invertir para que queden en orden cronológico ascendente
        ordered = list(reversed(results))
        history = []
        for m in ordered:
            history.append({
                "role": m.role,
                "parts": [{"text": m.content}]
            })
        return history
