"""
Email Service — خدمة إرسال البريد الإلكتروني

Features:
- إرسال الفواتير كـ PDF مرفق
- إرسال التقارير
- إرسال تنبيهات النظام
- قوالب بريد جاهزة (HTML)
- دعم SMTP

Usage:
    from infrastructure.services.email_service import EmailService

    email = EmailService(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        username="your@email.com",
        password="your-app-password",
    )
    email.send_invoice(to="customer@example.com", invoice_pdf="/path/to/invoice.pdf", invoice_no="INV-001")
"""
from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Optional


@dataclass
class EmailConfig:
    """إعدادات البريد الإلكتروني."""
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    username: str = ""
    password: str = ""
    from_name: str = "نظام ERP المحاسبي"
    from_email: str = ""
    use_tls: bool = True


class EmailService:
    """خدمة إرسال البريد الإلكتروني.

    يتطلب: لا شيء (يستخدم smtplib المدمج في Python)
    """

    def __init__(self, config: EmailConfig = None) -> None:
        self._config = config or EmailConfig()

    def send(
        self,
        to: str,
        subject: str,
        body: str,
        html: bool = False,
        attachments: list[str] = None,
        cc: list[str] = None,
    ) -> bool:
        """إرسال بريد إلكتروني.

        Args:
            to: البريد المستلم.
            subject: الموضوع.
            body: المحتوى (نص أو HTML).
            html: هل المحتوى HTML؟
            attachments: قائمة مسارات الملفات المرفقة.
            cc: قائمة بريد النسخة الكربونية.

        Returns: True إذا نجح.
        """
        if not self._config.username or not self._config.password:
            return False

        try:
            msg = MIMEMultipart()
            msg["From"] = f"{self._config.from_name} <{self._config.from_email or self._config.username}>"
            msg["To"] = to
            msg["Subject"] = subject
            if cc:
                msg["Cc"] = ", ".join(cc)

            # Body
            content_type = "html" if html else "plain"
            msg.attach(MIMEText(body, content_type, "utf-8"))

            # Attachments
            if attachments:
                for filepath in attachments:
                    self._attach_file(msg, filepath)

            # Send
            with smtplib.SMTP(self._config.smtp_host, self._config.smtp_port) as server:
                if self._config.use_tls:
                    server.starttls()
                server.login(self._config.username, self._config.password)
                recipients = [to] + (cc or [])
                server.sendmail(self._config.username, recipients, msg.as_string())

            return True

        except Exception:
            return False

    def send_invoice(
        self,
        to: str,
        invoice_pdf: str | Path,
        invoice_no: str,
        customer_name: str = "",
        amount: str = "",
    ) -> bool:
        """إرسال فاتورة بالبريد.

        Args:
            to: بريد العميل.
            invoice_pdf: مسار ملف PDF الفاتورة.
            invoice_no: رقم الفاتورة.
            customer_name: اسم العميل.
            amount: المبلغ.

        Returns: True إذا نجح.
        """
        subject = f"فاتورة رقم {invoice_no}"
        body = self._invoice_email_template(invoice_no, customer_name, amount)

        return self.send(
            to=to,
            subject=subject,
            body=body,
            html=True,
            attachments=[str(invoice_pdf)],
        )

    def send_report(
        self,
        to: str,
        report_pdf: str | Path,
        report_name: str,
    ) -> bool:
        """إرسال تقرير بالبريد."""
        subject = f"تقرير: {report_name}"
        body = f"""
        <html>
        <body dir="rtl">
        <h2>تقرير: {report_name}</h2>
        <p>تجدون مرفقًا تقرير "{report_name}".</p>
        <p>للاستفسار، يرجى التواصل معنا.</p>
        <hr>
        <p style="color: #888; font-size: 12px;">
            تم إرسال هذا البريد تلقائيًا من نظام ERP المحاسبي
        </p>
        </body>
        </html>
        """
        return self.send(
            to=to,
            subject=subject,
            body=body,
            html=True,
            attachments=[str(report_pdf)],
        )

    def send_alert(
        self,
        to: str,
        alert_type: str,
        message: str,
    ) -> bool:
        """إرسال تنبيه بالبريد."""
        subject = f"⚠️ تنبيه: {alert_type}"
        body = f"""
        <html>
        <body dir="rtl">
        <h2 style="color: #EF4444;">⚠️ تنبيه: {alert_type}</h2>
        <p>{message}</p>
        <p>يرجى مراجعة النظام في أقرب وقت.</p>
        </body>
        </html>
        """
        return self.send(to=to, subject=subject, body=body, html=True)

    def _attach_file(self, msg: MIMEMultipart, filepath: str) -> None:
        """إرفاق ملف بالبريد."""
        path = Path(filepath)
        if not path.exists():
            return

        with open(path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())

        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f'attachment; filename="{path.name}"',
        )
        msg.attach(part)

    def _invoice_email_template(
        self,
        invoice_no: str,
        customer_name: str,
        amount: str,
    ) -> str:
        """قالب بريد الفاتورة (HTML)."""
        return f"""
        <html>
        <body dir="rtl" style="font-family: 'Noto Sans Arabic', sans-serif; background-color: #F0F4F8; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 20px; padding: 30px;">
                <h2 style="color: #2D3748;">فاتورة جديدة</h2>
                <p>مرحبًا{f' {customer_name}' if customer_name else ''},</p>
                <p>تجدون مرفقًا فاتورتكم رقم <strong>{invoice_no}</strong>{f' بقيمة <strong>{amount}</strong>' if amount else ''}.</p>
                <p>يرجى السداد خلال المدة المتفق عليها.</p>
                <hr style="border: none; border-top: 1px solid #E4EBF5; margin: 20px 0;">
                <p style="color: #718096; font-size: 12px;">
                    تم إرسال هذه الفاتورة تلقائيًا من نظام ERP المحاسبي.<br>
                    لأي استفسار، يرجى التواصل معنا.
                </p>
            </div>
        </body>
        </html>
        """

    def is_ready(self) -> bool:
        """هل إعدادات البريد مكتملة؟"""
        return bool(self._config.username and self._config.password)

    def test_connection(self) -> bool:
        """اختبار الاتصال بـ SMTP."""
        try:
            with smtplib.SMTP(self._config.smtp_host, self._config.smtp_port) as server:
                if self._config.use_tls:
                    server.starttls()
                server.login(self._config.username, self._config.password)
            return True
        except Exception:
            return False
