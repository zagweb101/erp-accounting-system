"""
Reports Window - شاشة التقارير المالية
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QDialog,
    QFormLayout, QDialogButtonBox, QComboBox, QDoubleSpinBox, QSpinBox,
    QCheckBox, QGroupBox, QPlainTextEdit, QTabWidget, QSplitter,
    QListWidget, QListWidgetItem, QFrame, QScrollArea, QDateEdit,
)

try:
    import qtawesome as qta
except ImportError:
    qta = None

from infrastructure.config.settings import settings
from infrastructure.ui.windows._async_worker import AsyncWorker


class ReportsWindow(QWidget):
    """شاشة التقارير المالية."""

    def __init__(self, current_user, account_repo, journal_repo, parent=None) -> None:
        super().__init__(parent)
        self._current_user = current_user
        self._account_repo = account_repo
        self._journal_repo = journal_repo
        self._worker: Optional[AsyncWorker] = None
        self._setup_ui()
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        # Apply Soft UI automatically
        try:
            from infrastructure.ui.theme.soft_auto import auto_apply_soft_ui
            auto_apply_soft_ui(self)
        except Exception:
            pass

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Top bar
        top_bar = QHBoxLayout()
        title = QLabel("📊 التقارير المالية")
        title.setStyleSheet("color: #2D3748; font-size: 20px; font-weight: bold;")
        top_bar.addWidget(title)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        # Reports grid
        reports_layout = QHBoxLayout()
        reports_layout.setSpacing(12)

        # 4 main report cards
        self._add_report_card(
            reports_layout,
            "⚖️ ميزان المراجعة",
            "Trial Balance",
            "يعرض أرصدة كل الحسابات (مدين/دائن) للتأكد من التوازن.",
            "#6B8AFE",
            self._on_trial_balance,
        )
        self._add_report_card(
            reports_layout,
            "📋 قائمة المركز المالي",
            "Balance Sheet",
            "الأصول، الخصوم، وحقوق الملكية في تاريخ معين.",
            "#68D391",
            self._on_balance_sheet,
        )
        self._add_report_card(
            reports_layout,
            "💰 قائمة الدخل",
            "Income Statement",
            "الإيرادات والمصروفات وصافي الربح خلال فترة.",
            "#F6AD55",
            self._on_income_statement,
        )
        self._add_report_card(
            reports_layout,
            "📈 كشف حساب",
            "Account Statement",
            "تفصيل حركات حساب معين خلال فترة.",
            "#B794F4",
            self._on_account_statement,
        )

        layout.addLayout(reports_layout)

        # Results area (table + buttons)
        self.results_label = QLabel("اختر تقريرًا لعرضه هنا")
        self.results_label.setStyleSheet(
            "color: #A0AEC0; font-size: 14px; padding: 40px; "
            "background-color: #FFFFFF; border-radius: 14px; border: 1px solid #E4EBF5;"
        )
        self.results_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Results table (hidden initially)
        self.results_table = QTableWidget()
        self.results_table.setVisible(False)
        self.results_table.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
                border: 1px solid #E4EBF5; border-radius: 12px;
                gridline-color: #E4EBF5;
            }
            QHeaderView::section {
                background-color: #2D3748; color: #FFFFFF;
                padding: 8px; border: none; font-weight: bold;
            }
        """)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout.addWidget(self.results_label)
        layout.addWidget(self.results_table)

        # Export button
        export_layout = QHBoxLayout()
        export_layout.addStretch()

        self.export_pdf_button = QPushButton("📄 تصدير PDF")
        self.export_pdf_button.setStyleSheet("""
            QPushButton {
                background-color: #B794F4; color: #FFFFFF;
                padding: 8px 16px; border-radius: 12px;
            }
            QPushButton:hover { background-color: #6D28D9; }
            QPushButton:disabled { background-color: #A0AEC0; }
        """)
        self.export_pdf_button.clicked.connect(self._on_export_pdf)
        self.export_pdf_button.setEnabled(False)
        export_layout.addWidget(self.export_pdf_button)

        layout.addLayout(export_layout)

        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #A0AEC0; font-size: 11px;")
        layout.addWidget(self.status_label)

        # Store last report for export
        self._last_report_type: Optional[str] = None
        self._last_report_data: Optional[dict] = None

    def _add_report_card(
        self, parent_layout, title, subtitle, description, color, callback,
    ) -> None:
        """إضافة بطاقة تقرير."""
        card = QFrame()
        card.setFixedHeight(160)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border: 1px solid #E4EBF5;
                border-right: 4px solid {color};
                border-radius: 14px;
                padding: 12px;
            }}
            QFrame:hover {{
                border: 2px solid {color};
            }}
        """)
        card.setCursor(Qt.CursorShape.PointingHandCursor)

        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {color}; font-size: 16px; font-weight: bold;")
        title_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        card_layout.addWidget(title_label)

        sub_label = QLabel(subtitle)
        sub_label.setStyleSheet("color: #A0AEC0; font-size: 11px; font-style: italic;")
        card_layout.addWidget(sub_label)

        desc_label = QLabel(description)
        desc_label.setStyleSheet("color: #718096; font-size: 11px;")
        desc_label.setWordWrap(True)
        desc_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        card_layout.addWidget(desc_label)

        btn = QPushButton("عرض التقرير")
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color}; color: #FFFFFF;
                padding: 6px; border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{ opacity: 0.9; }}
        """)
        btn.clicked.connect(callback)
        card_layout.addWidget(btn)

        parent_layout.addWidget(card)

    def _on_trial_balance(self) -> None:
        """عرض ميزان المراجعة."""
        self.status_label.setText("جارٍ إعداد ميزان المراجعة...")
        self._last_report_type = "trial_balance"

        from use_cases.reports.report_use_cases import GenerateTrialBalanceUseCase

        async def _generate():
            uc = GenerateTrialBalanceUseCase()
            report = await uc.execute(datetime.now(), self._current_user)
            return report

        self._worker = AsyncWorker(_generate)
        self._worker.finished_signal.connect(self._show_trial_balance)
        self._worker.error_signal.connect(self._on_error)
        self._worker.start()

    def _show_trial_balance(self, report) -> None:
        """عرض ميزان المراجعة في الجدول."""
        self.results_label.setVisible(False)
        self.results_table.setVisible(True)
        self.export_pdf_button.setEnabled(True)

        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels([
            "الكود", "اسم الحساب", "النوع", "مدين", "دائن",
        ])
        self.results_table.setRowCount(len(report.lines))

        for i, line in enumerate(report.lines):
            self.results_table.setItem(i, 0, QTableWidgetItem(line.account_code))
            self.results_table.setItem(i, 1, QTableWidgetItem(line.account_name))
            type_ar = {
                "ASSET": "أصول", "LIABILITY": "خصوم", "EQUITY": "حقوق ملكية",
                "REVENUE": "إيرادات", "EXPENSE": "مصروفات",
            }.get(line.account_type, line.account_type)
            self.results_table.setItem(i, 2, QTableWidgetItem(type_ar))
            dr_item = QTableWidgetItem(f"{line.debit:,.2f}" if line.debit > 0 else "—")
            dr_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_table.setItem(i, 3, dr_item)
            cr_item = QTableWidgetItem(f"{line.credit:,.2f}" if line.credit > 0 else "—")
            cr_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_table.setItem(i, 4, cr_item)

        # Totals row
        total_row = self.results_table.rowCount()
        self.results_table.insertRow(total_row)
        self.results_table.setItem(total_row, 0, QTableWidgetItem(""))
        self.results_table.setItem(total_row, 1, QTableWidgetItem("الإجمالي"))
        self.results_table.setItem(total_row, 2, QTableWidgetItem(""))
        total_dr = QTableWidgetItem(f"{report.total_debit:,.2f}")
        total_dr.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        total_cr = QTableWidgetItem(f"{report.total_credit:,.2f}")
        total_cr.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.results_table.setItem(total_row, 3, total_dr)
        self.results_table.setItem(total_row, 4, total_cr)

        status = "✓ متوازن" if report.is_balanced else "✗ غير متوازن"
        self.status_label.setText(
            f"ميزان المراجعة كما في {report.as_of_date.strftime('%Y-%m-%d')} — {status} "
            f"(مدين: {report.total_debit:,.2f} | دائن: {report.total_credit:,.2f})"
        )

        # Store data for PDF export
        self._last_report_data = {
            "as_of_date": report.as_of_date.isoformat(),
            "lines": [
                {
                    "account_code": l.account_code,
                    "account_name": l.account_name,
                    "account_type": l.account_type,
                    "debit": float(l.debit),
                    "credit": float(l.credit),
                }
                for l in report.lines
            ],
            "total_debit": float(report.total_debit),
            "total_credit": float(report.total_credit),
            "is_balanced": report.is_balanced,
            "difference": float(report.difference),
        }

    def _on_balance_sheet(self) -> None:
        """عرض قائمة المركز المالي."""
        self.status_label.setText("جارٍ إعداد قائمة المركز المالي...")
        self._last_report_type = "balance_sheet"

        from use_cases.reports.report_use_cases import GenerateBalanceSheetUseCase

        async def _generate():
            uc = GenerateBalanceSheetUseCase()
            report = await uc.execute(datetime.now(), self._current_user)
            return report

        self._worker = AsyncWorker(_generate)
        self._worker.finished_signal.connect(self._show_balance_sheet)
        self._worker.error_signal.connect(self._on_error)
        self._worker.start()

    def _show_balance_sheet(self, report) -> None:
        self.results_label.setVisible(False)
        self.results_table.setVisible(True)
        self.export_pdf_button.setEnabled(True)

        # Single table with sections: Assets / Liabilities / Equity
        rows_count = (
            1 + len(report.assets) + 1 +  # header + items + total
            1 + len(report.liabilities) + 1 +
            1 + len(report.equity) + 1
        )
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["الكود", "اسم الحساب", "المبلغ"])
        self.results_table.setRowCount(rows_count)

        row = 0
        # Assets section
        self._add_section_header(row, "الأصول", "#6B8AFE")
        row += 1
        for line in report.assets:
            self._add_data_row(row, line.account_code, line.account_name, line.amount)
            row += 1
        self._add_total_row(row, "إجمالي الأصول", report.total_assets)
        row += 1

        # Liabilities
        self._add_section_header(row, "الخصوم", "#FC8181")
        row += 1
        for line in report.liabilities:
            self._add_data_row(row, line.account_code, line.account_name, line.amount)
            row += 1
        self._add_total_row(row, "إجمالي الخصوم", report.total_liabilities)
        row += 1

        # Equity
        self._add_section_header(row, "حقوق الملكية", "#68D391")
        row += 1
        for line in report.equity:
            self._add_data_row(row, line.account_code, line.account_name, line.amount)
            row += 1
        self._add_total_row(row, "إجمالي حقوق الملكية", report.total_equity)

        status = "✓ متوازن" if report.is_balanced else "⚠ قبل الإقفال"
        self.status_label.setText(
            f"قائمة المركز المالي كما في {report.as_of_date.strftime('%Y-%m-%d')} — {status} "
            f"(أصول: {report.total_assets:,.2f} | خصوم: {report.total_liabilities:,.2f} | "
            f"حقوق ملكية: {report.total_equity:,.2f})"
        )

        self._last_report_data = {
            "as_of_date": report.as_of_date.isoformat(),
            "assets": [
                {"account_code": l.account_code, "account_name": l.account_name, "amount": float(l.amount)}
                for l in report.assets
            ],
            "liabilities": [
                {"account_code": l.account_code, "account_name": l.account_name, "amount": float(l.amount)}
                for l in report.liabilities
            ],
            "equity": [
                {"account_code": l.account_code, "account_name": l.account_name, "amount": float(l.amount)}
                for l in report.equity
            ],
            "total_assets": float(report.total_assets),
            "total_liabilities": float(report.total_liabilities),
            "total_equity": float(report.total_equity),
            "is_balanced": report.is_balanced,
        }

    def _add_section_header(self, row: int, title: str, color: str) -> None:
        item = QTableWidgetItem(title)
        item.setBackground(Qt.GlobalColor.darkBlue)
        item.setForeground(Qt.GlobalColor.#FFFFFF)
        font = item.font()
        font.setBold(True)
        font.setPointSize(12)
        item.setFont(font)
        self.results_table.setItem(row, 0, item)
        self.results_table.setItem(row, 1, QTableWidgetItem(""))
        self.results_table.setItem(row, 2, QTableWidgetItem(""))

    def _add_data_row(self, row: int, code: str, name: str, amount) -> None:
        self.results_table.setItem(row, 0, QTableWidgetItem(code))
        self.results_table.setItem(row, 1, QTableWidgetItem(name))
        amt_item = QTableWidgetItem(f"{amount:,.2f}")
        amt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.results_table.setItem(row, 2, amt_item)

    def _add_total_row(self, row: int, title: str, total) -> None:
        self.results_table.setItem(row, 0, QTableWidgetItem(""))
        title_item = QTableWidgetItem(title)
        font = title_item.font()
        font.setBold(True)
        title_item.setFont(font)
        self.results_table.setItem(row, 1, title_item)
        total_item = QTableWidgetItem(f"{total:,.2f}")
        total_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        font = total_item.font()
        font.setBold(True)
        total_item.setFont(font)
        self.results_table.setItem(row, 2, total_item)

    def _on_income_statement(self) -> None:
        """عرض قائمة الدخل."""
        self.status_label.setText("جارٍ إعداد قائمة الدخل...")
        self._last_report_type = "income_statement"

        from use_cases.reports.report_use_cases import GenerateIncomeStatementUseCase

        async def _generate():
            uc = GenerateIncomeStatementUseCase()
            end = datetime.now()
            start = end - timedelta(days=30)  # Last 30 days
            report = await uc.execute(start, end, self._current_user)
            return report

        self._worker = AsyncWorker(_generate)
        self._worker.finished_signal.connect(self._show_income_statement)
        self._worker.error_signal.connect(self._on_error)
        self._worker.start()

    def _show_income_statement(self, report) -> None:
        self.results_label.setVisible(False)
        self.results_table.setVisible(True)
        self.export_pdf_button.setEnabled(True)

        rows_count = (
            1 + len(report.revenues) + 1 +
            1 + len(report.expenses) + 1 +
            1  # Net income
        )
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["الكود", "اسم الحساب", "المبلغ"])
        self.results_table.setRowCount(rows_count)

        row = 0
        # Revenues
        self._add_section_header(row, "الإيرادات", "#68D391")
        row += 1
        for line in report.revenues:
            self._add_data_row(row, line.account_code, line.account_name, line.amount)
            row += 1
        self._add_total_row(row, "إجمالي الإيرادات", report.total_revenue)
        row += 1

        # Expenses
        self._add_section_header(row, "المصروفات", "#FC8181")
        row += 1
        for line in report.expenses:
            self._add_data_row(row, line.account_code, line.account_name, line.amount)
            row += 1
        self._add_total_row(row, "إجمالي المصروفات", report.total_expense)
        row += 1

        # Net income
        net_color = "#68D391" if report.is_profit else "#FC8181"
        net_text = f"صافي {'الربح' if report.is_profit else 'الخسارة'}: {report.net_income:,.2f}"
        self._add_section_header(row, net_text, net_color)

        status = "ربح" if report.is_profit else "خسارة"
        self.status_label.setText(
            f"قائمة الدخل من {report.start_date.strftime('%Y-%m-%d')} إلى "
            f"{report.end_date.strftime('%Y-%m-%d')} — {status} "
            f"(إيرادات: {report.total_revenue:,.2f} | مصروفات: {report.total_expense:,.2f} | "
            f"صافي: {report.net_income:,.2f})"
        )

    def _on_account_statement(self) -> None:
        """عرض كشف حساب."""
        # Show account picker dialog
        from PySide6.QtWidgets import QInputDialog
        from domain.value_objects.value_objects import AccountType

        # Load all accounts first
        async def _load():
            accounts = []
            for acc_type in AccountType:
                accs = await self._account_repo.list_by_type(acc_type.value)
                accounts.extend(accs)
            return accounts

        def _show_dialog(accounts):
            if not accounts:
                QMessageBox.warning(self, "تنبيه", "لا توجد حسابات")
                return

            items = [f"{a.code} - {a.name}" for a in accounts]
            item, ok = QInputDialog.getItem(
                self, "اختر حسابًا", "الحساب:", items, 0, False,
            )
            if not ok or not item:
                return

            idx = items.index(item)
            account = accounts[idx]
            self._generate_account_statement(account.id, account.code, account.name)

        self._worker = AsyncWorker(_load)
        self._worker.finished_signal.connect(_show_dialog)
        self._worker.error_signal.connect(self._on_error)
        self._worker.start()

    def _generate_account_statement(self, account_id, code, name) -> None:
        from use_cases.reports.report_use_cases import GenerateAccountStatementUseCase

        async def _generate():
            uc = GenerateAccountStatementUseCase()
            end = datetime.now()
            start = end - timedelta(days=90)
            report = await uc.execute(account_id, start, end, self._current_user)
            return report

        def _show(report):
            self.results_label.setVisible(False)
            self.results_table.setVisible(True)

            self.results_table.setColumnCount(6)
            self.results_table.setHorizontalHeaderLabels([
                "التاريخ", "رقم القيد", "الوصف", "مدين", "دائن", "الرصيد",
            ])
            self.results_table.setRowCount(len(report.lines))

            for i, line in enumerate(report.lines):
                self.results_table.setItem(i, 0, QTableWidgetItem(line.date.strftime("%Y-%m-%d")))
                self.results_table.setItem(i, 1, QTableWidgetItem(line.entry_no))
                self.results_table.setItem(i, 2, QTableWidgetItem(line.description))
                dr_item = QTableWidgetItem(f"{line.debit:,.2f}" if line.debit > 0 else "—")
                dr_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.results_table.setItem(i, 3, dr_item)
                cr_item = QTableWidgetItem(f"{line.credit:,.2f}" if line.credit > 0 else "—")
                cr_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.results_table.setItem(i, 4, cr_item)
                bal_item = QTableWidgetItem(f"{line.balance:,.2f}")
                bal_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.results_table.setItem(i, 5, bal_item)

            self.status_label.setText(
                f"كشف حساب: {code} - {name} | "
                f"رصيد افتتاحي: {report.opening_balance:,.2f} | "
                f"رصيد ختامي: {report.closing_balance:,.2f} | "
                f"عدد الحركات: {len(report.lines)}"
            )

        self._worker = AsyncWorker(_generate)
        self._worker.finished_signal.connect(_show)
        self._worker.error_signal.connect(self._on_error)
        self._worker.start()

    def _on_export_pdf(self) -> None:
        """تصدير التقرير الحالي إلى PDF."""
        if not self._last_report_data:
            return

        try:
            from infrastructure.services.pdf_service import PDFService
            pdf = PDFService()

            if self._last_report_type == "trial_balance":
                path = pdf.export_trial_balance_pdf(self._last_report_data)
            elif self._last_report_type == "balance_sheet":
                path = pdf.export_balance_sheet_pdf(self._last_report_data)
            else:
                QMessageBox.information(self, "تنبيه", "تصدير هذا التقرير غير مدعوم بعد")
                return

            QMessageBox.information(self, "تم التصدير", f"تم حفظ PDF في:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "خطأ في التصدير", str(e))

    def _on_error(self, error_msg: str) -> None:
        self.status_label.setText(f"⚠ خطأ: {error_msg}")
        QMessageBox.critical(self, "خطأ", error_msg)
