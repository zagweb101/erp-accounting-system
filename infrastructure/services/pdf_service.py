"""
PDF Service - خدمة توليد ملفات PDF للفواتير والتقارير

تستخدم ReportLab + تدعم العربية عبر arabic-reshaper + python-bidi.
"""
from __future__ import annotations

import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional
from uuid import UUID

# Try imports — degrade gracefully if libs missing
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm, mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, Image,
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_AVAILABLE = True
except ImportError:
    ARABIC_AVAILABLE = False


# Register Arabic font (if available)
ARABIC_FONT_REGISTERED = False
ARABIC_FONT_NAME = "Helvetica"  # fallback

if REPORTLAB_AVAILABLE:
    font_paths = [
        "/home/z/my-project/assets/fonts/NotoNaskhArabic-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                pdfmetrics.registerFont(TTFont("ArabicFont", fp))
                ARABIC_FONT_NAME = "ArabicFont"
                ARABIC_FONT_REGISTERED = True
                break
            except Exception:
                continue


def _ar(text: str) -> str:
    """Reshape Arabic text for proper RTL rendering."""
    if not text:
        return ""
    if ARABIC_AVAILABLE:
        try:
            reshaped = arabic_reshaper.reshape(str(text))
            return get_display(reshaped)
        except Exception:
            return str(text)
    return str(text)


def _fmt_amount(amount: Decimal | float) -> str:
    """Format decimal amount: 1234.56 → '1,234.56'"""
    try:
        return f"{Decimal(str(amount)):,.2f}"
    except Exception:
        return str(amount)


class PDFService:
    """خدمة توليد PDF."""

    def __init__(self, output_dir: str = "./exports") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_styles(self) -> dict:
        """أنماط النص."""
        styles = getSampleStyleSheet() if REPORTLAB_AVAILABLE else None

        title_style = ParagraphStyle(
            "ArabicTitle",
            parent=styles["Title"] if styles else None,
            fontName=ARABIC_FONT_NAME,
            fontSize=20,
            leading=24,
            alignment=TA_CENTER,
            spaceAfter=12,
        )

        heading_style = ParagraphStyle(
            "ArabicHeading",
            parent=styles["Heading2"] if styles else None,
            fontName=ARABIC_FONT_NAME,
            fontSize=14,
            leading=18,
            alignment=TA_RIGHT,
            spaceAfter=8,
        )

        body_style = ParagraphStyle(
            "ArabicBody",
            parent=styles["Normal"] if styles else None,
            fontName=ARABIC_FONT_NAME,
            fontSize=11,
            leading=15,
            alignment=TA_RIGHT,
        )

        return {
            "title": title_style,
            "heading": heading_style,
            "body": body_style,
        }

    def export_invoice_pdf(
        self,
        invoice_data: dict,
        company_data: Optional[dict] = None,
        filename: Optional[str] = None,
    ) -> str:
        """تصدير فاتورة كـ PDF. يُعيد المسار الكامل للملف."""
        if not REPORTLAB_AVAILABLE:
            raise RuntimeError("reportlab not installed. Run: pip install reportlab")

        if filename is None:
            filename = f"invoice_{invoice_data.get('invoice_no', 'unknown')}.pdf"
        filepath = self.output_dir / filename

        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        styles = self._get_styles()
        elements = []

        # Company header (right-aligned for RTL)
        if company_data:
            company_name = company_data.get("name", "")
            elements.append(Paragraph(_ar(company_name), styles["title"]))
            for line in [
                company_data.get("address", ""),
                f"هاتف: {company_data.get('phone', '')}",
                f"الرقم الضريبي: {company_data.get('tax_number', '')}",
            ]:
                if line:
                    elements.append(Paragraph(_ar(line), styles["body"]))
            elements.append(Spacer(1, 12))

        # Invoice title
        inv_type = invoice_data.get("invoice_type", "SALE")
        title = "فاتورة بيع" if inv_type == "SALE" else "فاتورة شراء"
        elements.append(Paragraph(_ar(title), styles["heading"]))
        elements.append(Spacer(1, 8))

        # Invoice info table
        info_data = [
            [_ar("رقم الفاتورة"), _ar(invoice_data.get("invoice_no", ""))],
            [_ar("التاريخ"), invoice_data.get("issue_date", "")[:10] if invoice_data.get("issue_date") else ""],
            [_ar("العميل/المورد"), _ar(invoice_data.get("party_name", ""))],
            [_ar("الحالة"), _ar(invoice_data.get("status", ""))],
        ]
        info_table = Table(info_data, colWidths=[4 * cm, 12 * cm])
        info_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), ARABIC_FONT_NAME),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (0, 0), (0, -1), "RIGHT"),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5F9")),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 16))

        # Items table
        items_header = [
            _ar("المنتج"),
            _ar("الكمية"),
            _ar("السعر"),
            _ar("الضريبة%"),
            _ar("الخصم"),
            _ar("الإجمالي"),
        ]
        items_rows = [items_header]
        for item in invoice_data.get("items", []):
            items_rows.append([
                _ar(item.get("product_name", "")),
                str(item.get("quantity", "")),
                _fmt_amount(item.get("unit_price", 0)),
                f"{item.get('tax_rate', 15)}%",
                _fmt_amount(item.get("discount", 0)),
                _fmt_amount(item.get("line_total", 0)),
            ])

        items_table = Table(items_rows, colWidths=[5 * cm, 2 * cm, 2.5 * cm, 2 * cm, 2 * cm, 2.5 * cm])
        items_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), ARABIC_FONT_NAME),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), ARABIC_FONT_NAME),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 16))

        # Totals table
        totals_data = [
            [_ar("الإجمالي الفرعي"), _fmt_amount(invoice_data.get("subtotal", 0))],
            [_ar("ضريبة القيمة المضافة"), _fmt_amount(invoice_data.get("tax_amount", 0))],
            [_ar("الخصم"), _fmt_amount(invoice_data.get("discount", 0))],
            [_ar("الإجمالي النهائي"), _fmt_amount(invoice_data.get("total", 0))],
        ]
        totals_table = Table(totals_data, colWidths=[8 * cm, 4 * cm])
        totals_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), ARABIC_FONT_NAME),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("ALIGN", (0, 0), (0, -1), "RIGHT"),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#DBEAFE")),
            ("FONTNAME", (0, -1), (-1, -1), ARABIC_FONT_NAME),
            ("FONTSIZE", (0, -1), (-1, -1), 12),
        ]))
        elements.append(totals_table)
        elements.append(Spacer(1, 24))

        # Notes
        if invoice_data.get("notes"):
            elements.append(Paragraph(_ar("ملاحظات:"), styles["heading"]))
            elements.append(Paragraph(_ar(invoice_data["notes"]), styles["body"]))

        # Build
        doc.build(elements)
        return str(filepath)

    def export_trial_balance_pdf(
        self,
        report_data: dict,
        filename: Optional[str] = None,
    ) -> str:
        """تصدير ميزان المراجعة."""
        if not REPORTLAB_AVAILABLE:
            raise RuntimeError("reportlab not installed")
        if filename is None:
            filename = f"trial_balance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = self.output_dir / filename

        doc = SimpleDocTemplate(
            str(filepath), pagesize=A4,
            rightMargin=2 * cm, leftMargin=2 * cm,
            topMargin=2 * cm, bottomMargin=2 * cm,
        )
        styles = self._get_styles()
        elements = []

        elements.append(Paragraph(_ar("ميزان المراجعة"), styles["title"]))
        elements.append(Paragraph(
            _ar(f"كما في: {report_data.get('as_of_date', '')[:10] if report_data.get('as_of_date') else ''}"),
            styles["body"],
        ))
        elements.append(Spacer(1, 16))

        # Table
        header = [_ar("الكود"), _ar("اسم الحساب"), _ar("النوع"), _ar("مدين"), _ar("دائن")]
        rows = [header]
        for line in report_data.get("lines", []):
            rows.append([
                line.get("account_code", ""),
                _ar(line.get("account_name", "")),
                _ar(line.get("account_type", "")),
                _fmt_amount(line.get("debit", 0)),
                _fmt_amount(line.get("credit", 0)),
            ])
        # Totals row
        rows.append([
            "", _ar("الإجمالي"), "",
            _fmt_amount(report_data.get("total_debit", 0)),
            _fmt_amount(report_data.get("total_credit", 0)),
        ])

        table = Table(rows, colWidths=[2.5 * cm, 6 * cm, 3 * cm, 2.5 * cm, 2.5 * cm])
        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), ARABIC_FONT_NAME),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#DBEAFE")),
            ("FONTNAME", (0, -1), (-1, -1), ARABIC_FONT_NAME),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F8FAFC")]),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 12))

        # Status
        is_balanced = report_data.get("is_balanced", False)
        status_text = "✓ متوازن" if is_balanced else "✗ غير متوازن"
        status_color = "#10B981" if is_balanced else "#EF4444"
        status_style = ParagraphStyle(
            "Status", parent=styles["body"],
            fontSize=14, textColor=colors.HexColor(status_color),
            alignment=TA_CENTER,
        )
        elements.append(Paragraph(_ar(status_text), status_style))

        doc.build(elements)
        return str(filepath)

    def export_balance_sheet_pdf(self, report_data: dict, filename: Optional[str] = None) -> str:
        """تصدير قائمة المركز المالي (الميزانية العمومية)."""
        if not REPORTLAB_AVAILABLE:
            raise RuntimeError("reportlab not installed")
        if filename is None:
            filename = f"balance_sheet_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = self.output_dir / filename

        doc = SimpleDocTemplate(
            str(filepath), pagesize=A4,
            rightMargin=2 * cm, leftMargin=2 * cm,
            topMargin=2 * cm, bottomMargin=2 * cm,
        )
        styles = self._get_styles()
        elements = []

        elements.append(Paragraph(_ar("قائمة المركز المالي"), styles["title"]))
        elements.append(Paragraph(
            _ar(f"كما في: {report_data.get('as_of_date', '')[:10] if report_data.get('as_of_date') else ''}"),
            styles["body"],
        ))
        elements.append(Spacer(1, 16))

        # Assets section
        elements.append(Paragraph(_ar("الأصول"), styles["heading"]))
        assets_rows = [[_ar("الكود"), _ar("اسم الحساب"), _ar("المبلغ")]]
        for line in report_data.get("assets", []):
            assets_rows.append([
                line.get("account_code", ""),
                _ar(line.get("account_name", "")),
                _fmt_amount(line.get("amount", 0)),
            ])
        assets_rows.append(["", _ar("إجمالي الأصول"), _fmt_amount(report_data.get("total_assets", 0))])

        table = Table(assets_rows, colWidths=[2.5 * cm, 9 * cm, 4 * cm])
        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), ARABIC_FONT_NAME),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#DBEAFE")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 16))

        # Liabilities section
        elements.append(Paragraph(_ar("الخصوم"), styles["heading"]))
        liab_rows = [[_ar("الكود"), _ar("اسم الحساب"), _ar("المبلغ")]]
        for line in report_data.get("liabilities", []):
            liab_rows.append([
                line.get("account_code", ""),
                _ar(line.get("account_name", "")),
                _fmt_amount(line.get("amount", 0)),
            ])
        liab_rows.append(["", _ar("إجمالي الخصوم"), _fmt_amount(report_data.get("total_liabilities", 0))])

        table2 = Table(liab_rows, colWidths=[2.5 * cm, 9 * cm, 4 * cm])
        table2.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), ARABIC_FONT_NAME),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EF4444")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#FEE2E2")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ]))
        elements.append(table2)
        elements.append(Spacer(1, 16))

        # Equity section
        elements.append(Paragraph(_ar("حقوق الملكية"), styles["heading"]))
        eq_rows = [[_ar("الكود"), _ar("اسم الحساب"), _ar("المبلغ")]]
        for line in report_data.get("equity", []):
            eq_rows.append([
                line.get("account_code", ""),
                _ar(line.get("account_name", "")),
                _fmt_amount(line.get("amount", 0)),
            ])
        eq_rows.append(["", _ar("إجمالي حقوق الملكية"), _fmt_amount(report_data.get("total_equity", 0))])

        table3 = Table(eq_rows, colWidths=[2.5 * cm, 9 * cm, 4 * cm])
        table3.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), ARABIC_FONT_NAME),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#10B981")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#D1FAE5")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ]))
        elements.append(table3)
        elements.append(Spacer(1, 24))

        # Verification
        is_balanced = report_data.get("is_balanced", False)
        status_text = "✓ متوازن: الأصول = الخصوم + حقوق الملكية" if is_balanced else "✗ غير متوازن"
        status_color = "#10B981" if is_balanced else "#EF4444"
        status_style = ParagraphStyle(
            "Status", parent=styles["body"],
            fontSize=12, textColor=colors.HexColor(status_color),
            alignment=TA_CENTER,
        )
        elements.append(Paragraph(_ar(status_text), status_style))

        doc.build(elements)
        return str(filepath)
