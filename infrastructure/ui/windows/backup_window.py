"""
Backup Window - شاشة النسخ الاحتياطي والاستعادة
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QDialog,
    QFormLayout, QDialogButtonBox, QComboBox, QDoubleSpinBox,
    QPlainTextEdit, QTabWidget, QGroupBox, QFrame, QFileDialog,
)

from infrastructure.ui.windows._async_worker import AsyncWorker
from infrastructure.services.backup_service import BackupService


class BackupWindow(QWidget):
    """شاشة النسخ الاحتياطي."""

    def __init__(self, current_user, parent=None) -> None:
        super().__init__(parent)
        self._current_user = current_user
        self._backup_service = BackupService()
        self._setup_ui()
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        # Apply Soft UI automatically
        try:
            from infrastructure.ui.theme.soft_auto import auto_apply_soft_ui
            auto_apply_soft_ui(self)
        except Exception:
            pass
        self._load_backups()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Top bar
        top_bar = QHBoxLayout()
        title = QLabel("💾 النسخ الاحتياطي")
        title.setStyleSheet("color: #2D3748; font-size: 20px; font-weight: bold;")
        top_bar.addWidget(title)

        top_bar.addStretch()

        self.create_button = QPushButton("📥 إنشاء نسخة احتياطية")
        self.create_button.setStyleSheet("""
            QPushButton {
                background-color: #68D391; color: #FFFFFF;
                padding: 8px 16px; border-radius: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #48BB78; }
        """)
        self.create_button.setToolTip("إنشاء نسخة احتياطية كاملة من قاعدة البيانات")
        self.create_button.clicked.connect(self._on_create_backup)
        top_bar.addWidget(self.create_button)

        self.restore_button = QPushButton("📤 استعادة نسخة")
        self.restore_button.setStyleSheet("""
            QPushButton {
                background-color: #F6AD55; color: #FFFFFF;
                padding: 8px 16px; border-radius: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #ED8936; }
            QPushButton:disabled { background-color: #A0AEC0; }
        """)
        self.restore_button.setToolTip("استعادة نسخة احتياطية (يستبدل البيانات الحالية)")
        self.restore_button.clicked.connect(self._on_restore_backup)
        self.restore_button.setEnabled(False)
        top_bar.addWidget(self.restore_button)

        layout.addLayout(top_bar)

        # Info card
        info_card = QFrame()
        info_card.setStyleSheet("""
            QFrame {
                background-color: #F6AD5515;
                border: 1px solid #FDE68A;
                border-radius: 14px;
                padding: 12px;
            }
        """)
        info_layout = QVBoxLayout(info_card)

        info_title = QLabel("⚠️ معلومات مهمة")
        info_title.setStyleSheet("color: #92400E; font-weight: bold; font-size: 14px;")
        info_title.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        info_layout.addWidget(info_title)

        info_text = QLabel(
            "• النسخة الاحتياطية تحفظ كل البيانات في ملف مضغوط (.zip)\n"
            "• الاستعادة تستبدل البيانات الحالية بالكامل\n"
            "• يُنصح بإنشاء نسخة احتياطية قبل أي عملية استعادة\n"
            "• يُنصح بجدولة نسخ يومية تلقائية"
        )
        info_text.setStyleSheet("color: #92400E; font-size: 12px;")
        info_text.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        info_layout.addWidget(info_text)

        layout.addWidget(info_card)

        # Backups table
        table_label = QLabel("النسخ الاحتياطية المتاحة:")
        table_label.setStyleSheet("color: #2D3748; font-weight: bold;")
        layout.addWidget(table_label)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "اسم الملف", "التاريخ", "بواسطة", "الحجم", "الوصف",
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF; alternate-background-color: #F0F4F8;
                border: 1px solid #E4EBF5; border-radius: 12px;
                gridline-color: #E4EBF5;
            }
            QHeaderView::section {
                background-color: #2D3748; color: #FFFFFF;
                padding: 8px; border: none; font-weight: bold;
            }
        """)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.table)

        # Action buttons
        actions = QHBoxLayout()

        self.delete_button = QPushButton("🗑️ حذف نسخة")
        self.delete_button.setStyleSheet("""
            QPushButton {
                background-color: #FC8181; color: #FFFFFF;
                padding: 8px 16px; border-radius: 12px;
            }
            QPushButton:hover { background-color: #E53E3E; }
            QPushButton:disabled { background-color: #A0AEC0; }
        """)
        self.delete_button.setToolTip("حذف النسخة الاحتياطية المحددة")
        self.delete_button.clicked.connect(self._on_delete_backup)
        self.delete_button.setEnabled(False)
        actions.addWidget(self.delete_button)

        actions.addStretch()

        self.refresh_button = QPushButton("🔄 تحديث")
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #E4EBF5; color: #2D3748;
                padding: 8px 16px; border-radius: 12px; border: 1px solid #C3CAD7;
            }
            QPushButton:hover { background-color: #E4EBF5; }
        """)
        self.refresh_button.clicked.connect(self._load_backups)
        actions.addWidget(self.refresh_button)

        layout.addLayout(actions)

        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #A0AEC0; font-size: 11px;")
        layout.addWidget(self.status_label)

    def _load_backups(self) -> None:
        """تحميل قائمة النسخ الاحتياطية."""
        self.status_label.setText("جارٍ التحميل...")

        try:
            backups = self._backup_service.list_backups()
            self.table.setRowCount(len(backups))
            for i, b in enumerate(backups):
                self.table.setItem(i, 0, QTableWidgetItem(b.get("file_name", "—")))
                ts = b.get("backup_timestamp", "")
                self.table.setItem(i, 1, QTableWidgetItem(ts))
                self.table.setItem(i, 2, QTableWidgetItem(b.get("created_by", "—")))
                size_kb = b.get("file_size", 0) // 1024
                size_item = QTableWidgetItem(f"{size_kb} KB")
                size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(i, 3, size_item)
                self.table.setItem(i, 4, QTableWidgetItem(b.get("description", "—")))
            self.status_label.setText(f"إجمالي النسخ: {len(backups)}")
        except Exception as e:
            self.status_label.setText(f"⚠ خطأ: {e}")

    def _on_selection_changed(self) -> None:
        has_selection = self.table.currentRow() >= 0
        self.restore_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)

    def _on_create_backup(self) -> None:
        """إنشاء نسخة احتياطية جديدة."""
        from PySide6.QtWidgets import QInputDialog

        description, ok = QInputDialog.getText(
            self, "وصف النسخة",
            "أدخل وصفًا للنسخة الاحتياطية (اختياري):",
        )
        if not ok:
            return

        try:
            path = self._backup_service.create_backup(
                description=description or "manual backup",
                created_by=self._current_user.username,
            )
            QMessageBox.information(
                self, "نجاح",
                f"تم إنشاء النسخة الاحتياطية:\n{path}"
            )
            self._load_backups()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل إنشاء النسخة: {e}")

    def _on_restore_backup(self) -> None:
        """استعادة نسخة احتياطية."""
        row = self.table.currentRow()
        if row < 0:
            return

        file_name = self.table.item(row, 0).text()

        reply = QMessageBox.warning(
            self, "⚠️ تأكيد الاستعادة",
            f"هل أنت متأكد من استعادة النسخة '{file_name}'؟\n\n"
            "⚠️ هذا سيستبدل كل البيانات الحالية!\n"
            "⚠️ سيتم إنشاء نسخة احتياطية للبيانات الحالية أولًا.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            backup_path = self._backup_service.backup_dir / file_name
            result = self._backup_service.restore_backup(backup_path, confirm=True)
            if result:
                QMessageBox.information(
                    self, "نجاح",
                    "تمت الاستعادة بنجاح.\nأعد تشغيل التطبيق لتحديث البيانات."
                )
                self._load_backups()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل الاستعادة: {e}")

    def _on_delete_backup(self) -> None:
        """حذف نسخة احتياطية."""
        row = self.table.currentRow()
        if row < 0:
            return

        file_name = self.table.item(row, 0).text()

        reply = QMessageBox.question(
            self, "تأكيد الحذف",
            f"هل تريد حذف النسخة '{file_name}'؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            backup_path = self._backup_service.backup_dir / file_name
            result = self._backup_service.delete_backup(backup_path)
            if result:
                QMessageBox.information(self, "نجاح", "تم حذف النسخة")
                self._load_backups()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل الحذف: {e}")
