"""
Login Window v2 — Soft UI Design

Claymorphism + Soft UI + Organic UI
"""
from __future__ import annotations

import asyncio
import sys
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import QFont, QPixmap, QColor
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QFrame, QCheckBox,
    QSizePolicy,
)

from infrastructure.ui.theme.soft_ui import SoftColors, add_soft_shadow
from infrastructure.ui.widgets.soft_components import SoftCard
from domain.entities.user import User
from domain.exceptions.exceptions import (
    AccountLockedException, InvalidCredentialsException, ValidationException,
)
from infrastructure.config.settings import get_settings
from use_cases.auth.auth_use_cases import LoginRequest, LoginUseCase


class LoginWorker(QThread):
    finished_signal = Signal(object)
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
    """نافذة تسجيل الدخول بتصميم Soft UI."""

    login_successful = Signal(object)

    def __init__(self, login_use_case: LoginUseCase) -> None:
        super().__init__()
        self._login_use_case = login_use_case
        self._worker: Optional[LoginWorker] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        settings = get_settings()
        self.setWindowTitle(f"{settings.APP_NAME} - تسجيل الدخول")
        self.setFixedSize(1000, 650)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Right side (RTL) — Branding with gradient
        branding = self._build_branding_panel()
        main_layout.addWidget(branding, 1)

        # Left side — Login form with Soft UI
        form_panel = self._build_form_panel()
        main_layout.addWidget(form_panel, 1)

    def _build_branding_panel(self) -> QWidget:
        """لوحة العلامة التجارية بتدرج لوني عضوي (Organic UI)."""
        panel = QFrame()
        panel.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {SoftColors.ACCENT_BLUE_DARK},
                    stop:0.5 {SoftColors.ACCENT_BLUE},
                    stop:1 {SoftColors.ACCENT_PURPLE});
                border: none;
            }}
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(60, 60, 60, 60)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Logo
        logo = QLabel("📊")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet("font-size: 80px; background: transparent;")
        layout.addWidget(logo)

        # App name
        name = QLabel("ERP Accounting")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setStyleSheet("""
            color: white; font-size: 32px; font-weight: 800;
            background: transparent; letter-spacing: 2px;
        """)
        layout.addWidget(name)

        # Subtitle
        subtitle = QLabel("نظام محاسبي متكامل يعتمد القيد المزدوج")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        subtitle.setStyleSheet("""
            color: rgba(255,255,255,0.85); font-size: 15px;
            background: transparent;
        """)
        layout.addWidget(subtitle)

        layout.addSpacing(20)

        # Features list
        features = [
            "🤖 مساعد ذكاء اصطناعي",
            "📊 تقارير مالية احترافية",
            "🔒 أمان متعدد الطبقات",
            "💾 نسخ احتياطي تلقائي",
        ]
        for feat in features:
            label = QLabel(feat)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            label.setStyleSheet("""
                color: rgba(255,255,255,0.9); font-size: 14px;
                background: transparent; padding: 4px;
            """)
            layout.addWidget(label)

        layout.addStretch()

        # Footer
        footer = QLabel(f"v{get_settings().APP_VERSION} © 2026")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 11px; background: transparent;")
        layout.addWidget(footer)

        return panel

    def _build_form_panel(self) -> QWidget:
        """لوحة نموذج الدخول بتصميم Soft UI."""
        panel = QFrame()
        panel.setStyleSheet(f"background-color: {SoftColors.BG_PRIMARY};")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(60, 60, 60, 60)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Title
        title = QLabel("تسجيل الدخول")
        title.setObjectName("title")
        title.setStyleSheet(f"color: {SoftColors.TEXT_PRIMARY}; font-size: 28px; font-weight: 800;")
        title.setAlignment(Qt.AlignmentFlag.AlignRight)
        title.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout.addWidget(title)

        subtitle = QLabel("مرحبًا بك! أدخل بياناتك للمتابعة")
        subtitle.setStyleSheet(f"color: {SoftColors.TEXT_SECONDARY}; font-size: 14px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignRight)
        subtitle.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout.addWidget(subtitle)

        layout.addSpacing(20)

        # Username
        user_label = QLabel("اسم المستخدم")
        user_label.setStyleSheet(f"color: {SoftColors.TEXT_PRIMARY}; font-size: 13px; font-weight: 600;")
        user_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout.addWidget(user_label)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("أدخل اسم المستخدم")
        self.username_input.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.username_input.setMinimumHeight(50)
        self.username_input.returnPressed.connect(self._on_login_clicked)
        self.username_input.setAccessibleName("اسم المستخدم")
        self.username_input.setToolTip("أدخل اسم المستخدم الخاص بك")
        layout.addWidget(self.username_input)

        # Password
        pass_label = QLabel("كلمة المرور")
        pass_label.setStyleSheet(f"color: {SoftColors.TEXT_PRIMARY}; font-size: 13px; font-weight: 600;")
        pass_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout.addWidget(pass_label)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("أدخل كلمة المرور")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.password_input.setMinimumHeight(50)
        self.password_input.returnPressed.connect(self._on_login_clicked)
        self.password_input.setAccessibleName("كلمة المرور")
        self.password_input.setToolTip("أدخل كلمة المرور الخاصة بك")
        layout.addWidget(self.password_input)

        # Remember + Forgot
        options = QHBoxLayout()
        options.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self.remember_checkbox = QCheckBox("تذكرني")
        self.remember_checkbox.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        options.addWidget(self.remember_checkbox)
        options.addStretch()

        forgot = QPushButton("نسيت كلمة المرور؟")
        forgot.setStyleSheet(f"border: none; color: {SoftColors.ACCENT_BLUE}; background: transparent; font-size: 12px;")
        forgot.setCursor(Qt.CursorShape.PointingHandCursor)
        options.addWidget(forgot)
        layout.addLayout(options)

        layout.addSpacing(10)

        # Login button (primary — soft blue)
        self.login_button = QPushButton("تسجيل الدخول")
        self.login_button.setObjectName("primary")
        self.login_button.setMinimumHeight(52)
        self.login_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_button.clicked.connect(self._on_login_clicked)
        self.login_button.setAccessibleName("زر تسجيل الدخول")
        layout.addWidget(self.login_button)

        # Exit button
        exit_btn = QPushButton("خروج")
        exit_btn.setMinimumHeight(44)
        exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        exit_btn.clicked.connect(self.close)
        layout.addWidget(exit_btn)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {SoftColors.ACCENT_RED_DARK}; font-size: 12px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.status_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout.addWidget(self.status_label)

        layout.addStretch()

        return panel

    def _on_login_clicked(self) -> None:
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            self.status_label.setText("⚠ الرجاء إدخال اسم المستخدم وكلمة المرور")
            return

        self.login_button.setEnabled(False)
        self.login_button.setText("جارٍ تسجيل الدخول...")
        self.status_label.setText("")

        request = LoginRequest(username=username, password=password)
        self._worker = LoginWorker(self._login_use_case, request)
        self._worker.finished_signal.connect(self._on_login_success)
        self._worker.error_signal.connect(self._on_login_error)
        self._worker.start()

    def _on_login_success(self, response) -> None:
        self.login_button.setEnabled(True)
        self.login_button.setText("تسجيل الدخول")
        self.login_successful.emit(response)

    def _on_login_error(self, error_msg: str) -> None:
        self.login_button.setEnabled(True)
        self.login_button.setText("تسجيل الدخول")
        self.status_label.setText(f"⚠ {error_msg}")
        self.password_input.clear()
        self.password_input.setFocus()

    def closeEvent(self, event) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(1000)
        super().closeEvent(event)
