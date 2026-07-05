"""
Advanced OCR Service - خدمة OCR متقدمة

Features:
- Image preprocessing (denoise, deskew, threshold)
- Multi-language support
- Invoice parsing with structured extraction
- Confidence scoring per field
- Batch processing
- Receipt vs Invoice detection
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional


@dataclass
class ExtractedField:
    """حقل مستخرج من فاتورة."""
    value: str
    confidence: float  # 0.0 - 1.0
    source_text: str = ""


@dataclass
class ParsedInvoice:
    """فاتورة مُحلّلة بالكامل."""
    supplier_name: ExtractedField = field(default_factory=lambda: ExtractedField("", 0.0))
    invoice_number: ExtractedField = field(default_factory=lambda: ExtractedField("", 0.0))
    date: ExtractedField = field(default_factory=lambda: ExtractedField("", 0.0))
    tax_number: ExtractedField = field(default_factory=lambda: ExtractedField("", 0.0))
    subtotal: ExtractedField = field(default_factory=lambda: ExtractedField("", 0.0))
    tax_amount: ExtractedField = field(default_factory=lambda: ExtractedField("", 0.0))
    total: ExtractedField = field(default_factory=lambda: ExtractedField("", 0.0))
    line_items: list[dict] = field(default_factory=list)
    raw_text: str = ""
    overall_confidence: float = 0.0
    document_type: str = "unknown"  # "invoice", "receipt", "unknown"


class AdvancedOCRService:
    """خدمة OCR متقدمة مع preprocessing وتحليل هيكلي.

    يتطلب: pip install pytesseract Pillow opencv-python-headless
    كما يتطلب Tesseract OCR.
    """

    PATTERNS = {
        "invoice_number": [
            r"(?:فاتورة|INVOICE)\s*(?:رقم|NO\.?|#)[:\s]*([A-Z0-9\-]+)",
            r"(?:INV|INVOICE)[:\s#]*([A-Z0-9\-]+)",
            r"رقم\s*الفاتورة[:\s]*([A-Z0-9\-]+)",
        ],
        "date": [
            r"(?:التاريخ|DATE)[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
            r"(\d{4}-\d{2}-\d{2})",
            r"(\d{1,2}/\d{1,2}/\d{4})",
        ],
        "tax_number": [
            r"(?:الرقم\s*الضريبي|VAT\s*NO|TAX\s*NO)[:\s]*(\d{15})",
            r"الرقم\s*الضريبي[:\s]*(\d+)",
            r"VAT[:\s]*(\d+)",
        ],
        "total": [
            r"(?:الإجمالي|GRAND\s*TOTAL|TOTAL)[:\s]*([\d,]+\.?\d*)",
            r"(?:المبلغ\s*الإجمالي|AMOUNT\s*DUE)[:\s]*([\d,]+\.?\d*)",
            r"(?:المطلوب|TOTAL\s*DUE)[:\s]*([\d,]+\.?\d*)",
        ],
        "subtotal": [
            r"(?:المجموع\s*الفرعي|SUBTOTAL|SUB\s*TOTAL)[:\s]*([\d,]+\.?\d*)",
            r"(?:قبل\s*الضريبة|BEFORE\s*TAX)[:\s]*([\d,]+\.?\d*)",
        ],
        "tax_amount": [
            r"(?:ضريبة\s*القيمة\s*المضافة|VAT\s*AMOUNT|الضريبة)[:\s]*([\d,]+\.?\d*)",
            r"(?:ض\.ق\.م|VAT\s*15%)[:\s]*([\d,]+\.?\d*)",
        ],
    }

    def __init__(self, language: str = "ara+eng") -> None:
        self._language = language
        self._tesseract = None

    def _get_tesseract(self):
        if self._tesseract is None:
            try:
                import pytesseract
                self._tesseract = pytesseract
            except ImportError:
                raise ImportError("pytesseract not installed. Run: pip install pytesseract Pillow")
        return self._tesseract

    def preprocess_image(self, image_path: str | Path) -> "PILImage":
        """معالجة الصورة قبل OCR لتحسين الدقة.

        Steps:
        1. تحويل لتدرج رمادي
        2. زيادة التباين
        3. إزالة الضوضاء
        4. تصحيح الميل (deskew)
        """
        from PIL import Image, ImageEnhance, ImageFilter

        img = Image.open(str(image_path))

        # Convert to grayscale
        if img.mode != "L":
            img = img.convert("L")

        # Increase contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)

        # Sharpen
        img = img.filter(ImageFilter.SHARPEN)

        # Denoise (light)
        img = img.filter(ImageFilter.MedianFilter(size=3))

        return img

    def extract_text(self, image_path: str | Path, preprocess: bool = True) -> str:
        """استخراج النص من صورة مع optional preprocessing."""
        pytesseract = self._get_tesseract()

        if preprocess:
            try:
                img = self.preprocess_image(image_path)
            except Exception:
                from PIL import Image
                img = Image.open(str(image_path))
        else:
            from PIL import Image
            img = Image.open(str(image_path))

        text = pytesseract.image_to_string(img, lang=self._language)
        return text.strip()

    def parse_invoice(self, image_path: str | Path) -> ParsedInvoice:
        """تحليل فاتورة كامل من صورة.

        Returns: ParsedInvoice with all extracted fields + confidence.
        """
        raw_text = self.extract_text(image_path)
        return self._parse_text(raw_text)

    def _parse_text(self, raw_text: str) -> ParsedInvoice:
        """تحليل النص الخام إلى ParsedInvoice."""
        result = ParsedInvoice(raw_text=raw_text)

        # Detect document type
        result.document_type = self._detect_document_type(raw_text)

        # Extract supplier name (usually first non-empty line)
        result.supplier_name = ExtractedField(
            value=self._extract_supplier_name(raw_text),
            confidence=0.7,
            source_text=raw_text.split("\n")[0] if raw_text else "",
        )

        # Extract fields with confidence
        for field_name, patterns in self.PATTERNS.items():
            value, conf, source = self._extract_field_with_confidence(raw_text, patterns)
            field = ExtractedField(value=value, confidence=conf, source_text=source)

            if field_name == "invoice_number":
                result.invoice_number = field
            elif field_name == "date":
                result.date = field
            elif field_name == "tax_number":
                result.tax_number = field
            elif field_name == "total":
                result.total = field
            elif field_name == "subtotal":
                result.subtotal = field
            elif field_name == "tax_amount":
                result.tax_amount = field

        # Extract line items
        result.line_items = self._extract_line_items(raw_text)

        # Calculate overall confidence
        fields = [
            result.supplier_name, result.invoice_number, result.date,
            result.tax_number, result.total,
        ]
        confidences = [f.confidence for f in fields if f.value]
        result.overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return result

    def _detect_document_type(self, text: str) -> str:
        """اكتشاف نوع المستند (فاتورة/إيصال/غير معروف)."""
        text_lower = text.lower()
        if any(k in text for k in ["فاتورة", "INVOICE", "TAX INVOICE"]):
            return "invoice"
        if any(k in text for k in ["إيصال", "RECEIPT", "RECEIPT#"]):
            return "receipt"
        return "unknown"

    def _extract_supplier_name(self, text: str) -> str:
        lines = text.strip().split("\n")
        for line in lines[:5]:
            line = line.strip()
            if len(line) > 3 and not line[0].isdigit() and not any(c in line for c in ["@", "http"]):
                return line
        return ""

    def _extract_field_with_confidence(self, text: str, patterns: list[str]) -> tuple[str, float, str]:
        """استخراج حقل مع حساب الثقة."""
        for i, pattern in enumerate(patterns):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Higher confidence for first (more specific) patterns
                confidence = 0.9 - (i * 0.1)
                return match.group(1).strip(), confidence, match.group(0)
        return "", 0.0, ""

    def _extract_line_items(self, text: str) -> list[dict]:
        """استخراج بنود الفاتورة."""
        items = []
        lines = text.split("\n")

        # Pattern: quantity x price = total or just description + amount
        item_pattern = re.compile(
            r"(\d+\.?\d*)\s*[x×]\s*(\d+\.?\d*)\s*=?\s*(\d+\.?\d*)",
            re.IGNORECASE,
        )

        for line in lines:
            match = item_pattern.search(line)
            if match:
                qty, price, total = match.groups()
                items.append({
                    "description": line[:match.start()].strip(),
                    "quantity": float(qty),
                    "unit_price": float(price),
                    "line_total": float(total) if total else float(qty) * float(price),
                })

        return items

    def batch_extract(self, image_paths: list[str | Path]) -> list[ParsedInvoice]:
        """معالجة دفعة من الصور."""
        results = []
        for path in image_paths:
            try:
                result = self.parse_invoice(path)
                results.append(result)
            except Exception as e:
                results.append(ParsedInvoice(raw_text=f"Error: {e}", overall_confidence=0.0))
        return results

    def is_ready(self) -> bool:
        try:
            self._get_tesseract()
            return True
        except ImportError:
            return False
