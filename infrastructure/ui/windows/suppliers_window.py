"""
Suppliers Window - شاشة إدارة الموردين

مشابهة لشاشة العملاء لكن للموردين.
"""
from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Optional
from uuid import UUID

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QDialog,
    QFormLayout, QDialogButtonBox, QComboBox, QDoubleSpinBox, QSpinBox,
    QCheckBox, QGroupBox, QPlainTextEdit,
)

from infrastructure.ui.windows._async_worker import AsyncWorker


class SupplierFormDialog(QDialog):
    """نموذج إضافة/تعديل مورد."""

    def __init__(self, parent=None, supplier_data: Optional[dict] = None) -> None:
        super().__init__(parent)
        self._supplier_data = supplier_data
        self._setup_ui()
        if supplier_data:
            self._fill_form(supplier_data)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        # Apply Soft UI automatically
        try:
            from infrastructure.ui.theme.soft_auto import auto_apply_soft_ui
            auto_apply_soft_ui(self)
        except Exception:
            pass

    def _setup_ui(self) -> None:
        self.setWindowTitle("بيانات المورد")
        self.setFixedSize(600, 720)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(8)

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("S-001")
        self.code_input.setAccessibleName("كود المورد")
        form.addRow("كود المورد *:", self.code_input)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("اسم المورد")
        self.name_input.setAccessibleName("اسم المورد")
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
        self.category_input.addItems(["regular", "wholesale", "manufacturer", "service"])
        form.addRow("التصنيف:", self.category_input)

        layout.addLayout(form)

        notes_label = QLabel("ملاحظات:")
        notes_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout.addWidget(notes_label)
        self.notes_input = QPlainTextEdit()
        self.notes_input.setMaximumHeight(80)
        layout.addWidget(self.notes_input)

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
        """)

    def _fill_form(self, data: dict) -> None:
        self.code_input.setText(data.get("code", ""))
        self.code_input.setEnabled(False)
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
        if data.get("supplier_category") in ["regular", "wholesale", "manufacturer", "service"]:
            self.category_input.setCurrentText(data["supplier_category"])

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
            "supplier_category": self.category_input.currentText(),
            "notes": self.notes_input.toPlainText().strip(),
        }


class SuppliersWindow(QWidget):
    """شاشة إدارة الموردين."""

    def __init__(self, current_user, supplier_repo, parent=None) -> None:
        super().__init__(parent)
        self._current_user = current_user
        self._supplier_repo = supplier_repo
        self._worker: Optional[AsyncWorker] = None
        self._setup_ui()
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._load_suppliers()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Top bar
        top_bar = QHBoxLayout()

        title = QLabel("🚚 إدارة الموردين")
        title.setStyleSheet("color: #2D3748; font-size: 20px; font-weight: bold;")
        top_bar.addWidget(title)

        top_bar.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 بحث بالاسم أو الكود...")
        self.search_input.setMinimumWidth(300)
        self.search_input.textChanged.connect(self._on_search_changed)
        self.search_input.setAccessibleName("حقل البحث عن الموردين")
        top_bar.addWidget(self.search_input)

        self.add_button = QPushButton("➕ إضافة مورد")
        self.add_button.setStyleSheet("""
            QPushButton {
                background-color: #68D391; color: #FFFFFF;
                padding: 8px 16px; border-radius: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #48BB78; }
        """)
        self.add_button.setToolTip("إضافة مورد جديد")
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

        # Action buttons
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
        self.edit_button.setToolTip("تعديل بيانات المورد المحدد")
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
        self.delete_button.setToolTip("حذف (تعطيل) المورد المحدد")
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
        self.refresh_button.setToolTip("إعادة تحميل قائمة الموردين")
        self.refresh_button.clicked.connect(self._load_suppliers)
        actions.addWidget(self.refresh_button)

        layout.addLayout(actions)

        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #A0AEC0; font-size: 11px;")
        layout.addWidget(self.status_label)

    def _load_suppliers(self) -> None:
        self.status_label.setText("جارٍ التحميل...")

        async def _load():
            return await self._supplier_repo.list_all(skip=0, limit=1000)

        self._worker = AsyncWorker(_load)
        self._worker.finished_signal.connect(self._on_suppliers_loaded)
        self._worker.error_signal.connect(self._on_error)
        self._worker.start()

    def _on_suppliers_loaded(self, suppliers: list) -> None:
        self.table.setRowCount(len(suppliers))
        for i, s in enumerate(suppliers):
            self.table.setItem(i, 0, QTableWidgetItem(s.code))
            self.table.setItem(i, 1, QTableWidgetItem(s.name))
            self.table.setItem(i, 2, QTableWidgetItem(s.phone))
            self.table.setItem(i, 3, QTableWidgetItem(s.email))
            balance_item = QTableWidgetItem(f"{s.current_balance:,.2f} ر.س")
            balance_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 4, balance_item)
            limit_item = QTableWidgetItem(
                f"{s.credit_limit:,.2f}" if s.credit_limit > 0 else "-"
            )
            limit_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 5, limit_item)
            status_item = QTableWidgetItem("✓ نشط" if s.is_active else "✗ معطّل")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 6, status_item)

        self.status_label.setText(f"إجمالي الموردين: {len(suppliers)}")

    def _on_search_changed(self, text: str) -> None:
        if len(text) < 2:
            self._load_suppliers()
            return
        QTimer.singleShot(300, lambda: self._do_search(text))

    def _do_search(self, text: str) -> None:
        async def _search():
            # Use list_all since search isn't in ISupplierRepository
            all_suppliers = await self._supplier_repo.list_all(skip=0, limit=1000)
            query_lower = text.lower()
            return [
                s for s in all_suppliers
                if query_lower in s.name.lower() or query_lower in s.code.lower()
                or query_lower in (s.phone or "").lower()
            ]

        self._worker = AsyncWorker(_search)
        self._worker.finished_signal.connect(self._on_suppliers_loaded)
        self._worker.error_signal.connect(self._on_error)
        self._worker.start()

    def _on_row_double_clicked(self, index) -> None:
        self.edit_button.setEnabled(True)
        self.delete_button.setEnabled(True)

    def _on_add_clicked(self) -> None:
        dialog = SupplierFormDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            self._create_supplier(data)

    def _create_supplier(self, data: dict) -> None:
        from use_cases.suppliers.supplier_use_cases import (
            CreateSupplierUseCase, CreateSupplierRequest,
        )

        async def _create():
            uc = CreateSupplierUseCase(self._supplier_repo)
            req = CreateSupplierRequest(**data)
            return await uc.execute(req, self._current_user)

        self._worker = AsyncWorker(_create)
        self._worker.finished_signal.connect(lambda _: (
            QMessageBox.information(self, "نجاح", "تم إنشاء المورد بنجاح"),
            self._load_suppliers(),
        ))
        self._worker.error_signal.connect(lambda e: QMessageBox.critical(self, "خطأ", e))
        self._worker.start()

    def _on_edit_clicked(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        code = self.table.item(row, 0).text()

        async def _do_edit():
            supplier = await self._supplier_repo.get_by_code(code)
            if supplier is None:
                return None
            dialog = SupplierFormDialog(self, {
                "code": supplier.code,
                "name": supplier.name,
                "name_en": supplier.name_en,
                "phone": supplier.phone,
                "email": supplier.email,
                "address": supplier.address,
                "tax_number": supplier.tax_number,
                "opening_balance": supplier.opening_balance,
                "credit_limit": supplier.credit_limit,
                "payment_terms_days": supplier.payment_terms_days,
                "supplier_category": supplier.supplier_category,
                "notes": supplier.notes,
            })
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return None
            return dialog.get_data()

        self._worker = AsyncWorker(_do_edit)

        def _on_data(data):
            if data is None:
                return
            self._update_supplier(code, data)

        self._worker.finished_signal.connect(_on_data)
        self._worker.error_signal.connect(lambda e: QMessageBox.critical(self, "خطأ", e))
        self._worker.start()

    def _update_supplier(self, code: str, data: dict) -> None:
        from use_cases.suppliers.supplier_use_cases import (
            UpdateSupplierUseCase, UpdateSupplierRequest,
        )

        async def _update():
            supplier = await self._supplier_repo.get_by_code(code)
            if supplier is None:
                return None
            uc = UpdateSupplierUseCase(self._supplier_repo)
            req = UpdateSupplierRequest(
                supplier_id=supplier.id,
                name=data.get("name"),
                name_en=data.get("name_en"),
                phone=data.get("phone"),
                email=data.get("email"),
                address=data.get("address"),
                tax_number=data.get("tax_number"),
                credit_limit=data.get("credit_limit"),
                payment_terms_days=data.get("payment_terms_days"),
                supplier_category=data.get("supplier_category"),
                notes=data.get("notes"),
            )
            return await uc.execute(req, self._current_user)

        self._worker = AsyncWorker(_update)
        self._worker.finished_signal.connect(lambda _: (
            QMessageBox.information(self, "نجاح", "تم تحديث المورد بنجاح"),
            self._load_suppliers(),
        ))
        self._worker.error_signal.connect(lambda e: QMessageBox.critical(self, "خطأ", e))
        self._worker.start()

    def _on_delete_clicked(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return

        code = self.table.item(row, 0).text()
        name = self.table.item(row, 1).text()

        reply = QMessageBox.question(
            self, "تأكيد الحذف",
            f"هل تريد حذف المورد '{name}'؟\nسيتم تعطيله (لن يُحذف فعليًا).",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        from use_cases.suppliers.supplier_use_cases import DeleteSupplierUseCase

        async def _delete():
            supplier = await self._supplier_repo.get_by_code(code)
            if supplier is None:
                return False
            uc = DeleteSupplierUseCase(self._supplier_repo)
            return await uc.execute(supplier.id, self._current_user)

        self._worker = AsyncWorker(_delete)
        self._worker.finished_signal.connect(lambda _: (
            QMessageBox.information(self, "نجاح", "تم حذف المورد"),
            self._load_suppliers(),
        ))
        self._worker.error_signal.connect(lambda e: QMessageBox.critical(self, "خطأ", e))
        self._worker.start()

    def _on_error(self, error_msg: str) -> None:
        self.status_label.setText(f"⚠ خطأ: {error_msg}")
