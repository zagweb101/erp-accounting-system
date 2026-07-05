"""
نقطة الدخول الرئيسية للتطبيق - Application Entry Point

Usage:
    python -m erp_accounting.main         # تشغيل التطبيق
    python -m erp_accounting.main --init  # تهيئة DB فقط
    python -m erp_accounting.main --seed  # تهيئة + بيانات افتراضية
"""
from __future__ import annotations

import asyncio
import sys
from typing import Optional

from PySide6.QtWidgets import QApplication
from loguru import logger

from adapters.repositories.sql_alchemy.user_repository import SqlAlchemyUserRepository
from adapters.repositories.sql_alchemy.account_journal_repository import (
    SqlAlchemyAccountRepository,
    SqlAlchemyJournalEntryRepository,
)
from domain.entities.user import User
from infrastructure.config.settings import settings
from use_cases.auth.auth_use_cases import LoginUseCase


def setup_logging() -> None:
    """إعداد نظام التسجيل (loguru)."""
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )
    # Add file logging
    settings.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logger.add(
        settings.LOG_FILE,
        level=settings.LOG_LEVEL,
        rotation="10 MB",
        retention="30 days",
        compression="zip",
    )


def init_database() -> None:
    """تهيئة قاعدة البيانات."""
    from infrastructure.db.session import init_db
    logger.info("Initializing database...")
    init_db()
    logger.info("✓ Database initialized")


def run_seed() -> None:
    """تشغيل بيانات seed الافتراضية."""
    from infrastructure.db.seed import seed_all
    seed_all()


def run_app() -> int:
    """تشغيل تطبيق PySide6."""
    # Initialize DB if needed
    init_database()

    # Try to seed (idempotent — only creates if missing)
    try:
        run_seed()
    except Exception as e:
        logger.warning(f"Seed skipped: {e}")

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName(settings.APP_NAME)
    app.setApplicationVersion(settings.APP_VERSION)
    app.setOrganizationName("ERP Accounting")

    # Set font
    font = app.font()
    font.setPointSize(11)
    font.setFamily("Noto Sans Arabic")
    app.setFont(font)

    # Set RTL layout direction globally
    app.setLayoutDirection(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.LayoutDirection.RightToLeft)

    # Apply Soft UI theme
    try:
        from infrastructure.ui.theme.soft_ui import SoftUITheme
        SoftUITheme.apply(app)
        logger.info("Soft UI theme applied")
    except Exception as e:
        logger.info(f"Soft UI theme not available: {e}, using default")

    # Wire up dependencies (manual DI — could use a container later)
    user_repo = SqlAlchemyUserRepository()
    login_use_case = LoginUseCase(user_repo=user_repo)

    # Show login window
    from infrastructure.ui.windows.login_window_v2 import LoginWindow as LoginWindow
    from infrastructure.ui.windows.main_window import MainWindow

    login_window = LoginWindow(login_use_case=login_use_case)
    main_window: Optional[MainWindow] = None

    def on_login_success(response) -> None:
        nonlocal main_window
        logger.info(f"User logged in: {response.user.username}")
        main_window = MainWindow(current_user=response.user)
        main_window.show()
        login_window.close()

    login_window.login_successful.connect(on_login_success)
    login_window.show()

    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    return app.exec()


def main() -> int:
    """Main entry point."""
    setup_logging()

    # Parse args
    if "--init" in sys.argv:
        init_database()
        return 0
    if "--seed" in sys.argv:
        init_database()
        run_seed()
        return 0
    if "--help" in sys.argv or "-h" in sys.argv:
        print("""
ERP Accounting System v{settings.APP_VERSION}

Usage:
    python -m erp_accounting.main         # تشغيل التطبيق
    python -m erp_accounting.main --init  # تهيئة DB فقط
    python -m erp_accounting.main --seed  # تهيئة + بيانات افتراضية
    python -m erp_accounting.main --help  # هذه الرسالة
""".format(settings=settings))
        return 0

    # Run the app
    return run_app()


if __name__ == "__main__":
    sys.exit(main())
