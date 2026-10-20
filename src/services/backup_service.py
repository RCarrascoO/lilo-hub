import os
import sqlite3
import shutil
from datetime import datetime, timedelta

class BackupService:
    BACKUP_DIR = "/backups" if os.path.exists("/backups") else "data/backups"
    DB_PATH = "data/lilo.db"
    RETENTION_DAYS = 7

    @classmethod
    def create_backup(cls) -> dict:
        """Crea una copia de seguridad consistente de SQLite usando la API de backup en caliente."""
        os.makedirs(cls.BACKUP_DIR, exist_ok=True)

        if not os.path.exists(cls.DB_PATH):
            return {"success": False, "error": "Archivo de base de datos no encontrado."}

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"lilo_backup_{timestamp}.db"
        backup_filepath = os.path.join(cls.BACKUP_DIR, backup_filename)

        try:
            # Backup seguro en caliente mediante la API oficial de SQLite
            source_conn = sqlite3.connect(cls.DB_PATH)
            dest_conn = sqlite3.connect(backup_filepath)
            with dest_conn:
                source_conn.backup(dest_conn)
            dest_conn.close()
            source_conn.close()

            # Purgar respaldos antiguos
            cls.cleanup_old_backups()

            file_size_kb = round(os.path.getsize(backup_filepath) / 1024, 1)
            return {
                "success": True,
                "filepath": backup_filepath,
                "filename": backup_filename,
                "size_kb": file_size_kb
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def cleanup_old_backups(cls):
        """Elimina respaldos con más de RETENTION_DAYS días de antigüedad."""
        if not os.path.exists(cls.BACKUP_DIR):
            return

        cutoff = datetime.now() - timedelta(days=cls.RETENTION_DAYS)
        for f in os.listdir(cls.BACKUP_DIR):
            if f.startswith("lilo_backup_") and f.endswith(".db"):
                path = os.path.join(cls.BACKUP_DIR, f)
                try:
                    mtime = datetime.fromtimestamp(os.path.getmtime(path))
                    if mtime < cutoff:
                        os.remove(path)
                except Exception:
                    pass
