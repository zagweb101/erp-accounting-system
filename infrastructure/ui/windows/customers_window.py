"""
Customers Window - نافذة إدارة العملاء

عرض + بحث + إضافة + تعديل + حذف.
"""
from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Optional
from uuid import UUID

from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QDialog,
    QFormLayout, QDialogButtonBox, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QGroupBox, QPlainTextEdit,
)

try:
    import qtawesome as qta
except ImportError:
    qta = None


class AsyncWorker(QThread):
    """Generic async worker."""
    finished_signal = Signal(object)
    error_signal = Signal(str)

    def __init__(self, coro_factory) -> None:
        super().__init__()
        self._coro_factory = coro_factory

    def run(self) -> None:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._coro_factory())
            self.finished_signal.emit(result)
        except Exception as e:
            self.error_signal.emit(str(e))


class CustomerFormDialog(QDialog):
    """نموذج إضافة/تعديل عميل."""

    def __init__(self, parent=None, customer_data: Optional[dict] = None) -> None:
        super().__init__(parent)
        self._customer_data = customer_data
        self._setup_ui()
        if customer_data:
            self._fill_form(customer_data)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        # Apply Soft UI automatically
        try:
            from infrastructure.ui.theme.soft_auto import auto_apply_soft_ui
            auto_apply_soft_ui(self)
        except Exception:
            pass

    def _setup_ui(self) -> None:
        self.setWindowTitle("بيانات العميل")
        self.setFixedSize(600, 700)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Form
        form = QFormLayout()
        form.setSpacing(8)

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("C-001")
        form.addRow("كود العميل *:", self.code_input)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("اسم العميل")
        form.addRow("الاسم *:", self.name_input)

        self.name_en_input = QLineEdit()
        form.addRow("الاسم (إنجليزي):", self.name_en_input)

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("05xxxxxxxx")
        form.addRow("الهاتف:", self.phone_input)

        self.email_input = QLineEdit()
        form.addRow("البريد الإلكتروني:", self.email_input)

        self.address_input = QLineEdit()
        form.addRow("العنوان:", self.address_input)

        self.tax_input = QLineEdit()
        self.tax_input.setPlaceholderText("300000000000003")
        form.addRow("الرقم الضريبي:", self.tax_input)

        self.opening_balance_input = QDoubleSpinBox()
        self.opening_balance_input.setRange(0, 999999999)
        self.opening_balance_input.setDecimals(2)
        self.opening_balance_input.setSuffix(" ر.س")
        form.addRow("الرصيد الافتتاحي:", self.opening_balance_input)

        self.credit_limit_input = QDoubleSpinBox()
        self.credit_limit_input.setRange(0, 999999999)
        self.credit_limit_input.setDecimals(2)
        self.credit_limit_input.setSuffix(" ر.س")
        form.addRow("حد الائتمان:", self.credit_limit_input)

        self.payment_terms_input = QSpinBox()
        self.payment_terms_input.setRange(0, 365)
        self.payment_terms_input.setValue(30)
        self.payment_terms_input.setSuffix(" يوم")
        form.addRow("آجل السداد:", self.payment_terms_input)

        self.category_input = QComboBox()
        self.category_input.addItems(["regular", "vip", "wholesale", "retail"])
        form.addRow("التصنيف:", self.category_input)

        layout.addLayout(form)

        # Notes
        notes_label = QLabel("ملاحظات:")
        notes_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout.addWidget(notes_label)
        self.notes_input = QPlainTextEdit()
        self.notes_input.setMaximumHeight(80)
        layout.addWidget(self.notes_input)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("حفظ")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("إلغاء")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet("""
            QDialog { background-color: #F0F4F8; }
            QLabel { color: #2D3748; font-size: 13px; }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                padding: 8px; border: 1px solid #C3CAD7;
                border-radius: 12px; background-color: #FFFFFF;
            }
            QLineEdit:focus, QComboBox:focus { border: 2px solid #6B8AFE; }
            QPlainTextEdit {
                border: 1px solid #C3CAD7; border-radius: 12px;
                padding: 6px; background-color: #FFFFFF;
            }
            QPushButton {
                padding: 8px 24px; border-radius: 12px;
                background-color: #6B8AFE; color: #FFFFFF;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #5A7AED; }
        """)

    def _fill_form(self, data: dict) -> None:
        self.code_input.setText(data.get("code", ""))
        self.code_input.setEnabled(False)  # Cannot change code
        self.name_input.setText(data.get("name", ""))
        self.name_en_input.setText(data.get("name_en", ""))
        self.phone_input.setText(data.get("phone", ""))
        self.email_input.setText(data.get("email", ""))
        self.address_input.setText(data.get("address", ""))
        self.tax_input.setText(data.get("tax_number", ""))
        self.opening_balance_input.setValue(float(data.get("opening_balance", 0)))
        self.credit_limit_input.setValue(float(data.get("credit_limit", 0)))
        self.payment_terms_input.setValue(int(data.get("payment_terms_days", 30)))
        self.notes_input.setPlainText(data.get("notes", ""))
        if data.get("customer_category") in ["regular", "vip", "wholesale", "retail"]:
            self.category_input.setCurrentText(data["customer_category"])

    def get_data(self) -> dict:
        return {
            "code": self.code_input.text().strip(),
            "name": self.name_input.text().strip(),
            "name_en": self.name_en_input.text().strip(),
            "phone": self.phone_input.text().strip(),
            "email": self.email_input.text().strip(),
            "address": self.address_input.text().strip(),
            "tax_number": self.tax_input.text().strip(),
            "opening_balance": Decimal(str(self.opening_balance_input.value())),
            "credit_limit": Decimal(str(self.credit_limit_input.value())),
            "payment_terms_days": self.payment_terms_input.value(),
            "customer_category": self.category_input.currentText(),
            "notes": self.notes_input.toPlainText().strip(),
        }


class CustomersWindow(QWidget):
    """شاشة إدارة العملاء."""

    def __init__(self, current_user, customer_repo, parent=None) -> None:
        super().__init__(parent)
        self._current_user = current_user
        self._customer_repo = customer_repo
        self._worker: Optional[AsyncWorker] = None
        self._setup_ui()
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._load_customers()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Top bar: search + add button
        top_bar = QHBoxLayout()

        title = QLabel("👥 إدارة العملاء")
        title.setStyleSheet("color: #2D3748; font-size: 20px; font-weight: bold;")
        top_bar.addWidget(title)

        top_bar.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 بحث بالاسم أو الكود أو الهاتف...")
        self.search_input.setMinimumWidth(300)
        self.search_input.textChanged.connect(self._on_search_changed)
        top_bar.addWidget(self.search_input)

        self.add_button = QPushButton("➕ إضافة عميل")
        self.add_button.setStyleSheet("""
            QPushButton {
                background-color: #68D391; color: #FFFFFF;
                padding: 8px 16px; border-radius: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #48BB78; }
        """)
        self.add_button.clicked.connect(self._on_add_clicked)
        top_bar.addWidget(self.add_button)

        layout.addLayout(top_bar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "الكود", "الاسم", "الهاتف", "البريد", "الرصيد", "حد الائتمان", "الحالة",
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
        self.table.doubleClicked.connect(self._on_row_double_clicked)
        layout.addWidget(self.table)

        # Action buttons (below table)
        actions = QHBoxLayout()

        self.edit_button = QPushButton("✏️ تعديل")
        self.edit_button.setStyleSheet("""
            QPushButton {
                background-color: #6B8AFE; color: #FFFFFF;
                padding: 8px 16px; border-radius: 12px;
            }
            QPushButton:hover { background-color: #5A7AED; }
            QPushButton:disabled { background-color: #A0AEC0; }
        """)
        self.edit_button.clicked.connect(self._on_edit_clicked)
        self.edit_button.setEnabled(False)
        actions.addWidget(self.edit_button)

        self.delete_button = QPushButton("🗑️ حذف")
        self.delete_button.setStyleSheet("""
            QPushButton {
                background-color: #FC8181; color: #FFFFFF;
                padding: 8px 16px; border-radius: 12px;
            }
            QPushButton:hover { background-color: #E53E3E; }
            QPushButton:disabled { background-color: #A0AEC0; }
        """)
        self.delete_button.clicked.connect(self._on_delete_clicked)
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
        self.refresh_button.clicked.connect(self._load_customers)
        actions.addWidget(self.refresh_button)

        layout.addLayout(actions)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #A0AEC0; font-size: 11px;")
        layout.addWidget(self.status_label)

    def _load_customers(self) -> None:
        """تحميل قائمة العملاء."""
        self.status_label.setText("جارٍ التحميل...")

        async def _load():
            return await self._customer_repo.list_all(skip=0, limit=1000)

        self._worker = AsyncWorker(_load)
        self._worker.finished_signal.connect(self._on_customers_loaded)
        self._worker.error_signal.connect(self._on_error)
        self._worker.start()

    def _on_customers_loaded(self, customers: list) -> None:
        self.table.setRowCount(len(customers))
        for i, c in enumerate(customers):
            self.table.setItem(i, 0, QTableWidgetItem(c.code))
            self.table.setItem(i, 1, QTableWidgetItem(c.name))
            self.table.setItem(i, 2, QTableWidgetItem(c.phone))
            self.table.setItem(i, 3, QTableWidgetItem(c.email))
            balance_item = QTableWidgetItem(f"{c.current_balance:,.2f} ر.س")
            balance_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 4, balance_item)
            limit_item = QTableWidgetItem(
                f"{c.credit_limit:,.2f}" if c.credit_limit > 0 else "—"
            )
            limit_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 5, limit_item)
            status_item = QTableWidgetItem("✓ نشط" if c.is_active else "✗ معطّل")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 6, status_item)

        self.status_label.setText(f"إجمالي العملاء: {len(customers)}")

    def _on_search_changed(self, text: str) -> None:
        """بحث ديناميكي."""
        if len(text) < 2:
            self._load_customers()
            return

        async def _search():
            return await self._customer_repo.search(text, limit=50)

        QTimer.singleShot(300, lambda: self._do_search(text))

    def _do_search(self, text: str) -> None:
        async def _search():
            return await self._customer_repo.search(text, limit=50)

        self._worker = AsyncWorker(_search)
        self._worker.finished_signal.connect(self._on_customers_loaded)
        self._worker.error_signal.connect(self._on_error)
        self._worker.start()

    def _on_row_double_clicked(self, index) -> None:
        self.edit_button.setEnabled(True)
        self.delete_button.setEnabled(True)

    def _on_add_clicked(self) -> None:
        """فتح نموذج إضافة عميل."""
        dialog = CustomerFormDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            self._create_customer(data)

    def _create_customer(self, data: dict) -> None:
        from use_cases.customers.customer_use_cases import (
            CreateCustomerUseCase, CreateCustomerRequest,
        )

        async def _create():
            uc = CreateCustomerUseCase(self._customer_repo)
            req = CreateCustomerRequest(**data)
            return await uc.execute(req, self._current_user)

        self._worker = AsyncWorker(_create)
        self._worker.finished_signal.connect(lambda _: (
            QMessageBox.information(self, "نجاح", "تم إنشاء العميل بنجاح"),
            self._load_customers(),
        ))
        self._worker.error_signal.connect(lambda e: QMessageBox.critical(self, "خطأ", e))
        self._worker.start()

    def _on_edit_clicked(self) -> None:
        """فتح نموذج تعديل عميل."""
        row = self.table.currentRow()
        if row < 0:
            return

        code = self.table.item(row, 0).text()

        async def _get():
            return await self._customer_repo.get_by_code(code)

        async def _do_edit():
            customer = await self._customer_repo.get_by_code(code)
            if customer is None:
                return None
            dialog = CustomerFormDialog(self, {
                "code": customer.code,
                "name": customer.name,
                "name_en": customer.name_en,
                "phone": customer.phone,
                "email": customer.email,
                "address": customer.address,
                "tax_number": customer.tax_number,
                "opening_balance": customer.opening_balance,
                "credit_limit": customer.credit_limit,
                "payment_terms_days": customer.payment_terms_days,
                "customer_category": customer.customer_category,
                "notes": customer.notes,
            })
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return None
            return dialog.get_data()

        self._worker = AsyncWorker(_do_edit)

        def _on_data(data):
            if data is None:
                return
            self._update_customer(code, data)

        self._worker.finished_signal.connect(_on_data)
        self._worker.error_signal.connect(lambda e: QMessageBox.critical(self, "خطأ", e))
        self._worker.start()

    def _update_customer(self, code: str, data: dict) -> None:
        from use_cases.customers.customer_use_cases import (
            UpdateCustomerUseCase, UpdateCustomerRequest,
        )

        async def _update():
            customer = await self._customer_repo.get_by_code(code)
            if customer is None:
                return None
            uc = UpdateCustomerUseCase(self._customer_repo)
            req = UpdateCustomerRequest(
                customer_id=customer.id,
                name=data.get("name"),
                name_en=data.get("name_en"),
                phone=data.get("phone"),
                email=data.get("email"),
                address=data.get("address"),
                tax_number=data.get("tax_number"),
                credit_limit=data.get("credit_limit"),
                payment_terms_days=data.get("payment_terms_days"),
                customer_category=data.get("customer_category"),
                notes=data.get("notes"),
            )
            return await uc.execute(req, self._current_user)

        self._worker = AsyncWorker(_update)
        self._worker.finished_signal.connect(lambda _: (
            QMessageBox.information(self, "نجاح", "تم تحديث العميل بنجاح"),
            self._load_customers(),
        ))
        self._worker.error_signal.connect(lambda e: QMessageBox.critical(self, "خطأ", e))
        self._worker.start()

    def _on_delete_clicked(self) -> None:
        """حذف (تعطيل) عميل."""
        row = self.table.currentRow()
        if row < 0:
            return

        code = self.table.item(row, 0).text()
        name = self.table.item(row, 1).text()

        reply = QMessageBox.question(
            self, "تأكيد الحذف",
            f"هل تريد حذف العميل '{name}'؟\nملاحظة: سيتم تعطيله (لن يُحذف فعليًا).",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        from use_cases.customers.customer_use_cases import DeleteCustomerUseCase

        async def _delete():
            customer = await self._customer_repo.get_by_code(code)
            if customer is None:
                return False
            uc = DeleteCustomerUseCase(self._customer_repo)
            return await uc.execute(customer.id, self._current_user)

        self._worker = AsyncWorker(_delete)
        self._worker.finished_signal.connect(lambda _: (
            QMessageBox.information(self, "نجاح", "تم حذف العميل"),
            self._load_customers(),
        ))
        self._worker.error_signal.connect(lambda e: QMessageBox.critical(self, "خطأ", e))
        self._worker.start()

    def _on_export_excel(self) -> None:
        """تصدير العملاء إلى Excel."""
        try:
            from infrastructure.ui.services.ui_service_integration import export_to_excel

            async def _get_data():
                customers = await self._customer_repo.list_all(skip=0, limit=10000)
                return [c.to_dict() if hasattr(c, 'to_dict') else {
                    "code": c.code, "name": c.name, "phone": c.phone,
                    "email": c.email, "current_balance": float(c.current_balance),
                    "credit_limit": float(c.credit_limit), "is_active": c.is_active,
                } for c in customers]

            from infrastructure.ui.windows._async_worker import AsyncWorker

            def _do_export(customers_data):
                export_to_excel("customers", customers_data, parent=self)

            self._worker = AsyncWorker(_get_data)
            self._worker.finished_signal.connect(_do_export)
            self._worker.error_signal.connect(lambda e: self._on_error(e))
            self._worker.start()
        except Exception as e:
            self._on_error(str(e))

    def _on_import_excel(self) -> None:
        """استيراد عملاء من Excel."""
        try:
            from infrastructure.ui.services.ui_service_integration import import_from_excel
            data = import_from_excel("customers", parent=self)
            if data:
                self.status_label.setText(f"✓ تم استيراد {len(data)} عميل — استخدمهم لإنشاء العملاء")
        except Exception as e:
            self._on_error(str(e))

    def _on_error(self, error_msg: str) -> None:
        self.status_label.setText(f"⚠ خطأ: {error_msg}")
