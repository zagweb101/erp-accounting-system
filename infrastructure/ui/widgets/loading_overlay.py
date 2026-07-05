"""
Loading Spinner Helper - مساعد حالة التحميل

يوفّر مؤشرات تحميل للعمليات الطويلة في الواجهة.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QProgressBar, QLabel, QVBoxLayout, QDialog, QPushButton,
)

try:
    import qtawesome as qta
except ImportError:
    qta = None


class LoadingOverlay(QDialog):
    """نافذة تحميل عائمة - تُعرض أثناء العمليات الطويلة.

    Usage:
        overlay = LoadingOverlay("جارٍ حفظ الفاتورة...", parent=self)
        overlay.show()
        # ... do work ...
        overlay.close()
    """

    def __init__(
        self,
        message: str = "جارٍ التحميل...",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._setup_ui(message)
        self._timer: Optional[QTimer] = None
        self._progress = 0

    def _setup_ui(self, message: str) -> None:
        """إعداد الواجهة."""
        self.setWindowTitle("جارٍ المعالجة")
        self.setFixedSize(300, 120)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog
        )
        self.setModal(True)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Message
        self.message_label = QLabel(message)
        self.message_label.setStyleSheet(
            "color: #0F172A; font-size: 14px; font-weight: bold;"
        )
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout.addWidget(self.message_label)

        # Progress bar (indeterminate)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate mode
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                background-color: #F1F5F9;
                height: 8px;
            }
            QProgressBar::chunk {
                background-color: #2563EB;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Stylesheet for dialog
        self.setStyleSheet("""
            QDialog {
                background-color: white;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
        """)

    def update_message(self, message: str) -> None:
        """تحديث رسالة التحميل."""
        self.message_label.setText(message)

    def start(self) -> None:
        """بدء عرض التحميل."""
        self.show()
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

    def stop(self) -> None:
        """إيقاف عرض التحميل."""
        self.close()


def show_loading(message: str, parent: Optional[QWidget] = None) -> LoadingOverlay:
    """Helper سريع لعرض نافذة تحميل.

    Usage:
        overlay = show_loading("جارٍ الحفظ...", self)
        try:
            # ... long operation ...
            pass
        finally:
            overlay.stop()
    """
    overlay = LoadingOverlay(message=message, parent=parent)
    overlay.start()
    return overlay
