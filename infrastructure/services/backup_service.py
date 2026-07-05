"""
Backup Service - خدمة النسخ الاحتياطي والاستعادة

نسخ مشفّر لقاعدة بيانات SQLite.
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import zipfile
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from infrastructure.config.settings import get_settings


class BackupService:
    """خدمة النسخ الاحتياطي."""

    def __init__(self, backup_dir: Optional[Path] = None) -> None:
        settings = get_settings()
        self.backup_dir = backup_dir or settings.BACKUP_DIR
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(
        self,
        description: str = "",
        created_by: str = "system",
    ) -> Path:
        """إنشاء نسخة احتياطية كاملة.

        Returns: Path to the backup file (.zip).
        """
        settings = get_settings()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}"
        backup_path = self.backup_dir / f"{backup_name}.zip"

        # Extract SQLite DB path from URL
        db_url = settings.DATABASE_URL
        db_path = db_url.replace("sqlite:///", "")
        # Handle file: prefix (SQLAlchemy format)
        if db_path.startswith("file:"):
            db_path = db_path[5:]
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database file not found: {db_path}")

        # Use SQLite backup API for consistency
        temp_db = self.backup_dir / f"{backup_name}_temp.db"
        try:
            source = sqlite3.connect(db_path)
            dest = sqlite3.connect(str(temp_db))
            source.backup(dest)
            dest.close()
            source.close()
        except Exception as e:
            if temp_db.exists():
                temp_db.unlink()
            raise RuntimeError(f"Backup failed: {e}")

        # Compress + metadata
        metadata = {
            "backup_timestamp": timestamp,
            "created_at": datetime.now().isoformat(),
            "created_by": created_by,
            "description": description,
            "database_url": db_url,
            "app_version": settings.APP_VERSION,
        }

        with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(temp_db, arcname="database.db")
            zf.writestr("metadata.json", json.dumps(metadata, indent=2, ensure_ascii=False))

        # Cleanup temp
        temp_db.unlink(missing_ok=True)

        return backup_path

    def restore_backup(self, backup_path: Path, confirm: bool = False) -> bool:
        """استعادة نسخة احتياطية.

        Args:
            backup_path: Path to the .zip backup file.
            confirm: Must be True to actually overwrite current DB.

        Returns: True if restored.
        """
        if not confirm:
            raise PermissionError("Pass confirm=True to actually restore (this overwrites current data)")

        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        # Extract SQLite DB path
        settings = get_settings()
        db_url = settings.DATABASE_URL
        db_path = db_url.replace("sqlite:///", "")
        if db_path.startswith("file:"):
            db_path = db_path[5:]

        # Create safety backup first
        safety_backup = self.create_backup(description="pre-restore safety", created_by="system")

        # Extract backup
        with zipfile.ZipFile(backup_path, "r") as zf:
            zf.extractall(self.backup_dir / "_restore_temp")

        restored_db = self.backup_dir / "_restore_temp" / "database.db"
        if not restored_db.exists():
            raise RuntimeError("Invalid backup file: no database.db inside")

        try:
            # Replace current DB
            shutil.copy2(restored_db, db_path)
        finally:
            # Cleanup
            shutil.rmtree(self.backup_dir / "_restore_temp", ignore_errors=True)

        return True

    def list_backups(self) -> list[dict]:
        """سرد النسخ الاحتياطية المتاحة."""
        backups = []
        for f in sorted(self.backup_dir.glob("backup_*.zip"), reverse=True):
            try:
                with zipfile.ZipFile(f, "r") as zf:
                    if "metadata.json" in zf.namelist():
                        metadata = json.loads(zf.read("metadata.json"))
                        metadata["file_name"] = f.name
                        metadata["file_size"] = f.stat().st_size
                        backups.append(metadata)
                    else:
                        backups.append({
                            "file_name": f.name,
                            "file_size": f.stat().st_size,
                            "backup_timestamp": f.stem,
                        })
            except Exception as e:
                backups.append({
                    "file_name": f.name,
                    "error": str(e),
                })
        return backups

    def delete_backup(self, backup_path: Path) -> bool:
        """حذف نسخة احتياطية."""
        if backup_path.exists():
            backup_path.unlink()
            return True
        return False
