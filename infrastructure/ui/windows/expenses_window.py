"""
Expenses & Revenues Window - شاشة المصروفات والإيرادات اليدوية
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional
from uuid import UUID

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QDialog,
    QFormLayout, QDialogButtonBox, QComboBox, QDoubleSpinBox,
    QPlainTextEdit, QTabWidget, QGroupBox, QFrame,
)

from infrastructure.ui.windows._async_worker import AsyncWorker


class ExpenseFormDialog(QDialog):
    """نموذج تسجيل مصروف/إيراد."""

    def __init__(self, parent=None, is_expense: bool = True, accounts: list = None) -> None:
        super().__init__(parent)
        self._is_expense = is_expense
        self._accounts = accounts or []
        self._setup_ui()
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        # Apply Soft UI automatically
        try:
            from infrastructure.ui.theme.soft_auto import auto_apply_soft_ui
            auto_apply_soft_ui(self)
        except Exception:
            pass

    def _setup_ui(self) -> None:
        title = "تسجيل مصروف" if self._is_expense else "تسجيل إيراد"
        self.setWindowTitle(title)
        self.setFixedSize(500, 500)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(8)

        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("وصف المصروف/الإيراد")
        self.desc_input.setAccessibleName("الوصف")
        form.addRow("الوصف *:", self.desc_input)

        # Account selector (expense or revenue account)
        account_label = "حساب المصروف:" if self._is_expense else "حساب الإيراد:"
        self.account_input = QComboBox()
        for acc in self._accounts:
            self.account_input.addItem(f"{acc[0]} - {acc[1]}", userData=acc[0])
        form.addRow(account_label, self.account_input)

        self.amount_input = QDoubleSpinBox()
        self.amount_input.setRange(0.01, 999999999)
        self.amount_input.setDecimals(2)
        self.amount_input.setSuffix(" ر.س")
        form.addRow("المبلغ *:", self.amount_input)

        # Payment account (cash or bank)
        self.payment_input = QComboBox()
        self.payment_input.addItem("1101 - الصندوق (نقدي)", userData="1101")
        self.payment_input.addItem("1102 - البنك (تحويل)", userData="1102")
        pay_label = "من حساب:" if self._is_expense else "إلى حساب:"
        form.addRow(pay_label, self.payment_input)

        self.reference_input = QLineEdit()
        self.reference_input.setPlaceholderText("رقم المستند (اختياري)")
        form.addRow("المرجع:", self.reference_input)

        layout.addLayout(form)

        # Notes
        notes_label = QLabel("ملاحظات:")
        layout.addWidget(notes_label)
        self.notes_input = QPlainTextEdit()
        self.notes_input.setMaximumHeight(60)
        layout.addWidget(self.notes_input)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("حفظ")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("إلغاء")
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet("""
            QDialog { background-color: #F0F4F8; }
            QLabel { color: #2D3748; font-size: 13px; }
            QLineEdit, QComboBox, QDoubleSpinBox {
                padding: 8px; border: 1px solid #C3CAD7;
                border-radius: 12px; background-color: #FFFFFF;
            }
        """)

    def _validate_and_accept(self) -> None:
        if not self.desc_input.text().strip():
            QMessageBox.warning(self, "تنبيه", "الرجاء إدخال الوصف")
            return
        if self.amount_input.value() <= 0:
            QMessageBox.warning(self, "تنبيه", "المبلغ يجب أن يكون أكبر من صفر")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "description": self.desc_input.text().strip(),
            "account_code": self.account_input.currentData(),
            "amount": Decimal(str(self.amount_input.value())),
            "payment_account_code": self.payment_input.currentData(),
            "reference": self.reference_input.text().strip(),
            "notes": self.notes_input.toPlainText().strip(),
        }


class ExpensesWindow(QWidget):
    """شاشة المصروفات والإيرادات."""

    def __init__(
        self, current_user, account_repo, journal_repo, parent=None
    ) -> None:
        super().__init__(parent)
        self._current_user = current_user
        self._account_repo = account_repo
        self._journal_repo = journal_repo
        self._worker: Optional[AsyncWorker] = None
        self._setup_ui()
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Top bar
        top_bar = QHBoxLayout()
        title = QLabel("💰 المصروفات والإيرادات")
        title.setStyleSheet("color: #2D3748; font-size: 20px; font-weight: bold;")
        top_bar.addWidget(title)

        top_bar.addStretch()

        self.expense_button = QPushButton("💸 مصروف جديد")
        self.expense_button.setStyleSheet("""
            QPushButton {
                background-color: #FC8181; color: #FFFFFF;
                padding: 8px 16px; border-radius: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #E53E3E; }
        """)
        self.expense_button.setToolTip("تسجيل مصروف جديد (كهرباء، إيجار، رواتب)")
        self.expense_button.clicked.connect(lambda: self._on_record_clicked(is_expense=True))
        top_bar.addWidget(self.expense_button)

        self.revenue_button = QPushButton("💵 إيراد جديد")
        self.revenue_button.setStyleSheet("""
            QPushButton {
                background-color: #68D391; color: #FFFFFF;
                padding: 8px 16px; border-radius: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #48BB78; }
        """)
        self.revenue_button.setToolTip("تسجيل إيراد غير تشغيلي (فوائد بنكية)")
        self.revenue_button.clicked.connect(lambda: self._on_record_clicked(is_expense=False))
        top_bar.addWidget(self.revenue_button)

        layout.addLayout(top_bar)

        # Info card
        info_card = QFrame()
        info_card.setStyleSheet("""
            QFrame {
                background-color: #A5B8FF;
                border: 1px solid #A5B8FF;
                border-radius: 14px;
                padding: 16px;
            }
        """)
        info_layout = QVBoxLayout(info_card)

        info_title = QLabel("💡 كيف يعمل؟")
        info_title.setStyleSheet("color: #5A7AED; font-weight: bold; font-size: 14px;")
        info_title.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        info_layout.addWidget(info_title)

        info_text = QLabel(
            "• المصروف: من ح/ المصروف (مدين) → إلى ح/ الصندوق أو البنك (دائن)\n"
            "• الإيراد: من ح/ الصندوق أو البنك (مدين) → إلى ح/ الإيراد (دائن)\n"
            "• كل عملية تُولّد قيدًا محاسبيًا متوازنًا تلقائيًا وتُرحّله فورًا"
        )
        info_text.setStyleSheet("color: #5A7AED; font-size: 12px;")
        info_text.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        info_layout.addWidget(info_text)

        layout.addWidget(info_card)

        layout.addStretch()

        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #A0AEC0; font-size: 11px;")
        layout.addWidget(self.status_label)

    def _on_record_clicked(self, is_expense: bool) -> None:
        """فتح نموذج تسجيل مصروف/إيراد."""
        # Load accounts first
        async def _load_accounts():
            from domain.value_objects.value_objects import AccountType
            acc_type = AccountType.EXPENSE if is_expense else AccountType.REVENUE
            accounts = await self._account_repo.list_by_type(acc_type.value)
            return [(a.code, a.name) for a in accounts]

        def _show_dialog(accounts):
            dialog = ExpenseFormDialog(self, is_expense=is_expense, accounts=accounts)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()
                self._record_transaction(data, is_expense)

        self._worker = AsyncWorker(_load_accounts)
        self._worker.finished_signal.connect(_show_dialog)
        self._worker.error_signal.connect(lambda e: QMessageBox.critical(self, "خطأ", e))
        self._worker.start()

    def _record_transaction(self, data: dict, is_expense: bool) -> None:
        """تسجيل المصروف/الإيراد."""
        from use_cases.journal.expenses_use_cases import (
            RecordExpenseUseCase, RecordExpenseRequest,
            RecordRevenueUseCase, RecordRevenueRequest,
        )
        from use_cases.journal.journal_use_cases import (
            AutoJournalBuilder, CreateJournalEntryUseCase, PostJournalEntryUseCase,
        )

        async def _record():
            journal_builder = AutoJournalBuilder(self._account_repo)
            create_uc = CreateJournalEntryUseCase(self._journal_repo, self._account_repo)
            post_uc = PostJournalEntryUseCase(self._journal_repo)

            if is_expense:
                uc = RecordExpenseUseCase(
                    account_repo=self._account_repo,
                    journal_builder=journal_builder,
                    create_journal_uc=create_uc,
                    post_journal_uc=post_uc,
                )
                req = RecordExpenseRequest(
                    description=data["description"],
                    expense_account_code=data["account_code"],
                    amount=data["amount"],
                    payment_account_code=data["payment_account_code"],
                    reference=data["reference"],
                )
                return await uc.execute(req, self._current_user)
            else:
                uc = RecordRevenueUseCase(
                    account_repo=self._account_repo,
                    journal_builder=journal_builder,
                    create_journal_uc=create_uc,
                    post_journal_uc=post_uc,
                )
                req = RecordRevenueRequest(
                    description=data["description"],
                    revenue_account_code=data["account_code"],
                    amount=data["amount"],
                    receipt_account_code=data["payment_account_code"],
                    reference=data["reference"],
                )
                return await uc.execute(req, self._current_user)

        self._worker = AsyncWorker(_record)
        action = "المصروف" if is_expense else "الإيراد"
        self._worker.finished_signal.connect(
            lambda entry_no: (
                QMessageBox.information(
                    self, "نجاح",
                    f"تم تسجيل {action} بنجاح\nرقم القيد: {entry_no}"
                ),
            )
        )
        self._worker.error_signal.connect(lambda e: QMessageBox.critical(self, "خطأ", e))
        self._worker.start()
