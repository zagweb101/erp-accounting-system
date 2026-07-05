"""
Soft UI Theme Helper — يطبّق Soft UI على الشاشات الموجودة

بدلًا من إعادة كتابة كل شاشة، نُطبّق الأنماط عبر هذا الـ helper.
"""
from __future__ import annotations

from PySide6.QtWidgets import QWidget, QPushButton, QTableWidget, QHeaderView
from infrastructure.ui.theme.soft_ui import SoftColors, SoftUIStyleSheet


def apply_soft_ui_to_window(window: QWidget) -> None:
    """تطبيق أنماط Soft UI على أي نافذة موجودة.

    Args:
        window: النافذة التي سيُطبّق عليها الثيم.
    """
    # Apply full stylesheet (overrides per-window styles)
    window.setStyleSheet(SoftUIStyleSheet.generate())

    # Set RTL
    window.setLayoutDirection(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.LayoutDirection.RightToLeft)


def style_button_primary(btn: QPushButton) -> None:
    """تنسيق زر كـ primary (أزرق ناعم)."""
    btn.setObjectName("primary")
    btn.setMinimumHeight(44)
    btn.setCursor(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.CursorShape.PointingHandCursor)


def style_button_success(btn: QPushButton) -> None:
    """تنسيق زر كـ success (أخضر ناعم)."""
    btn.setObjectName("success")
    btn.setMinimumHeight(44)
    btn.setCursor(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.CursorShape.PointingHandCursor)


def style_button_danger(btn: QPushButton) -> None:
    """تنسيق زر كـ danger (أحمر ناعم)."""
    btn.setObjectName("danger")
    btn.setMinimumHeight(44)
    btn.setCursor(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.CursorShape.PointingHandCursor)


def style_button_warning(btn: QPushButton) -> None:
    """تنسيق زر كـ warning (برتقالي ناعم)."""
    btn.setObjectName("warning")
    btn.setMinimumHeight(44)
    btn.setCursor(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.CursorShape.PointingHandCursor)


def style_table(table: QTableWidget) -> None:
    """تنسيق جدول بـ Soft UI."""
    from PySide6.QtCore import Qt
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)


def style_title_label(label) -> None:
    """تنسيق عنوان بـ Soft UI."""
    label.setObjectName("title")
    label.setLayoutDirection(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.LayoutDirection.RightToLeft)


def style_subtitle_label(label) -> None:
    """تنسيق عنوان فرعي."""
    label.setObjectName("subtitle")
    label.setLayoutDirection(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.LayoutDirection.RightToLeft)


def get_soft_card_style(accent_color: str = None) -> str:
    """نمط بطاقة Soft UI."""
    if accent_color:
        return f"""
            QFrame#card {{
                background-color: {SoftColors.SURFACE_LIGHT};
                border: none;
                border-right: 4px solid {accent_color};
                border-radius: 20px;
            }}
        """
    return f"""
        QFrame#card {{
            background-color: {SoftColors.SURFACE_LIGHT};
            border: none;
            border-radius: 20px;
        }}
    """


def get_top_bar_style() -> str:
    """نمط شريط علوي ناعم."""
    return f"""
        QFrame {{
            background-color: {SoftColors.SURFACE_LIGHT};
            border: none;
            border-bottom: 1px solid {SoftColors.BG_SECONDARY};
            border-radius: 0px;
        }}
    """


def get_status_label_style() -> str:
    """نمط تسمية الحالة."""
    return f"color: {SoftColors.TEXT_MUTED}; font-size: 11px;"


def get_search_input_style() -> str:
    """نمط حقل البحث."""
    return f"""
        QLineEdit {{
            background-color: {SoftColors.BG_INPUT};
            border: 2px solid {SoftColors.BG_SECONDARY};
            border-radius: 16px;
            padding: 10px 18px;
            font-size: 14px;
        }}
        QLineEdit:focus {{
            border: 2px solid {SoftColors.ACCENT_BLUE};
        }}
    """
