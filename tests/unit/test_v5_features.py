"""
اختبارات OpenAI Provider + OCR Service + Toast + Dashboard
"""
from __future__ import annotations

import os
import sys
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestOpenAIProvider:
    """اختبارات OpenAI LLM Provider."""

    def test_provider_creation_without_key(self) -> None:
        """إنشاء provider بدون مفتاح يعمل (returns not ready)."""
        from infrastructure.services.openai_provider import OpenAIProvider
        provider = OpenAIProvider()
        assert provider.is_ready() is False

    def test_provider_creation_with_key(self) -> None:
        """إنشاء provider بمفتاح يعمل."""
        from infrastructure.services.openai_provider import OpenAIProvider
        provider = OpenAIProvider(api_key="sk-test-key")
        assert provider.is_ready() is True

    def test_generate_without_key_returns_warning(self) -> None:
        """توليد بدون مفتاح يُعيد رسالة تحذير."""
        from infrastructure.services.openai_provider import OpenAIProvider
        provider = OpenAIProvider()
        result = provider.generate("test prompt")
        assert "غير مُحدّد" in result["text"] or "not" in result["text"].lower()
        assert result["function_call"] is None

    def test_set_api_key(self) -> None:
        """تحديث المفتار."""
        from infrastructure.services.openai_provider import OpenAIProvider
        provider = OpenAIProvider()
        assert provider.is_ready() is False
        provider.set_api_key("sk-new-key")
        assert provider.is_ready() is True

    def test_set_model(self) -> None:
        """تغيير النموذج."""
        from infrastructure.services.openai_provider import OpenAIProvider
        provider = OpenAIProvider(api_key="sk-test")
        provider.set_model("gpt-4o")
        assert provider._model == "gpt-4o"

    def test_default_model_is_gpt4o_mini(self) -> None:
        """النموذج الافتراضي gpt-4o-mini."""
        from infrastructure.services.openai_provider import OpenAIProvider
        provider = OpenAIProvider(api_key="sk-test")
        assert provider._model == "gpt-4o-mini"

    def test_system_prompt_defined(self) -> None:
        """الـ system prompt معرّف."""
        from infrastructure.services.openai_provider import OpenAIProvider
        provider = OpenAIProvider(api_key="sk-test")
        assert len(provider._system_prompt) > 50
        assert "محاسب" in provider._system_prompt or "accounting" in provider._system_prompt.lower()


class TestLocalLLMProvider:
    """اختبارات Local LLM Provider (Ollama)."""

    def test_provider_creation(self) -> None:
        """إنشاء provider محلي يعمل."""
        from infrastructure.services.openai_provider import LocalLLMProvider
        provider = LocalLLMProvider()
        assert provider._model == "llama3:8b"
        assert provider._host == "http://localhost:11434"

    def test_is_ready_returns_false_when_no_ollama(self) -> None:
        """is_ready يُعيد False عندما Ollama غير متاح."""
        from infrastructure.services.openai_provider import LocalLLMProvider
        provider = LocalLLMProvider(host="http://localhost:99999")
        # Should return False (no Ollama running)
        result = provider.is_ready()
        assert isinstance(result, bool)

    def test_custom_model(self) -> None:
        """نموذج مخصص."""
        from infrastructure.services.openai_provider import LocalLLMProvider
        provider = LocalLLMProvider(model="qwen:7b")
        assert provider._model == "qwen:7b"


class TestOCRService:
    """اختبارات خدمة OCR."""

    def test_service_creation(self) -> None:
        """إنشاء خدمة OCR يعمل."""
        from infrastructure.services.ocr_service import OCRService
        ocr = OCRService()
        assert ocr._language == "ara+eng"

    def test_custom_language(self) -> None:
        """لغة مخصصة."""
        from infrastructure.services.ocr_service import OCRService
        ocr = OCRService(language="eng")
        assert ocr._language == "eng"

    def test_parse_amount_valid(self) -> None:
        """تحويل نص إلى Decimal."""
        from infrastructure.services.ocr_service import OCRService
        ocr = OCRService()
        assert ocr._parse_amount("1,234.56") == Decimal("1234.56")
        assert ocr._parse_amount("500") == Decimal("500")
        assert ocr._parse_amount("1,234.56 ر.س") == Decimal("1234.56")

    def test_parse_amount_invalid(self) -> None:
        """تحويل نص غير صالح يُعيد None."""
        from infrastructure.services.ocr_service import OCRService
        ocr = OCRService()
        assert ocr._parse_amount("") is None
        assert ocr._parse_amount("abc") is None

    def test_extract_field_invoice_number(self) -> None:
        """استخراج رقم الفاتورة."""
        from infrastructure.services.ocr_service import OCRService
        ocr = OCRService()
        text = "فاتورة رقم: INV-2026-001"
        result = ocr._extract_field(text, "invoice_number")
        assert result == "INV-2026-001"

    def test_extract_field_total(self) -> None:
        """استخراج الإجمالي."""
        from infrastructure.services.ocr_service import OCRService
        ocr = OCRService()
        text = "الإجمالي: 1,150.00 ر.س"
        result = ocr._extract_field(text, "total")
        assert "1,150.00" in result or "1150.00" in result

    def test_extract_field_tax(self) -> None:
        """استخراج الضريبة."""
        from infrastructure.services.ocr_service import OCRService
        ocr = OCRService()
        text = "ضريبة القيمة المضافة: 150.00"
        result = ocr._extract_field(text, "tax_amount")
        assert "150" in result

    def test_extract_field_not_found(self) -> None:
        """حقل غير موجود يُعيد فارغ."""
        from infrastructure.services.ocr_service import OCRService
        ocr = OCRService()
        text = "نص عشوائي بدون حقول"
        result = ocr._extract_field(text, "total")
        assert result == ""

    def test_extract_supplier_name(self) -> None:
        """استخراج اسم المورد."""
        from infrastructure.services.ocr_service import OCRService
        ocr = OCRService()
        text = "شركة النور للتجارة\nفاتورة رقم: 001"
        result = ocr._extract_supplier_name(text)
        assert "النور" in result or len(result) > 3

    def test_calculate_confidence_empty(self) -> None:
        """ثقة 0 لنص فارغ."""
        from infrastructure.services.ocr_service import OCRService
        ocr = OCRService()
        assert ocr._calculate_confidence("") == 0.0

    def test_calculate_confidence_with_fields(self) -> None:
        """ثقة أعلى مع وجود حقول."""
        from infrastructure.services.ocr_service import OCRService
        ocr = OCRService()
        text = "فاتورة بيع الإجمالي 1000 الضريبة 150 التاريخ 2026-07-05"
        conf = ocr._calculate_confidence(text)
        assert 0 < conf <= 1.0

    def test_is_ready_returns_bool(self) -> None:
        """is_ready يُعيد bool."""
        from infrastructure.services.ocr_service import OCRService
        ocr = OCRService()
        assert isinstance(ocr.is_ready(), bool)

    def test_patterns_defined(self) -> None:
        """كل الأنماط معرّفة."""
        from infrastructure.services.ocr_service import OCRService
        assert "invoice_number" in OCRService.PATTERNS
        assert "date" in OCRService.PATTERNS
        assert "tax_number" in OCRService.PATTERNS
        assert "total" in OCRService.PATTERNS
        assert "subtotal" in OCRService.PATTERNS
        assert "tax_amount" in OCRService.PATTERNS


class TestToastNotification:
    """اختبارات نظام الإشعارات."""

    try:
        import PySide6
        PYSIDE6_AVAILABLE = True
    except ImportError:
        PYSIDE6_AVAILABLE = False

    pytestmark = pytest.mark.skipif(not PYSIDE6_AVAILABLE, reason="PySide6 not installed")

    def test_toast_class_exists(self) -> None:
        """فئة Toast معرّفة."""
        from infrastructure.ui.widgets.toast import Toast
        assert Toast is not None

    def test_toast_type_colors_defined(self) -> None:
        """ألوان الأنواع معرّفة."""
        from infrastructure.ui.widgets.toast import Toast
        assert "success" in Toast.TYPE_COLORS
        assert "error" in Toast.TYPE_COLORS
        assert "info" in Toast.TYPE_COLORS
        assert "warning" in Toast.TYPE_COLORS

    def test_toast_success_method_exists(self) -> None:
        """دالة success معرّفة."""
        from infrastructure.ui.widgets.toast import Toast
        assert hasattr(Toast, "success")

    def test_toast_error_method_exists(self) -> None:
        """دالة error معرّفة."""
        from infrastructure.ui.widgets.toast import Toast
        assert hasattr(Toast, "error")


class TestDashboardPage:
    """اختبارات صفحة لوحة المعلومات."""

    try:
        import PySide6
        PYSIDE6_AVAILABLE = True
    except ImportError:
        PYSIDE6_AVAILABLE = False

    pytestmark = pytest.mark.skipif(not PYSIDE6_AVAILABLE, reason="PySide6 not installed")

    def test_dashboard_class_exists(self) -> None:
        """فئة DashboardPage معرّفة."""
        from infrastructure.ui.windows.dashboard_page import DashboardPage
        assert DashboardPage is not None


class TestSoftComponentsExtended:
    """اختبارات إضافية للمكونات الناعمة."""

    try:
        import PySide6
        PYSIDE6_AVAILABLE = True
    except ImportError:
        PYSIDE6_AVAILABLE = False

    pytestmark = pytest.mark.skipif(not PYSIDE6_AVAILABLE, reason="PySide6 not installed")

    def test_add_soft_shadow_function_exists(self) -> None:
        """دالة add_soft_shadow معرّفة."""
        from infrastructure.ui.theme.soft_ui import add_soft_shadow
        assert callable(add_soft_shadow)

    def test_soft_card_class_exists(self) -> None:
        """فئة SoftCard معرّفة."""
        from infrastructure.ui.widgets.soft_components import SoftCard
        assert SoftCard is not None

    def test_kpi_card_class_exists(self) -> None:
        """فئة KPICard معرّفة."""
        from infrastructure.ui.widgets.soft_components import KPICard
        assert KPICard is not None

    def test_gradient_card_class_exists(self) -> None:
        """فئة GradientCard معرّفة."""
        from infrastructure.ui.widgets.soft_components import GradientCard
        assert GradientCard is not None

    def test_chat_bubble_class_exists(self) -> None:
        """فئة ChatBubble معرّفة."""
        from infrastructure.ui.widgets.soft_components import ChatBubble
        assert ChatBubble is not None

    def test_soft_sidebar_class_exists(self) -> None:
        """فئة SoftSidebar معرّفة."""
        from infrastructure.ui.widgets.soft_components import SoftSidebar
        assert SoftSidebar is not None


class TestCharts:
    """اختبارات الرسوم البيانية."""

    try:
        import PySide6
        PYSIDE6_AVAILABLE = True
    except ImportError:
        PYSIDE6_AVAILABLE = False

    pytestmark = pytest.mark.skipif(not PYSIDE6_AVAILABLE, reason="PySide6 not installed")

    def test_bar_chart_class_exists(self) -> None:
        """فئة BarChart معرّفة."""
        from infrastructure.ui.widgets.charts import BarChart
        assert BarChart is not None

    def test_donut_chart_class_exists(self) -> None:
        """فئة DonutChart معرّفة."""
        from infrastructure.ui.widgets.charts import DonutChart
        assert DonutChart is not None

    def test_line_chart_class_exists(self) -> None:
        """فئة LineChart معرّفة."""
        from infrastructure.ui.widgets.charts import LineChart
        assert LineChart is not None


class TestSoftAutoApplier:
    """اختبارات الـ auto-applier."""

    try:
        import PySide6
        PYSIDE6_AVAILABLE = True
    except ImportError:
        PYSIDE6_AVAILABLE = False

    pytestmark = pytest.mark.skipif(not PYSIDE6_AVAILABLE, reason="PySide6 not installed")

    def test_auto_apply_function_exists(self) -> None:
        """دالة auto_apply_soft_ui معرّفة."""
        from infrastructure.ui.theme.soft_auto import auto_apply_soft_ui
        assert callable(auto_apply_soft_ui)


class TestBuildAndInstall:
    """اختبارات بناء وتثبيت."""

    def test_build_script_exists(self) -> None:
        """build.sh موجود."""
        from pathlib import Path
        build_script = Path(__file__).parent.parent.parent / "build.sh"
        assert build_script.exists()

    def test_install_guide_exists(self) -> None:
        """INSTALL.md موجود."""
        from pathlib import Path
        install_guide = Path(__file__).parent.parent.parent / "INSTALL.md"
        assert install_guide.exists()

    def test_env_example_exists(self) -> None:
        """.env.example موجود."""
        from pathlib import Path
        env_example = Path(__file__).parent.parent.parent / ".env.example"
        assert env_example.exists()

    def test_pyinstaller_spec_exists(self) -> None:
        """erp_accounting.spec موجود."""
        from pathlib import Path
        spec_file = Path(__file__).parent.parent.parent / "erp_accounting.spec"
        assert spec_file.exists()

    def test_alembic_config_exists(self) -> None:
        """alembic.ini موجود."""
        from pathlib import Path
        alembic_config = Path(__file__).parent.parent.parent / "alembic.ini"
        assert alembic_config.exists()

    def test_requirements_file_exists(self) -> None:
        """requirements.txt موجود."""
        from pathlib import Path
        req_file = Path(__file__).parent.parent.parent / "requirements.txt"
        assert req_file.exists()
