"""
Login Window - نافذة تسجيل الدخول

نافذة احترافية بتصميم حديث (Dark Mode) تدعم RTL.
"""
from __future__ import annotations

import asyncio
import sys
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QIcon, QPixmap, QColor
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QFrame, QCheckBox,
    QSizePolicy, QSpacerItem,
)

try:
    import qtawesome as qta
except ImportError:
    qta = None

try:
    import qdarktheme
except ImportError:
    qdarktheme = None

from domain.entities.user import User
from domain.exceptions.exceptions import (
    AccountLockedException,
    InvalidCredentialsException,
    ValidationException,
)
from infrastructure.config.settings import settings
from use_cases.auth.auth_use_cases import LoginRequest, LoginUseCase


class LoginWorker(QThread):
    """Async worker for login (لا يجمد الواجهة)."""

    finished_signal = Signal(object)  # User or None
    error_signal = Signal(str)

    def __init__(self, login_use_case: LoginUseCase, request: LoginRequest) -> None:
        super().__init__()
        self._login_use_case = login_use_case
        self._request = request

    def run(self) -> None:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(self._login_use_case.execute(self._request))
            self.finished_signal.emit(response)
        except (InvalidCredentialsException, AccountLockedException, ValidationException) as e:
            self.error_signal.emit(str(e))
        except Exception as e:
            self.error_signal.emit(f"خطأ غير متوقع: {e}")


class LoginWindow(QMainWindow):
    """نافذة تسجيل الدخول."""

    login_successful = Signal(object)  # emits User object

    def __init__(self, login_use_case: LoginUseCase) -> None:
        super().__init__()
        self._login_use_case = login_use_case
        self._worker: Optional[LoginWorker] = None
        self._setup_ui()
        self._apply_styles()

    def _setup_ui(self) -> None:
        self.setWindowTitle(f"{settings.APP_NAME} - تسجيل الدخول")
        self.setFixedSize(900, 600)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        # Main layout: two columns (branding + form)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Right side (RTL = first) - Branding
        branding = self._build_branding_panel()
        main_layout.addWidget(branding, 1)

        # Left side - Login form
        form_panel = self._build_form_panel()
        main_layout.addWidget(form_panel, 1)

    def _build_branding_panel(self) -> QWidget:
        """لوحة العلامة التجارية (يمين الشاشة في RTL)."""
        panel = QFrame()
        panel.setObjectName("brandingPanel")
        panel.setStyleSheet("""
            #brandingPanel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0A1628, stop:1 #1E40AF);
            }
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(60, 60, 60, 60)
        layout.setSpacing(20)

        # Top spacer
        layout.addStretch(1)

        # Logo / Icon
        logo_label = QLabel("ERP")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setStyleSheet("""
            color: #10B981;
            font-size: 56px;
            font-weight: bold;
            letter-spacing: 8px;
        """)
        layout.addWidget(logo_label)

        # App name
        name_label = QLabel(settings.APP_NAME)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("color: white; font-size: 22px; font-weight: bold;")
        layout.addWidget(name_label)

        # Subtitle
        subtitle = QLabel("نظام محاسبي متكامل يعتمد القيد المزدوج")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #94A3B8; font-size: 13px;")
        layout.addWidget(subtitle)

        # Bottom spacer
        layout.addStretch(2)

        # Footer
        footer = QLabel(f"v{settings.APP_VERSION} © 2026")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #64748B; font-size: 11px;")
        layout.addWidget(footer)

        return panel

    def _build_form_panel(self) -> QWidget:
        """لوحة نموذج الدخول (يسار الشاشة في RTL)."""
        panel = QFrame()
        panel.setStyleSheet("background-color: #F8FAFC;")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(60, 60, 60, 60)
        layout.setSpacing(16)

        # Top spacer
        layout.addStretch(1)

        # Title
        title = QLabel("تسجيل الدخول")
        title.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        title.setStyleSheet("color: #0A1628; font-size: 28px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(title)

        # Subtitle
        subtitle = QLabel("مرحبًا بك! أدخل بياناتك للمتابعة")
        subtitle.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        subtitle.setStyleSheet("color: #64748B; font-size: 13px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(subtitle)

        layout.addSpacing(20)

        # Username field
        username_label = QLabel("اسم المستخدم")
        username_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        username_label.setStyleSheet("color: #0F172A; font-size: 13px; font-weight: bold;")
        layout.addWidget(username_label)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("أدخل اسم المستخدم")
        self.username_input.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.username_input.setMinimumHeight(44)
        self.username_input.returnPressed.connect(self._on_login_clicked)
        layout.addWidget(self.username_input)

        # Password field
        password_label = QLabel("كلمة المرور")
        password_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        password_label.setStyleSheet("color: #0F172A; font-size: 13px; font-weight: bold;")
        layout.addWidget(password_label)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("أدخل كلمة المرور")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.password_input.setMinimumHeight(44)
        self.password_input.returnPressed.connect(self._on_login_clicked)
        layout.addWidget(self.password_input)

        # Remember me + forgot password
        options_layout = QHBoxLayout()
        options_layout.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self.remember_checkbox = QCheckBox("تذكرني")
        self.remember_checkbox.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        options_layout.addWidget(self.remember_checkbox)

        options_layout.addStretch()

        forgot_button = QPushButton("نسيت كلمة المرور؟")
        forgot_button.setStyleSheet(
            "border: none; color: #2563EB; background: transparent; font-size: 12px;"
        )
        forgot_button.setCursor(Qt.CursorShape.PointingHandCursor)
        options_layout.addWidget(forgot_button)
        layout.addLayout(options_layout)

        layout.addSpacing(10)

        # Login button
        self.login_button = QPushButton("تسجيل الدخول")
        self.login_button.setMinimumHeight(48)
        self.login_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_button.clicked.connect(self._on_login_clicked)
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
            QPushButton:pressed {
                background-color: #1E40AF;
            }
            QPushButton:disabled {
                background-color: #94A3B8;
            }
        """)
        layout.addWidget(self.login_button)

        # Exit button
        exit_button = QPushButton("خروج")
        exit_button.setMinimumHeight(40)
        exit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        exit_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #64748B;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #F1F5F9;
                color: #0F172A;
            }
        """)
        exit_button.clicked.connect(self.close)
        layout.addWidget(exit_button)

        # Status label (for errors)
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #EF4444; font-size: 12px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.status_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout.addWidget(self.status_label)

        # Bottom spacer
        layout.addStretch(2)

        return panel

    def _apply_styles(self) -> None:
        """Apply global styles to inputs."""
        input_style = """
            QLineEdit {
                padding: 10px 14px;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                background-color: white;
                font-size: 14px;
                color: #0F172A;
            }
            QLineEdit:focus {
                border: 2px solid #2563EB;
                padding: 9px 13px;
            }
            QCheckBox {
                color: #475569;
                font-size: 12px;
            }
        """
        self.setStyleSheet(input_style)

    def _on_login_clicked(self) -> None:
        """معالجة نقرة زر الدخول."""
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            self.status_label.setText("⚠ الرجاء إدخال اسم المستخدم وكلمة المرور")
            return

        # Disable button + show loading
        self.login_button.setEnabled(False)
        self.login_button.setText("جارٍ تسجيل الدخول...")
        self.status_label.setText("")

        # Run async login in background thread
        request = LoginRequest(username=username, password=password)
        self._worker = LoginWorker(self._login_use_case, request)
        self._worker.finished_signal.connect(self._on_login_success)
        self._worker.error_signal.connect(self._on_login_error)
        self._worker.start()

    def _on_login_success(self, response) -> None:
        """نجح تسجيل الدخول."""
        self.login_button.setEnabled(True)
        self.login_button.setText("تسجيل الدخول")
        self.login_successful.emit(response)

    def _on_login_error(self, error_msg: str) -> None:
        """فشل تسجيل الدخول."""
        self.login_button.setEnabled(True)
        self.login_button.setText("تسجيل الدخول")
        self.status_label.setText(f"⚠ {error_msg}")

        # Clear password field
        self.password_input.clear()
        self.password_input.setFocus()

    def closeEvent(self, event) -> None:
        """Clean up worker thread on close."""
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(1000)
        super().closeEvent(event)
