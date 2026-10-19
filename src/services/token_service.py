from datetime import datetime, date, timezone, timedelta
from sqlalchemy import select, func
from src.database.db import AsyncSessionLocal
from src.database.models import TokenUsage

class TokenService:
    # Límites oficiales de Google AI Studio (Free Tier)
    DAILY_REQUEST_LIMIT = 1500  # 1500 RPD (Requests Per Day) para Flash / Flash-Lite
    RATE_LIMIT_RPM = 15         # 15 RPM (Requests Per Minute)

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

    @classmethod
    async def get_summary(cls) -> dict:
        """Devuelve un resumen mutable del consumo, cuotas restantes y cuenta regresiva de recarga."""
        today_start = datetime.combine(date.today(), datetime.min.time())
        month_start = datetime(date.today().year, date.today().month, 1)

        async with AsyncSessionLocal() as session:
            # 1. Peticiones hoy y tokens hoy
            q_today_tokens = select(func.sum(TokenUsage.total_tokens)).where(TokenUsage.created_at >= today_start)
            tokens_today = (await session.execute(q_today_tokens)).scalar() or 0

            q_today_reqs = select(func.count(TokenUsage.id)).where(TokenUsage.created_at >= today_start)
            requests_today = (await session.execute(q_today_reqs)).scalar() or 0

            # 2. Tokens este mes
            q_month_tokens = select(func.sum(TokenUsage.total_tokens)).where(TokenUsage.created_at >= month_start)
            tokens_month = (await session.execute(q_month_tokens)).scalar() or 0

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

        # Cálculo de reinicio de cuota (Google AI Studio reinicia a las 00:00 UTC)
        now_utc = datetime.now(timezone.utc)
        reset_utc = (now_utc + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        diff = reset_utc - now_utc
        hours_to_reset, remainder = divmod(diff.seconds, 3600)
        minutes_to_reset = remainder // 60

        remaining_requests = max(0, cls.DAILY_REQUEST_LIMIT - requests_today)
        used_percent = round((requests_today / cls.DAILY_REQUEST_LIMIT) * 100, 1)

        return {
            "requests_today": requests_today,
            "daily_limit": cls.DAILY_REQUEST_LIMIT,
            "remaining_requests": remaining_requests,
            "used_percent": used_percent,
            "hours_to_reset": hours_to_reset,
            "minutes_to_reset": minutes_to_reset,
            "tokens_today": tokens_today,
            "tokens_month": tokens_month,
            "tokens_total": tokens_total,
            "models": model_stats
        }
