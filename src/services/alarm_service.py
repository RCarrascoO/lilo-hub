import logging
import datetime
from typing import Dict, Any, Optional, Tuple
import httpx
from zoneinfo import ZoneInfo

from src.config import settings
from src.services.google_service import google_service
from src.services.gemini_service import gemini_service
from src.services.vault_service import VaultService
from src.services.wol_service import WOLService
from src.services.system_service import SystemService

logger = logging.getLogger("lilo-hub")

# Horario base por defecto: día de la semana (0=Lunes, 6=Domingo)
DEFAULT_WEEKLY_SCHEDULE: Dict[int, Optional[str]] = {
    0: "07:40",  # Lunes
    1: "06:20",  # Martes
    2: "08:20",  # Miércoles
    3: "06:20",  # Jueves
    4: "10:00",  # Viernes
    5: "09:00",  # Sábado
    6: None,     # Domingo (apagado por defecto)
}


class AlarmService:
    def __init__(self):
        self.tz = ZoneInfo(settings.TIMEZONE)
        # Overrides manuales temporales: dict[str(YYYY-MM-DD), str(HH:MM) | None]
        self._manual_overrides: Dict[str, Optional[str]] = {}
        # Estado de watchdog activo: task_id o fecha
        self.pending_acknowledgment: Optional[str] = None

    def get_alarm_time_for_date(self, target_date: datetime.date) -> Optional[Tuple[int, int]]:
        """
        Retorna (hora, minuto) de la alarma para una fecha, respetando overrides y el horario base.
        """
        date_str = target_date.isoformat()
        if date_str in self._manual_overrides:
            val = self._manual_overrides[date_str]
            if val is None:
                return None
            h, m = map(int, val.split(":"))
            return (h, m)

        weekday = target_date.weekday()
        default_time = DEFAULT_WEEKLY_SCHEDULE.get(weekday)
        if not default_time:
            return None

        h, m = map(int, default_time.split(":"))
        return (h, m)

    def set_manual_alarm(self, target_date: datetime.date, time_str: Optional[str]):
        """
        Configura o deshabilita la alarma para una fecha específica ('HH:MM' o None para desactivar).
        """
        date_str = target_date.isoformat()
        self._manual_overrides[date_str] = time_str
        logger.info(f"Alarma para {date_str} actualizada manualmente a: {time_str}")

    def get_next_alarm(self) -> Optional[datetime.datetime]:
        """
        Calcula el próximo datetime en el que sonará la alarma.
        """
        now = datetime.datetime.now(self.tz)
        today = now.date()

        # Revisar hoy
        today_alarm = self.get_alarm_time_for_date(today)
        if today_alarm:
            h, m = today_alarm
            alarm_dt = datetime.datetime(today.year, today.month, today.day, h, m, tzinfo=self.tz)
            if alarm_dt > now:
                return alarm_dt

        # Revisar próximos 7 días
        for offset in range(1, 8):
            next_day = today + datetime.timedelta(days=offset)
            next_alarm = self.get_alarm_time_for_date(next_day)
            if next_alarm:
                h, m = next_alarm
                return datetime.datetime(next_day.year, next_day.month, next_day.day, h, m, tzinfo=self.tz)

        return None

    async def send_ntfy_alert(self, title: str, message: str, priority: int = 5):
        """
        Envía una notificación push persistente vía ntfy (open-source self-hosted / cloud).
        Usa payload JSON para soportar emojis UTF-8 en el título sin fallas de codificación en headers.
        """
        if not settings.NTFY_TOPIC:
            return

        url = f"{settings.NTFY_SERVER.rstrip('/')}"
        payload = {
            "topic": settings.NTFY_TOPIC,
            "title": title,
            "message": message,
            "priority": priority,  # 5 = urgente / max prioridad (suena continuo en Android)
            "tags": ["alarm_clock", "warning"]
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    logger.info("Notificación ntfy enviada exitosamente con payload JSON.")
                else:
                    logger.warning(f"ntfy respondió con status {res.status_code}: {res.text}")
        except Exception as e:
            logger.error(f"Error enviando alerta ntfy: {e}")

    async def generate_briefing(self) -> Tuple[str, str, Optional[bytes]]:
        """
        Genera el reporte matutino:
        - Retorna: (texto_telegram, guion_audio, audio_bytes_ogg_opus)
        """
        now = datetime.datetime.now(self.tz)
        today_str = now.strftime("%A %d de %B de %Y")

        # 1. Google Calendar
        events = google_service.get_calendar_events(days=1, max_results=5)
        events_text = "No hay eventos programados para hoy."
        if events:
            lines = []
            for ev in events:
                time_part = "Todo el día" if ev["is_all_day"] else ev["start"].split("T")[-1][:5] if "T" in str(ev["start"]) else ev["start"]
                lines.append(f"• {time_part} - {ev['summary']}")
            events_text = "\n".join(lines)

        # 2. Gmail
        emails = google_service.get_unread_emails(max_results=3)
        emails_text = "Bandeja al día, no hay correos urgentes."
        if emails:
            lines = []
            for em in emails:
                sender_short = em["sender"].split("<")[0].strip()
                lines.append(f"• De {sender_short}: {em['subject']}")
            emails_text = "\n".join(lines)

        # 3. Servidor y Tokens
        srv_stats = SystemService.get_metrics()
        srv_text = f"RAM: {srv_stats.get('ram_used_gb', 0):.1f}/{srv_stats.get('ram_total_gb', 0):.1f}GB | CPU: {srv_stats.get('cpu_percent', 0)}%"

        # 4. Prompt para guión y resumen
        prompt = (
            f"Hoy es {today_str}, hora actual {now.strftime('%H:%M')}.\n"
            f"El usuario es Renato. Actúa como Lilo, su asistente de cabecera inteligente y profesional.\n"
            f"Datos del día:\n"
            f"- Eventos/Clases de hoy:\n{events_text}\n"
            f"- Correos recientes no leídos:\n{emails_text}\n"
            f"- Estado del servidor:\n{srv_text}\n\n"
            "Tu tarea es generar DOS cosas separadas por el delimitador '---SCRIPT---':\n"
            "1. TEXTO: Una ficha visual limpia, motivadora y ejecutiva para Telegram, usando emojis y viñetas claras.\n"
            "---SCRIPT---\n"
            "2. GUION: Un guión hablado para nota de voz de exactamente 20 a 30 segundos. Tono enérgico, claro y directo. "
            "Saluda a Renato, dile la hora, destaca su primera clase o evento del día y anímalo a levantarse con energía."
        )

        try:
            response_text = await gemini_service.generate_briefing_text(prompt, user_id=0)
        except Exception as e:
            logger.error(f"Error generando texto del briefing: {e}")
            response_text = f"¡Buenos días Renato!\n\n📅 Agenda de hoy:\n{events_text}\n\n✉️ Correos:\n{emails_text}"

        if "---SCRIPT---" in response_text:
            parts = response_text.split("---SCRIPT---", 1)
            text_card = parts[0].strip()
            spoken_script = parts[1].strip()
        else:
            text_card = response_text.strip()
            spoken_script = (
                f"¡Buenos días Renato! Son las {now.strftime('%H:%M')}. "
                f"Tienes clases hoy. Revisa tu agenda y que tengas una excelente jornada."
            )

        # 5. Sintetizar voz TTS
        audio_bytes = None
        try:
            audio_bytes = await gemini_service.generate_voice_audio(spoken_script, user_id=0)
        except Exception as e:
            logger.warning(f"No se pudo sintetizar voz para la alarma: {e}")

        return (text_card, spoken_script, audio_bytes)


alarm_service = AlarmService()
