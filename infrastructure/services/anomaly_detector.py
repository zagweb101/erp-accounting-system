"""
Anomaly Detection Service - خدمة كشف الحالات الشاذة

تراقب العمليات المالية وتكتشف الأنماط غير المعتادة:
- فواتير بحجم غير عادي
- تعديلات بعد الإقفال
- دخول في أوقات غير معتادة
- تجاوز حدود الائتمان
- تكرار عمليات مشبوهة

No ML libraries - pure statistical heuristics.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID


@dataclass
class Anomaly:
    """حالة شاذة مكتشفة."""
    type: str  # "large_invoice", "after_hours", "credit_limit", "rapid_edit", "duplicate"
    severity: str  # "low", "medium", "high", "critical"
    description: str
    entity_type: str = ""  # "invoice", "user", "journal"
    entity_id: str = ""
    detected_at: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)


class AnomalyDetector:
    """كاشف الحالات الشاذة.

    Uses statistical heuristics:
    - Z-score for amount outliers
    - Time-based rules for after-hours access
    - Rate limiting for rapid operations
    - Duplicate detection
    """

    # Thresholds
    Z_SCORE_THRESHOLD = 2.5  # Anything > 2.5 std deviations is anomalous
    AFTER_HOURS_START = 22   # 10 PM
    AFTER_HOURS_END = 6      # 6 AM
    RAPID_EDIT_WINDOW = 60   # seconds
    MAX_RAPID_EDITS = 5

    def __init__(self) -> None:
        self._invoice_amounts: list[float] = []
        self._user_activity: dict[str, list[datetime]] = {}
        self._recent_operations: list[dict] = []

    def check_invoice_amount(
        self,
        amount: float,
        customer_id: str = "",
        invoice_id: str = "",
    ) -> Optional[Anomaly]:
        """فحص إذا كان مبلغ الفاتورة شاذًا.

        Uses Z-score: if amount > mean + 2.5*std, it's anomalous.
        """
        self._invoice_amounts.append(amount)

        # Need at least 10 invoices for meaningful stats
        if len(self._invoice_amounts) < 10:
            return None

        mean = sum(self._invoice_amounts) / len(self._invoice_amounts)
        variance = sum((x - mean) ** 2 for x in self._invoice_amounts) / len(self._invoice_amounts)
        std = variance ** 0.5

        if std == 0:
            return None

        z_score = (amount - mean) / std

        if z_score > self.Z_SCORE_THRESHOLD:
            severity = "critical" if z_score > 4 else "high" if z_score > 3 else "medium"
            return Anomaly(
                type="large_invoice",
                severity=severity,
                description=(
                    f"فاتورة بمبلغ غير معتاد: {amount:,.2f} ر.س "
                    f"(المعدل: {mean:,.2f}، Z-score: {z_score:.2f})"
                ),
                entity_type="invoice",
                entity_id=invoice_id,
                metadata={
                    "amount": amount,
                    "mean": mean,
                    "std": std,
                    "z_score": z_score,
                    "customer_id": customer_id,
                },
            )
        return None

    def check_after_hours_access(
        self,
        username: str,
        timestamp: Optional[datetime] = None,
    ) -> Optional[Anomaly]:
        """فحص الدخول في أوقات غير العمل."""
        ts = timestamp or datetime.now()
        hour = ts.hour

        if hour >= self.AFTER_HOURS_START or hour < self.AFTER_HOURS_END:
            return Anomaly(
                type="after_hours",
                severity="medium",
                description=(
                    f"دخول في وقت غير عادي: {ts.strftime('%H:%M')} "
                    f"بواسطة {username}"
                ),
                entity_type="user",
                metadata={"username": username, "hour": hour, "timestamp": ts.isoformat()},
            )
        return None

    def check_rapid_edits(
        self,
        user_id: str,
        operation: str,
        entity_id: str = "",
    ) -> Optional[Anomaly]:
        """فحص التعديلات السريعة المتتالية."""
        now = datetime.now()
        key = f"{user_id}:{operation}"

        if key not in self._user_activity:
            self._user_activity[key] = []

        # Remove old entries
        self._user_activity[key] = [
            t for t in self._user_activity[key]
            if (now - t).total_seconds() < self.RAPID_EDIT_WINDOW
        ]

        self._user_activity[key].append(now)

        if len(self._user_activity[key]) > self.MAX_RAPID_EDITS:
            return Anomaly(
                type="rapid_edit",
                severity="high",
                description=(
                    f"تعديلات سريعة متتالية: {len(self._user_activity[key])} "
                    f"عملية '{operation}' في أقل من دقيقة بواسطة {user_id}"
                ),
                entity_type="user",
                entity_id=user_id,
                metadata={
                    "operation": operation,
                    "count": len(self._user_activity[key]),
                    "window_seconds": self.RAPID_EDIT_WINDOW,
                },
            )
        return None

    def check_credit_limit_breach(
        self,
        customer_name: str,
        credit_limit: float,
        current_balance: float,
        invoice_amount: float,
    ) -> Optional[Anomaly]:
        """فحص تجاوز حد الائتمان."""
        total = current_balance + invoice_amount
        if credit_limit > 0 and total > credit_limit:
            severity = "critical" if total > credit_limit * 1.5 else "high"
            return Anomaly(
                type="credit_limit",
                severity=severity,
                description=(
                    f"تجاوز حد الائتمان للعميل {customer_name}: "
                    f"الحد {credit_limit:,.2f}، المتوقع {total:,.2f}"
                ),
                entity_type="customer",
                metadata={
                    "customer_name": customer_name,
                    "credit_limit": credit_limit,
                    "current_balance": current_balance,
                    "invoice_amount": invoice_amount,
                    "projected_total": total,
                },
            )
        return None

    def check_duplicate_invoice(
        self,
        amount: float,
        customer_id: str,
        timestamp: Optional[datetime] = None,
    ) -> Optional[Anomaly]:
        """فحص الفواتير المكررة (نفس المبلغ + نفس العميل في وقت قريب)."""
        ts = timestamp or datetime.now()
        key = f"{customer_id}:{amount:.2f}"

        for op in self._recent_operations:
            if op["key"] == key:
                time_diff = (ts - op["timestamp"]).total_seconds()
                if time_diff < 300:  # 5 minutes
                    return Anomaly(
                        type="duplicate",
                        severity="high",
                        description=(
                            f"فاتورة مكررة محتملة: نفس المبلغ ({amount:,.2f}) "
                            f"ونفس العميل خلال {time_diff:.0f} ثانية"
                        ),
                        entity_type="invoice",
                        metadata={
                            "amount": amount,
                            "customer_id": customer_id,
                            "time_diff_seconds": time_diff,
                        },
                    )

        self._recent_operations.append({"key": key, "timestamp": ts})
        # Clean old entries
        self._recent_operations = [
            op for op in self._recent_operations
            if (ts - op["timestamp"]).total_seconds() < 3600  # 1 hour
        ]

        return None

    def get_statistics(self) -> dict:
        """إحصائيات الـ anomaly detector."""
        return {
            "tracked_invoices": len(self._invoice_amounts),
            "tracked_activities": sum(len(v) for v in self._user_activity.values()),
            "recent_operations": len(self._recent_operations),
        }
