"""
Cash Flow Prediction Service — خدمة التنبؤ بالتدفقات النقدية

يحلّل بيانات الفواتير التاريخية ويتنبأ بالتدفقات النقدية المستقبلية.

Methods:
- Simple moving average
- Linear regression
- Seasonal naive (last year same period)
- ARIMA-like (simplified)

No external ML libraries required — pure Python implementation.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional


@dataclass
class CashFlowPrediction:
    """نتيجة التنبؤ بالتدفق النقدي."""
    predicted_inflow: float
    predicted_outflow: float
    predicted_net: float
    current_balance: float
    projected_balance: float
    confidence: float  # 0.0 - 1.0
    method: str
    daily_predictions: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class CashFlowPredictor:
    """التنبؤ بالتدفقات النقدية باستخدام methods إحصائية بسيطة.

    No sklearn/statsmodels required — pure Python.
    """

    def __init__(self, min_history_days: int = 30) -> None:
        self._min_history = min_history_days

    def predict(
        self,
        historical_inflows: list[float],
        historical_outflows: list[float],
        current_balance: float,
        forecast_days: int = 30,
        method: str = "moving_average",
    ) -> CashFlowPrediction:
        """التنبؤ بالتدفق النقدي.

        Args:
            historical_inflows: التدفقات الداخلة التاريخية (يومية).
            historical_outflows: التدفقات الخارجة التاريخية (يومية).
            current_balance: الرصيد الحالي.
            forecast_days: عدد أيام التنبؤ.
            method: "moving_average" أو "linear_regression" أو "seasonal_naive".

        Returns: CashFlowPrediction with daily predictions.
        """
        if len(historical_inflows) < self._min_history:
            return self._insufficient_data_prediction(current_balance, forecast_days)

        if method == "moving_average":
            return self._moving_average(
                historical_inflows, historical_outflows,
                current_balance, forecast_days,
            )
        elif method == "linear_regression":
            return self._linear_regression(
                historical_inflows, historical_outflows,
                current_balance, forecast_days,
            )
        elif method == "seasonal_naive":
            return self._seasonal_naive(
                historical_inflows, historical_outflows,
                current_balance, forecast_days,
            )
        else:
            return self._moving_average(
                historical_inflows, historical_outflows,
                current_balance, forecast_days,
            )

    def _moving_average(
        self,
        inflows: list[float],
        outflows: list[float],
        balance: float,
        days: int,
    ) -> CashFlowPrediction:
        """تنبؤ بالمعدل المتحرك (آخر 7 أيام)."""
        window = min(7, len(inflows))
        avg_inflow = sum(inflows[-window:]) / window
        avg_outflow = sum(outflows[-window:]) / window

        daily_predictions = []
        projected = balance
        for i in range(days):
            projected += avg_inflow - avg_outflow
            daily_predictions.append({
                "day": i + 1,
                "date": (datetime.now() + timedelta(days=i + 1)).strftime("%Y-%m-%d"),
                "predicted_inflow": round(avg_inflow, 2),
                "predicted_outflow": round(avg_outflow, 2),
                "projected_balance": round(projected, 2),
            })

        predicted_inflow = avg_inflow * days
        predicted_outflow = avg_outflow * days
        warnings = []
        if projected < 0:
            warnings.append(f"⚠️ نقص نقدي متوقع في اليوم {self._find_shortfall_day(daily_predictions)}")
        if projected < balance * 0.2:
            warnings.append("⚠️ الرصيد المتوقع أقل من 20% من الحالي")

        confidence = min(0.8, len(inflows) / 90)  # More data = higher confidence

        return CashFlowPrediction(
            predicted_inflow=round(predicted_inflow, 2),
            predicted_outflow=round(predicted_outflow, 2),
            predicted_net=round(predicted_inflow - predicted_outflow, 2),
            current_balance=balance,
            projected_balance=round(projected, 2),
            confidence=round(confidence, 2),
            method="moving_average",
            daily_predictions=daily_predictions,
            warnings=warnings,
        )

    def _linear_regression(
        self,
        inflows: list[float],
        outflows: list[float],
        balance: float,
        days: int,
    ) -> CashFlowPrediction:
        """تنبؤ بالانحدار الخطي."""
        n = len(inflows)
        x = list(range(n))

        # Calculate linear regression for inflows
        inflow_slope, inflow_intercept = self._linear_fit(x, inflows)
        outflow_slope, outflow_intercept = self._linear_fit(x, outflows)

        daily_predictions = []
        projected = balance
        for i in range(days):
            future_x = n + i
            predicted_in = inflow_slope * future_x + inflow_intercept
            predicted_out = outflow_slope * future_x + outflow_intercept
            projected += predicted_in - predicted_out
            daily_predictions.append({
                "day": i + 1,
                "date": (datetime.now() + timedelta(days=i + 1)).strftime("%Y-%m-%d"),
                "predicted_inflow": round(max(0, predicted_in), 2),
                "predicted_outflow": round(max(0, predicted_out), 2),
                "projected_balance": round(projected, 2),
            })

        total_in = sum(d["predicted_inflow"] for d in daily_predictions)
        total_out = sum(d["predicted_outflow"] for d in daily_predictions)

        warnings = []
        if projected < 0:
            warnings.append("⚠️ نقص نقدي متوقع بناءً على الاتجاه الحالي")

        confidence = min(0.75, len(inflows) / 120)

        return CashFlowPrediction(
            predicted_inflow=round(total_in, 2),
            predicted_outflow=round(total_out, 2),
            predicted_net=round(total_in - total_out, 2),
            current_balance=balance,
            projected_balance=round(projected, 2),
            confidence=round(confidence, 2),
            method="linear_regression",
            daily_predictions=daily_predictions,
            warnings=warnings,
        )

    def _seasonal_naive(
        self,
        inflows: list[float],
        outflows: list[float],
        balance: float,
        days: int,
    ) -> CashFlowPrediction:
        """تنبؤ موسمي بسيط (آخر 7 أيام تتكرر)."""
        window = min(7, len(inflows))
        daily_predictions = []
        projected = balance

        for i in range(days):
            idx = (n - window + i) % window if (n := len(inflows)) >= window else 0
            predicted_in = inflows[-window + idx] if len(inflows) >= window else 0
            predicted_out = outflows[-window + idx] if len(outflows) >= window else 0
            projected += predicted_in - predicted_out
            daily_predictions.append({
                "day": i + 1,
                "date": (datetime.now() + timedelta(days=i + 1)).strftime("%Y-%m-%d"),
                "predicted_inflow": round(predicted_in, 2),
                "predicted_outflow": round(predicted_out, 2),
                "projected_balance": round(projected, 2),
            })

        total_in = sum(d["predicted_inflow"] for d in daily_predictions)
        total_out = sum(d["predicted_outflow"] for d in daily_predictions)

        return CashFlowPrediction(
            predicted_inflow=round(total_in, 2),
            predicted_outflow=round(total_out, 2),
            predicted_net=round(total_in - total_out, 2),
            current_balance=balance,
            projected_balance=round(projected, 2),
            confidence=0.6,
            method="seasonal_naive",
            daily_predictions=daily_predictions,
            warnings=[],
        )

    def _linear_fit(self, x: list[float], y: list[float]) -> tuple[float, float]:
        """حساب خط الانحدار (slope, intercept)."""
        n = len(x)
        if n == 0:
            return 0.0, 0.0
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi ** 2 for xi in x)

        denominator = n * sum_x2 - sum_x ** 2
        if denominator == 0:
            return 0.0, sum_y / n if n > 0 else 0.0

        slope = (n * sum_xy - sum_x * sum_y) / denominator
        intercept = (sum_y - slope * sum_x) / n
        return slope, intercept

    def _find_shortfall_day(self, predictions: list[dict]) -> int:
        """إيجاد أول يوم يتوقع فيه نقص نقدي."""
        for p in predictions:
            if p["projected_balance"] < 0:
                return p["day"]
        return -1

    def _insufficient_data_prediction(
        self, balance: float, days: int,
    ) -> CashFlowPrediction:
        """تنبؤ عند عدم كفاية البيانات."""
        return CashFlowPrediction(
            predicted_inflow=0.0,
            predicted_outflow=0.0,
            predicted_net=0.0,
            current_balance=balance,
            projected_balance=balance,
            confidence=0.0,
            method="insufficient_data",
            warnings=["⚠️ بيانات تاريخية غير كافية للتنبؤ (الحد الأدنى 30 يومًا)"],
        )
