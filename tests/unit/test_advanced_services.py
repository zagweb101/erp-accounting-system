"""
اختبارات شاملة للخدمات المتقدمة v8.0

Tests:
- AdvancedOpenAIProvider (caching, rate limit, cost tracking)
- AdvancedOCRService (parsing, confidence, line items)
- CashFlowPredictor (moving average, linear regression, seasonal)
- AnomalyDetector (large invoice, after hours, rapid edits, duplicate)
- ExcelService (export, import, templates)
- EmailService (config, templates, ready check)
- BankReconciliationService (matching, report)
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestAdvancedOpenAIProvider:
    """اختبارات OpenAI Provider المتقدم."""

    def test_creation_without_key(self) -> None:
        from infrastructure.services.advanced_llm_provider import AdvancedOpenAIProvider
        provider = AdvancedOpenAIProvider()
        assert provider.is_ready() is False

    def test_creation_with_key(self) -> None:
        from infrastructure.services.advanced_llm_provider import AdvancedOpenAIProvider
        provider = AdvancedOpenAIProvider(api_key="sk-test")
        assert provider.is_ready() is True

    def test_generate_without_key_returns_warning(self) -> None:
        from infrastructure.services.advanced_llm_provider import AdvancedOpenAIProvider
        provider = AdvancedOpenAIProvider()
        result = provider.generate("test")
        assert "غير مُحدّد" in result["text"]
        assert result["function_call"] is None

    def test_cache_enabled_by_default(self) -> None:
        from infrastructure.services.advanced_llm_provider import AdvancedOpenAIProvider
        provider = AdvancedOpenAIProvider(api_key="sk-test")
        assert provider._enable_cache is True

    def test_rate_limiting(self) -> None:
        from infrastructure.services.advanced_llm_provider import AdvancedOpenAIProvider
        provider = AdvancedOpenAIProvider(api_key="sk-test", rate_limit_per_minute=3)
        assert provider._check_rate_limit() is True
        assert provider._check_rate_limit() is True
        assert provider._check_rate_limit() is True
        assert provider._check_rate_limit() is False  # Exceeded

    def test_usage_tracking(self) -> None:
        from infrastructure.services.advanced_llm_provider import AdvancedOpenAIProvider
        provider = AdvancedOpenAIProvider(api_key="sk-test")
        usage = provider.get_usage()
        assert usage.total_tokens == 0
        assert usage.requests_count == 0

    def test_usage_report(self) -> None:
        from infrastructure.services.advanced_llm_provider import AdvancedOpenAIProvider
        provider = AdvancedOpenAIProvider(api_key="sk-test")
        report = provider.get_usage_report()
        assert "تقرير" in report or "report" in report.lower()

    def test_clear_cache(self) -> None:
        from infrastructure.services.advanced_llm_provider import AdvancedOpenAIProvider
        provider = AdvancedOpenAIProvider(api_key="sk-test")
        provider._cache["test"] = {"text": "cached"}
        assert len(provider._cache) == 1
        provider.clear_cache()
        assert len(provider._cache) == 0

    def test_fallback_provider(self) -> None:
        from infrastructure.services.advanced_llm_provider import AdvancedOpenAIProvider
        from infrastructure.services.ai_agent_service import MockLLMProvider
        fallback = MockLLMProvider()
        provider = AdvancedOpenAIProvider(api_key="", fallback_provider=fallback)
        # Should use fallback when no key
        result = provider.generate("test")
        assert result["text"] != ""

    def test_pricing_defined(self) -> None:
        from infrastructure.services.advanced_llm_provider import AdvancedOpenAIProvider
        assert "gpt-4o-mini" in AdvancedOpenAIProvider.PRICING
        assert "gpt-4o" in AdvancedOpenAIProvider.PRICING


class TestAdvancedOCRService:
    """اختبارات OCR المتقدم."""

    def test_creation(self) -> None:
        from infrastructure.services.advanced_ocr_service import AdvancedOCRService
        ocr = AdvancedOCRService()
        assert ocr._language == "ara+eng"

    def test_parse_amount_valid(self) -> None:
        from infrastructure.services.advanced_ocr_service import AdvancedOCRService
        ocr = AdvancedOCRService()
        result = ocr._parse_text("فاتورة رقم: INV-001\nالإجمالي: 1,150.00\nالضريبة: 150.00")
        assert result.document_type == "invoice"
        assert result.invoice_number.value == "INV-001"
        assert result.overall_confidence > 0

    def test_detect_invoice(self) -> None:
        from infrastructure.services.advanced_ocr_service import AdvancedOCRService
        ocr = AdvancedOCRService()
        assert ocr._detect_document_type("فاتورة ضريبية") == "invoice"
        assert ocr._detect_document_type("TAX INVOICE") == "invoice"

    def test_detect_receipt(self) -> None:
        from infrastructure.services.advanced_ocr_service import AdvancedOCRService
        ocr = AdvancedOCRService()
        assert ocr._detect_document_type("إيصال استلام") == "receipt"
        assert ocr._detect_document_type("RECEIPT#123") == "receipt"

    def test_detect_unknown(self) -> None:
        from infrastructure.services.advanced_ocr_service import AdvancedOCRService
        ocr = AdvancedOCRService()
        assert ocr._detect_document_type("نص عشوائي") == "unknown"

    def test_extract_field_confidence(self) -> None:
        from infrastructure.services.advanced_ocr_service import AdvancedOCRService
        ocr = AdvancedOCRService()
        value, conf, source = ocr._extract_field_with_confidence(
            "فاتورة رقم: INV-001",
            ocr.PATTERNS["invoice_number"],
        )
        assert value == "INV-001"
        assert conf > 0.8  # First pattern = high confidence

    def test_extract_field_not_found(self) -> None:
        from infrastructure.services.advanced_ocr_service import AdvancedOCRService
        ocr = AdvancedOCRService()
        value, conf, source = ocr._extract_field_with_confidence(
            "نص عشوائي بدون أي حقول معروفة",
            ocr.PATTERNS["invoice_number"],
        )
        assert value == ""

    def test_line_items_extraction(self) -> None:
        from infrastructure.services.advanced_ocr_service import AdvancedOCRService
        ocr = AdvancedOCRService()
        text = "لابتوب 2x2500=5000\nماوس 5x50=250"
        items = ocr._extract_line_items(text)
        assert len(items) == 2
        assert items[0]["quantity"] == 2.0
        assert items[0]["unit_price"] == 2500.0


class TestCashFlowPredictor:
    """اختبارات التنبؤ بالتدفق النقدي."""

    def test_insufficient_data(self) -> None:
        from infrastructure.services.cash_flow_predictor import CashFlowPredictor
        predictor = CashFlowPredictor(min_history_days=30)
        result = predictor.predict(
            historical_inflows=[100, 200, 300],
            historical_outflows=[50, 100, 150],
            current_balance=5000,
            forecast_days=30,
        )
        assert result.confidence == 0.0
        assert len(result.warnings) > 0

    def test_moving_average(self) -> None:
        from infrastructure.services.cash_flow_predictor import CashFlowPredictor
        predictor = CashFlowPredictor(min_history_days=10)
        inflows = [1000] * 15  # 15 days of 1000 inflow
        outflows = [500] * 15
        result = predictor.predict(inflows, outflows, 10000, 30, method="moving_average")
        assert result.method == "moving_average"
        assert result.predicted_inflow > 0
        assert len(result.daily_predictions) == 30

    def test_linear_regression(self) -> None:
        from infrastructure.services.cash_flow_predictor import CashFlowPredictor
        predictor = CashFlowPredictor(min_history_days=10)
        # Increasing trend
        inflows = [1000 + i * 100 for i in range(20)]
        outflows = [500] * 20
        result = predictor.predict(inflows, outflows, 10000, 30, method="linear_regression")
        assert result.method == "linear_regression"
        assert len(result.daily_predictions) == 30

    def test_seasonal_naive(self) -> None:
        from infrastructure.services.cash_flow_predictor import CashFlowPredictor
        predictor = CashFlowPredictor(min_history_days=10)
        inflows = [100, 200, 300, 400, 500, 600, 700] * 3  # 21 days
        outflows = [50, 100, 150, 200, 250, 300, 350] * 3
        result = predictor.predict(inflows, outflows, 10000, 14, method="seasonal_naive")
        assert result.method == "seasonal_naive"
        assert len(result.daily_predictions) == 14

    def test_shortfall_warning(self) -> None:
        from infrastructure.services.cash_flow_predictor import CashFlowPredictor
        predictor = CashFlowPredictor(min_history_days=10)
        inflows = [100] * 15
        outflows = [5000] * 15  # High outflow → negative balance
        result = predictor.predict(inflows, outflows, 1000, 30, method="moving_average")
        assert len(result.warnings) > 0
        assert "نقص" in result.warnings[0] or "⚠" in result.warnings[0]

    def test_linear_fit(self) -> None:
        from infrastructure.services.cash_flow_predictor import CashFlowPredictor
        predictor = CashFlowPredictor()
        slope, intercept = predictor._linear_fit([1, 2, 3, 4, 5], [2, 4, 6, 8, 10])
        assert abs(slope - 2.0) < 0.01  # Perfect linear: y = 2x
        assert abs(intercept - 0.0) < 0.01


class TestAnomalyDetector:
    """اختبارات كاشف الحالات الشاذة."""

    def test_large_invoice_detected(self) -> None:
        from infrastructure.services.anomaly_detector import AnomalyDetector
        detector = AnomalyDetector()
        # Add 10 normal invoices
        for i in range(10):
            detector.check_invoice_amount(100, invoice_id=str(i))
        # Add a very large invoice
        anomaly = detector.check_invoice_amount(10000, invoice_id="big")
        assert anomaly is not None
        assert anomaly.type == "large_invoice"
        assert anomaly.severity in ["medium", "high", "critical"]

    def test_normal_invoice_no_anomaly(self) -> None:
        from infrastructure.services.anomaly_detector import AnomalyDetector
        detector = AnomalyDetector()
        # Add 15 normal invoices with same amount
        for i in range(15):
            detector.check_invoice_amount(100, invoice_id=str(i))
        # 16th invoice with very close amount (no anomaly)
        result = detector.check_invoice_amount(100, invoice_id="normal")
        assert result is None  # Same amount = no anomaly

    def test_after_hours_detection(self) -> None:
        from infrastructure.services.anomaly_detector import AnomalyDetector
        detector = AnomalyDetector()
        # 2 AM
        late_time = datetime.now().replace(hour=2, minute=0)
        anomaly = detector.check_after_hours_access("admin", late_time)
        assert anomaly is not None
        assert anomaly.type == "after_hours"

    def test_business_hours_no_anomaly(self) -> None:
        from infrastructure.services.anomaly_detector import AnomalyDetector
        detector = AnomalyDetector()
        # 2 PM
        day_time = datetime.now().replace(hour=14, minute=0)
        anomaly = detector.check_after_hours_access("admin", day_time)
        assert anomaly is None

    def test_rapid_edits_detection(self) -> None:
        from infrastructure.services.anomaly_detector import AnomalyDetector
        detector = AnomalyDetector()
        user_id = str(uuid4())
        # 6 rapid edits (threshold is 5)
        for _ in range(6):
            anomaly = detector.check_rapid_edits(user_id, "update")
        assert anomaly is not None
        assert anomaly.type == "rapid_edit"

    def test_credit_limit_breach(self) -> None:
        from infrastructure.services.anomaly_detector import AnomalyDetector
        detector = AnomalyDetector()
        anomaly = detector.check_credit_limit_breach(
            customer_name="أحمد",
            credit_limit=5000,
            current_balance=4000,
            invoice_amount=2000,  # Total = 6000 > 5000
        )
        assert anomaly is not None
        assert anomaly.type == "credit_limit"

    def test_credit_limit_ok(self) -> None:
        from infrastructure.services.anomaly_detector import AnomalyDetector
        detector = AnomalyDetector()
        anomaly = detector.check_credit_limit_breach(
            customer_name="أحمد",
            credit_limit=10000,
            current_balance=4000,
            invoice_amount=2000,  # Total = 6000 < 10000
        )
        assert anomaly is None

    def test_duplicate_invoice_detection(self) -> None:
        from infrastructure.services.anomaly_detector import AnomalyDetector
        detector = AnomalyDetector()
        now = datetime.now()
        # First invoice
        detector.check_duplicate_invoice(1000.00, "cust-1", now)
        # Duplicate within 5 minutes
        anomaly = detector.check_duplicate_invoice(1000.00, "cust-1", now + timedelta(seconds=30))
        assert anomaly is not None
        assert anomaly.type == "duplicate"

    def test_different_amounts_no_duplicate(self) -> None:
        from infrastructure.services.anomaly_detector import AnomalyDetector
        detector = AnomalyDetector()
        now = datetime.now()
        detector.check_duplicate_invoice(1000.00, "cust-1", now)
        anomaly = detector.check_duplicate_invoice(2000.00, "cust-1", now + timedelta(seconds=30))
        assert anomaly is None

    def test_statistics(self) -> None:
        from infrastructure.services.anomaly_detector import AnomalyDetector
        detector = AnomalyDetector()
        for i in range(5):
            detector.check_invoice_amount(100, invoice_id=str(i))
        stats = detector.get_statistics()
        assert stats["tracked_invoices"] == 5


class TestExcelService:
    """اختبارات خدمة Excel."""

    def test_service_creation(self) -> None:
        from infrastructure.services.excel_service import ExcelService
        service = ExcelService()
        assert service is not None

    def test_export_customers(self, tmp_path) -> None:
        from infrastructure.services.excel_service import ExcelService
        service = ExcelService()
        filepath = tmp_path / "customers.xlsx"
        result = service.export_customers(
            [{"code": "C-001", "name": "Test", "phone": "050", "email": "t@e.com",
              "current_balance": 1000, "credit_limit": 5000, "is_active": True}],
            filepath,
        )
        assert Path(result).exists()

    def test_export_products(self, tmp_path) -> None:
        from infrastructure.services.excel_service import ExcelService
        service = ExcelService()
        filepath = tmp_path / "products.xlsx"
        result = service.export_products(
            [{"sku": "P-001", "name": "Test", "cost_price": 100, "sale_price": 200}],
            filepath,
        )
        assert Path(result).exists()

    def test_export_invoices(self, tmp_path) -> None:
        from infrastructure.services.excel_service import ExcelService
        service = ExcelService()
        filepath = tmp_path / "invoices.xlsx"
        result = service.export_invoices(
            [{"invoice_no": "INV-001", "invoice_type": "SALE", "total": 1000}],
            filepath,
        )
        assert Path(result).exists()

    def test_generate_customer_template(self, tmp_path) -> None:
        from infrastructure.services.excel_service import ExcelService
        service = ExcelService()
        filepath = tmp_path / "template.xlsx"
        result = service.generate_customer_template(filepath)
        assert Path(result).exists()

    def test_generate_product_template(self, tmp_path) -> None:
        from infrastructure.services.excel_service import ExcelService
        service = ExcelService()
        filepath = tmp_path / "template.xlsx"
        result = service.generate_product_template(filepath)
        assert Path(result).exists()

    def test_import_customers(self, tmp_path) -> None:
        from infrastructure.services.excel_service import ExcelService
        service = ExcelService()
        # First export, then import
        filepath = tmp_path / "customers.xlsx"
        service.export_customers(
            [{"code": "C-001", "name": "Test", "phone": "050", "email": "t@e.com",
              "current_balance": 1000, "credit_limit": 5000, "is_active": True}],
            filepath,
        )
        # Import
        customers = service.import_customers(filepath)
        assert len(customers) >= 1
        assert customers[0]["code"] == "C-001"


class TestEmailService:
    """اختبارات خدمة البريد."""

    def test_service_creation(self) -> None:
        from infrastructure.services.email_service import EmailService, EmailConfig
        service = EmailService()
        assert service is not None

    def test_not_ready_without_config(self) -> None:
        from infrastructure.services.email_service import EmailService
        service = EmailService()
        assert service.is_ready() is False

    def test_ready_with_config(self) -> None:
        from infrastructure.services.email_service import EmailService, EmailConfig
        config = EmailConfig(username="test@gmail.com", password="pass")
        service = EmailService(config)
        assert service.is_ready() is True

    def test_send_without_config_returns_false(self) -> None:
        from infrastructure.services.email_service import EmailService
        service = EmailService()
        result = service.send("to@test.com", "subject", "body")
        assert result is False

    def test_invoice_template_contains_invoice_no(self) -> None:
        from infrastructure.services.email_service import EmailService
        service = EmailService()
        template = service._invoice_email_template("INV-001", "أحمد", "1000")
        assert "INV-001" in template
        assert "أحمد" in template


class TestBankReconciliation:
    """اختبارات التسوية البنكية."""

    def test_service_creation(self) -> None:
        from infrastructure.services.bank_reconciliation_service import BankReconciliationService
        service = BankReconciliationService()
        assert service is not None

    def test_perfect_match(self) -> None:
        from infrastructure.services.bank_reconciliation_service import (
            BankReconciliationService, BankTransaction,
        )
        service = BankReconciliationService()
        date = datetime.now()
        bank_txs = [BankTransaction(
            date=date, description="Payment", amount=Decimal("1000"),
            balance_after=Decimal("9000"),
        )]
        system_payments = [{"date": date, "amount": 1000, "invoice_no": "INV-001"}]

        result = service.reconcile(bank_txs, system_payments)
        assert len(result.matched_transactions) == 1
        assert len(result.unmatched_bank) == 0
        assert len(result.unmatched_system) == 0

    def test_unmatched_bank(self) -> None:
        from infrastructure.services.bank_reconciliation_service import (
            BankReconciliationService, BankTransaction,
        )
        service = BankReconciliationService()
        date = datetime.now()
        bank_txs = [BankTransaction(
            date=date, description="Unknown", amount=Decimal("500"),
            balance_after=Decimal("9500"),
        )]
        system_payments = [{"date": date, "amount": 1000, "invoice_no": "INV-001"}]

        result = service.reconcile(bank_txs, system_payments)
        assert len(result.unmatched_bank) == 1
        assert len(result.unmatched_system) == 1

    def test_reconciliation_report(self) -> None:
        from infrastructure.services.bank_reconciliation_service import (
            BankReconciliationService, ReconciliationResult,
        )
        service = BankReconciliationService()
        result = ReconciliationResult(
            bank_balance=Decimal("10000"),
            system_balance=Decimal("9500"),
            difference=Decimal("500"),
        )
        report = service.generate_reconciliation_report(result)
        assert "التسوية" in report
        assert "10,000" in report
