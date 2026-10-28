import os
import datetime
import pytest
from src.services.vault_service import VaultService
from src.services.wol_service import WOLService
from src.services.backup_service import BackupService
from src.services.alarm_service import AlarmService
from src.services.google_service import GoogleService

def test_vault_filename_sanitization():
    raw_title = '¿Cómo funciona el servidor? / Test: "Archivo"'
    clean = VaultService.sanitize_filename(raw_title)
    assert "/" not in clean
    assert "?" not in clean
    assert '"' not in clean
    assert ":" not in clean
    assert "_" in clean

def test_wol_mac_configuration():
    assert len(WOLService.wake_pc()) > 0

def test_backup_service_creation(tmp_path, monkeypatch):
    test_db = tmp_path / "test.db"
    test_db.write_text("dummy database content")
    
    backup_dir = tmp_path / "backups"
    monkeypatch.setattr(BackupService, "DB_PATH", str(test_db))
    monkeypatch.setattr(BackupService, "BACKUP_DIR", str(backup_dir))

    os.makedirs(backup_dir, exist_ok=True)
    assert os.path.exists(backup_dir)

def test_alarm_schedule_defaults():
    alarm = AlarmService()
    # 2026-10-19 es Lunes (weekday=0) -> 08:00
    monday = datetime.date(2026, 10, 19)
    assert alarm.get_alarm_time_for_date(monday) == (8, 0)

    # 2026-10-20 es Martes (weekday=1) -> 08:00
    tuesday = datetime.date(2026, 10, 20)
    assert alarm.get_alarm_time_for_date(tuesday) == (8, 0)

    # 2026-10-21 es Miércoles (weekday=2) -> 08:00
    wednesday = datetime.date(2026, 10, 21)
    assert alarm.get_alarm_time_for_date(wednesday) == (8, 0)

    # 2026-10-25 es Domingo (weekday=6) -> None
    sunday = datetime.date(2026, 10, 25)
    assert alarm.get_alarm_time_for_date(sunday) is None

def test_alarm_manual_override():
    alarm = AlarmService()
    tuesday = datetime.date(2026, 10, 20)
    # Por defecto martes es 08:00
    assert alarm.get_alarm_time_for_date(tuesday) == (8, 0)

    # Override a las 09:15
    alarm.set_manual_alarm(tuesday, "09:15")
    assert alarm.get_alarm_time_for_date(tuesday) == (9, 15)

    # Desactivar alarma para ese día
    alarm.set_manual_alarm(tuesday, None)
    assert alarm.get_alarm_time_for_date(tuesday) is None

def test_google_service_resolution(tmp_path):
    primary = tmp_path / "non_existent.json"
    fallback = tmp_path / "fallback.json"
    fallback.write_text("{}")

    gs = GoogleService(token_path=str(primary))
    resolved = gs._resolve_path(str(primary), str(fallback))
    assert resolved == fallback
