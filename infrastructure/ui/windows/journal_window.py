"""
Journal Window - شاشة القيود المحاسبية

عرض القيود + إنشاء قيد يدوي + ترحيل + قلب.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QDialog,
    QFormLayout, QDialogButtonBox, QComboBox, QDoubleSpinBox,
    QPlainTextEdit, QDateEdit, QGroupBox, QFrame,
)

from infrastructure.ui.windows._async_worker import AsyncWorker


class JournalWindow(QWidget):
    """شاشة عرض القيود المحاسبية."""

    def __init__(self, current_user, journal_repo, account_repo, parent=None) -> None:
        super().__init__(parent)
        self._current_user = current_user
        self._journal_repo = journal_repo
        self._account_repo = account_repo
        self._worker: Optional[AsyncWorker] = None
        self._setup_ui()
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        # Apply Soft UI automatically
        try:
            from infrastructure.ui.theme.soft_auto import auto_apply_soft_ui
            auto_apply_soft_ui(self)
        except Exception:
            pass
        self._load_entries()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Top bar
        top_bar = QHBoxLayout()
        title = QLabel("📖 القيود المحاسبية")
        title.setStyleSheet("color: #2D3748; font-size: 20px; font-weight: bold;")
        top_bar.addWidget(title)

        top_bar.addStretch()

        self.new_button = QPushButton("➕ قيد يدوي جديد")
        self.new_button.setStyleSheet("""
            QPushButton {
                background-color: #68D391; color: #FFFFFF;
                padding: 8px 16px; border-radius: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #48BB78; }
        """)
        self.new_button.setToolTip("إنشاء قيد محاسبي يدوي")
        self.new_button.clicked.connect(self._on_new_clicked)
        top_bar.addWidget(self.new_button)

        layout.addLayout(top_bar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "رقم القيد", "التاريخ", "الوصف", "المدين", "الدائن", "الحالة",
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
        layout.addWidget(self.table)

        # Action buttons
        actions = QHBoxLayout()

        self.view_button = QPushButton("👁️ عرض التفاصيل")
        self.view_button.setStyleSheet("""
            QPushButton {
                background-color: #6B8AFE; color: #FFFFFF;
                padding: 8px 16px; border-radius: 12px;
            }
            QPushButton:hover { background-color: #5A7AED; }
            QPushButton:disabled { background-color: #A0AEC0; }
        """)
        self.view_button.setToolTip("عرض تفاصيل القيد المحدد")
        self.view_button.clicked.connect(self._on_view_clicked)
        self.view_button.setEnabled(False)
        actions.addWidget(self.view_button)

        self.reverse_button = QPushButton("↩️ قلب القيد")
        self.reverse_button.setStyleSheet("""
            QPushButton {
                background-color: #F6AD55; color: #FFFFFF;
                padding: 8px 16px; border-radius: 12px;
            }
            QPushButton:hover { background-color: #ED8936; }
            QPushButton:disabled { background-color: #A0AEC0; }
        """)
        self.reverse_button.setToolTip("قلب القيد المحدد (إنشاء قيد عكسي)")
        self.reverse_button.clicked.connect(self._on_reverse_clicked)
        self.reverse_button.setEnabled(False)
        actions.addWidget(self.reverse_button)

        actions.addStretch()

        self.refresh_button = QPushButton("🔄 تحديث")
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #E4EBF5; color: #2D3748;
                padding: 8px 16px; border-radius: 12px; border: 1px solid #C3CAD7;
            }
            QPushButton:hover { background-color: #E4EBF5; }
        """)
        self.refresh_button.clicked.connect(self._load_entries)
        actions.addWidget(self.refresh_button)

        layout.addLayout(actions)

        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #A0AEC0; font-size: 11px;")
        layout.addWidget(self.status_label)

    def _load_entries(self) -> None:
        self.status_label.setText("جارٍ التحميل...")

        async def _load():
            from datetime import timedelta
            end = datetime.now()
            start = end - timedelta(days=90)
            return await self._journal_repo.list_by_date_range(start, end, skip=0, limit=500)

        self._worker = AsyncWorker(_load)
        self._worker.finished_signal.connect(self._on_entries_loaded)
        self._worker.error_signal.connect(self._on_error)
        self._worker.start()

    def _on_entries_loaded(self, entries: list) -> None:
        self.table.setRowCount(len(entries))
        for i, e in enumerate(entries):
            self.table.setItem(i, 0, QTableWidgetItem(e.entry_no))
            self.table.setItem(i, 1, QTableWidgetItem(e.date.strftime("%Y-%m-%d")))
            self.table.setItem(i, 2, QTableWidgetItem(e.description[:80] + "..." if len(e.description) > 80 else e.description))
            dr_item = QTableWidgetItem(f"{e.total_debit():,.2f}")
            dr_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 3, dr_item)
            cr_item = QTableWidgetItem(f"{e.total_credit():,.2f}")
            cr_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 4, cr_item)
            status_text = {
                "DRAFT": "📝 مسودة",
                "POSTED": "✓ مرحّل",
                "REVERSED": "↩️ مقلوب",
            }.get(e.status.value, e.status.value)
            status_item = QTableWidgetItem(status_text)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 5, status_item)

        self.status_label.setText(f"إجمالي القيود: {len(entries)}")
        self.view_button.setEnabled(False)
        self.reverse_button.setEnabled(False)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)

    def _on_selection_changed(self) -> None:
        has_selection = self.table.currentRow() >= 0
        self.view_button.setEnabled(has_selection)
        self.reverse_button.setEnabled(has_selection)

    def _on_new_clicked(self) -> None:
        """إنشاء قيد يدوي."""
        dialog = ManualJournalDialog(self, self._account_repo)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            self._create_manual_entry(data)

    def _create_manual_entry(self, data: dict) -> None:
        from use_cases.journal.journal_use_cases import (
            CreateJournalEntryUseCase, CreateJournalEntryRequest, JournalLineDTO,
        )
        from domain.entities.journal import JournalEntryReferenceType

        async def _create():
            uc = CreateJournalEntryUseCase(self._journal_repo, self._account_repo)
            req = CreateJournalEntryRequest(
                description=data["description"],
                reference_type=JournalEntryReferenceType.MANUAL,
                lines=[
                    JournalLineDTO(
                        account_code=l["account_code"],
                        debit=l["debit"],
                        credit=l["credit"],
                        description=l["description"],
                    )
                    for l in data["lines"]
                ],
            )
            entry = await uc.execute(req, self._current_user.id)
            # Auto-post
            from use_cases.journal.journal_use_cases import PostJournalEntryUseCase
            post_uc = PostJournalEntryUseCase(self._journal_repo)
            return await post_uc.execute(entry.id, self._current_user.id)

        self._worker = AsyncWorker(_create)
        self._worker.finished_signal.connect(lambda e: (
            QMessageBox.information(self, "نجاح", f"تم إنشاء وترحيل القيد: {e.entry_no}"),
            self._load_entries(),
        ))
        self._worker.error_signal.connect(lambda err: QMessageBox.critical(self, "خطأ", err))
        self._worker.start()

    def _on_view_clicked(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        entry_no = self.table.item(row, 0).text()

        async def _get():
            return await self._journal_repo.get_by_no(entry_no)

        def _show(entry):
            if entry is None:
                QMessageBox.warning(self, "تنبيه", "القيد غير موجود")
                return
            msg = (
                f"رقم القيد: {entry.entry_no}\n"
                f"التاريخ: {entry.date.strftime('%Y-%m-%d %H:%M')}\n"
                f"الوصف: {entry.description}\n"
                f"الحالة: {entry.status.value}\n\n"
                f"البنود:\n"
            )
            for i, line in enumerate(entry.lines, 1):
                msg += (
                    f"  {i}. حساب: {line.account_id}\n"
                    f"     مدين: {line.debit:,.2f} | دائن: {line.credit:,.2f}\n"
                    f"     {line.description}\n"
                )
            msg += (
                f"\nالإجمالي:\n"
                f"  مدين: {entry.total_debit():,.2f}\n"
                f"  دائن: {entry.total_credit():,.2f}\n"
                f"  متوازن: {'✓' if entry.is_balanced() else '✗'}"
            )
            QMessageBox.information(self, f"تفاصيل القيد {entry_no}", msg)

        self._worker = AsyncWorker(_get)
        self._worker.finished_signal.connect(_show)
        self._worker.error_signal.connect(lambda e: QMessageBox.critical(self, "خطأ", e))
        self._worker.start()

    def _on_reverse_clicked(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        entry_no = self.table.item(row, 0).text()

        reply = QMessageBox.question(
            self, "تأكيد القلب",
            f"هل تريد قلب القيد '{entry_no}'؟\nسيتم إنشاء قيد عكسي.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        from use_cases.journal.journal_use_cases import ReverseJournalEntryUseCase

        async def _reverse():
            entry = await self._journal_repo.get_by_no(entry_no)
            if entry is None:
                return None
            uc = ReverseJournalEntryUseCase(self._journal_repo)
            return await uc.execute(entry.id, self._current_user.id)

        self._worker = AsyncWorker(_reverse)
        self._worker.finished_signal.connect(lambda e: (
            QMessageBox.information(self, "نجاح", f"تم قلب القيد. القيد العكسي: {e.entry_no if e else ''}"),
            self._load_entries(),
        ))
        self._worker.error_signal.connect(lambda e: QMessageBox.critical(self, "خطأ", e))
        self._worker.start()

    def _on_error(self, error_msg: str) -> None:
        self.status_label.setText(f"⚠ خطأ: {error_msg}")


class ManualJournalDialog(QDialog):
    """نافذة إنشاء قيد يدوي."""

    def __init__(self, parent=None, account_repo=None) -> None:
        super().__init__(parent)
        self._account_repo = account_repo
        self._setup_ui()
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

    def _setup_ui(self) -> None:
        self.setWindowTitle("قيد محاسبي يدوي")
        self.resize(800, 600)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Description
        desc_layout = QFormLayout()
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("وصف القيد...")
        self.desc_input.setAccessibleName("وصف القيد")
        desc_layout.addRow("الوصف:", self.desc_input)
        layout.addLayout(desc_layout)

        # Lines table
        lines_label = QLabel("بنود القيد (مدين = دائن):")
        lines_label.setStyleSheet("color: #2D3748; font-weight: bold;")
        layout.addWidget(lines_label)

        self.lines_table = QTableWidget()
        self.lines_table.setColumnCount(4)
        self.lines_table.setHorizontalHeaderLabels([
            "كود الحساب", "مدين", "دائن", "الوصف",
        ])
        self.lines_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.lines_table.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
                border: 1px solid #E4EBF5; border-radius: 12px;
            }
            QHeaderView::section {
                background-color: #2D3748; color: #FFFFFF;
                padding: 6px; border: none; font-weight: bold;
            }
        """)
        layout.addWidget(self.lines_table)

        # Add/Remove line buttons
        line_buttons = QHBoxLayout()

        add_line_btn = QPushButton("➕ إضافة بند")
        add_line_btn.setStyleSheet("background-color: #68D391; color: #FFFFFF; padding: 6px;")
        add_line_btn.clicked.connect(self._add_line)
        line_buttons.addWidget(add_line_btn)

        remove_line_btn = QPushButton("➖ حذف بند")
        remove_line_btn.setStyleSheet("background-color: #FC8181; color: #FFFFFF; padding: 6px;")
        remove_line_btn.clicked.connect(self._remove_line)
        line_buttons.addWidget(remove_line_btn)

        line_buttons.addStretch()
        layout.addLayout(line_buttons)

        # Totals
        self.totals_label = QLabel("المدين: 0.00 | الدائن: 0.00 | الفرق: 0.00")
        self.totals_label.setStyleSheet("color: #6B8AFE; font-size: 14px; font-weight: bold;")
        self.totals_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.totals_label)

        self.lines_table.cellChanged.connect(self._update_totals)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("حفظ وترحيل")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("إلغاء")
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Add 2 default lines
        self._add_line()
        self._add_line()

    def _add_line(self) -> None:
        row = self.lines_table.rowCount()
        self.lines_table.insertRow(row)
        self.lines_table.setItem(row, 0, QTableWidgetItem(""))
        self.lines_table.setItem(row, 1, QTableWidgetItem("0.00"))
        self.lines_table.setItem(row, 2, QTableWidgetItem("0.00"))
        self.lines_table.setItem(row, 3, QTableWidgetItem(""))

    def _remove_line(self) -> None:
        row = self.lines_table.currentRow()
        if row >= 0 and self.lines_table.rowCount() > 2:
            self.lines_table.removeRow(row)
            self._update_totals()

    def _update_totals(self) -> None:
        total_debit = Decimal("0")
        total_credit = Decimal("0")
        for r in range(self.lines_table.rowCount()):
            try:
                d = Decimal(self.lines_table.item(r, 1).text() or "0")
                c = Decimal(self.lines_table.item(r, 2).text() or "0")
                total_debit += d
                total_credit += c
            except Exception:
                continue
        diff = total_debit - total_credit
        color = "#68D391" if diff == 0 else "#FC8181"
        self.totals_label.setText(
            f"المدين: {total_debit:,.2f} | الدائن: {total_credit:,.2f} | الفرق: {diff:,.2f}"
        )
        self.totals_label.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")

    def _validate_and_accept(self) -> None:
        data = self.get_data()
        if not data["description"]:
            QMessageBox.warning(self, "تنبيه", "الرجاء إدخال وصف للقيد")
            return
        if len(data["lines"]) < 2:
            QMessageBox.warning(self, "تنبيه", "القيد يحتاج على الأقل لبندين")
            return
        total_debit = sum(Decimal(str(l["debit"])) for l in data["lines"])
        total_credit = sum(Decimal(str(l["credit"])) for l in data["lines"])
        if total_debit != total_credit:
            QMessageBox.warning(
                self, "قيد غير متوازن",
                f"المدين ({total_debit}) ≠ الدائن ({total_credit})\nالفرق: {total_debit - total_credit}"
            )
            return
        self.accept()

    def get_data(self) -> dict:
        lines = []
        for r in range(self.lines_table.rowCount()):
            account_code = self.lines_table.item(r, 0).text().strip() if self.lines_table.item(r, 0) else ""
            if not account_code:
                continue
            lines.append({
                "account_code": account_code,
                "debit": self.lines_table.item(r, 1).text() or "0",
                "credit": self.lines_table.item(r, 2).text() or "0",
                "description": self.lines_table.item(r, 3).text() if self.lines_table.item(r, 3) else "",
            })
        return {
            "description": self.desc_input.text().strip(),
            "lines": lines,
        }
