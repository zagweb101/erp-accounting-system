"""
OCR Service — خدمة التعرف الضوئي على المستندات

تستخرج بيانات الفواتير من الصور تلقائيًا.
يدعم:
- استخراج النص من الصور (PIL + pytesseract)
- تحليل الفواتير السعودية (فاتورة ضريبية)
- استخراج: المورد، رقم الفاتورة، التاريخ، البنود، الإجمالي، الضريبة

Usage:
    from infrastructure.services.ocr_service import OCRService

    ocr = OCRService()
    result = ocr.extract_from_image("/path/to/invoice.jpg")
    print(result["supplier_name"])  # "شركة النور للتجارة"
    print(result["total"])          # 1150.00
"""
from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional


class OCRService:
    """خدمة استخراج البيانات من المستندات المصوّرة.

    يتطلب تثبيت: pip install pytesseract Pillow
    كما يتطلب Tesseract OCR: https://github.com/tesseract-ocr/tesseract
    """

    # Patterns for Arabic invoice extraction
    PATTERNS = {
        "invoice_number": [
            r"فاتورة\s*(?:رقم|NUMBER)[:\s]*([A-Z0-9\-]+)",
            r"(?:INV|INVOICE)[:\s]*([A-Z0-9\-]+)",
            r"رقم\s*الفاتورة[:\s]*([A-Z0-9\-]+)",
        ],
        "date": [
            r"(?:التاريخ|DATE)[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
            r"(\d{4}-\d{2}-\d{2})",
        ],
        "tax_number": [
            r"(?:الرقم\s*الضريبي|VAT|TAX\s*NO)[:\s]*(\d{15})",
            r"الرقم\s*الضريبي[:\s]*(\d+)",
        ],
        "total": [
            r"(?:الإجمالي|TOTAL)[:\s]*([\d,]+\.?\d*)",
            r"(?:المبلغ\s*الإجمالي|GRAND\s*TOTAL)[:\s]*([\d,]+\.?\d*)",
            r"(?:المطلوب|AMOUNT\s*DUE)[:\s]*([\d,]+\.?\d*)",
        ],
        "subtotal": [
            r"(?:المجموع\s*الفرعي|SUBTOTAL|SUB\s*TOTAL)[:\s]*([\d,]+\.?\d*)",
            r"(?:قبل\s*الضريبة|BEFORE\s*TAX)[:\s]*([\d,]+\.?\d*)",
        ],
        "tax_amount": [
            r"(?:ضريبة\s*القيمة\s*المضافة|VAT|الضريبة)[:\s]*([\d,]+\.?\d*)",
            r"(?:ض\.ق\.م|VAT\s*15%)[:\s]*([\d,]+\.?\d*)",
        ],
    }

    def __init__(self, language: str = "ara+eng") -> None:
        """تهيئة خدمة OCR.

        Args:
            language: لغة الـ OCR (افتراضي: عربي + إنجليزي).
        """
        self._language = language
        self._tesseract = None

    def _get_tesseract(self):
        """الحصول على pytesseract (lazy init)."""
        if self._tesseract is None:
            try:
                import pytesseract
                self._tesseract = pytesseract
            except ImportError:
                raise ImportError(
                    "pytesseract not installed. Run: pip install pytesseract Pillow"
                )
        return self._tesseract

    def extract_text(self, image_path: str | Path) -> str:
        """استخراج النص الخام من صورة.

        Args:
            image_path: مسار الصورة.

        Returns: النص المستخرج.
        """
        try:
            from PIL import Image
            pytesseract = self._get_tesseract()

            img = Image.open(str(image_path))
            text = pytesseract.image_to_string(img, lang=self._language)
            return text.strip()
        except Exception as e:
            return f"OCR Error: {e}"

    def extract_from_image(self, image_path: str | Path) -> dict:
        """استخراج بيانات فاتورة من صورة.

        Args:
            image_path: مسار صورة الفاتورة.

        Returns: dict with:
            - supplier_name: str
            - invoice_number: str
            - date: str
            - tax_number: str
            - subtotal: Decimal
            - tax_amount: Decimal
            - total: Decimal
            - raw_text: str (النص الخام)
            - confidence: float (0-1)
        """
        raw_text = self.extract_text(image_path)

        result = {
            "supplier_name": self._extract_supplier_name(raw_text),
            "invoice_number": self._extract_field(raw_text, "invoice_number"),
            "date": self._extract_field(raw_text, "date"),
            "tax_number": self._extract_field(raw_text, "tax_number"),
            "subtotal": self._parse_amount(self._extract_field(raw_text, "subtotal")),
            "tax_amount": self._parse_amount(self._extract_field(raw_text, "tax_amount")),
            "total": self._parse_amount(self._extract_field(raw_text, "total")),
            "raw_text": raw_text,
            "confidence": self._calculate_confidence(raw_text),
        }

        return result

    def _extract_supplier_name(self, text: str) -> str:
        """استخراج اسم المورد/الشركة."""
        lines = text.strip().split("\n")
        # Usually the first non-empty line is the company name
        for line in lines[:5]:
            line = line.strip()
            if len(line) > 3 and not line[0].isdigit():
                return line
        return ""

    def _extract_field(self, text: str, field_name: str) -> str:
        """استخراج حقل محدد باستخدام regex patterns."""
        patterns = self.PATTERNS.get(field_name, [])
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""

    def _parse_amount(self, text: str) -> Optional[Decimal]:
        """تحويل نص إلى Decimal."""
        if not text:
            return None
        try:
            clean = text.replace(",", "").replace("ر.س", "").replace("SAR", "").strip()
            return Decimal(clean)
        except Exception:
            return None

    def _calculate_confidence(self, text: str) -> float:
        """تقدير ثقة الـ OCR (0-1)."""
        if not text:
            return 0.0
        # Heuristic: more text = higher confidence
        length_score = min(len(text) / 500, 1.0)
        # Check for key fields
        fields_found = 0
        for field in ["فاتورة", "الإجمالي", "الضريبة", "التاريخ"]:
            if field in text:
                fields_found += 1
        field_score = fields_found / 4
        return (length_score + field_score) / 2

    def is_ready(self) -> bool:
        """هل Tesseract مثبت وجاهز؟"""
        try:
            self._get_tesseract()
            return True
        except ImportError:
            return False
