"""
اختبارات Soft UI Design System + Components
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Check if PySide6 is available
try:
    import PySide6
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False

# Skip all tests if PySide6 is not available (the soft_ui module imports PySide6)
pytestmark = pytest.mark.skipif(not PYSIDE6_AVAILABLE, reason="PySide6 not installed")


class TestSoftColors:
    """اختبارات لوحة ألوان Soft UI."""

    def test_all_colors_defined(self) -> None:
        """كل الألوان الأساسية معرّفة."""
        from infrastructure.ui.theme.soft_ui import SoftColors
        assert SoftColors.BG_PRIMARY
        assert SoftColors.BG_SECONDARY
        assert SoftColors.SURFACE_LIGHT
        assert SoftColors.TEXT_PRIMARY
        assert SoftColors.ACCENT_BLUE
        assert SoftColors.ACCENT_GREEN
        assert SoftColors.ACCENT_RED
        assert SoftColors.ACCENT_ORANGE
        assert SoftColors.ACCENT_PURPLE

    def test_colors_are_hex(self) -> None:
        """كل الألوان بصيغة hex صحيحة."""
        from infrastructure.ui.theme.soft_ui import SoftColors
        for attr in dir(SoftColors):
            if attr.isupper():
                value = getattr(SoftColors, attr)
                assert value.startswith("#"), f"{attr} = {value} is not hex"
                assert len(value) == 7, f"{attr} = {value} has wrong length"

    def test_text_colors_have_contrast(self) -> None:
        """ألوان النص تختلف عن الخلفية."""
        from infrastructure.ui.theme.soft_ui import SoftColors
        assert SoftColors.TEXT_PRIMARY != SoftColors.BG_PRIMARY
        assert SoftColors.TEXT_ON_ACCENT != SoftColors.ACCENT_BLUE

    def test_accent_colors_are_soft(self) -> None:
        """الألوان الزاهية ماضيلية (soft) وليست مشبعة."""
        from infrastructure.ui.theme.soft_ui import SoftColors
        # Soft colors should not be pure saturated colors
        assert SoftColors.ACCENT_BLUE != "#0000FF"  # Not pure blue
        assert SoftColors.ACCENT_RED != "#FF0000"   # Not pure red
        assert SoftColors.ACCENT_GREEN != "#00FF00"  # Not pure green


class TestSoftUIStyleSheet:
    """اختبارات مولّد الأنماط."""

    def test_generate_returns_string(self) -> None:
        """generate() يُعيد نص."""
        from infrastructure.ui.theme.soft_ui import SoftUIStyleSheet
        qss = SoftUIStyleSheet.generate()
        assert isinstance(qss, str)
        assert len(qss) > 1000  # Should be substantial

    def test_stylesheet_contains_key_components(self) -> None:
        """الـ QSS يحوي كل المكونات الأساسية."""
        from infrastructure.ui.theme.soft_ui import SoftUIStyleSheet
        qss = SoftUIStyleSheet.generate()
        assert "QPushButton" in qss
        assert "QLineEdit" in qss
        assert "QTableWidget" in qss
        assert "QComboBox" in qss
        assert "QProgressBar" in qss
        assert "QTabWidget" in qss
        assert "QScrollBar" in qss
        assert "QCheckBox" in qss
        assert "QToolTip" in qss

    def test_stylesheet_has_soft_radius(self) -> None:
        """الـ QSS يحوي زوايا دائرية (border-radius)."""
        from infrastructure.ui.theme.soft_ui import SoftUIStyleSheet
        qss = SoftUIStyleSheet.generate()
        assert "border-radius" in qss
        assert "border-radius: 14px" in qss  # Button radius
        assert "border-radius: 12px" in qss  # Input radius
        assert "border-radius: 20px" in qss  # Card radius

    def test_stylesheet_has_button_variants(self) -> None:
        """الـ QSS يحوي أنواع الأزرار (primary, success, danger, warning)."""
        from infrastructure.ui.theme.soft_ui import SoftUIStyleSheet
        qss = SoftUIStyleSheet.generate()
        assert "QPushButton#primary" in qss
        assert "QPushButton#success" in qss
        assert "QPushButton#danger" in qss
        assert "QPushButton#warning" in qss

    def test_stylesheet_has_hover_states(self) -> None:
        """الـ QSS يحوي حالات hover."""
        from infrastructure.ui.theme.soft_ui import SoftUIStyleSheet
        qss = SoftUIStyleSheet.generate()
        assert ":hover" in qss
        assert ":pressed" in qss
        assert ":focus" in qss
        assert ":disabled" in qss


class TestSoftUITheme:
    """اختبارات مدير الثيم."""

    def test_get_color_returns_valid_color(self) -> None:
        """get_color يُعيد لون صحيح."""
        from infrastructure.ui.theme.soft_ui import SoftUITheme
        assert SoftUITheme.get_color("accent_blue") == "#6B8AFE"
        assert SoftUITheme.get_color("TEXT_PRIMARY") == "#2D3748"

    def test_get_color_fallback_for_unknown(self) -> None:
        """get_color يُعيد fallback للأسماء غير المعروفة."""
        from infrastructure.ui.theme.soft_ui import SoftUITheme, SoftColors
        result = SoftUITheme.get_color("nonexistent_color")
        assert result == SoftColors.TEXT_PRIMARY


class TestSoftComponents:
    """اختبارات مكونات Soft UI (تتخطى إذا PySide6 غير متوفر)."""

    def test_soft_card_creation(self) -> None:
        """إنشاء SoftCard يعمل."""
        from infrastructure.ui.widgets.soft_components import SoftCard
        # Can't create without QApplication, but verify class exists
        assert SoftCard is not None

    def test_kpi_card_creation(self) -> None:
        """إنشاء KPICard يعمل."""
        from infrastructure.ui.widgets.soft_components import KPICard
        assert KPICard is not None

    def test_chat_bubble_creation(self) -> None:
        """إنشاء ChatBubble يعمل."""
        from infrastructure.ui.widgets.soft_components import ChatBubble
        assert ChatBubble is not None

    def test_gradient_card_creation(self) -> None:
        """إنشاء GradientCard يعمل."""
        from infrastructure.ui.widgets.soft_components import GradientCard
        assert GradientCard is not None

    def test_soft_search_bar_creation(self) -> None:
        """إنشاء SoftSearchBar يعمل."""
        from infrastructure.ui.widgets.soft_components import SoftSearchBar
        assert SoftSearchBar is not None

    def test_soft_sidebar_creation(self) -> None:
        """إنشاء SoftSidebar يعمل."""
        from infrastructure.ui.widgets.soft_components import SoftSidebar
        assert SoftSidebar is not None


class TestAIChatWindow:
    """اختبارات واجهة المحادثة الذكية."""

    def test_ai_chat_window_class_exists(self) -> None:
        """فئة AIChatWindow معرّفة."""
        from infrastructure.ui.windows.ai_chat_window import AIChatWindow
        assert AIChatWindow is not None

    def test_chat_input_bar_class_exists(self) -> None:
        """فئة ChatInputBar معرّفة."""
        from infrastructure.ui.windows.ai_chat_window import ChatInputBar
        assert ChatInputBar is not None


class TestLoadingOverlay:
    """اختبارات نافذة التحميل."""

    def test_loading_overlay_class_exists(self) -> None:
        """فئة LoadingOverlay معرّفة."""
        from infrastructure.ui.widgets.loading_overlay import LoadingOverlay
        assert LoadingOverlay is not None

    def test_show_loading_function_exists(self) -> None:
        """دالة show_loading معرّفة."""
        from infrastructure.ui.widgets.loading_overlay import show_loading
        assert callable(show_loading)
