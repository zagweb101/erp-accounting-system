"""
Soft UI Design System - نظام التصميم الناعم

يجمع ثلاثة أنماط:
- Claymorphism: عناصر طينية بظلال منتفخة
- Soft UI (Neumorphism): ظلال داخلية وخارجية ناعمة
- Organic UI: أشكال منحنية وألوان طبيعية

Usage:
    from infrastructure.ui.theme.soft_ui import SoftUITheme
    SoftUITheme.apply(app)  # Apply to entire QApplication
"""
from __future__ import annotations

from PySide6.QtGui import QColor, QPalette, QFont
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication


# ============================================================
# Color Palette - ألوان ناعمة (Soft Palette)
# ============================================================
class SoftColors:
    """لوحة ألوان Soft UI - ألوان هادئة، ماضيلية، طبيعية."""

    # Base backgrounds (very soft, near-white with tint)
    BG_PRIMARY = "#F0F4F8"
    BG_SECONDARY = "#E4EBF5"
    BG_CARD = "#FFFFFF"
    BG_INPUT = "#F7F9FC"
    BG_SIDEBAR = "#E4EBF5"

    # Surface
    SURFACE_LIGHT = "#FFFFFF"
    SURFACE_DARK = "#D1D9E6"
    SURFACE_HOVER = "#EDF1F7"

    # Text
    TEXT_PRIMARY = "#2D3748"
    TEXT_SECONDARY = "#718096"
    TEXT_MUTED = "#A0AEC0"
    TEXT_ON_ACCENT = "#FFFFFF"

    # Accents (soft, muted)
    ACCENT_BLUE = "#6B8AFE"
    ACCENT_BLUE_DARK = "#5A7AED"
    ACCENT_BLUE_LIGHT = "#A5B8FF"

    ACCENT_GREEN = "#68D391"
    ACCENT_GREEN_DARK = "#48BB78"
    ACCENT_GREEN_LIGHT = "#9AE6B4"

    ACCENT_ORANGE = "#F6AD55"
    ACCENT_ORANGE_DARK = "#ED8936"
    ACCENT_ORANGE_LIGHT = "#FBD38D"

    ACCENT_RED = "#FC8181"
    ACCENT_RED_DARK = "#E53E3E"
    ACCENT_RED_LIGHT = "#FEB2B2"

    ACCENT_PURPLE = "#B794F4"
    ACCENT_PURPLE_DARK = "#9F7AEA"
    ACCENT_PURPLE_LIGHT = "#D6BCFA"

    ACCENT_TEAL = "#4FD1C5"
    ACCENT_PINK = "#F687B3"

    # Shadows
    SHADOW_LIGHT = "#FFFFFF"
    SHADOW_DARK = "#C3CAD7"
    SHADOW_DARKER = "#A8B0C0"

    # Organic gradients
    GRADIENT_OCEAN = "#6B8AFE"
    GRADIENT_FOREST = "#68D391"
    GRADIENT_SUNSET = "#F6AD55"
    GRADIENT_LAVENDER = "#B794F4"


# ============================================================
# QSS Stylesheet Generator
# ============================================================
class SoftUIStyleSheet:
    """يولّد QSS شامل لنظام Soft UI."""

    @staticmethod
    def generate() -> str:
        c = SoftColors
        return f"""
        QWidget {{
            font-family: "Noto Sans Arabic", "Segoe UI", "Cairo", sans-serif;
            font-size: 14px;
            color: {c.TEXT_PRIMARY};
            background-color: {c.BG_PRIMARY};
        }}

        /* Soft Button */
        QPushButton {{
            background-color: {c.SURFACE_LIGHT};
            border: none;
            border-radius: 14px;
            padding: 10px 24px;
            font-size: 14px;
            font-weight: 600;
            color: {c.TEXT_PRIMARY};
            min-height: 20px;
        }}
        QPushButton:hover {{ background-color: {c.SURFACE_HOVER}; }}
        QPushButton:pressed {{ background-color: {c.SURFACE_DARK}; }}
        QPushButton:disabled {{ background-color: {c.BG_SECONDARY}; color: {c.TEXT_MUTED}; }}

        QPushButton#primary {{ background-color: {c.ACCENT_BLUE}; color: {c.TEXT_ON_ACCENT}; }}
        QPushButton#primary:hover {{ background-color: {c.ACCENT_BLUE_DARK}; }}

        QPushButton#success {{ background-color: {c.ACCENT_GREEN}; color: {c.TEXT_ON_ACCENT}; }}
        QPushButton#success:hover {{ background-color: {c.ACCENT_GREEN_DARK}; }}

        QPushButton#danger {{ background-color: {c.ACCENT_RED}; color: {c.TEXT_ON_ACCENT}; }}
        QPushButton#danger:hover {{ background-color: {c.ACCENT_RED_DARK}; }}

        QPushButton#warning {{ background-color: {c.ACCENT_ORANGE}; color: {c.TEXT_ON_ACCENT}; }}
        QPushButton#warning:hover {{ background-color: {c.ACCENT_ORANGE_DARK}; }}

        /* Soft Input */
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {c.BG_INPUT};
            border: 2px solid {c.BG_SECONDARY};
            border-radius: 12px;
            padding: 10px 14px;
            font-size: 14px;
            color: {c.TEXT_PRIMARY};
            selection-background-color: {c.ACCENT_BLUE_LIGHT};
        }}
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border: 2px solid {c.ACCENT_BLUE};
            background-color: {c.SURFACE_LIGHT};
        }}

        /* Soft ComboBox & SpinBox */
        QComboBox {{
            background-color: {c.BG_INPUT};
            border: 2px solid {c.BG_SECONDARY};
            border-radius: 12px;
            padding: 8px 14px;
            font-size: 14px;
            min-width: 120px;
        }}
        QComboBox:focus {{ border: 2px solid {c.ACCENT_BLUE}; }}
        QComboBox::drop-down {{ border: none; width: 30px; }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid {c.TEXT_SECONDARY};
            margin-right: 10px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {c.SURFACE_LIGHT};
            border: 1px solid {c.BG_SECONDARY};
            border-radius: 8px;
            padding: 4px;
            selection-background-color: {c.ACCENT_BLUE_LIGHT};
        }}

        QSpinBox, QDoubleSpinBox {{
            background-color: {c.BG_INPUT};
            border: 2px solid {c.BG_SECONDARY};
            border-radius: 12px;
            padding: 8px 14px;
            font-size: 14px;
        }}
        QSpinBox:focus, QDoubleSpinBox:focus {{ border: 2px solid {c.ACCENT_BLUE}; }}

        /* Soft Card */
        QFrame#card {{
            background-color: {c.SURFACE_LIGHT};
            border: none;
            border-radius: 20px;
        }}

        QGroupBox {{
            background-color: {c.SURFACE_LIGHT};
            border: none;
            border-radius: 16px;
            margin-top: 12px;
            padding: 16px;
            font-weight: 600;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top right;
            padding: 4px 12px;
            background-color: {c.ACCENT_BLUE_LIGHT};
            border-radius: 8px;
            color: {c.ACCENT_BLUE_DARK};
        }}

        /* Soft Table */
        QTableWidget {{
            background-color: {c.SURFACE_LIGHT};
            border: none;
            border-radius: 16px;
            gridline-color: {c.BG_SECONDARY};
            selection-background-color: {c.ACCENT_BLUE_LIGHT};
            selection-color: {c.TEXT_PRIMARY};
            alternate-background-color: {c.BG_INPUT};
        }}
        QTableWidget::item {{ padding: 8px; border: none; }}
        QTableWidget::item:selected {{ background-color: {c.ACCENT_BLUE_LIGHT}; }}
        QHeaderView::section {{
            background-color: {c.ACCENT_BLUE};
            color: {c.TEXT_ON_ACCENT};
            padding: 10px;
            border: none;
            font-weight: 700;
            font-size: 13px;
        }}
        QHeaderView::section:first {{ border-top-left-radius: 16px; }}
        QHeaderView::section:last {{ border-top-right-radius: 16px; }}
        QTableCornerButton::section {{ background-color: {c.ACCENT_BLUE}; border: none; }}

        /* Soft ScrollBar */
        QScrollBar:vertical {{
            background-color: transparent;
            width: 10px;
            margin: 4px;
            border-radius: 5px;
        }}
        QScrollBar::handle:vertical {{
            background-color: {c.SHADOW_DARK};
            border-radius: 5px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{ background-color: {c.TEXT_MUTED}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        QScrollBar:horizontal {{
            background-color: transparent;
            height: 10px;
            margin: 4px;
            border-radius: 5px;
        }}
        QScrollBar::handle:horizontal {{
            background-color: {c.SHADOW_DARK};
            border-radius: 5px;
            min-width: 30px;
        }}

        /* Soft CheckBox */
        QCheckBox {{ spacing: 8px; font-size: 14px; color: {c.TEXT_PRIMARY}; }}
        QCheckBox::indicator {{
            width: 22px; height: 22px;
            border-radius: 7px;
            border: 2px solid {c.BG_SECONDARY};
            background-color: {c.BG_INPUT};
        }}
        QCheckBox::indicator:checked {{
            background-color: {c.ACCENT_BLUE};
            border: 2px solid {c.ACCENT_BLUE_DARK};
        }}
        QCheckBox::indicator:hover {{ border: 2px solid {c.ACCENT_BLUE}; }}

        /* Soft ProgressBar */
        QProgressBar {{
            background-color: {c.BG_SECONDARY};
            border: none;
            border-radius: 8px;
            text-align: center;
            font-size: 12px;
            height: 12px;
        }}
        QProgressBar::chunk {{
            background-color: {c.ACCENT_BLUE};
            border-radius: 8px;
        }}

        /* Soft TabWidget */
        QTabWidget::pane {{ border: none; background-color: transparent; }}
        QTabBar::tab {{
            background-color: {c.BG_SECONDARY};
            color: {c.TEXT_SECONDARY};
            padding: 10px 24px;
            margin: 2px;
            border: none;
            border-radius: 10px;
            font-weight: 600;
        }}
        QTabBar::tab:selected {{
            background-color: {c.SURFACE_LIGHT};
            color: {c.ACCENT_BLUE_DARK};
        }}
        QTabBar::tab:hover {{ background-color: {c.SURFACE_HOVER}; }}

        /* Soft Menu */
        QMenuBar {{
            background-color: {c.BG_PRIMARY};
            color: {c.TEXT_PRIMARY};
            padding: 4px;
            border-bottom: 1px solid {c.BG_SECONDARY};
        }}
        QMenuBar::item {{
            background-color: transparent;
            padding: 6px 12px;
            border-radius: 8px;
        }}
        QMenuBar::item:selected {{ background-color: {c.BG_SECONDARY}; }}
        QMenu {{
            background-color: {c.SURFACE_LIGHT};
            border: 1px solid {c.BG_SECONDARY};
            border-radius: 12px;
            padding: 8px;
        }}
        QMenu::item {{ padding: 8px 24px; border-radius: 8px; }}
        QMenu::item:selected {{ background-color: {c.ACCENT_BLUE_LIGHT}; }}

        /* Soft Dialog */
        QDialog {{ background-color: {c.BG_PRIMARY}; }}

        /* Soft ScrollArea */
        QScrollArea {{ background-color: transparent; border: none; }}
        QScrollArea > QWidget > QWidget {{ background-color: transparent; }}

        /* Soft Label */
        QLabel {{ color: {c.TEXT_PRIMARY}; background-color: transparent; }}
        QLabel#title {{ font-size: 24px; font-weight: 700; }}
        QLabel#subtitle {{ font-size: 16px; font-weight: 600; color: {c.TEXT_SECONDARY}; }}
        QLabel#caption {{ font-size: 12px; color: {c.TEXT_MUTED}; }}
        QLabel#kpiValue {{ font-size: 28px; font-weight: 800; color: {c.ACCENT_BLUE_DARK}; }}
        QLabel#kpiLabel {{ font-size: 12px; color: {c.TEXT_SECONDARY}; }}

        /* Soft ToolBar */
        QToolBar {{
            background-color: {c.SURFACE_LIGHT};
            border: none;
            border-bottom: 1px solid {c.BG_SECONDARY};
            padding: 6px;
            spacing: 4px;
        }}

        /* Soft StatusBar */
        QStatusBar {{
            background-color: {c.BG_SECONDARY};
            color: {c.TEXT_SECONDARY};
            border: none;
            font-size: 12px;
            padding: 4px;
        }}

        /* Soft ToolTip */
        QToolTip {{
            background-color: {c.TEXT_PRIMARY};
            color: {c.SURFACE_LIGHT};
            border: none;
            border-radius: 8px;
            padding: 6px 12px;
            font-size: 12px;
        }}

        /* Soft ToolButton */
        QToolButton {{
            background-color: transparent;
            border: none;
            border-radius: 10px;
            padding: 6px;
        }}
        QToolButton:hover {{ background-color: {c.BG_SECONDARY}; }}
        QToolButton:pressed {{ background-color: {c.SHADOW_DARK}; }}
        """


# ============================================================
# Soft UI Theme Manager
# ============================================================
class SoftUITheme:
    """مدير ثيم Soft UI - يطبّق الثيم على التطبيق بالكامل."""

    @staticmethod
    def apply(app: QApplication, mode: str = "light") -> None:
        """تطبيق ثيم Soft UI على التطبيق.

        Args:
            app: تطبيق QApplication.
            mode: "light" أو "dark".
        """
        font = QFont("Noto Sans Arabic", 10)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        app.setFont(font)

        app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        stylesheet = SoftUIStyleSheet.generate()
        app.setStyleSheet(stylesheet)

        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(SoftColors.BG_PRIMARY))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(SoftColors.TEXT_PRIMARY))
        palette.setColor(QPalette.ColorRole.Base, QColor(SoftColors.SURFACE_LIGHT))
        palette.setColor(QPalette.ColorRole.Text, QColor(SoftColors.TEXT_PRIMARY))
        palette.setColor(QPalette.ColorRole.Button, QColor(SoftColors.SURFACE_LIGHT))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(SoftColors.TEXT_PRIMARY))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(SoftColors.ACCENT_BLUE_LIGHT))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(SoftColors.TEXT_PRIMARY))
        app.setPalette(palette)

    @staticmethod
    def get_color(name: str) -> str:
        """الحصول على لون من اللوحة بالاسم."""
        return getattr(SoftColors, name.upper(), SoftColors.TEXT_PRIMARY)
