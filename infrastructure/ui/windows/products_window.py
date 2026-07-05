"""
Products Window - شاشة إدارة المنتجات والمخزون
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
    QFormLayout, QDialogButtonBox, QComboBox, QDoubleSpinBox, QSpinBox,
    QCheckBox, QGroupBox, QPlainTextEdit, QTabWidget,
)

try:
    import qtawesome as qta
except ImportError:
    qta = None

from infrastructure.ui.windows._async_worker import AsyncWorker


class ProductFormDialog(QDialog):
    """نموذج إضافة/تعديل منتج."""

    def __init__(self, parent=None, product_data: Optional[dict] = None) -> None:
        super().__init__(parent)
        self._product_data = product_data
        self._setup_ui()
        if product_data:
            self._fill_form(product_data)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        # Apply Soft UI automatically
        try:
            from infrastructure.ui.theme.soft_auto import auto_apply_soft_ui
            auto_apply_soft_ui(self)
        except Exception:
            pass

    def _setup_ui(self) -> None:
        self.setWindowTitle("بيانات المنتج")
        self.setFixedSize(600, 720)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(8)

        self.sku_input = QLineEdit()
        self.sku_input.setPlaceholderText("PROD-001")
        form.addRow("SKU *:", self.sku_input)

        self.barcode_input = QLineEdit()
        form.addRow("الباركود:", self.barcode_input)

        self.name_input = QLineEdit()
        form.addRow("الاسم *:", self.name_input)

        self.name_en_input = QLineEdit()
        form.addRow("الاسم (إنجليزي):", self.name_en_input)

        self.category_input = QLineEdit()
        self.category_input.setPlaceholderText("إلكترونيات، ملابس، إلخ")
        form.addRow("التصنيف:", self.category_input)

        self.unit_input = QComboBox()
        self.unit_input.addItems(["piece", "kg", "liter", "box", "meter", "pack"])
        form.addRow("الوحدة:", self.unit_input)

        self.cost_price_input = QDoubleSpinBox()
        self.cost_price_input.setRange(0, 999999999)
        self.cost_price_input.setDecimals(2)
        self.cost_price_input.setSuffix(" ر.س")
        form.addRow("سعر التكلفة:", self.cost_price_input)

        self.sale_price_input = QDoubleSpinBox()
        self.sale_price_input.setRange(0, 999999999)
        self.sale_price_input.setDecimals(2)
        self.sale_price_input.setSuffix(" ر.س")
        form.addRow("سعر البيع:", self.sale_price_input)

        self.tax_rate_input = QDoubleSpinBox()
        self.tax_rate_input.setRange(0, 100)
        self.tax_rate_input.setDecimals(2)
        self.tax_rate_input.setValue(15.0)
        self.tax_rate_input.setSuffix(" %")
        form.addRow("نسبة الضريبة:", self.tax_rate_input)

        self.min_stock_input = QDoubleSpinBox()
        self.min_stock_input.setRange(0, 999999999)
        self.min_stock_input.setDecimals(2)
        form.addRow("الحد الأدنى للمخزون:", self.min_stock_input)

        self.description_input = QPlainTextEdit()
        self.description_input.setMaximumHeight(80)
        form.addRow("الوصف:", self.description_input)

        # Profit margin label (auto-calculated)
        self.margin_label = QLabel("-")
        self.margin_label.setStyleSheet("color: #68D391; font-weight: bold;")
        form.addRow("هامش الربح:", self.margin_label)

        # Connect price changes to margin calculation
        self.cost_price_input.valueChanged.connect(self._update_margin)
        self.sale_price_input.valueChanged.connect(self._update_margin)

        layout.addLayout(form)

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
        """)

    def _update_margin(self) -> None:
        cost = self.cost_price_input.value()
        sale = self.sale_price_input.value()
        if cost > 0:
            margin = ((sale - cost) / cost) * 100
            self.margin_label.setText(f"{margin:.2f}%")
            color = "#68D391" if margin >= 0 else "#FC8181"
            self.margin_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        else:
            self.margin_label.setText("-")

    def _fill_form(self, data: dict) -> None:
        self.sku_input.setText(data.get("sku", ""))
        self.sku_input.setEnabled(False)
        self.barcode_input.setText(data.get("barcode", ""))
        self.name_input.setText(data.get("name", ""))
        self.name_en_input.setText(data.get("name_en", ""))
        self.category_input.setText(data.get("category", ""))
        if data.get("unit") in ["piece", "kg", "liter", "box", "meter", "pack"]:
            self.unit_input.setCurrentText(data["unit"])
        self.cost_price_input.setValue(float(data.get("cost_price", 0)))
        self.sale_price_input.setValue(float(data.get("sale_price", 0)))
        self.tax_rate_input.setValue(float(data.get("tax_rate", 15)))
        self.min_stock_input.setValue(float(data.get("min_stock_level", 0)))
        self.description_input.setPlainText(data.get("description", ""))
        self._update_margin()

    def get_data(self) -> dict:
        return {
            "sku": self.sku_input.text().strip(),
            "barcode": self.barcode_input.text().strip(),
            "name": self.name_input.text().strip(),
            "name_en": self.name_en_input.text().strip(),
            "category": self.category_input.text().strip(),
            "unit": self.unit_input.currentText(),
            "cost_price": Decimal(str(self.cost_price_input.value())),
            "sale_price": Decimal(str(self.sale_price_input.value())),
            "tax_rate": Decimal(str(self.tax_rate_input.value())),
            "min_stock_level": Decimal(str(self.min_stock_input.value())),
            "description": self.description_input.toPlainText().strip(),
        }


class ProductsWindow(QWidget):
    """شاشة إدارة المنتجات."""

    def __init__(self, current_user, product_repo, inventory_repo, parent=None) -> None:
        super().__init__(parent)
        self._current_user = current_user
        self._product_repo = product_repo
        self._inventory_repo = inventory_repo
        self._worker: Optional[AsyncWorker] = None
        self._setup_ui()
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._load_products()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Top bar
        top_bar = QHBoxLayout()

        title = QLabel("📦 إدارة المنتجات والمخزون")
        title.setStyleSheet("color: #2D3748; font-size: 20px; font-weight: bold;")
        top_bar.addWidget(title)

        top_bar.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 بحث بالاسم أو SKU أو الباركود...")
        self.search_input.setMinimumWidth(300)
        self.search_input.textChanged.connect(self._on_search_changed)
        top_bar.addWidget(self.search_input)

        self.add_button = QPushButton("➕ إضافة منتج")
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

        # Tabs: All Products | Low Stock Alerts
        tabs = QTabWidget()

        # Tab 1: All products
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "SKU", "الاسم", "التصنيف", "سعر التكلفة", "سعر البيع", "هامش الربح", "المخزون", "الحالة",
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
        tabs.addTab(self.table, "كل المنتجات")

        # Tab 2: Low stock alerts
        self.low_stock_table = QTableWidget()
        self.low_stock_table.setColumnCount(5)
        self.low_stock_table.setHorizontalHeaderLabels([
            "SKU", "الاسم", "المخزون الحالي", "الحد الأدنى", "النقص",
        ])
        self.low_stock_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.low_stock_table.setAlternatingRowColors(True)
        self.low_stock_table.setStyleSheet(self.table.styleSheet())
        tabs.addTab(self.low_stock_table, "⚠️ تنبيهات المخزون")

        layout.addWidget(tabs)

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
        self.edit_button.clicked.connect(self._on_edit_clicked)
        self.edit_button.setEnabled(False)
        actions.addWidget(self.edit_button)

        self.adjust_button = QPushButton("🔄 تسوية مخزون")
        self.adjust_button.setStyleSheet("""
            QPushButton {
                background-color: #F6AD55; color: #FFFFFF;
                padding: 8px 16px; border-radius: 12px;
            }
            QPushButton:hover { background-color: #ED8936; }
            QPushButton:disabled { background-color: #A0AEC0; }
        """)
        self.adjust_button.clicked.connect(self._on_adjust_clicked)
        self.adjust_button.setEnabled(False)
        actions.addWidget(self.adjust_button)

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
        self.refresh_button.clicked.connect(self._load_products)
        actions.addWidget(self.refresh_button)

        layout.addLayout(actions)

        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #A0AEC0; font-size: 11px;")
        layout.addWidget(self.status_label)

    def _load_products(self) -> None:
        self.status_label.setText("جارٍ التحميل...")

        async def _load():
            products = await self._product_repo.list_all(skip=0, limit=1000)
            # Get balances for each product
            result = []
            for p in products:
                balance = await self._inventory_repo.get_balance(p.id)
                result.append((p, balance))
            # Get low stock
            low_stock = await self._inventory_repo.get_low_stock_products()
            return result, low_stock

        self._worker = AsyncWorker(_load)
        self._worker.finished_signal.connect(self._on_products_loaded)
        self._worker.error_signal.connect(self._on_error)
        self._worker.start()

    def _on_products_loaded(self, data) -> None:
        products_with_balances, low_stock = data

        # All products table
        self.table.setRowCount(len(products_with_balances))
        for i, (p, balance) in enumerate(products_with_balances):
            self.table.setItem(i, 0, QTableWidgetItem(p.sku))
            self.table.setItem(i, 1, QTableWidgetItem(p.name))
            self.table.setItem(i, 2, QTableWidgetItem(p.category))
            cost_item = QTableWidgetItem(f"{p.cost_price:,.2f}")
            cost_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 3, cost_item)
            sale_item = QTableWidgetItem(f"{p.sale_price:,.2f}")
            sale_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 4, sale_item)
            margin = float(p.profit_margin())
            margin_item = QTableWidgetItem(f"{margin:.1f}%")
            margin_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            color = "#68D391" if margin >= 0 else "#FC8181"
            margin_item.setForeground(Qt.GlobalColor.green if margin >= 30 else (
                Qt.GlobalColor.darkYellow if margin >= 10 else Qt.GlobalColor.red
            ))
            self.table.setItem(i, 5, margin_item)
            stock_item = QTableWidgetItem(f"{balance:.2f} {p.unit}")
            stock_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # Color: red if below minimum
            if p.min_stock_level > 0 and balance < float(p.min_stock_level):
                stock_item.setForeground(Qt.GlobalColor.red)
            self.table.setItem(i, 6, stock_item)
            status_item = QTableWidgetItem("✓ نشط" if p.is_active else "✗ معطّل")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 7, status_item)

        # Low stock table
        self.low_stock_table.setRowCount(len(low_stock))
        for i, (product, balance) in enumerate(low_stock):
            self.low_stock_table.setItem(i, 0, QTableWidgetItem(product.sku))
            self.low_stock_table.setItem(i, 1, QTableWidgetItem(product.name))
            bal_item = QTableWidgetItem(f"{balance:.2f}")
            bal_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            bal_item.setForeground(Qt.GlobalColor.red)
            self.low_stock_table.setItem(i, 2, bal_item)
            min_item = QTableWidgetItem(f"{product.min_stock_level:.2f}")
            min_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.low_stock_table.setItem(i, 3, min_item)
            shortage = float(product.min_stock_level) - balance
            short_item = QTableWidgetItem(f"{shortage:.2f}")
            short_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            short_item.setForeground(Qt.GlobalColor.red)
            self.low_stock_table.setItem(i, 4, short_item)

        self.status_label.setText(
            f"إجمالي المنتجات: {len(products_with_balances)} | "
            f"⚠️ تنبيهات نقص المخزون: {len(low_stock)}"
        )

    def _on_search_changed(self, text: str) -> None:
        if len(text) < 2:
            self._load_products()
            return
        QTimer.singleShot(300, lambda: self._do_search(text))

    def _do_search(self, text: str) -> None:
        async def _search():
            return await self._product_repo.search(text, limit=50)

        self._worker = AsyncWorker(_search)
        self._worker.finished_signal.connect(self._on_search_results)
        self._worker.error_signal.connect(self._on_error)
        self._worker.start()

    def _on_search_results(self, products) -> None:
        self.table.setRowCount(len(products))
        for i, p in enumerate(products):
            self.table.setItem(i, 0, QTableWidgetItem(p.sku))
            self.table.setItem(i, 1, QTableWidgetItem(p.name))
            self.table.setItem(i, 2, QTableWidgetItem(p.category))
            self.table.setItem(i, 3, QTableWidgetItem(f"{p.cost_price:,.2f}"))
            self.table.setItem(i, 4, QTableWidgetItem(f"{p.sale_price:,.2f}"))
            self.table.setItem(i, 5, QTableWidgetItem(f"{float(p.profit_margin()):.1f}%"))
            self.table.setItem(i, 6, QTableWidgetItem("-"))  # No balance loaded
            self.table.setItem(i, 7, QTableWidgetItem("✓ نشط" if p.is_active else "✗ معطّل"))

    def _on_row_double_clicked(self, index) -> None:
        self.edit_button.setEnabled(True)
        self.adjust_button.setEnabled(True)
        self.delete_button.setEnabled(True)

    def _on_add_clicked(self) -> None:
        dialog = ProductFormDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            self._create_product(data)

    def _create_product(self, data: dict) -> None:
        from use_cases.products.product_use_cases import (
            CreateProductUseCase, CreateProductRequest,
        )

        async def _create():
            uc = CreateProductUseCase(self._product_repo)
            req = CreateProductRequest(**data)
            return await uc.execute(req, self._current_user)

        self._worker = AsyncWorker(_create)
        self._worker.finished_signal.connect(lambda _: (
            QMessageBox.information(self, "نجاح", "تم إنشاء المنتج بنجاح"),
            self._load_products(),
        ))
        self._worker.error_signal.connect(lambda e: QMessageBox.critical(self, "خطأ", e))
        self._worker.start()

    def _on_edit_clicked(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        sku = self.table.item(row, 0).text()

        async def _do_edit():
            product = await self._product_repo.get_by_sku(sku)
            if product is None:
                return None
            dialog = ProductFormDialog(self, {
                "sku": product.sku,
                "barcode": product.barcode,
                "name": product.name,
                "name_en": product.name_en,
                "category": product.category,
                "unit": product.unit,
                "cost_price": product.cost_price,
                "sale_price": product.sale_price,
                "tax_rate": product.tax_rate,
                "min_stock_level": product.min_stock_level,
                "description": product.description,
            })
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return None
            return dialog.get_data()

        self._worker = AsyncWorker(_do_edit)

        def _on_data(data):
            if data is None:
                return
            self._update_product(sku, data)

        self._worker.finished_signal.connect(_on_data)
        self._worker.error_signal.connect(lambda e: QMessageBox.critical(self, "خطأ", e))
        self._worker.start()

    def _update_product(self, sku: str, data: dict) -> None:
        from use_cases.products.product_use_cases import (
            UpdateProductUseCase, UpdateProductRequest,
        )

        async def _update():
            product = await self._product_repo.get_by_sku(sku)
            if product is None:
                return None
            uc = UpdateProductUseCase(self._product_repo)
            req = UpdateProductRequest(
                product_id=product.id,
                name=data.get("name"),
                barcode=data.get("barcode"),
                description=data.get("description"),
                category=data.get("category"),
                cost_price=data.get("cost_price"),
                sale_price=data.get("sale_price"),
                tax_rate=data.get("tax_rate"),
                min_stock_level=data.get("min_stock_level"),
            )
            return await uc.execute(req, self._current_user)

        self._worker = AsyncWorker(_update)
        self._worker.finished_signal.connect(lambda _: (
            QMessageBox.information(self, "نجاح", "تم تحديث المنتج"),
            self._load_products(),
        ))
        self._worker.error_signal.connect(lambda e: QMessageBox.critical(self, "خطأ", e))
        self._worker.start()

    def _on_adjust_clicked(self) -> None:
        """فتح نافذة تسوية المخزون."""
        row = self.table.currentRow()
        if row < 0:
            return
        sku = self.table.item(row, 0).text()
        name = self.table.item(row, 1).text()
        current_stock_text = self.table.item(row, 6).text().split()[0] if self.table.item(row, 6) else "0"

        from PySide6.QtWidgets import QInputDialog
        new_qty, ok = QInputDialog.getDouble(
            self, "تسوية المخزون",
            f"المنتج: {name}\nالمخزون الحالي: {current_stock_text}\n\nأدخل الكمية الجديدة:",
            value=float(current_stock_text), decimals=2, minimum=0, maximum=999999999,
        )
        if not ok:
            return

        reason, ok2 = QInputDialog.getText(
            self, "سبب التسوية",
            "سبب التسوية (جرد، تالف، خطأ، إلخ):",
        )
        if not ok2 or not reason.strip():
            return

        from use_cases.products.product_use_cases import AdjustInventoryUseCase

        async def _adjust():
            product = await self._product_repo.get_by_sku(sku)
            if product is None:
                return None
            uc = AdjustInventoryUseCase(self._product_repo, self._inventory_repo)
            return await uc.execute(
                product.id, Decimal(str(new_qty)), reason.strip(), self._current_user,
            )

        self._worker = AsyncWorker(_adjust)
        self._worker.finished_signal.connect(lambda _: (
            QMessageBox.information(self, "نجاح", "تم تسوية المخزون"),
            self._load_products(),
        ))
        self._worker.error_signal.connect(lambda e: QMessageBox.critical(self, "خطأ", e))
        self._worker.start()

    def _on_delete_clicked(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        sku = self.table.item(row, 0).text()
        name = self.table.item(row, 1).text()

        reply = QMessageBox.question(
            self, "تأكيد الحذف",
            f"هل تريد حذف المنتج '{name}'؟\nسيتم تعطيله (لن يُحذف فعليًا).",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        from use_cases.products.product_use_cases import DeleteProductUseCase

        async def _delete():
            product = await self._product_repo.get_by_sku(sku)
            if product is None:
                return False
            uc = DeleteProductUseCase(self._product_repo)
            return await uc.execute(product.id, self._current_user)

        self._worker = AsyncWorker(_delete)
        self._worker.finished_signal.connect(lambda _: (
            QMessageBox.information(self, "نجاح", "تم حذف المنتج"),
            self._load_products(),
        ))
        self._worker.error_signal.connect(lambda e: QMessageBox.critical(self, "خطأ", e))
        self._worker.start()

    def _on_export_excel(self) -> None:
        """تصدير المنتجات إلى Excel."""
        try:
            from infrastructure.ui.services.ui_service_integration import export_to_excel

            async def _get_data():
                products = await self._product_repo.list_all(skip=0, limit=10000)
                return [{
                    "sku": p.sku, "barcode": p.barcode, "name": p.name,
                    "category": p.category, "unit": p.unit,
                    "cost_price": float(p.cost_price), "sale_price": float(p.sale_price),
                    "tax_rate": float(p.tax_rate), "min_stock_level": float(p.min_stock_level),
                } for p in products]

            from infrastructure.ui.windows._async_worker import AsyncWorker

            def _do_export(data):
                export_to_excel("products", data, parent=self)

            self._worker = AsyncWorker(_get_data)
            self._worker.finished_signal.connect(_do_export)
            self._worker.error_signal.connect(lambda e: self._on_error(e))
            self._worker.start()
        except Exception as e:
            self._on_error(str(e))

    def _on_error(self, error_msg: str) -> None:
        self.status_label.setText(f"⚠ خطأ: {error_msg}")
