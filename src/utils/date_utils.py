import datetime
from zoneinfo import ZoneInfo
from typing import Union
from src.config import settings

DIAS_SEMANA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
]

def get_now() -> datetime.datetime:
    return datetime.datetime.now(ZoneInfo(settings.TIMEZONE))

def get_spanish_weekday(dt: datetime.datetime) -> str:
    return DIAS_SEMANA[dt.weekday()]

def get_spanish_month(dt: datetime.datetime) -> str:
    return MESES[dt.month - 1]

def format_spanish_date(dt: datetime.datetime, include_time: bool = True) -> str:
    dia_sem = get_spanish_weekday(dt).capitalize()
    mes = get_spanish_month(dt)
    if include_time:
        return f"{dia_sem} {dt.day} de {mes} de {dt.year}, {dt.strftime('%H:%M')}"
    return f"{dia_sem} {dt.day} de {mes} de {dt.year}"

def format_relative_event_time(dt_or_str: Union[str, datetime.datetime], is_all_day: bool = False) -> str:
    """
    Formatea una fecha de evento de forma amigable y natural en español.
    Ej: 'Hoy (miércoles) a las 18:30' o 'Mañana (jueves) a las 08:00' o 'Viernes 23 de octubre'.
    """
    now = get_now()
    if isinstance(dt_or_str, str):
        try:
            if "T" in dt_or_str:
                dt = datetime.datetime.fromisoformat(dt_or_str)
            else:
                parts = [int(p) for p in dt_or_str.split("-")]
                dt = datetime.datetime(parts[0], parts[1], parts[2], tzinfo=ZoneInfo(settings.TIMEZONE))
        except Exception:
            return str(dt_or_str)
    else:
        dt = dt_or_str

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(settings.TIMEZONE))
    else:
        dt = dt.astimezone(ZoneInfo(settings.TIMEZONE))

    today = now.date()
    event_date = dt.date()
    diff = (event_date - today).days

    dia_nombre = get_spanish_weekday(dt)
    time_str = dt.strftime("%H:%M")

    if diff == 0:
        rel = "Hoy"
    elif diff == 1:
        rel = "Mañana"
    elif diff == 2:
        rel = "Pasado mañana"
    elif diff == -1:
        rel = "Ayer"
    else:
        rel = f"{dia_nombre.capitalize()} {dt.day} de {get_spanish_month(dt)}"

    if is_all_day:
        return f"{rel} ({dia_nombre}) [Todo el día]"
    return f"{rel} ({dia_nombre}) a las {time_str}"
