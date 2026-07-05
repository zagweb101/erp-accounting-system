"""
Service Integration Helper - يربط الخدمات المتقدمة بالـ UI

يوفر دوال سهلة للاستدعاء من أي شاشة:
- export_to_excel()
- send_email()
- scan_invoice_ocr()
- check_anomaly()
- predict_cash_flow()
"""
from __future__ import annotations

import asyncio
from typing import Optional

from PySide6.QtWidgets import QWidget, QFileDialog, QMessageBox


def export_to_excel(
    data_type: str,
    data: list[dict],
    parent: QWidget = None,
) -> Optional[str]:
    """تصدير بيانات إلى Excel."""
    filepath, _ = QFileDialog.getSaveFileName(
        parent, "تصدير إلى Excel", f"{data_type}.xlsx", "Excel Files (*.xlsx)",
    )
    if not filepath:
        return None

    try:
        from infrastructure.services.excel_service import ExcelService
        service = ExcelService()

        if data_type == "customers":
            service.export_customers(data, filepath)
        elif data_type == "products":
            service.export_products(data, filepath)
        elif data_type == "invoices":
            service.export_invoices(data, filepath)
        elif data_type == "trial_balance":
            service.export_trial_balance(data, filepath)
        else:
            QMessageBox.warning(parent, "خطأ", f"نوع غير مدعوم: {data_type}")
            return None

        QMessageBox.information(parent, "نجاح", f"تم التصدير إلى:\n{filepath}")
        return filepath
    except Exception as e:
        QMessageBox.critical(parent, "خطأ", f"فشل التصدير: {e}")
        return None


def import_from_excel(
    data_type: str,
    parent: QWidget = None,
) -> Optional[list[dict]]:
    """استيراد بيانات من Excel."""
    filepath, _ = QFileDialog.getOpenFileName(
        parent, "استيراد من Excel", "", "Excel Files (*.xlsx *.xls)",
    )
    if not filepath:
        return None

    try:
        from infrastructure.services.excel_service import ExcelService
        service = ExcelService()

        if data_type == "customers":
            data = service.import_customers(filepath)
        elif data_type == "products":
            data = service.import_products(filepath)
        else:
            return None

        QMessageBox.information(parent, "نجاح", f"تم استيراد {len(data)} عنصر")
        return data
    except Exception as e:
        QMessageBox.critical(parent, "خطأ", f"فشل الاستيراد: {e}")
        return None


def send_invoice_email(
    to_email: str,
    pdf_path: str,
    invoice_no: str,
    customer_name: str = "",
    amount: str = "",
    parent: QWidget = None,
) -> bool:
    """إرسال فاتورة بالبريد الإلكتروني."""
    try:
        from infrastructure.services.email_service import EmailService, EmailConfig
        from infrastructure.config.settings import get_settings

        settings = get_settings()
        config = EmailConfig(
            username=settings.COMPANY_EMAIL or "",
            password="",
        )

        if not config.username:
            QMessageBox.warning(parent, "إعدادات البريد",
                "يرجى إعداد بريد الشركة في .env أولاً.")
            return False

        service = EmailService(config)
        success = service.send_invoice(to_email, pdf_path, invoice_no, customer_name, amount)

        if success:
            QMessageBox.information(parent, "نجاح", f"تم الإرسال إلى:\n{to_email}")
        else:
            QMessageBox.warning(parent, "فشل", "تعذّر الإرسال. تحقق من الإعدادات.")
        return success
    except Exception as e:
        QMessageBox.critical(parent, "خطأ", f"فشل: {e}")
        return False


def scan_invoice_image(
    image_path: str,
    parent: QWidget = None,
) -> Optional[dict]:
    """مسح صورة فاتورة باستخدام OCR."""
    try:
        from infrastructure.services.advanced_ocr_service import AdvancedOCRService
        ocr = AdvancedOCRService()

        if not ocr.is_ready():
            QMessageBox.warning(parent, "OCR غير متاح",
                "Tesseract OCR غير مثبت.")
            return None

        result = ocr.parse_invoice(image_path)
        msg = (
            f"📄 نوع: {result.document_type}\n"
            f"🏢 المورد: {result.supplier_name.value}\n"
            f"📋 رقم: {result.invoice_number.value}\n"
            f"💰 الإجمالي: {result.total.value}\n"
            f"✅ الثقة: {result.overall_confidence:.0%}"
        )
        QMessageBox.information(parent, "نتائج OCR", msg)
        return {
            "supplier_name": result.supplier_name.value,
            "invoice_number": result.invoice_number.value,
            "total": result.total.value,
            "confidence": result.overall_confidence,
        }
    except Exception as e:
        QMessageBox.critical(parent, "خطأ OCR", f"فشل: {e}")
        return None


def check_invoice_anomaly(
    amount: float,
    customer_id: str = "",
    invoice_id: str = "",
    parent: QWidget = None,
) -> Optional[str]:
    """فحص فاتورة للحالات الشاذة."""
    try:
        from infrastructure.services.anomaly_detector import AnomalyDetector
        detector = AnomalyDetector()
        anomaly = detector.check_invoice_amount(amount, customer_id, invoice_id)
        if anomaly and parent:
            QMessageBox.warning(parent, f"⚠️ {anomaly.severity.upper()}", anomaly.description)
        return anomaly.description if anomaly else None
    except Exception:
        return None


def get_cash_flow_prediction(
    inflows: list[float],
    outflows: list[float],
    balance: float,
    days: int = 30,
    parent: QWidget = None,
) -> Optional[dict]:
    """الحصول على تنبؤ التدفق النقدي."""
    try:
        from infrastructure.services.cash_flow_predictor import CashFlowPredictor
        predictor = CashFlowPredictor(min_history_days=7)
        result = predictor.predict(inflows, outflows, balance, days)

        if parent:
            msg = (
                f"📊 التنبؤ ({days} يوم)\n\n"
                f"📈 داخل: {result.predicted_inflow:,.2f}\n"
                f"📉 خارج: {result.predicted_outflow:,.2f}\n"
                f"💰 صافي: {result.predicted_net:,.2f}\n\n"
                f"الرصيد المتوقع: {result.projected_balance:,.2f}\n"
                f"الثقة: {result.confidence:.0%}"
            )
            if result.warnings:
                msg += "\n\n" + "\n".join(result.warnings)
            QMessageBox.information(parent, "التنبؤ النقدي", msg)

        return {
            "predicted_inflow": result.predicted_inflow,
            "predicted_outflow": result.predicted_outflow,
            "projected_balance": result.projected_balance,
            "confidence": result.confidence,
            "warnings": result.warnings,
        }
    except Exception as e:
        if parent:
            QMessageBox.critical(parent, "خطأ", f"فشل: {e}")
        return None
