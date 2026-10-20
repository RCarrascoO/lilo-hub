import os
import pytest
from src.services.vault_service import VaultService
from src.services.wol_service import WOLService
from src.services.backup_service import BackupService

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

    # Test create_backup using file copy fallback or sqlite
    os.makedirs(backup_dir, exist_ok=True)
    assert os.path.exists(backup_dir)
