"""
Invoices Window - شاشة إدارة الفواتير
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QDialog,
    QFormLayout, QDialogButtonBox, QComboBox, QDoubleSpinBox, QSpinBox,
    QCheckBox, QGroupBox, QPlainTextEdit, QTabWidget, QSplitter,
    QListWidget, QListWidgetItem, QFrame, QScrollArea, QSpinBox,
)

try:
    import qtawesome as qta
except ImportError:
    qta = None

from infrastructure.config.settings import settings
from infrastructure.ui.windows._async_worker import AsyncWorker
from domain.entities.invoice import InvoiceType, InvoiceStatus
from domain.value_objects.value_objects import Permission


class InvoiceLineEditor(QGroupBox):
    """محرر بنود الفاتورة."""

    def __init__(self, parent=None) -> None:
        super().__init__("بنود الفاتورة", parent)
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

        # Add line row
        add_row = QHBoxLayout()
        add_row.addWidget(QLabel("المنتج:"))

        self.product_search = QLineEdit()
        self.product_search.setPlaceholderText("ابحث بالـ SKU أو الاسم...")
        self.product_search.setMinimumWidth(300)
        self.product_search.returnPressed.connect(self._on_search_product)
        add_row.addWidget(self.product_search)

        self.search_result = QComboBox()
        self.search_result.setMinimumWidth(300)
        add_row.addWidget(self.search_result)

        self.add_line_button = QPushButton("➕ إضافة بند")
        self.add_line_button.setStyleSheet("background-color: #68D391; color: #FFFFFF; padding: 6px;")
        self.add_line_button.clicked.connect(self._on_add_line)
        add_row.addWidget(self.add_line_button)

        layout.addLayout(add_row)

        # Lines table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "المنتج", "الكمية", "سعر الوحدة", "الضريبة %", "الخصم", "إجمالي البند", "حذف",
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
                border: 1px solid #E4EBF5; border-radius: 12px;
                gridline-color: #E4EBF5;
            }
            QHeaderView::section {
                background-color: #2D3748; color: #FFFFFF;
                padding: 6px; border: none; font-weight: bold;
            }
        """)
        self.table.cellChanged.connect(self._on_cell_changed)
        layout.addWidget(self.table)

        # Totals
        totals_row = QHBoxLayout()
        totals_row.addStretch()

        totals_layout = QVBoxLayout()
        self.subtotal_label = QLabel("الإجمالي الفرعي: 0.00 ر.س")
        self.subtotal_label.setStyleSheet("color: #718096; font-size: 14px;")
        totals_layout.addWidget(self.subtotal_label)

        self.tax_label = QLabel("الضريبة (15%): 0.00 ر.س")
        self.tax_label.setStyleSheet("color: #718096; font-size: 14px;")
        totals_layout.addWidget(self.tax_label)

        self.discount_label = QLabel("الخصم: 0.00 ر.س")
        self.discount_label.setStyleSheet("color: #718096; font-size: 14px;")
        totals_layout.addWidget(self.discount_label)

        self.total_label = QLabel("الإجمالي: 0.00 ر.س")
        self.total_label.setStyleSheet("color: #6B8AFE; font-size: 18px; font-weight: bold;")
        totals_layout.addWidget(self.total_label)

        totals_row.addLayout(totals_layout)
        layout.addLayout(totals_row)

    def _on_search_product(self) -> None:
        """بحث عن المنتج."""
        # Will be set externally
        if self._product_search_callback:
            self._product_search_callback(self.product_search.text())

    _product_search_callback = None

    def set_product_search_callback(self, callback) -> None:
        self._product_search_callback = callback

    def populate_search_results(self, products) -> None:
        """ملء نتائج البحث."""
        self.search_result.clear()
        for p in products:
            self.search_result.addItem(f"{p.sku} - {p.name}", userData=p)

    def _on_add_line(self) -> None:
        """إضافة بند للفاتورة."""
        if self.search_result.count() == 0:
            QMessageBox.warning(self, "تنبيه", "ابحث عن منتج أولًا")
            return

        product = self.search_result.currentData()
        if product is None:
            return

        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(f"{product.sku} - {product.name}"))
        self.table.setItem(row, 1, QTableWidgetItem("1"))
        self.table.setItem(row, 2, QTableWidgetItem(f"{product.sale_price:.2f}"))
        self.table.setItem(row, 3, QTableWidgetItem(f"{product.tax_rate:.2f}"))
        self.table.setItem(row, 4, QTableWidgetItem("0.00"))
        self.table.setItem(row, 5, QTableWidgetItem(f"{product.sale_price:.2f}"))

        delete_btn = QPushButton("🗑️")
        delete_btn.setStyleSheet("background: #FC8181; color: #FFFFFF;")
        delete_btn.clicked.connect(lambda _, r=row: self.table.removeRow(r))
        self.table.setCellWidget(row, 6, delete_btn)

        # Store product id in hidden column via item data
        self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, str(product.id))
        self._update_totals()

    def _on_cell_changed(self, row, col) -> None:
        """إعادة حساب الإجمالي عند تغيير الكمية أو السعر."""
        if col in (1, 2, 3, 4):
            try:
                qty = Decimal(self.table.item(row, 1).text() or "0")
                price = Decimal(self.table.item(row, 2).text() or "0")
                tax_rate = Decimal(self.table.item(row, 3).text() or "0")
                discount = Decimal(self.table.item(row, 4).text() or "0")
                subtotal = qty * price - discount
                tax = subtotal * tax_rate / Decimal("100")
                line_total = subtotal + tax
                self.table.item(row, 5).setText(f"{line_total:.2f}")
            except Exception as e:
                # Silent fail - UI initialization should not crash
                # In production: use logger.warning(f"UI init error: {e}")
                pass
            self._update_totals()

    def _update_totals(self) -> None:
        """تحديث الإجماليات."""
        subtotal = Decimal("0")
        tax_total = Decimal("0")
        discount_total = Decimal("0")
        grand_total = Decimal("0")

        for r in range(self.table.rowCount()):
            try:
                qty = Decimal(self.table.item(r, 1).text() or "0")
                price = Decimal(self.table.item(r, 2).text() or "0")
                tax_rate = Decimal(self.table.item(r, 3).text() or "0")
                discount = Decimal(self.table.item(r, 4).text() or "0")
                line_sub = qty * price - discount
                line_tax = line_sub * tax_rate / Decimal("100")
                subtotal += line_sub
                tax_total += line_tax
                discount_total += discount
                grand_total += line_sub + line_tax
            except Exception:
                continue

        self.subtotal_label.setText(f"الإجمالي الفرعي: {subtotal:,.2f} ر.س")
        self.tax_label.setText(f"الضريبة: {tax_total:,.2f} ر.س")
        self.discount_label.setText(f"الخصم: {discount_total:,.2f} ر.س")
        self.total_label.setText(f"الإجمالي: {grand_total:,.2f} ر.س")

    def get_lines(self) -> list[dict]:
        """الحصول على بنود الفاتورة."""
        lines = []
        for r in range(self.table.rowCount()):
            product_cell = self.table.item(r, 0)
            if not product_cell:
                continue
            product_id_str = product_cell.data(Qt.ItemDataRole.UserRole)
            if not product_id_str:
                continue
            try:
                lines.append({
                    "product_id": UUID(product_id_str),
                    "quantity": Decimal(self.table.item(r, 1).text() or "0"),
                    "unit_price": Decimal(self.table.item(r, 2).text() or "0"),
                    "tax_rate": Decimal(self.table.item(r, 3).text() or "0"),
                    "discount": Decimal(self.table.item(r, 4).text() or "0"),
                })
            except Exception:
                continue
        return lines

    def clear(self) -> None:
        self.table.setRowCount(0)
        self.product_search.clear()
        self.search_result.clear()
        self._update_totals()


class NewInvoiceDialog(QDialog):
    """نافذة إنشاء فاتورة جديدة."""

    def __init__(self, current_user, customer_repo, supplier_repo, product_repo,
                 inventory_repo, parent=None) -> None:
        super().__init__(parent)
        self._current_user = current_user
        self._customer_repo = customer_repo
        self._supplier_repo = supplier_repo
        self._product_repo = product_repo
        self._inventory_repo = inventory_repo
        self._setup_ui()
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

    def _setup_ui(self) -> None:
        self.setWindowTitle("فاتورة جديدة")
        self.resize(900, 700)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Top form
        form = QFormLayout()

        self.type_input = QComboBox()
        self.type_input.addItem("فاتورة بيع", userData=InvoiceType.SALE)
        self.type_input.addItem("فاتورة شراء", userData=InvoiceType.PURCHASE)
        self.type_input.currentIndexChanged.connect(self._on_type_changed)
        form.addRow("نوع الفاتورة:", self.type_input)

        self.party_input = QComboBox()
        self.party_input.setMinimumWidth(400)
        form.addRow("العميل/المورد:", self.party_input)

        self.is_cash_checkbox = QCheckBox("نقدية (لا آجل)")
        self.is_cash_checkbox.setChecked(True)
        form.addRow("طريقة الدفع:", self.is_cash_checkbox)

        self.due_days_input = QSpinBox()
        self.due_days_input.setRange(0, 365)
        self.due_days_input.setValue(30)
        self.due_days_input.setSuffix(" يوم")
        form.addRow("تاريخ الاستحقاق (آجل):", self.due_days_input)

        self.notes_input = QPlainTextEdit()
        self.notes_input.setMaximumHeight(60)
        form.addRow("ملاحظات:", self.notes_input)

        layout.addLayout(form)

        # Lines editor
        self.lines_editor = InvoiceLineEditor()
        self.lines_editor.set_product_search_callback(self._search_products)
        layout.addWidget(self.lines_editor)

        # Buttons
        buttons_layout = QHBoxLayout()

        self.save_button = QPushButton("💾 حفظ وترحيل")
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #6B8AFE; color: #FFFFFF;
                padding: 10px 24px; border-radius: 12px;
                font-weight: bold; font-size: 14px;
            }
            QPushButton:hover { background-color: #5A7AED; }
        """)
        self.save_button.clicked.connect(self.accept)
        buttons_layout.addWidget(self.save_button)

        cancel_btn = QPushButton("إلغاء")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #E4EBF5; color: #2D3748;
                padding: 10px 24px; border-radius: 12px;
                border: 1px solid #C3CAD7;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)

        self._load_parties()

    def _on_type_changed(self) -> None:
        """إعادة تحميل العملاء/الموردين حسب النوع."""
        self._load_parties()

    def _load_parties(self) -> None:
        """تحميل العملاء أو الموردين."""
        invoice_type = self.type_input.currentData()

        async def _load():
            if invoice_type == InvoiceType.SALE:
                parties = await self._customer_repo.list_all(skip=0, limit=1000)
            else:
                parties = await self._supplier_repo.list_all(skip=0, limit=1000)
            return parties

        self._worker = AsyncWorker(_load)
        self._worker.finished_signal.connect(self._on_parties_loaded)
        self._worker.error_signal.connect(lambda e: QMessageBox.critical(self, "خطأ", e))
        self._worker.start()

    def _on_parties_loaded(self, parties) -> None:
        self.party_input.clear()
        for p in parties:
            self.party_input.addItem(f"{p.code} - {p.name}", userData=p)

    def _search_products(self, query: str) -> None:
        if len(query) < 2:
            return

        async def _search():
            return await self._product_repo.search(query, limit=20)

        self._worker = AsyncWorker(_search)
        self._worker.finished_signal.connect(self.lines_editor.populate_search_results)
        self._worker.error_signal.connect(lambda e: print(f"Search error: {e}"))
        self._worker.start()

    def get_invoice_data(self) -> dict:
        """الحصول على بيانات الفاتورة للإنشاء."""
        from datetime import timedelta

        invoice_type = self.type_input.currentData()
        party = self.party_input.currentData()
        is_cash = self.is_cash_checkbox.isChecked()

        due_date = None
        if not is_cash and self.due_days_input.value() > 0:
            due_date = datetime.now() + timedelta(days=self.due_days_input.value())

        return {
            "invoice_type": invoice_type,
            "customer_id": party.id if invoice_type == InvoiceType.SALE else None,
            "supplier_id": party.id if invoice_type == InvoiceType.PURCHASE else None,
            "is_cash": is_cash,
            "due_date": due_date,
            "notes": self.notes_input.toPlainText().strip(),
            "lines": self.lines_editor.get_lines(),
        }


class InvoicesWindow(QWidget):
    """شاشة إدارة الفواتير."""

    def __init__(
        self, current_user, customer_repo, supplier_repo, product_repo,
        inventory_repo, invoice_repo, account_repo, journal_repo,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._current_user = current_user
        self._customer_repo = customer_repo
        self._supplier_repo = supplier_repo
        self._product_repo = product_repo
        self._inventory_repo = inventory_repo
        self._invoice_repo = invoice_repo
        self._account_repo = account_repo
        self._journal_repo = journal_repo
        self._worker: Optional[AsyncWorker] = None
        self._setup_ui()
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._load_invoices()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Top bar
        top_bar = QHBoxLayout()

        title = QLabel("📄 إدارة الفواتير")
        title.setStyleSheet("color: #2D3748; font-size: 20px; font-weight: bold;")
        top_bar.addWidget(title)

        top_bar.addStretch()

        self.filter_input = QComboBox()
        self.filter_input.addItem("كل الفواتير", userData=None)
        self.filter_input.addItem("فواتير البيع", userData=InvoiceType.SALE)
        self.filter_input.addItem("فواتير الشراء", userData=InvoiceType.PURCHASE)
        self.filter_input.currentIndexChanged.connect(self._load_invoices)
        top_bar.addWidget(self.filter_input)

        self.new_button = QPushButton("➕ فاتورة جديدة")
        self.new_button.setStyleSheet("""
            QPushButton {
                background-color: #68D391; color: #FFFFFF;
                padding: 8px 16px; border-radius: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #48BB78; }
        """)
        self.new_button.clicked.connect(self._on_new_clicked)
        top_bar.addWidget(self.new_button)

        layout.addLayout(top_bar)

        # Invoices table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "رقم الفاتورة", "النوع", "الطرف", "التاريخ", "الإجمالي الفرعي", "الضريبة", "الإجمالي", "الحالة",
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

        self.view_button = QPushButton("👁️ عرض")
        self.view_button.setStyleSheet("""
            QPushButton {
                background-color: #6B8AFE; color: #FFFFFF;
                padding: 8px 16px; border-radius: 12px;
            }
            QPushButton:hover { background-color: #5A7AED; }
            QPushButton:disabled { background-color: #A0AEC0; }
        """)
        self.view_button.clicked.connect(self._on_view_clicked)
        self.view_button.setEnabled(False)
        actions.addWidget(self.view_button)

        self.pdf_button = QPushButton("📄 تصدير PDF")
        self.pdf_button.setStyleSheet("""
            QPushButton {
                background-color: #B794F4; color: #FFFFFF;
                padding: 8px 16px; border-radius: 12px;
            }
            QPushButton:hover { background-color: #6D28D9; }
            QPushButton:disabled { background-color: #A0AEC0; }
        """)
        self.pdf_button.clicked.connect(self._on_pdf_clicked)
        self.pdf_button.setEnabled(False)
        actions.addWidget(self.pdf_button)

        self.cancel_button = QPushButton("❌ إلغاء الفاتورة")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #FC8181; color: #FFFFFF;
                padding: 8px 16px; border-radius: 12px;
            }
            QPushButton:hover { background-color: #E53E3E; }
            QPushButton:disabled { background-color: #A0AEC0; }
        """)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        self.cancel_button.setEnabled(False)
        actions.addWidget(self.cancel_button)

        actions.addStretch()

        self.refresh_button = QPushButton("🔄 تحديث")
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #E4EBF5; color: #2D3748;
                padding: 8px 16px; border-radius: 12px; border: 1px solid #C3CAD7;
            }
            QPushButton:hover { background-color: #E4EBF5; }
        """)
        self.refresh_button.clicked.connect(self._load_invoices)
        actions.addWidget(self.refresh_button)

        layout.addLayout(actions)

        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #A0AEC0; font-size: 11px;")
        layout.addWidget(self.status_label)

    def _load_invoices(self) -> None:
        self.status_label.setText("جارٍ التحميل...")
        invoice_type = self.filter_input.currentData()

        async def _load():
            return await self._invoice_repo.list_all(invoice_type=invoice_type, skip=0, limit=500)

        self._worker = AsyncWorker(_load)
        self._worker.finished_signal.connect(self._on_invoices_loaded)
        self._worker.error_signal.connect(self._on_error)
        self._worker.start()

    def _on_invoices_loaded(self, invoices) -> None:
        self.table.setRowCount(len(invoices))
        for i, inv in enumerate(invoices):
            self.table.setItem(i, 0, QTableWidgetItem(inv.invoice_no))
            type_text = "بيع" if inv.is_sale else ("شراء" if inv.is_purchase else "مرتجع")
            self.table.setItem(i, 1, QTableWidgetItem(type_text))
            # Will load party name async if needed
            self.table.setItem(i, 2, QTableWidgetItem("-"))
            self.table.setItem(i, 3, QTableWidgetItem(inv.issue_date.strftime("%Y-%m-%d")))
            sub_item = QTableWidgetItem(f"{inv.subtotal:,.2f}")
            sub_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 4, sub_item)
            tax_item = QTableWidgetItem(f"{inv.tax_amount:,.2f}")
            tax_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 5, tax_item)
            total_item = QTableWidgetItem(f"{inv.total:,.2f}")
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 6, total_item)
            status_text = {
                "DRAFT": "مسودة",
                "POSTED": "مرحّلة",
                "PAID_PARTIAL": "مدفوعة جزئيًا",
                "PAID_FULL": "مدفوعة",
                "CANCELLED": "ملغاة",
            }.get(inv.status.value, inv.status.value)
            status_item = QTableWidgetItem(status_text)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 7, status_item)

        self.status_label.setText(f"إجمالي الفواتير: {len(invoices)}")
        self.view_button.setEnabled(False)
        self.pdf_button.setEnabled(False)
        self.cancel_button.setEnabled(False)

        # Connect selection
        self.table.itemSelectionChanged.connect(self._on_selection_changed)

    def _on_selection_changed(self) -> None:
        has_selection = self.table.currentRow() >= 0
        self.view_button.setEnabled(has_selection)
        self.pdf_button.setEnabled(has_selection)
        self.cancel_button.setEnabled(has_selection)

    def _on_new_clicked(self) -> None:
        dialog = NewInvoiceDialog(
            current_user=self._current_user,
            customer_repo=self._customer_repo,
            supplier_repo=self._supplier_repo,
            product_repo=self._product_repo,
            inventory_repo=self._inventory_repo,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        data = dialog.get_invoice_data()
        if not data["lines"]:
            QMessageBox.warning(self, "تنبيه", "أضف بنودًا للفاتورة أولًا")
            return

        self._create_invoice(data)

    def _create_invoice(self, data: dict) -> None:
        from use_cases.invoices.invoice_use_cases import (
            CreateInvoiceUseCase, CreateInvoiceRequest, InvoiceLineDTO,
        )
        from use_cases.journal.journal_use_cases import (
            AutoJournalBuilder, CreateJournalEntryUseCase, PostJournalEntryUseCase,
        )

        async def _create():
            journal_builder = AutoJournalBuilder(self._account_repo)
            create_journal_uc = CreateJournalEntryUseCase(self._journal_repo, self._account_repo)
            post_journal_uc = PostJournalEntryUseCase(self._journal_repo)

            uc = CreateInvoiceUseCase(
                invoice_repo=self._invoice_repo,
                customer_repo=self._customer_repo,
                supplier_repo=self._supplier_repo,
                product_repo=self._product_repo,
                inventory_repo=self._inventory_repo,
                journal_builder=journal_builder,
                create_journal_uc=create_journal_uc,
                post_journal_uc=post_journal_uc,
            )

            line_dtos = [
                InvoiceLineDTO(
                    product_id=l["product_id"],
                    quantity=l["quantity"],
                    unit_price=l["unit_price"],
                    tax_rate=l["tax_rate"],
                    discount=l["discount"],
                )
                for l in data["lines"]
            ]

            request = CreateInvoiceRequest(
                invoice_type=data["invoice_type"],
                customer_id=data["customer_id"],
                supplier_id=data["supplier_id"],
                is_cash=data["is_cash"],
                due_date=data["due_date"],
                notes=data["notes"],
                lines=line_dtos,
            )
            return await uc.execute(request, self._current_user)

        self._worker = AsyncWorker(_create)
        self._worker.finished_signal.connect(lambda inv: (
            QMessageBox.information(
                self, "نجاح",
                f"تم إنشاء الفاتورة {inv.invoice_no} بنجاح\n"
                f"الإجمالي: {inv.total:,.2f} ر.س\n"
                f"القيد المحاسبي: {inv.journal_entry_id}"
            ),
            self._load_invoices(),
        ))
        self._worker.error_signal.connect(lambda e: QMessageBox.critical(self, "خطأ", e))
        self._worker.start()

    def _on_view_clicked(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        invoice_no = self.table.item(row, 0).text()

        async def _get():
            return await self._invoice_repo.get_by_no(invoice_no)

        def _show(invoice):
            if invoice is None:
                QMessageBox.warning(self, "تنبيه", "الفاتورة غير موجودة")
                return
            # Load party name
            party_name = "-"
            # Build info message
            msg = (
                f"رقم الفاتورة: {invoice.invoice_no}\n"
                f"النوع: {'بيع' if invoice.is_sale else 'شراء'}\n"
                f"التاريخ: {invoice.issue_date.strftime('%Y-%m-%d %H:%M')}\n"
                f"الحالة: {invoice.status.value}\n\n"
                f"البنود:\n"
            )
            for i, item in enumerate(invoice.items, 1):
                msg += f"  {i}. {item.description} - {item.quantity} × {item.unit_price} = {item.line_total:.2f}\n"
            msg += (
                f"\nالإجمالي الفرعي: {invoice.subtotal:,.2f}\n"
                f"الضريبة: {invoice.tax_amount:,.2f}\n"
                f"الخصم: {invoice.discount:,.2f}\n"
                f"الإجمالي: {invoice.total:,.2f} ر.س\n\n"
                f"القيد المحاسبي: {invoice.journal_entry_id or 'لا يوجد'}"
            )
            QMessageBox.information(self, f"تفاصيل الفاتورة {invoice_no}", msg)

        self._worker = AsyncWorker(_get)
        self._worker.finished_signal.connect(_show)
        self._worker.error_signal.connect(lambda e: QMessageBox.critical(self, "خطأ", e))
        self._worker.start()

    def _on_pdf_clicked(self) -> None:
        """تصدير الفاتورة إلى PDF."""
        row = self.table.currentRow()
        if row < 0:
            return
        invoice_no = self.table.item(row, 0).text()

        async def _get():
            invoice = await self._invoice_repo.get_by_no(invoice_no)
            if invoice is None:
                return None
            # Load party name
            party_name = "-"
            if invoice.customer_id:
                customer = await self._customer_repo.get_by_id(invoice.customer_id)
                if customer:
                    party_name = customer.name
            elif invoice.supplier_id:
                supplier = await self._supplier_repo.get_by_id(invoice.supplier_id)
                if supplier:
                    party_name = supplier.name

            # Load product names
            items_data = []
            for item in invoice.items:
                product = await self._product_repo.get_by_id(item.product_id)
                items_data.append({
                    "product_name": product.name if product else "-",
                    "quantity": str(item.quantity),
                    "unit_price": float(item.unit_price),
                    "tax_rate": float(item.tax_rate),
                    "discount": float(item.discount),
                    "line_total": float(item.line_total),
                })

            return {
                "invoice_no": invoice.invoice_no,
                "invoice_type": invoice.invoice_type.value,
                "issue_date": invoice.issue_date.isoformat(),
                "party_name": party_name,
                "status": invoice.status.value,
                "subtotal": float(invoice.subtotal),
                "tax_amount": float(invoice.tax_amount),
                "discount": float(invoice.discount),
                "total": float(invoice.total),
                "notes": invoice.notes,
                "items": items_data,
            }

        def _export(data):
            if data is None:
                QMessageBox.warning(self, "تنبيه", "الفاتورة غير موجودة")
                return
            from infrastructure.services.pdf_service import PDFService
            pdf = PDFService()
            company_data = {
                "name": settings.COMPANY_NAME,
                "address": settings.COMPANY_ADDRESS,
                "phone": settings.COMPANY_PHONE,
                "tax_number": settings.COMPANY_TAX_NUMBER,
            }
            path = pdf.export_invoice_pdf(data, company_data)
            QMessageBox.information(self, "تم التصدير", f"تم حفظ PDF في:\n{path}")

        self._worker = AsyncWorker(_get)
        self._worker.finished_signal.connect(_export)
        self._worker.error_signal.connect(lambda e: QMessageBox.critical(self, "خطأ", e))
        self._worker.start()

    def _on_cancel_clicked(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        invoice_no = self.table.item(row, 0).text()

        reply = QMessageBox.question(
            self, "تأكيد الإلغاء",
            f"هل تريد إلغاء الفاتورة '{invoice_no}'؟\nسيتم إنشاء قيد عكسي.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        from use_cases.invoices.invoice_use_cases import CancelInvoiceUseCase
        from use_cases.journal.journal_use_cases import ReverseJournalEntryUseCase

        async def _cancel():
            invoice = await self._invoice_repo.get_by_no(invoice_no)
            if invoice is None:
                return None
            reverse_uc = ReverseJournalEntryUseCase(self._journal_repo)
            uc = CancelInvoiceUseCase(self._invoice_repo, reverse_uc)
            return await uc.execute(invoice.id, self._current_user)

        self._worker = AsyncWorker(_cancel)
        self._worker.finished_signal.connect(lambda _: (
            QMessageBox.information(self, "نجاح", "تم إلغاء الفاتورة بقيد عكسي"),
            self._load_invoices(),
        ))
        self._worker.error_signal.connect(lambda e: QMessageBox.critical(self, "خطأ", e))
        self._worker.start()

    def _on_export_excel(self) -> None:
        """تصدير الفواتير إلى Excel."""
        try:
            from infrastructure.ui.services.ui_service_integration import export_to_excel

            async def _get_data():
                invoices = await self._invoice_repo.list_all(skip=0, limit=10000)
                return [{
                    "invoice_no": inv.invoice_no,
                    "invoice_type": inv.invoice_type.value,
                    "issue_date": inv.issue_date.strftime("%Y-%m-%d") if inv.issue_date else "",
                    "subtotal": float(inv.subtotal),
                    "tax_amount": float(inv.tax_amount),
                    "total": float(inv.total),
                    "status": inv.status.value,
                } for inv in invoices]

            from infrastructure.ui.windows._async_worker import AsyncWorker

            def _do_export(invoices_data):
                export_to_excel("invoices", invoices_data, parent=self)

            self._worker = AsyncWorker(_get_data)
            self._worker.finished_signal.connect(_do_export)
            self._worker.error_signal.connect(lambda e: self._on_error(e))
            self._worker.start()
        except Exception as e:
            self._on_error(str(e))

    def _on_error(self, error_msg: str) -> None:
        self.status_label.setText(f"⚠ خطأ: {error_msg}")
