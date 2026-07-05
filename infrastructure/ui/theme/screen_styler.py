"""
Soft UI Screen Styler - يطبّق Soft UI مفصل على كل شاشة

بدلًا من إعادة كتابة كل شاشة، نستدعي هذه الدوال بعد إنشاء كل شاشة.
كل دالة تمرّ على widgets وتُطبّق أنماط Soft UI المناسبة.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QPushButton, QTableWidget, QHeaderView, QLabel,
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QFrame, QGroupBox, QTabWidget, QProgressBar, QTextEdit,
    QPlainTextEdit, QDialog, QDialogButtonBox, QToolBar,
    QStatusBar, QScrollArea, QMenu, QMenuBar,
)

from infrastructure.ui.theme.soft_ui import SoftColors, add_soft_shadow
from infrastructure.ui.widgets.soft_components import SoftCard


def style_customers_window(window: QWidget) -> None:
    """تطبيق Soft UI مفصل على شاشة العملاء."""
    _apply_common_styles(window)

    # Style all buttons by text
    for btn in window.findChildren(QPushButton):
        _style_button_by_text(btn)

    # Style tables
    for table in window.findChildren(QTableWidget):
        _style_table_soft(table)

    # Style search inputs
    for edit in window.findChildren(QLineEdit):
        if "search" in edit.placeholderText().lower() or "بحث" in edit.placeholderText():
            edit.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {SoftColors.BG_INPUT};
                    border: 2px solid {SoftColors.BG_SECONDARY};
                    border-radius: 16px;
                    padding: 10px 18px;
                    font-size: 14px;
                }}
                QLineEdit:focus {{ border: 2px solid {SoftColors.ACCENT_BLUE}; }}
            """)

    # Add shadows to frames that look like cards
    for frame in window.findChildren(QFrame):
        if frame.objectName() and "card" in frame.objectName().lower():
            add_soft_shadow(frame, blur=20, offset_y=4)


def style_products_window(window: QWidget) -> None:
    """تطبيق Soft UI مفصل على شاشة المنتجات."""
    _apply_common_styles(window)

    for btn in window.findChildren(QPushButton):
        _style_button_by_text(btn)

    for table in window.findChildren(QTableWidget):
        _style_table_soft(table)

    # Style tabs
    for tab in window.findChildren(QTabWidget):
        _style_tabs_soft(tab)


def style_invoices_window(window: QWidget) -> None:
    """تطبيق Soft UI مفصل على شاشة الفواتير."""
    _apply_common_styles(window)

    for btn in window.findChildren(QPushButton):
        _style_button_by_text(btn)

    for table in window.findChildren(QTableWidget):
        _style_table_soft(table)

    # Style combo boxes (filter)
    for combo in window.findChildren(QComboBox):
        combo.setMinimumHeight(40)


def style_reports_window(window: QWidget) -> None:
    """تطبيق Soft UI مفصل على شاشة التقارير."""
    _apply_common_styles(window)

    for btn in window.findChildren(QPushButton):
        _style_button_by_text(btn)

    for table in window.findChildren(QTableWidget):
        _style_table_soft(table)

    # Style report cards
    for frame in window.findChildren(QFrame):
        if frame.objectName() and "card" in frame.objectName().lower():
            add_soft_shadow(frame, blur=25, offset_y=6)
            frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {SoftColors.SURFACE_LIGHT};
                    border: none;
                    border-right: 4px solid {SoftColors.ACCENT_BLUE};
                    border-radius: 20px;
                    padding: 12px;
                }}
                QFrame:hover {{
                    background-color: {SoftColors.SURFACE_HOVER};
                }}
            """)


def style_suppliers_window(window: QWidget) -> None:
    """تطبيق Soft UI مفصل على شاشة الموردين."""
    _apply_common_styles(window)

    for btn in window.findChildren(QPushButton):
        _style_button_by_text(btn)

    for table in window.findChildren(QTableWidget):
        _style_table_soft(table)


def style_journal_window(window: QWidget) -> None:
    """تطبيق Soft UI مفصل على شاشة القيود."""
    _apply_common_styles(window)

    for btn in window.findChildren(QPushButton):
        _style_button_by_text(btn)

    for table in window.findChildren(QTableWidget):
        _style_table_soft(table)


def style_expenses_window(window: QWidget) -> None:
    """تطبيق Soft UI مفصل على شاشة المصروفات."""
    _apply_common_styles(window)

    for btn in window.findChildren(QPushButton):
        _style_button_by_text(btn)


def style_backup_window(window: QWidget) -> None:
    """تطبيق Soft UI مفصل على شاشة النسخ الاحتياطي."""
    _apply_common_styles(window)

    for btn in window.findChildren(QPushButton):
        _style_button_by_text(btn)

    for table in window.findChildren(QTableWidget):
        _style_table_soft(table)


def style_settings_window(window: QWidget) -> None:
    """تطبيق Soft UI مفصل على شاشة الإعدادات."""
    _apply_common_styles(window)

    for btn in window.findChildren(QPushButton):
        _style_button_by_text(btn)

    # Style tabs
    for tab in window.findChildren(QTabWidget):
        _style_tabs_soft(tab)

    # Style spin boxes
    for spin in window.findChildren((QSpinBox, QDoubleSpinBox)):
        spin.setMinimumHeight(40)


def style_ai_chat_window(window: QWidget) -> None:
    """تطبيق Soft UI مفصل على شاشة المحادثة الذكية."""
    _apply_common_styles(window)

    for btn in window.findChildren(QPushButton):
        _style_button_by_text(btn)


# ============================================================
# Common helpers
# ============================================================
def _apply_common_styles(window: QWidget) -> None:
    """تطبيق الأنماط المشتركة على أي نافذة."""
    window.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

    # Style all labels
    for label in window.findChildren(QLabel):
        label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        if not label.styleSheet() or "color" not in label.styleSheet():
            label.setStyleSheet(f"color: {SoftColors.TEXT_PRIMARY}; background: transparent;")

    # Style inputs
    for edit in window.findChildren((QLineEdit, QTextEdit, QPlainTextEdit)):
        if not edit.styleSheet() or "border-radius" not in edit.styleSheet():
            edit.setMinimumHeight(40)
            edit.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

    # Style combos
    for combo in window.findChildren(QComboBox):
        combo.setMinimumHeight(40)

    # Style checkboxes
    for cb in window.findChildren(QCheckBox):
        cb.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

    # Style status labels
    for label in window.findChildren(QLabel):
        if "status" in (label.objectName() or "").lower():
            label.setStyleSheet(f"color: {SoftColors.TEXT_MUTED}; font-size: 11px; background: transparent;")


def _style_button_by_text(btn: QPushButton) -> None:
    """تنسيق زر حسب نصه."""
    btn.setMinimumHeight(42)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

    text = btn.text().lower()

    if any(k in text for k in ["حفظ", "save", "تأكيد", "confirm", "إرسال", "send", "ترحيل"]):
        btn.setObjectName("primary")
    elif any(k in text for k in ["حذف", "delete", "إلغاء", "cancel", "رفض", "reject", "خروج"]):
        btn.setObjectName("danger")
    elif any(k in text for k in ["إضافة", "add", "جديد", "new", "➕", "إنشاء"]):
        btn.setObjectName("success")
    elif any(k in text for k in ["تحديث", "refresh", "تصدير", "export", "تسوية", "🔄"]):
        btn.setObjectName("warning")
    elif any(k in text for k in ["عرض", "view", "👁", "تفاصيل"]):
        btn.setObjectName("primary")
    elif any(k in text for k in ["قلب", "reverse", "↩"]):
        btn.setObjectName("warning")
    elif any(k in text for k in ["pdf", "تصدير pdf"]):
        btn.setObjectName("primary")


def _style_table_soft(table: QTableWidget) -> None:
    """تنسيق جدول بـ Soft UI."""
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    if table.horizontalHeader():
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)


def _style_tabs_soft(tabs: QTabWidget) -> None:
    """تنسيق تبويبات بـ Soft UI."""
    tabs.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
