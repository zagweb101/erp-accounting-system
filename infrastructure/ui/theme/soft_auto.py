"""
Soft UI Auto-Applier — يطبّق Soft UI تلقائيًا على كل الشاشات الموجودة

بدلًا من إعادة كتابة كل شاشة، نمرّ على كل widget ونُطبّق الأنماط.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QPushButton, QTableWidget, QHeaderView, QLabel,
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QFrame, QGroupBox, QTabWidget, QProgressBar, QTextEdit,
    QPlainTextEdit, QScrollArea, QDialog, QDialogButtonBox,
)
from PySide6.QtCore import Qt

from infrastructure.ui.theme.soft_ui import SoftColors, SoftUIStyleSheet


def auto_apply_soft_ui(window: QWidget) -> None:
    """تطبيق Soft UI تلقائيًا على نافذة وكل أبنائها.

    يمرّ على كل widget في النافذة ويُطبّق الأنماط المناسبة:
    - الأزرار: border-radius ناعم
    - الجداول: زوايا دائرية + alternating rows
    - حقول الإدخال: خلفية ناعمة + border-radius
    - التسميات: ألوان Soft UI

    Args:
        window: النافذة الجذرية.
    """
    # Apply the full stylesheet as base
    window.setStyleSheet(SoftUIStyleSheet.generate())

    # Set RTL
    window.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

    # Walk through all child widgets
    _style_widgets_recursive(window)


def _style_widgets_recursive(widget: QWidget) -> None:
    """تطبيق الأنماط على widget وكل أبنائه بشكل متكرر."""
    # Style this widget based on its type
    if isinstance(widget, QPushButton):
        _style_button(widget)
    elif isinstance(widget, QTableWidget):
        _style_table(widget)
    elif isinstance(widget, QLabel):
        _style_label(widget)
    elif isinstance(widget, (QLineEdit, QTextEdit, QPlainTextEdit)):
        _style_input(widget)
    elif isinstance(widget, (QComboBox, QSpinBox, QDoubleSpinBox)):
        _style_combo(widget)
    elif isinstance(widget, QCheckBox):
        _style_checkbox(widget)
    elif isinstance(widget, QFrame):
        _style_frame(widget)
    elif isinstance(widget, QGroupBox):
        _style_groupbox(widget)
    elif isinstance(widget, QDialogButtonBox):
        _style_dialog_buttons(widget)

    # Recurse into children
    for child in widget.children():
        if isinstance(child, QWidget):
            _style_widgets_recursive(child)


def _style_button(btn: QPushButton) -> None:
    """تنسيق زر."""
    btn.setMinimumHeight(40)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)

    # Detect button type by text
    text = btn.text().lower()
    if any(k in text for k in ["حفظ", "save", "تأكيد", "confirm", "إرسال"]):
        btn.setObjectName("primary")
    elif any(k in text for k in ["حذف", "delete", "إلغاء", "cancel", "رفض"]):
        btn.setObjectName("danger")
    elif any(k in text for k in ["إضافة", "add", "جديد", "new", "➕"]):
        btn.setObjectName("success")
    elif any(k in text for k in ["تحديث", "refresh", "تصدير", "export"]):
        btn.setObjectName("warning")


def _style_table(table: QTableWidget) -> None:
    """تنسيق جدول."""
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    if table.horizontalHeader():
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)


def _style_label(label: QLabel) -> None:
    """تنسيق تسمية."""
    label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    # Don't override if already has custom style
    current_style = label.styleSheet()
    if not current_style or "background" not in current_style:
        label.setStyleSheet(f"color: {SoftColors.TEXT_PRIMARY}; background: transparent;")


def _style_input(field) -> None:
    """تنسيق حقل إدخال."""
    field.setMinimumHeight(40)
    field.setLayoutDirection(Qt.LayoutDirection.LeftToRight)


def _style_combo(combo) -> None:
    """تنسيق قائمة منسدلة."""
    combo.setMinimumHeight(40)


def _style_checkbox(cb: QCheckBox) -> None:
    """تنسيق خانة اختيار."""
    cb.setLayoutDirection(Qt.LayoutDirection.RightToLeft)


def _style_frame(frame: QFrame) -> None:
    """تنسيق إطار."""
    # Keep existing styling if it has custom background
    pass


def _style_groupbox(group: QGroupBox) -> None:
    """تنسيق مجموعة."""
    group.setLayoutDirection(Qt.LayoutDirection.RightToLeft)


def _style_dialog_buttons(buttons: QDialogButtonBox) -> None:
    """تنسيق أزرار الحوار."""
    save_btn = buttons.button(QDialogButtonBox.StandardButton.Save)
    if save_btn:
        save_btn.setObjectName("primary")
        save_btn.setText("حفظ")
    cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
    if cancel_btn:
        cancel_btn.setText("إلغاء")
