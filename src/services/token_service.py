from datetime import datetime, date
from sqlalchemy import select, func
from src.database.db import AsyncSessionLocal
from src.database.models import TokenUsage

class TokenService:
    @staticmethod
    async def log_usage(
        user_id: int,
        model_name: str,
        feature: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int
    ):
        """Registra un evento de consumo de tokens en la base de datos."""
        async with AsyncSessionLocal() as session:
            record = TokenUsage(
                user_id=user_id,
                model_name=model_name,
                feature=feature,
                prompt_tokens=prompt_tokens or 0,
                completion_tokens=completion_tokens or 0,
                total_tokens=total_tokens or (prompt_tokens + completion_tokens)
            )
            session.add(record)
            await session.commit()

    @staticmethod
    async def get_summary() -> dict:
        """Devuelve un resumen mutable y detallado del consumo de tokens."""
        today_start = datetime.combine(date.today(), datetime.min.time())
        month_start = datetime(date.today().year, date.today().month, 1)

        async with AsyncSessionLocal() as session:
            # 1. Tokens hoy
            q_today = select(func.sum(TokenUsage.total_tokens)).where(TokenUsage.created_at >= today_start)
            tokens_today = (await session.execute(q_today)).scalar() or 0

            # 2. Tokens este mes
            q_month = select(func.sum(TokenUsage.total_tokens)).where(TokenUsage.created_at >= month_start)
            tokens_month = (await session.execute(q_month)).scalar() or 0

            # 3. Desglose por modelo este mes
            q_models = (
                select(
                    TokenUsage.model_name,
                    func.sum(TokenUsage.total_tokens),
                    func.count(TokenUsage.id)
                )
                .where(TokenUsage.created_at >= month_start)
                .group_by(TokenUsage.model_name)
            )
            model_stats = []
            for row in (await session.execute(q_models)).all():
                model_stats.append({
                    "model": row[0],
                    "tokens": row[1],
                    "calls": row[2]
                })

            # 4. Total histórico
            q_total = select(func.sum(TokenUsage.total_tokens))
            tokens_total = (await session.execute(q_total)).scalar() or 0

        return {
            "tokens_today": tokens_today,
            "tokens_month": tokens_month,
            "tokens_total": tokens_total,
            "models": model_stats
        }
