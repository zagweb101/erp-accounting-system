"""
Soft UI Components — مكونات UI ناعمة مخصصة

Claymorphism + Soft UI + Organic UI widgets.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QTimer
from PySide6.QtGui import QColor, QPainter, QLinearGradient, QBrush, QPaintEvent, QFont
from PySide6.QtWidgets import (
    QWidget, QPushButton, QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QSizePolicy, QStackedWidget, QGraphicsDropShadowEffect,
    QSpacerItem,
)

from infrastructure.ui.theme.soft_ui import SoftColors


# ============================================================
# Soft Shadow Effect — تأثير الظل الناعم
# ============================================================
def add_soft_shadow(
    widget: QWidget,
    blur: int = 20,
    offset_x: int = 0,
    offset_y: int = 4,
    color: QColor = None,
) -> QGraphicsDropShadowEffect:
    """إضافة ظل ناعم (Claymorphism) لأي عنصر.

    Args:
        widget: العنصر الذي سيُضاف له الظل.
        blur: درجة التمويه (أكبر = أنعم).
        offset_x: إزاحة أفقية.
        offset_y: إزاحة رأسية.
        color: لون الظل (افتراضي: رمادي ناعم).

    Returns: تأثير الظل المُضاف.
    """
    if color is None:
        color = QColor(SoftColors.SHADOW_DARK)
        color.setAlpha(120)

    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(offset_x, offset_y)
    effect.setColor(color)
    widget.setGraphicsEffect(effect)
    return effect


# ============================================================
# Soft Card — بطاقة ناعمة (Claymorphism)
# ============================================================
class SoftCard(QFrame):
    """بطاقة ناعمة بظل منتفخ (Claymorphism style).

    Features:
    - زوايا دائرية (20px)
    - ظل ناعم
    - خلفية بيضاء
    - تأثير hover اختياري
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        radius: int = 20,
        shadow: bool = True,
        bg_color: str = SoftColors.SURFACE_LIGHT,
    ) -> None:
        super().__init__(parent)
        self._radius = radius
        self._bg_color = bg_color
        self._shadow_effect: Optional[QGraphicsDropShadowEffect] = None

        self.setObjectName("card")
        self.setStyleSheet(f"""
            QFrame#card {{
                background-color: {bg_color};
                border: none;
                border-radius: {radius}px;
            }}
        """)

        if shadow:
            self._shadow_effect = add_soft_shadow(self, blur=25, offset_y=6)

        # Hover animation
        self._original_y = 0
        self._hover_anim: Optional[QPropertyAnimation] = None

    def set_elevated(self, elevated: bool = True) -> None:
        """رفع/خفض البطاقة (تأثير طفو)."""
        if elevated and self._shadow_effect:
            self._shadow_effect.setBlurRadius(35)
            self._shadow_effect.setOffset(0, 10)
        elif self._shadow_effect:
            self._shadow_effect.setBlurRadius(25)
            self._shadow_effect.setOffset(0, 6)

    def set_accent(self, color: str) -> None:
        """تغيير لون الحد الجانبي (accent border)."""
        self.setStyleSheet(f"""
            QFrame#card {{
                background-color: {self._bg_color};
                border: none;
                border-right: 4px solid {color};
                border-radius: {self._radius}px;
            }}
        """)


# ============================================================
# Gradient Card — بطاقة بتدرج لوني (Organic UI)
# ============================================================
class GradientCard(QFrame):
    """بطاقة بتدرج لوني عضوي.

    Examples:
        card = GradientCard(colors=["#6B8AFE", "#8FA8FF"], parent=self)
    """

    def __init__(
        self,
        colors: list[str] = None,
        parent: Optional[QWidget] = None,
        radius: int = 20,
        text_color: str = "#FFFFFF",
    ) -> None:
        super().__init__(parent)
        self._colors = colors or [SoftColors.ACCENT_BLUE, SoftColors.ACCENT_BLUE_LIGHT]
        self._radius = radius
        self._text_color = text_color

        # Build gradient QSS
        stops = []
        for i, c in enumerate(self._colors):
            pct = i / max(len(self._colors) - 1, 1)
            stops.append(f"stop:{pct:.2f} {c}")
        gradient = f"qlineargradient(x1:0, y1:0, x2:1, y2:1, {', '.join(stops)})"

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {gradient};
                border: none;
                border-radius: {radius}px;
            }}
        """)

        # Add shadow
        shadow_color = QColor(self._colors[-1])
        shadow_color.setAlpha(100)
        add_soft_shadow(self, blur=30, offset_y=8, color=shadow_color)

    def paintEvent(self, event: QPaintEvent) -> None:
        """رسم التدرج اللوني."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        from PySide6.QtGui import QLinearGradient, QBrush, QPainterPath
        rect = self.rect()
        path = QPainterPath()
        path.addRoundedRect(rect.x(), rect.y(), rect.width(), rect.height(), self._radius, self._radius)
        painter.setClipPath(path)

        gradient = QLinearGradient(0, 0, rect.width(), rect.height())
        for i, c in enumerate(self._colors):
            pct = i / max(len(self._colors) - 1, 1)
            gradient.setColorAt(pct, QColor(c))

        painter.fillRect(rect, QBrush(gradient))
        painter.end()


# ============================================================
# KPI Card — بطاقة مؤشر أداء
# ============================================================
class KPICard(SoftCard):
    """بطاقة KPI ناعمة — تعرض قيمة + تسمية + تغيير%.

    Features:
    - قيمة كبيرة (28px)
    - تسمية صغيرة
    - مؤشر التغيير (أعلى/أسفل)
    - لون accent جانبي
    """

    def __init__(
        self,
        label: str = "",
        value: str = "",
        change: str = "",
        accent_color: str = SoftColors.ACCENT_BLUE,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent=parent, radius=20, shadow=True)
        self.set_accent(accent_color)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(6)

        self._label = QLabel(label)
        self._label.setObjectName("kpiLabel")
        self._label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout.addWidget(self._label)

        self._value = QLabel(value)
        self._value.setObjectName("kpiValue")
        self._value.setStyleSheet(f"color: {accent_color}; font-size: 28px; font-weight: 800;")
        self._value.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout.addWidget(self._value)

        self._change = QLabel(change)
        self._change.setStyleSheet(f"color: {SoftColors.TEXT_MUTED}; font-size: 12px;")
        self._change.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout.addWidget(self._change)

    def set_value(self, value: str) -> None:
        self._value.setText(value)

    def set_label(self, label: str) -> None:
        self._label.setText(label)

    def set_change(self, change: str, positive: bool = True) -> None:
        """تحديث مؤشر التغيير."""
        color = SoftColors.ACCENT_GREEN if positive else SoftColors.ACCENT_RED
        self._change.setText(change)
        self._change.setStyleSheet(f"color: {color}; font-size: 12px;")


# ============================================================
# Soft Search Bar — شريط بحث ناعم
# ============================================================
class SoftSearchBar(QFrame):
    """شريط بحث ناعم بزاوية دائرية وأيقونة."""

    def __init__(self, placeholder: str = "🔍 بحث...", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._setup_ui(placeholder)
        add_soft_shadow(self, blur=15, offset_y=2)

    def _setup_ui(self, placeholder: str) -> None:
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {SoftColors.BG_INPUT};
                border: 2px solid {SoftColors.BG_SECONDARY};
                border-radius: 16px;
            }}
            QFrame:focus-within {{
                border: 2px solid {SoftColors.ACCENT_BLUE};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(8)

        # Search icon
        icon_label = QLabel("🔍")
        icon_label.setStyleSheet(f"color: {SoftColors.TEXT_MUTED}; font-size: 16px; background: transparent; border: none;")
        layout.addWidget(icon_label)

        # Input
        self._input = QLineEdit()
        self._input.setPlaceholderText(placeholder)
        self._input.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                border: none;
                font-size: 14px;
            }
            QLineEdit:focus { border: none; }
        """)
        self._input.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout.addWidget(self._input)

    def text(self) -> str:
        """الحصول على نص البحث."""
        return self._input.text()

    def set_text(self, text: str) -> None:
        """تحديد نص البحث."""
        self._input.setText(text)

    def textChanged(self):
        """Signal للنص المتغير."""
        return self._input.textChanged


# ============================================================
// Soft Sidebar — شريط جانبي ناعم (Organic UI)
# ============================================================
class SoftSidebar(QFrame):
    """شريط جانبي ناعم بتصميم Organic UI.

    Features:
    - خلفية ماضيلية ناعمة
    - أزرار منحنية
    - تأثير hover ناعم
    - قسم المستخدم في الأسفل
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(260)
        self._buttons: list[QPushButton] = []

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {SoftColors.BG_SIDEBAR};
                border: none;
                border-left: 1px solid {SoftColors.SHADOW_DARK};
            }}
        """)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 24, 16, 16)
        self._layout.setSpacing(6)

    def add_logo(self, text: str = "ERP") -> None:
        """إضافة شعار في أعلى الشريط."""
        logo = QLabel(text)
        logo.setStyleSheet(f"""
            color: {SoftColors.ACCENT_BLUE_DARK};
            font-size: 28px;
            font-weight: 800;
            background: transparent;
            padding: 8px;
        """)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._layout.addWidget(logo)

        # Subtitle
        subtitle = QLabel("نظام محاسبي متكامل")
        subtitle.setStyleSheet(f"""
            color: {SoftColors.TEXT_MUTED};
            font-size: 12px;
            background: transparent;
        """)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._layout.addWidget(subtitle)

        self._layout.addSpacing(20)

    def add_button(self, text: str, icon: str = "", active: bool = False) -> QPushButton:
        """إضافة زر للشريط الجانبي."""
        btn = QPushButton(f"  {icon}  {text}" if icon else text)
        btn.setMinimumHeight(48)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        btn.setStyleSheet(self._button_style(active))
        btn.clicked.connect(lambda: self._set_active(btn))
        self._buttons.append(btn)
        self._layout.addWidget(btn)
        return btn

    def _button_style(self, active: bool) -> str:
        """نمط الزر حسب الحالة."""
        if active:
            return f"""
                QPushButton {{
                    background-color: {SoftColors.ACCENT_BLUE};
                    color: {SoftColors.TEXT_ON_ACCENT};
                    border: none;
                    border-radius: 14px;
                    padding: 12px 16px;
                    text-align: right;
                    font-size: 14px;
                    font-weight: 700;
                }}
            """
        else:
            return f"""
                QPushButton {{
                    background-color: transparent;
                    color: {SoftColors.TEXT_SECONDARY};
                    border: none;
                    border-radius: 14px;
                    padding: 12px 16px;
                    text-align: right;
                    font-size: 14px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: {SoftColors.SURFACE_LIGHT};
                    color: {SoftColors.TEXT_PRIMARY};
                }}
            """

    def _set_active(self, active_btn: QPushButton) -> None:
        """تحديد الزر النشط."""
        for btn in self._buttons:
            btn.setStyleSheet(self._button_style(active=False))
        active_btn.setStyleSheet(self._button_style(active=True))

    def add_spacer(self) -> None:
        """إضافة مساحة مرنة."""
        self._layout.addStretch()

    def add_user_info(self, name: str, role: str) -> None:
        """إضافة معلومات المستخدم في أسفل الشريط."""
        card = SoftCard(self, radius=14, shadow=False, bg_color=SoftColors.SURFACE_LIGHT)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(2)

        name_label = QLabel(name)
        name_label.setStyleSheet(f"color: {SoftColors.TEXT_PRIMARY}; font-weight: 700; font-size: 13px; background: transparent;")
        name_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        card_layout.addWidget(name_label)

        role_label = QLabel(role)
        role_label.setStyleSheet(f"color: {SoftColors.TEXT_MUTED}; font-size: 11px; background: transparent;")
        role_label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        card_layout.addWidget(role_label)

        self._layout.addWidget(card)


# ============================================================
// Soft Chat Bubble — فقاعة محادثة (للـ AI Chat)
# ============================================================
class ChatBubble(QFrame):
    """فقاعة محادثة ناعمة (للـ AI Chat UI).

    Features:
    - زوايا دائرية كبيرة
    - لون مختلف للرسائل المُرسلة والمستلمة
    - ظل ناعم
    """

    def __init__(
        self,
        text: str,
        is_user: bool = True,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._is_user = is_user

        if is_user:
            bg = SoftColors.ACCENT_BLUE
            text_color = SoftColors.TEXT_ON_ACCENT
            align = Qt.AlignmentFlag.AlignLeft
        else:
            bg = SoftColors.SURFACE_LIGHT
            text_color = SoftColors.TEXT_PRIMARY
            align = Qt.AlignmentFlag.AlignRight

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: none;
                border-radius: 18px;
                border-bottom-left-radius: {'4px' if is_user else '18px'};
                border-bottom-right-radius: {'18px' if is_user else '4px'};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        label = QLabel(text)
        label.setStyleSheet(f"""
            color: {text_color};
            font-size: 14px;
            background: transparent;
        """)
        label.setWordWrap(True)
        label.setAlignment(align)
        label.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout.addWidget(label)

        # Add shadow
        shadow_color = QColor(SoftColors.SHADOW_DARK)
        shadow_color.setAlpha(80)
        add_soft_shadow(self, blur=12, offset_y=3, color=shadow_color)

        # Max width
        self.setMaximumWidth(500)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
