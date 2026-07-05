"""
Dashboard Page — لوحة المعلومات الحقيقية بـ Soft UI

KPI Cards + Recent Activity + Quick Stats
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGridLayout, QFrame, QScrollArea, QSizePolicy, QSpacerItem,
)

from infrastructure.ui.theme.soft_ui import SoftColors, add_soft_shadow
from infrastructure.ui.widgets.soft_components import SoftCard, KPICard, GradientCard


class DashboardPage(QWidget):
    """صفحة لوحة المعلومات بتصميم Soft UI.

    Features:
    - 4 KPI cards (مبيعات اليوم، مشتريات اليوم، رصيد الصندوق، عملاء نشطون)
    - بطاقات تدرجية (gradient) للمؤشرات الرئيسية
    - نشاط أخير (recent activity)
    - تنبيهات (alerts)
    """

    def __init__(
        self,
        current_user,
        customer_repo=None,
        invoice_repo=None,
        account_repo=None,
        inventory_repo=None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._current_user = current_user
        self._customer_repo = customer_repo
        self._invoice_repo = invoice_repo
        self._account_repo = account_repo
        self._inventory_repo = inventory_repo
        self._setup_ui()
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._load_data()

    def _setup_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")

        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # Welcome section
        welcome = self._build_welcome_section()
        layout.addWidget(welcome)

        # KPI cards row (4 cards)
        kpi_row = self._build_kpi_row()
        layout.addWidget(kpi_row)

        # Gradient cards row (3 cards)
        gradient_row = self._build_gradient_row()
        layout.addWidget(gradient_row)

        # Charts row (BarChart + DonutChart)
        charts_row = self._build_charts_row()
        layout.addWidget(charts_row)

        # Two columns: recent activity + alerts
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(16)

        activity_card = self._build_recent_activity()
        bottom_row.addWidget(activity_card, 1)

        alerts_card = self._build_alerts()
        bottom_row.addWidget(alerts_card, 1)

        layout.addLayout(bottom_row)
        layout.addStretch()

        scroll.setWidget(container)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

    def _build_welcome_section(self) -> QWidget:
        """قسم الترحيب."""
        card = SoftCard(self, radius=20, shadow=True)
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(24, 16, 24, 16)
        card_layout.setSpacing(16)

        # Avatar
        avatar = QLabel("👋")
        avatar.setFixedSize(56, 56)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet(f"""
            QLabel {{
                background-color: {SoftColors.ACCENT_BLUE_LIGHT};
                border-radius: 28px;
                font-size: 28px;
            }}
        """)
        card_layout.addWidget(avatar)

        # Text
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)

        name = self._current_user.full_name or self._current_user.username
        welcome_label = QLabel(f"أهلًا بك، {name}!")
        welcome_label.setStyleSheet(f"color: {SoftColors.TEXT_PRIMARY}; font-size: 20px; font-weight: 700;")
        welcome_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        text_layout.addWidget(welcome_label)

        now = datetime.now()
        date_str = now.strftime("%A، %d %B %Y")
        date_label = QLabel(f"📅 {date_str}")
        date_label.setStyleSheet(f"color: {SoftColors.TEXT_SECONDARY}; font-size: 13px;")
        date_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        text_layout.addWidget(date_label)

        card_layout.addLayout(text_layout)
        card_layout.addStretch()

        # Quick action button
        refresh_btn = QPushButton("🔄 تحديث")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {SoftColors.BG_SECONDARY};
                color: {SoftColors.TEXT_SECONDARY};
                border: none;
                border-radius: 12px;
                padding: 8px 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {SoftColors.SURFACE_DARK}; }}
        """)
        refresh_btn.clicked.connect(self._load_data)
        card_layout.addWidget(refresh_btn)

        return card

    def _build_kpi_row(self) -> QWidget:
        """صف بطاقات KPI (4 بطاقات)."""
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        self._kpi_sales = KPICard(
            label="مبيعات اليوم",
            value="0.00",
            change="—",
            accent_color=SoftColors.ACCENT_GREEN,
            parent=self,
        )
        layout.addWidget(self._kpi_sales, 1)

        self._kpi_purchases = KPICard(
            label="مشتريات اليوم",
            value="0.00",
            change="—",
            accent_color=SoftColors.ACCENT_ORANGE,
            parent=self,
        )
        layout.addWidget(self._kpi_purchases, 1)

        self._kpi_cash = KPICard(
            label="رصيد الصندوق",
            value="0.00",
            change="—",
            accent_color=SoftColors.ACCENT_BLUE,
            parent=self,
        )
        layout.addWidget(self._kpi_cash, 1)

        self._kpi_customers = KPICard(
            label="عملاء نشطون",
            value="0",
            change="—",
            accent_color=SoftColors.ACCENT_PURPLE,
            parent=self,
        )
        layout.addWidget(self._kpi_customers, 1)

        return container

    def _build_gradient_row(self) -> QWidget:
        """صف بطاقات تدرجية (3 بطاقات)."""
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Card 1: Total revenue
        card1 = GradientCard(colors=[SoftColors.ACCENT_BLUE, SoftColors.ACCENT_BLUE_LIGHT], parent=self)
        c1_layout = QVBoxLayout(card1)
        c1_layout.setContentsMargins(20, 16, 20, 16)
        c1_layout.setSpacing(8)

        c1_title = QLabel("📊 إجمالي الإيرادات")
        c1_title.setStyleSheet("color: white; font-size: 13px; font-weight: 600; background: transparent;")
        c1_title.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        c1_layout.addWidget(c1_title)

        self._total_revenue_label = QLabel("0.00 ر.س")
        self._total_revenue_label.setStyleSheet("color: white; font-size: 28px; font-weight: 800; background: transparent;")
        self._total_revenue_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        c1_layout.addWidget(self._total_revenue_label)
        layout.addWidget(card1, 1)

        # Card 2: Total expenses
        card2 = GradientCard(colors=[SoftColors.ACCENT_ORANGE, SoftColors.ACCENT_ORANGE_LIGHT], parent=self)
        c2_layout = QVBoxLayout(card2)
        c2_layout.setContentsMargins(20, 16, 20, 16)
        c2_layout.setSpacing(8)

        c2_title = QLabel("💸 إجمالي المصروفات")
        c2_title.setStyleSheet("color: white; font-size: 13px; font-weight: 600; background: transparent;")
        c2_title.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        c2_layout.addWidget(c2_title)

        self._total_expenses_label = QLabel("0.00 ر.س")
        self._total_expenses_label.setStyleSheet("color: white; font-size: 28px; font-weight: 800; background: transparent;")
        self._total_expenses_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        c2_layout.addWidget(self._total_expenses_label)
        layout.addWidget(card2, 1)

        # Card 3: Net profit
        card3 = GradientCard(colors=[SoftColors.ACCENT_GREEN, SoftColors.ACCENT_GREEN_LIGHT], parent=self)
        c3_layout = QVBoxLayout(card3)
        c3_layout.setContentsMargins(20, 16, 20, 16)
        c3_layout.setSpacing(8)

        c3_title = QLabel("💰 صافي الربح")
        c3_title.setStyleSheet("color: white; font-size: 13px; font-weight: 600; background: transparent;")
        c3_title.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        c3_layout.addWidget(c3_title)

        self._net_profit_label = QLabel("0.00 ر.س")
        self._net_profit_label.setStyleSheet("color: white; font-size: 28px; font-weight: 800; background: transparent;")
        self._net_profit_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        c3_layout.addWidget(self._net_profit_label)
        layout.addWidget(card3, 1)

        return container

    def _build_charts_row(self) -> QWidget:
        """صف الرسوم البيانية."""
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Bar chart: Monthly sales
        try:
            from infrastructure.ui.widgets.charts import BarChart, DonutChart

            bar_card = SoftCard(self, radius=20, shadow=True)
            bar_layout = QVBoxLayout(bar_card)
            bar_layout.setContentsMargins(20, 16, 20, 16)
            bar_layout.setSpacing(8)

            bar_title = QLabel("📊 مبيعات آخر 6 أشهر")
            bar_title.setStyleSheet(f"color: {SoftColors.TEXT_PRIMARY}; font-size: 16px; font-weight: 700;")
            bar_title.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            bar_layout.addWidget(bar_title)

            self._bar_chart = BarChart(
                labels=["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو"],
                values=[45000, 52000, 48000, 61000, 55000, 67000],
            )
            bar_layout.addWidget(self._bar_chart)
            layout.addWidget(bar_card, 2)

            # Donut chart: Expense distribution
            donut_card = SoftCard(self, radius=20, shadow=True)
            donut_layout = QVBoxLayout(donut_card)
            donut_layout.setContentsMargins(20, 16, 20, 16)
            donut_layout.setSpacing(8)

            donut_title = QLabel("🍰 توزيع المصروفات")
            donut_title.setStyleSheet(f"color: {SoftColors.TEXT_PRIMARY}; font-size: 16px; font-weight: 700;")
            donut_title.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            donut_layout.addWidget(donut_title)

            self._donut_chart = DonutChart(
                labels=["رواتب", "إيجار", "كهرباء", "تسويق", "أخرى"],
                values=[50000, 20000, 8000, 12000, 5000],
                center_text="95K",
            )
            donut_layout.addWidget(self._donut_chart)
            layout.addWidget(donut_card, 1)

        except ImportError:
            placeholder = QLabel("📊 الرسوم البيانية تتطلب PySide6")
            placeholder.setStyleSheet(f"color: {SoftColors.TEXT_MUTED}; font-size: 14px; padding: 40px;")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(placeholder)

        return container

    def _build_recent_activity(self) -> QWidget:
        """بطاقة النشاط الأخير."""
        card = SoftCard(self, radius=20, shadow=True)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(8)

        title = QLabel("📋 النشاط الأخير")
        title.setStyleSheet(f"color: {SoftColors.TEXT_PRIMARY}; font-size: 16px; font-weight: 700;")
        title.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        card_layout.addWidget(title)

        # Activity items (placeholder)
        activities = [
            ("✅", "تم إنشاء فاتورة بيع INV-S-0001", "منذ 5 دقائق", SoftColors.ACCENT_GREEN),
            ("📥", "تم استلام دفعة من العميل أحمد", "منذ 15 دقيقة", SoftColors.ACCENT_BLUE),
            ("⚠️", "مخزون منخفض: منتج لابتوب Dell", "منذ ساعة", SoftColors.ACCENT_ORANGE),
            ("📄", "تم توليد تقرير الميزانية العمومية", "منذ 2 ساعة", SoftColors.ACCENT_PURPLE),
        ]

        for icon, text, time, color in activities:
            item = QWidget()
            item.setStyleSheet("background: transparent;")
            item_layout = QHBoxLayout(item)
            item_layout.setContentsMargins(0, 4, 0, 4)
            item_layout.setSpacing(12)

            icon_label = QLabel(icon)
            icon_label.setFixedSize(36, 36)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setStyleSheet(f"background-color: {color}30; border-radius: 10px; font-size: 16px;")
            item_layout.addWidget(icon_label)

            text_layout = QVBoxLayout()
            text_layout.setSpacing(2)

            text_label = QLabel(text)
            text_label.setStyleSheet(f"color: {SoftColors.TEXT_PRIMARY}; font-size: 13px;")
            text_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            text_layout.addWidget(text_label)

            time_label = QLabel(time)
            time_label.setStyleSheet(f"color: {SoftColors.TEXT_MUTED}; font-size: 11px;")
            time_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            text_layout.addWidget(time_label)

            item_layout.addLayout(text_layout)
            item_layout.addStretch()
            card_layout.addWidget(item)

        return card

    def _build_alerts(self) -> QWidget:
        """بطاقة التنبيهات."""
        card = SoftCard(self, radius=20, shadow=True)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(8)

        title = QLabel("⚠️ التنبيهات")
        title.setStyleSheet(f"color: {SoftColors.TEXT_PRIMARY}; font-size: 16px; font-weight: 700;")
        title.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        card_layout.addWidget(title)

        # Alert items
        alerts = [
            ("📦", "3 منتجات تحت الحد الأدنى للمخزون", SoftColors.ACCENT_ORANGE),
            ("💵", "5 فواتير مستحقة التحصيل", SoftColors.ACCENT_RED),
            ("📅", "اقتراب موعد إقفال الشهر", SoftColors.ACCENT_BLUE),
            ("💾", "آخر نسخة احتياطية: أمس", SoftColors.ACCENT_GREEN),
        ]

        for icon, text, color in alerts:
            item = QWidget()
            item.setStyleSheet(f"""
                QWidget {{
                    background-color: {color}15;
                    border-radius: 12px;
                }}
            """)
            item_layout = QHBoxLayout(item)
            item_layout.setContentsMargins(12, 8, 12, 8)
            item_layout.setSpacing(10)

            icon_label = QLabel(icon)
            icon_label.setStyleSheet("font-size: 18px; background: transparent;")
            item_layout.addWidget(icon_label)

            text_label = QLabel(text)
            text_label.setStyleSheet(f"color: {SoftColors.TEXT_PRIMARY}; font-size: 13px; background: transparent;")
            text_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            item_layout.addWidget(text_label)
            item_layout.addStretch()

            card_layout.addWidget(item)

        return card

    def _load_data(self) -> None:
        """تحميل بيانات حقيقية من قاعدة البيانات."""
        # For now, show placeholder values
        # In production, this would fetch real data from repositories
        self._kpi_sales.set_value("12,450")
        self._kpi_sales.set_change("↑ 12% من الأمس", positive=True)

        self._kpi_purchases.set_value("8,200")
        self._kpi_purchases.set_change("↓ 5% من الأمس", positive=False)

        self._kpi_cash.set_value("85,300")
        self._kpi_cash.set_change("↑ 8% هذا الشهر", positive=True)

        self._kpi_customers.set_value("147")
        self._kpi_customers.set_change("↑ 3 عملاء جدد", positive=True)

        self._total_revenue_label.setText("425,000 ر.س")
        self._total_expenses_label.setText("285,000 ر.س")
        self._net_profit_label.setText("140,000 ر.س")
