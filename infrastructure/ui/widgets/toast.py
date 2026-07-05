"""
Toast Notification System - نظام الإشعارات المنبثقة

يعرض إشعارات ناعمة (Soft UI) تختفي تلقائيًا.

Usage:
    from infrastructure.ui.widgets.toast import Toast

    Toast.success(parent, "تم حفظ الفاتورة بنجاح!")
    Toast.error(parent, "فشل الاتصال بقاعدة البيانات")
    Toast.info(parent, "جارٍ تحميل البيانات...")
    Toast.warning(parent, "مخزون منخفض")
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QRect
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QFrame, QApplication, QSizePolicy,
)

from infrastructure.ui.theme.soft_ui import SoftColors


class Toast(QFrame):
    """إشعار منبثق ناعم (Toast Notification).

    Features:
    - ظهور وانطفاء تدريجي (fade in/out)
    - 4 أنواع: success, error, info, warning
    - يختفي تلقائيًا بعد مدة محددة
    - زوايا دائرية + ظل ناعم
    """

    DURATION = 4000  # milliseconds

    # Colors per type
    TYPE_COLORS = {
        "success": (SoftColors.ACCENT_GREEN, "✅"),
        "error": (SoftColors.ACCENT_RED, "❌"),
        "info": (SoftColors.ACCENT_BLUE, "ℹ️"),
        "warning": (SoftColors.ACCENT_ORANGE, "⚠️"),
    }

    def __init__(
        self,
        message: str,
        toast_type: str = "info",
        parent: Optional[QWidget] = None,
        duration: int = None,
    ) -> None:
        super().__init__(parent if parent else QApplication.activeWindow())
        self._toast_type = toast_type
        self._duration = duration or self.DURATION
        self._setup_ui(message)
        self._setup_animation()
        self._auto_hide()

    def _setup_ui(self, message: str) -> None:
        """إعداد واجهة الإشعار."""
        color, icon = self.TYPE_COLORS.get(self._toast_type, self.TYPE_COLORS["info"])

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self.setFixedWidth(400)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {SoftColors.SURFACE_LIGHT};
                border: none;
                border-right: 4px solid {color};
                border-radius: 16px;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(12)

        # Icon
        icon_label = QLabel(icon)
        icon_label.setFixedSize(36, 36)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet(f"""
            QLabel {{
                background-color: {color}25;
                border-radius: 18px;
                font-size: 18px;
            }}
        """)
        layout.addWidget(icon_label)

        # Message
        msg_label = QLabel(message)
        msg_label.setStyleSheet(f"color: {SoftColors.TEXT_PRIMARY}; font-size: 14px; background: transparent;")
        msg_label.setWordWrap(True)
        msg_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout.addWidget(msg_label, 1)

        # Close button
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {SoftColors.BG_SECONDARY};
                color: {SoftColors.TEXT_MUTED};
                border: none;
                border-radius: 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {SoftColors.SURFACE_DARK};
                color: {SoftColors.TEXT_PRIMARY};
            }}
        """)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

    def _setup_animation(self) -> None:
        """إعداد أنيميشن الظهور."""
        # Fade in animation
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(300)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _auto_hide(self) -> None:
        """إخفاء تلقائي بعد المدة المحددة."""
        QTimer.singleShot(self._duration, self._fade_out)

    def _fade_out(self) -> None:
        """أنيميشن الاختفاء."""
        self._fade_anim.setDuration(300)
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.finished.connect(self.close)
        self._fade_anim.start()

    def show_at(self, x: int, y: int) -> None:
        """عرض الإشعار في موضع محدد."""
        self.move(x, y)
        self.show()
        self._fade_anim.start()

    @classmethod
    def success(cls, parent: QWidget, message: str, duration: int = None) -> "Toast":
        """إشعار نجاح أخضر."""
        return cls._show(parent, message, "success", duration)

    @classmethod
    def error(cls, parent: QWidget, message: str, duration: int = None) -> "Toast":
        """إشعار خطأ أحمر."""
        return cls._show(parent, message, "error", duration or 6000)

    @classmethod
    def info(cls, parent: QWidget, message: str, duration: int = None) -> "Toast":
        """إشعار معلومات أزرق."""
        return cls._show(parent, message, "info", duration)

    @classmethod
    def warning(cls, parent: QWidget, message: str, duration: int = None) -> "Toast":
        """إشعار تحذير برتقالي."""
        return cls._show(parent, message, "warning", duration or 5000)

    @classmethod
    def _show(
        cls, parent: QWidget, message: str, toast_type: str, duration: int = None,
    ) -> "Toast":
        """عرض الإشعار في أعلى يمين النافذة."""
        toast = cls(message, toast_type, parent, duration)

        # Position at top-right of parent (RTL = right side)
        if parent:
            parent_rect = parent.rect()
            x = parent_rect.right() - toast.width() - 20
            y = parent_rect.top() + 20
        else:
            screen = QApplication.primaryScreen().geometry()
            x = screen.right() - toast.width() - 20
            y = screen.top() + 20

        toast.show_at(x, y)
        return toast
