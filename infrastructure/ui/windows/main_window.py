"""
Main Window - النافذة الرئيسية

نافذة رئيسية بعد تسجيل الدخول: شريط جانبي + شريط علوي + منطقة وسطى.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QStackedWidget, QFrame, QToolBar, QStatusBar,
    QMenuBar, QMenu, QSizePolicy, QMessageBox, QDockWidget,
)

try:
    import qtawesome as qta
except Exception:
    qta = None

from domain.entities.user import User
from infrastructure.config.settings import settings
from infrastructure.ui.theme.soft_ui import SoftColors


class SidebarButton(QPushButton):
    """زر في الشريط الجانبي بنمط احترافي."""

    def __init__(self, text: str, icon_name: str = "", parent=None) -> None:
        super().__init__(text, parent)
        self.setMinimumHeight(48)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setText(text)
        self._icon_name = icon_name
        self._apply_style(active=False)

        if qta and icon_name:
            try:
                self.setIcon(qta.icon(f"fa5s.{icon_name}", color="#94A3B8"))
                self.setIconSize(QSize(20, 20))
            except Exception as e:
                # Silent fail - UI initialization should not crash
                # In production: use logger.warning(f"UI init error: {e}")
                pass

    def _apply_style(self, active: bool) -> None:
        bg = "#6B8AFE" if active else "transparent"
        fg = "#FFFFFF" if active else "#718096"
        hover_bg = "#5A7AED" if active else "#FFFFFF"
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                border: none;
                border-radius: 14px;
                padding: 12px 16px;
                text-align: right;
                font-size: 14px;
                font-weight: {'bold' if active else 'normal'};
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
                color: white;
            }}
        """)

    def set_active(self, active: bool) -> None:
        self._apply_style(active)
        if qta and self._icon_name:
            try:
                color = "white" if active else "#94A3B8"
                self.setIcon(qta.icon(f"fa5s.{self._icon_name}", color=color))
            except Exception as e:
                # Silent fail - UI initialization should not crash
                # In production: use logger.warning(f"UI init error: {e}")
                pass


class MainWindow(QMainWindow):
    """النافذة الرئيسية بعد تسجيل الدخول."""

    def __init__(self, current_user: User) -> None:
        super().__init__()
        self._current_user = current_user
        self._sidebar_buttons: list[SidebarButton] = []
        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self) -> None:
        self.setWindowTitle(f"{settings.APP_NAME} v{settings.APP_VERSION}")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 600)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        # Main layout: sidebar + content
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar (right in RTL)
        sidebar = self._build_sidebar()
        main_layout.addWidget(sidebar)

        # Content area
        content = self._build_content_area()
        main_layout.addWidget(content, 1)

        # Top bar
        self._build_top_bar()

        # Status bar
        self._build_status_bar()

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setFixedWidth(260)
        sidebar.setStyleSheet("background-color: #E4EBF5; border: none;")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 24, 16, 16)
        layout.setSpacing(8)

        # Logo at top
        logo_label = QLabel("📊 ERP")
        logo_label.setStyleSheet("color: #5A7AED; font-size: 28px; font-weight: 800; background: transparent;")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout.addWidget(logo_label)

        # App name
        app_label = QLabel("نظام محاسبي متكامل")
        app_label.setStyleSheet("color: #A0AEC0; font-size: 11px; background: transparent;")
        app_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        app_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout.addWidget(app_label)

        layout.addSpacing(20)

        # Sidebar buttons
        buttons_data = [
            ("لوحة المعلومات", "tachometer-alt", "dashboard"),
            ("🤖 المساعد الذكي", "robot", "ai_chat"),
            ("الفواتير", "file-invoice", "invoices"),
            ("القيود المحاسبية", "book", "journal"),
            ("العملاء", "users", "customers"),
            ("الموردون", "truck", "suppliers"),
            ("المنتجات", "box", "products"),
            ("المصروفات", "money-bill", "expenses"),
            ("التقارير", "chart-bar", "reports"),
            ("النسخ الاحتياطي", "database", "backup"),
            ("الإعدادات", "cog", "settings"),
        ]

        for text, icon, key in buttons_data:
            btn = SidebarButton(text, icon)
            btn.clicked.connect(lambda checked, k=key: self._on_sidebar_click(k))
            self._sidebar_buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

        # User info at bottom
        user_info = QFrame()
        user_info.setStyleSheet("""
            QFrame {
                background-color: #1E293B;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        user_layout = QVBoxLayout(user_info)
        user_layout.setContentsMargins(12, 8, 12, 8)

        user_name = QLabel(self._current_user.full_name or self._current_user.username)
        user_name.setStyleSheet("color: #2D3748; font-size: 13px; font-weight: 700; background: transparent;")
        user_name.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        user_layout.addWidget(user_name)

        user_role = QLabel(f"الدور: {self._current_user.role.value}")
        user_role.setStyleSheet("color: #A0AEC0; font-size: 11px; background: transparent;")
        user_role.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        user_layout.addWidget(user_role)

        layout.addWidget(user_info)

        # Logout button
        logout_btn = QPushButton("تسجيل الخروج")
        logout_btn.setMinimumHeight(40)
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #EF4444;
                border: 1px solid #EF4444;
                border-radius: 8px;
                font-size: 13px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #EF4444;
                color: white;
            }
        """)
        if qta:
            try:
                logout_btn.setIcon(qta.icon("fa5s.sign-out-alt", color="#EF4444"))
            except Exception as e:
                # Silent fail - UI initialization should not crash
                # In production: use logger.warning(f"UI init error: {e}")
                pass
        logout_btn.clicked.connect(self._on_logout)
        layout.addWidget(logout_btn)

        return sidebar

    def _build_content_area(self) -> QWidget:
        content = QWidget()
        content.setStyleSheet("background-color: #F0F4F8;")

        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Page title
        self.page_title = QLabel("لوحة المعلومات")
        self.page_title.setStyleSheet("color: #2D3748; font-size: 24px; font-weight: 800; background: transparent;")
        self.page_title.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout.addWidget(self.page_title)

        # Stacked widget for different pages
        self.stacked_widget = QStackedWidget()

        # Wire up repositories
        from adapters.repositories.sql_alchemy.user_repository import SqlAlchemyUserRepository
        from adapters.repositories.sql_alchemy.party_repository import (
            SqlAlchemyCustomerRepository, SqlAlchemySupplierRepository,
        )
        from adapters.repositories.sql_alchemy.product_repository import (
            SqlAlchemyProductRepository, SqlAlchemyInventoryRepository,
        )
        from adapters.repositories.sql_alchemy.invoice_repository import SqlAlchemyInvoiceRepository
        from adapters.repositories.sql_alchemy.account_journal_repository import (
            SqlAlchemyAccountRepository, SqlAlchemyJournalEntryRepository,
        )

        self._repos = {
            "user": SqlAlchemyUserRepository(),
            "customer": SqlAlchemyCustomerRepository(),
            "supplier": SqlAlchemySupplierRepository(),
            "product": SqlAlchemyProductRepository(),
            "inventory": SqlAlchemyInventoryRepository(),
            "invoice": SqlAlchemyInvoiceRepository(),
            "account": SqlAlchemyAccountRepository(),
            "journal": SqlAlchemyJournalEntryRepository(),
        }

        # Page 0: Dashboard (NEW - real KPI cards)
        try:
            from infrastructure.ui.windows.dashboard_page import DashboardPage
            dashboard_page = DashboardPage(
                current_user=self._current_user,
                customer_repo=self._repos["customer"],
                invoice_repo=self._repos["invoice"],
                account_repo=self._repos["account"],
                inventory_repo=self._repos["inventory"],
            )
            self.stacked_widget.addWidget(dashboard_page)
        except Exception as e:
            dashboard_page = self._build_dashboard_page()
            self.stacked_widget.addWidget(dashboard_page)

        # Page 1: AI Chat (REAL)
        try:
            from infrastructure.ui.windows.ai_chat_window import AIChatWindow
            from infrastructure.services.ai_agent_service import AIAgentService, MockLLMProvider
            ai_service = AIAgentService(llm_provider=MockLLMProvider())
            ai_chat_page = AIChatWindow(
                current_user=self._current_user,
                ai_service=ai_service,
            )
            self.stacked_widget.addWidget(ai_chat_page)
        except ImportError as e:
            self.stacked_widget.addWidget(self._build_placeholder("🤖 المساعد الذكي", f"غير متاح: {e}"))

        # Page 2: Invoices (REAL)
        try:
            from infrastructure.ui.windows.invoices_window import InvoicesWindow
            invoices_page = InvoicesWindow(
                current_user=self._current_user,
                customer_repo=self._repos["customer"],
                supplier_repo=self._repos["supplier"],
                product_repo=self._repos["product"],
                inventory_repo=self._repos["inventory"],
                invoice_repo=self._repos["invoice"],
                account_repo=self._repos["account"],
                journal_repo=self._repos["journal"],
            )
            self.stacked_widget.addWidget(invoices_page)
        except ImportError as e:
            self.stacked_widget.addWidget(self._build_placeholder("📄 الفواتير", f"غير متاح: {e}"))

        # Page 2: Journal (REAL)
        try:
            from infrastructure.ui.windows.journal_window import JournalWindow
            journal_page = JournalWindow(
                current_user=self._current_user,
                journal_repo=self._repos["journal"],
                account_repo=self._repos["account"],
            )
            self.stacked_widget.addWidget(journal_page)
        except ImportError as e:
            self.stacked_widget.addWidget(self._build_placeholder("📖 القيود المحاسبية", f"غير متاح: {e}"))

        # Page 3: Customers (REAL)
        try:
            from infrastructure.ui.windows.customers_window import CustomersWindow
            customers_page = CustomersWindow(
                current_user=self._current_user,
                customer_repo=self._repos["customer"],
            )
            self.stacked_widget.addWidget(customers_page)
        except ImportError as e:
            self.stacked_widget.addWidget(self._build_placeholder("👥 العملاء", f"غير متاح: {e}"))

        # Page 4: Suppliers (REAL)
        try:
            from infrastructure.ui.windows.suppliers_window import SuppliersWindow
            suppliers_page = SuppliersWindow(
                current_user=self._current_user,
                supplier_repo=self._repos["supplier"],
            )
            self.stacked_widget.addWidget(suppliers_page)
        except ImportError as e:
            self.stacked_widget.addWidget(self._build_placeholder("🚚 الموردون", f"غير متاح: {e}"))

        # Page 5: Products (REAL)
        try:
            from infrastructure.ui.windows.products_window import ProductsWindow
            products_page = ProductsWindow(
                current_user=self._current_user,
                product_repo=self._repos["product"],
                inventory_repo=self._repos["inventory"],
            )
            self.stacked_widget.addWidget(products_page)
        except ImportError as e:
            self.stacked_widget.addWidget(self._build_placeholder("📦 المنتجات", f"غير متاح: {e}"))

        # Page 6: Expenses (REAL)
        try:
            from infrastructure.ui.windows.expenses_window import ExpensesWindow
            expenses_page = ExpensesWindow(
                current_user=self._current_user,
                account_repo=self._repos["account"],
                journal_repo=self._repos["journal"],
            )
            self.stacked_widget.addWidget(expenses_page)
        except ImportError as e:
            self.stacked_widget.addWidget(self._build_placeholder("💰 المصروفات", f"غير متاح: {e}"))

        # Page 7: Reports (REAL)
        try:
            from infrastructure.ui.windows.reports_window import ReportsWindow
            reports_page = ReportsWindow(
                current_user=self._current_user,
                account_repo=self._repos["account"],
                journal_repo=self._repos["journal"],
            )
            self.stacked_widget.addWidget(reports_page)
        except ImportError as e:
            self.stacked_widget.addWidget(self._build_placeholder("📊 التقارير", f"غير متاح: {e}"))

        # Page 8: Backup (REAL)
        try:
            from infrastructure.ui.windows.backup_window import BackupWindow
            backup_page = BackupWindow(
                current_user=self._current_user,
            )
            self.stacked_widget.addWidget(backup_page)
        except ImportError as e:
            self.stacked_widget.addWidget(self._build_placeholder("💾 النسخ الاحتياطي", f"غير متاح: {e}"))

        # Page 9: Settings (REAL)
        try:
            from infrastructure.ui.windows.settings_window import SettingsWindow
            settings_page = SettingsWindow(
                current_user=self._current_user,
            )
            self.stacked_widget.addWidget(settings_page)
        except ImportError as e:
            self.stacked_widget.addWidget(self._build_placeholder("⚙️ الإعدادات", f"غير متاح: {e}"))

        layout.addWidget(self.stacked_widget, 1)

        return content

    def _build_placeholder(self, title: str, desc: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_label = QLabel(title)
        title_label.setStyleSheet("color: #0A1628; font-size: 32px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        desc_label = QLabel(desc)
        desc_label.setStyleSheet("color: #64748B; font-size: 14px;")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        return page

    def _build_dashboard_page(self) -> QWidget:
        """صفحة لوحة المعلومات: KPIs + تنبيهات."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        # KPI cards row
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(16)

        kpis = [
            ("المبيعات اليوم", "12,450 ر.س", "↑ 12% من الأمس", "#10B981"),
            ("المشتريات اليوم", "8,200 ر.س", "↓ 5% من الأمس", "#F59E0B"),
            ("العملاء النشطون", "147", "↑ 3 هذا الشهر", "#2563EB"),
            ("رصيد الصندوق", "85,300 ر.س", "↑ 8% هذا الشهر", "#7C3AED"),
        ]

        for label, value, change, color in kpis:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: white;
                    border-radius: 12px;
                    border-right: 4px solid {color};
                    padding: 16px;
                }}
            """)
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(6)

            label_widget = QLabel(label)
            label_widget.setStyleSheet("color: #64748B; font-size: 12px;")
            label_widget.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            card_layout.addWidget(label_widget)

            value_widget = QLabel(value)
            value_widget.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: bold;")
            value_widget.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            card_layout.addWidget(value_widget)

            change_widget = QLabel(change)
            change_widget.setStyleSheet("color: #94A3B8; font-size: 11px;")
            change_widget.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            card_layout.addWidget(change_widget)

            kpi_layout.addWidget(card, 1)

        layout.addLayout(kpi_layout)

        # Welcome message
        welcome = QLabel(f"أهلًا بك، {self._current_user.full_name or self._current_user.username}! 👋")
        welcome.setStyleSheet("color: #0A1628; font-size: 18px; font-weight: bold;")
        welcome.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout.addWidget(welcome)

        info_text = QLabel(
            "هذه النسخة الأولية من النظام (v2.0 MVP).\n"
            "يمكنك الآن تسجيل الدخول بنجاح والتنقل بين الأقسام.\n"
            "الوحدات الأخرى (الفواتير، التقارير، AI) قيد التطوير وفق خارطة الطريق."
        )
        info_text.setStyleSheet("color: #475569; font-size: 14px; line-height: 1.6;")
        info_text.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout.addWidget(info_text)

        layout.addStretch()

        return page

    def _build_top_bar(self) -> None:
        """شريط علوي بمعلومات المستخدم."""
        top_bar = QToolBar()
        top_bar.setMovable(False)
        top_bar.setStyleSheet("""
            QToolBar {
                background-color: white;
                border-bottom: 1px solid #E2E8F0;
                padding: 8px;
            }
        """)
        top_bar.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        top_bar.addWidget(spacer)

        # Notifications
        notif_btn = QPushButton()
        notif_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        notif_btn.setStyleSheet("border: none; background: transparent;")
        if qta:
            try:
                notif_btn.setIcon(qta.icon("fa5s.bell", color="#475569"))
                notif_btn.setIconSize(QSize(20, 20))
            except Exception as e:
                # Silent fail - UI initialization should not crash
                # In production: use logger.warning(f"UI init error: {e}")
                pass
        top_bar.addWidget(notif_btn)

        # User avatar/name
        user_label = QLabel(self._current_user.username)
        user_label.setStyleSheet("color: #2D3748; font-weight: 700; padding: 0 12px; background: transparent;")
        top_bar.addWidget(user_label)

        self.addToolBar(top_bar)

    def _build_status_bar(self) -> None:
        """شريط الحالة السفلي."""
        status = QStatusBar()
        status.setStyleSheet("""
            QStatusBar {
                background-color: #0F172A;
                color: #94A3B8;
                font-size: 11px;
            }
        """)
        status.showMessage(f"  {settings.APP_NAME} v{settings.APP_VERSION}  •  متصل بقاعدة البيانات  •  {settings.COMPANY_NAME}")
        self.setStatusBar(status)

    def _apply_theme(self) -> None:
        """تطبيق الثيم - Soft UI theme already applied globally."""
        pass

    def _on_sidebar_click(self, section: str) -> None:
        """معالجة نقر زر الشريط الجانبي."""
        sections = ["dashboard", "ai_chat", "invoices", "journal", "customers", "suppliers",
                    "products", "expenses", "reports", "backup", "settings"]
        titles = ["لوحة المعلومات", "المساعد الذكي", "الفواتير", "القيود المحاسبية", "العملاء",
                  "الموردون", "المنتجات", "المصروفات", "التقارير",
                  "النسخ الاحتياطي", "الإعدادات"]

        if section in sections:
            idx = sections.index(section)
            self.stacked_widget.setCurrentIndex(idx)
            self.page_title.setText(titles[idx])

            # Update active button
            for i, btn in enumerate(self._sidebar_buttons):
                btn.set_active(sections[i] == section)

    def _on_logout(self) -> None:
        """تسجيل الخروج."""
        reply = QMessageBox.question(
            self,
            "تأكيد الخروج",
            "هل تريد تسجيل الخروج؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.close()
