"""
Charts Widget - رسوم بيانية ناعمة باستخدام QPainter

يوفّر:
- BarChart: رسم بياني أعمدة
- LineChart: رسم بياني خطي
- DonutChart: رسم دائري مجوّف
- PieChart: رسم دائري

كلها بـ Soft UI styling (ألوان ماضيلية، زوايا ناعمة).
"""
from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QLinearGradient,
    QPainterPath, QPaintEvent, QFontMetrics,
)
from PySide6.QtWidgets import QWidget, QSizePolicy

from infrastructure.ui.theme.soft_ui import SoftColors


class BarChart(QWidget):
    """رسم بياني أعمدة بـ Soft UI.

    Features:
    - أعمدة بزوايا دائرية
    - ألوان ماضيلية
    - تسميات أسفل كل عمود
    - قيم فوق كل عمود
    """

    def __init__(
        self,
        labels: list[str] = None,
        values: list[float] = None,
        colors: list[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._labels = labels or []
        self._values = values or []
        self._colors = colors or [
            SoftColors.ACCENT_BLUE,
            SoftColors.ACCENT_GREEN,
            SoftColors.ACCENT_ORANGE,
            SoftColors.ACCENT_PURPLE,
            SoftColors.ACCENT_RED,
            SoftColors.ACCENT_TEAL,
        ]
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_data(self, labels: list[str], values: list[float]) -> None:
        """تحديث البيانات."""
        self._labels = labels
        self._values = values
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """رسم الرسم البياني."""
        if not self._values:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        margin = 30
        chart_rect = QRectF(
            rect.x() + margin, rect.y() + margin,
            rect.width() - 2 * margin, rect.height() - 2 * margin - 20,
        )

        # Find max value for scaling
        max_val = max(self._values) if self._values else 1
        if max_val == 0:
            max_val = 1

        # Draw bars
        n = len(self._values)
        if n == 0:
            return

        bar_width = min(60, (chart_rect.width() - 20) / n - 10)
        total_width = n * (bar_width + 10) - 10
        start_x = chart_rect.x() + (chart_rect.width() - total_width) / 2

        for i, (label, value) in enumerate(zip(self._labels, self._values)):
            x = start_x + i * (bar_width + 10)
            bar_height = (value / max_val) * chart_rect.height() * 0.85
            y = chart_rect.bottom() - bar_height

            # Bar with gradient
            color = QColor(self._colors[i % len(self._colors)])
            gradient = QLinearGradient(x, y, x, chart_rect.bottom())
            gradient.setColorAt(0, color)
            light_color = QColor(color)
            light_color.setAlpha(150)
            gradient.setColorAt(1, light_color)

            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.PenStyle.NoPen)

            # Rounded top bar
            path = QPainterPath()
            path.addRoundedRect(QRectF(x, y, bar_width, bar_height), 6, 6)
            painter.drawPath(path)

            # Value label above bar
            painter.setPen(QColor(SoftColors.TEXT_PRIMARY))
            font = QFont("Noto Sans Arabic", 9, QFont.Weight.Bold)
            painter.setFont(font)
            value_text = f"{value:,.0f}"
            painter.drawText(
                QRectF(x - 10, y - 20, bar_width + 20, 18),
                Qt.AlignmentFlag.AlignCenter, value_text,
            )

            # Category label below bar
            painter.setPen(QColor(SoftColors.TEXT_SECONDARY))
            font = QFont("Noto Sans Arabic", 8)
            painter.setFont(font)
            painter.drawText(
                QRectF(x - 15, chart_rect.bottom() + 4, bar_width + 30, 16),
                Qt.AlignmentFlag.AlignCenter, label,
            )

        painter.end()


class DonutChart(QWidget):
    """رسم دائري مجوّف بـ Soft UI.

    Features:
    - حلقات ناعمة بألوان ماضيلية
    - فجوة في المنتصف (donut hole)
    - تسميات بنسب مئوية
    - نص في المنتصف (المجموع)
    """

    def __init__(
        self,
        labels: list[str] = None,
        values: list[float] = None,
        colors: list[str] = None,
        center_text: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._labels = labels or []
        self._values = values or []
        self._colors = colors or [
            SoftColors.ACCENT_BLUE,
            SoftColors.ACCENT_GREEN,
            SoftColors.ACCENT_ORANGE,
            SoftColors.ACCENT_PURPLE,
            SoftColors.ACCENT_RED,
        ]
        self._center_text = center_text
        self.setMinimumHeight(200)
        self.setMinimumWidth(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_data(self, labels: list[str], values: list[float], center_text: str = "") -> None:
        """تحديث البيانات."""
        self._labels = labels
        self._values = values
        self._center_text = center_text
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """رسم الرسم الدائري."""
        if not self._values:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        cx = rect.center().x()
        cy = rect.center().y()
        radius = min(rect.width(), rect.height()) / 2 - 20
        inner_radius = radius * 0.6

        total = sum(self._values)
        if total == 0:
            return

        # Draw arcs
        start_angle = 90 * 16  # Start from top
        for i, value in enumerate(self._values):
            angle = (value / total) * 360 * 16
            color = QColor(self._colors[i % len(self._colors)])

            # Outer arc
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)

            # Draw pie segment
            painter.drawPie(
                QRectF(cx - radius, cy - radius, radius * 2, radius * 2),
                int(start_angle), int(-angle),
            )
            start_angle -= angle

        # Draw inner circle (donut hole)
        painter.setBrush(QBrush(QColor(SoftColors.BG_PRIMARY)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), inner_radius, inner_radius)

        # Center text
        if self._center_text:
            painter.setPen(QColor(SoftColors.TEXT_PRIMARY))
            font = QFont("Noto Sans Arabic", 14, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(
                QRectF(cx - inner_radius, cy - inner_radius, inner_radius * 2, inner_radius * 2),
                Qt.AlignmentFlag.AlignCenter, self._center_text,
            )

        painter.end()


class LineChart(QWidget):
    """رسم بياني خطي بـ Soft UI.

    Features:
    - خط ناعم بألوان ماضيلية
    - مساحة مظللة تحت الخط
    - نقاط على كل قيمة
    """

    def __init__(
        self,
        labels: list[str] = None,
        values: list[float] = None,
        color: str = SoftColors.ACCENT_BLUE,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._labels = labels or []
        self._values = values or []
        self._color = color
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_data(self, labels: list[str], values: list[float]) -> None:
        """تحديث البيانات."""
        self._labels = labels
        self._values = values
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """رسم الرسم الخطي."""
        if len(self._values) < 2:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        margin = 30
        chart_rect = QRectF(
            rect.x() + margin, rect.y() + margin,
            rect.width() - 2 * margin, rect.height() - 2 * margin - 20,
        )

        max_val = max(self._values) if self._values else 1
        if max_val == 0:
            max_val = 1

        n = len(self._values)
        step_x = chart_rect.width() / (n - 1) if n > 1 else 0

        points = []
        for i, value in enumerate(self._values):
            x = chart_rect.x() + i * step_x
            y = chart_rect.bottom() - (value / max_val) * chart_rect.height() * 0.85
            points.append(QPointF(x, y))

        # Draw filled area under the line
        color = QColor(self._color)
        gradient = QLinearGradient(0, chart_rect.y(), 0, chart_rect.bottom())
        light = QColor(color)
        light.setAlpha(60)
        gradient.setColorAt(0, light)
        transparent = QColor(color)
        transparent.setAlpha(10)
        gradient.setColorAt(1, transparent)

        path = QPainterPath()
        path.moveTo(points[0])
        for p in points[1:]:
            path.lineTo(p)
        path.lineTo(QPointF(points[-1].x(), chart_rect.bottom()))
        path.lineTo(QPointF(points[0].x(), chart_rect.bottom()))
        path.closeSubpath()

        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)

        # Draw line
        painter.setPen(QPen(color, 3))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        path2 = QPainterPath()
        path2.moveTo(points[0])
        for p in points[1:]:
            path2.lineTo(p)
        painter.drawPath(path2)

        # Draw points
        painter.setBrush(QBrush(color))
        for p in points:
            painter.drawEllipse(p, 5, 5)

        # Draw labels
        painter.setPen(QColor(SoftColors.TEXT_SECONDARY))
        font = QFont("Noto Sans Arabic", 8)
        painter.setFont(font)
        for i, label in enumerate(self._labels):
            x = chart_rect.x() + i * step_x
            painter.drawText(
                QRectF(x - 30, chart_rect.bottom() + 4, 60, 16),
                Qt.AlignmentFlag.AlignCenter, label,
            )

        painter.end()
