"""
Application Configuration - إعدادات التطبيق

تُحمَّل من متغيرات البيئة أو ملف .env
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """إعدادات التطبيق الأساسية."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "نظام ERP محاسبي متكامل"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"  # TODO: generate strong key

    # Database
    DATABASE_URL: str = "sqlite:///./erp_accounting.db"
    DB_ECHO: bool = False  # print SQL queries (debug only)

    # Security
    BCRYPT_COST: int = 12
    SESSION_DURATION_HOURS: int = 8
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCK_DURATION_MINUTES: int = 15

    # Backup
    BACKUP_DIR: Path = Path("./backups")
    BACKUP_ENCRYPTION_KEY: str = ""  # empty = no encryption

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Path = Path("./logs/app.log")

    # Company info (for invoices & reports)
    COMPANY_NAME: str = "شركتي"
    COMPANY_NAME_EN: str = "My Company"
    COMPANY_TAX_NUMBER: str = ""
    COMPANY_PHONE: str = ""
    COMPANY_EMAIL: str = ""
    COMPANY_ADDRESS: str = ""
    COMPANY_LOGO_PATH: str = ""

    # Defaults
    DEFAULT_CURRENCY: str = "SAR"
    DEFAULT_TAX_RATE: float = 15.0  # VAT السعودية
    FISCAL_YEAR_START_MONTH: int = 1  # يناير
    FISCAL_YEAR_START_DAY: int = 1


@lru_cache
def get_settings() -> Settings:
    """الحصول على إعدادات التطبيق (cached singleton)."""
    return Settings()


# Global settings instance
settings = get_settings()
