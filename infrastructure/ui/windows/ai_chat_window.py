"""
AI Chat Window — واجهة المحادثة مع المساعد الذكي

Design: Soft UI + Claymorphism + Organic UI
Features:
- فقاعات محادثة ناعمة
- حقل إدخال بزاوية دائرية
- أزرار تأكيد/رفض للإجراءات المقترحة
- سجل المحادثة
- مؤشر تحميل أثناء المعالجة
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QKeyEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QFrame, QSizePolicy, QMessageBox, QDialog,
    QTextEdit, QPlainTextEdit, QApplication, QSpacerItem,
)

from infrastructure.ui.theme.soft_ui import SoftColors
from infrastructure.ui.widgets.soft_components import add_soft_shadow
from infrastructure.ui.widgets.soft_components import (
    SoftCard, ChatBubble, SoftSearchBar,
)
from infrastructure.ui.widgets.loading_overlay import LoadingOverlay
from infrastructure.ui.windows._async_worker import AsyncWorker


class ChatInputBar(QFrame):
    """شريط إدخال المحادثة — ناعم بزاوية دائرية كبيرة."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._setup_ui()
        self._setup_style()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Input field
        self._input = QTextEdit()
        self._input.setPlaceholderText("اكتب رسالتك للمساعد الذكي...")
        self._input.setMaximumHeight(60)
        self._input.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout.addWidget(self._input, 1)

        # Send button
        self._send_button = QPushButton("➤")
        self._send_button.setFixedSize(48, 48)
        self._send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_button.setToolTip("إرسال الرسالة")
        self._send_button.clicked.connect(self._on_send)
        layout.addWidget(self._send_button)

    def _setup_style(self) -> None:
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {SoftColors.SURFACE_LIGHT};
                border: 2px solid {SoftColors.BG_SECONDARY};
                border-radius: 24px;
            }}
        """)
        self._input.setStyleSheet(f"""
            QTextEdit {{
                background-color: transparent;
                border: none;
                font-size: 14px;
                color: {SoftColors.TEXT_PRIMARY};
            }}
        """)
        self._send_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {SoftColors.ACCENT_BLUE};
                color: {SoftColors.TEXT_ON_ACCENT};
                border: none;
                border-radius: 24px;
                font-size: 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {SoftColors.ACCENT_BLUE_DARK};
            }}
            QPushButton:pressed {{
                background-color: {SoftColors.ACCENT_BLUE_DARK};
            }}
        """)

    def _on_send(self) -> None:
        """معالجة زر الإرسال."""
        text = self._input.toPlainText().strip()
        if text:
            self._input.clear()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Enter للإرسال، Shift+Enter لسطر جديد."""
        if event.key() == Qt.Key.Key_Return and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self._on_send()
        else:
            super().keyPressEvent(event)

    def text(self) -> str:
        """الحصول على النص."""
        return self._input.toPlainText().strip()

    def clear(self) -> None:
        """مسح النص."""
        self._input.clear()


class AIChatWindow(QWidget):
    """واجهة المحادثة مع المساعد الذكي.

    Design: Soft UI with Claymorphism chat bubbles.

    Features:
    - فقاعات محادثة (user: أزرق، AI: أبيض)
    - اقتراحات سريعة (quick actions)
    - تأكيد الإجراءات المقترحة
    - مؤشر تحميل أثناء المعالجة
    - سجل المحادثة الكامل
    """

    def __init__(
        self,
        current_user,
        ai_service=None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._current_user = current_user
        self._ai_service = ai_service
        self._worker: Optional[AsyncWorker] = None
        self._messages: list[dict] = []
        self._setup_ui()
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        # Welcome message
        self._add_ai_message(
            f"مرحبًا {current_user.full_name or current_user.username}! 👋\n\n"
            "أنا مساعدك المحاسبي الذكي. يمكنني:\n"
            "• إنشاء فواتير بيع وشراء\n"
            "• الاستعلام عن الأرصدة\n"
            "• توليد التقارير المالية\n"
            "• البحث عن العملاء والمنتجات\n\n"
            "كيف يمكنني مساعدتك اليوم؟"
        )

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header = self._build_header()
        layout.addWidget(header)

        # Quick actions bar
        quick_actions = self._build_quick_actions()
        layout.addWidget(quick_actions)

        # Chat area (scrollable)
        self._chat_scroll = QScrollArea()
        self._chat_scroll.setWidgetResizable(True)
        self._chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._chat_scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {SoftColors.BG_PRIMARY};
                border: none;
                border-radius: 20px;
            }}
        """)

        self._chat_container = QWidget()
        self._chat_layout = QVBoxLayout(self._chat_container)
        self._chat_layout.setContentsMargins(16, 16, 16, 16)
        self._chat_layout.setSpacing(12)
        self._chat_layout.addStretch()

        self._chat_scroll.setWidget(self._chat_container)
        layout.addWidget(self._chat_scroll, 1)

        # Proposed action panel (hidden by default)
        self._action_panel = self._build_action_panel()
        self._action_panel.setVisible(False)
        layout.addWidget(self._action_panel)

        # Input bar
        self._input_bar = ChatInputBar(self)
        layout.addWidget(self._input_bar)

        # Connect signals
        self._input_bar._send_button.clicked.connect(self._on_send_clicked)

    def _build_header(self) -> QWidget:
        """بناء ترويسة المحادثة."""
        card = SoftCard(self, radius=20, shadow=True)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(12)

        # AI avatar (gradient circle)
        avatar = QLabel("🤖")
        avatar.setFixedSize(48, 48)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet(f"""
            QLabel {{
                background-color: {SoftColors.ACCENT_PURPLE};
                border-radius: 24px;
                font-size: 24px;
            }}
        """)
        layout.addWidget(avatar)

        # Title
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        title = QLabel("المساعد المحاسبي الذكي")
        title.setStyleSheet(f"color: {SoftColors.TEXT_PRIMARY}; font-size: 16px; font-weight: 700; background: transparent;")
        title.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        info_layout.addWidget(title)

        status = QLabel("● متصل وجاهز")
        status.setStyleSheet(f"color: {SoftColors.ACCENT_GREEN_DARK}; font-size: 12px; background: transparent;")
        status.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        info_layout.addWidget(status)

        layout.addLayout(info_layout)
        layout.addStretch()

        # Clear chat button
        clear_btn = QPushButton("🗑️ مسح")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {SoftColors.BG_SECONDARY};
                color: {SoftColors.TEXT_SECONDARY};
                border: none;
                border-radius: 10px;
                padding: 6px 12px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {SoftColors.SURFACE_DARK};
            }}
        """)
        clear_btn.clicked.connect(self._clear_chat)
        layout.addWidget(clear_btn)

        return card

    def _build_quick_actions(self) -> QWidget:
        """بناء شريط الإجراءات السريعة."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        actions = [
            ("📊 ميزان المراجعة", "اعرض ميزان المراجعة"),
            ("💰 رصيد الصندوق", "ما هو رصيد الصندوق؟"),
            ("⚠️ مخزون منخفض", "اعرض المنتجات منخفضة المخزون"),
            ("📄 فاتورة بيع", "أنشئ فاتورة بيع"),
        ]

        for text, prompt in actions:
            btn = QPushButton(text)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {SoftColors.SURFACE_LIGHT};
                    color: {SoftColors.TEXT_SECONDARY};
                    border: 2px solid {SoftColors.BG_SECONDARY};
                    border-radius: 14px;
                    padding: 6px 14px;
                    font-size: 12px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {SoftColors.ACCENT_BLUE_LIGHT};
                    color: {SoftColors.ACCENT_BLUE_DARK};
                    border: 2px solid {SoftColors.ACCENT_BLUE};
                }}
            """)
            btn.clicked.connect(lambda checked, p=prompt: self._send_quick(p))
            layout.addWidget(btn)

        layout.addStretch()
        return container

    def _build_action_panel(self) -> QWidget:
        """بناء لوحة الإجراء المقترح (للتأكيد)."""
        card = SoftCard(self, radius=16, shadow=True, bg_color=SoftColors.ACCENT_ORANGE_LIGHT)
        card.set_accent(SoftColors.ACCENT_ORANGE)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        title = QLabel("⚡ إجراء مقترح")
        title.setStyleSheet(f"color: {SoftColors.ACCENT_ORANGE_DARK}; font-weight: 700; font-size: 14px; background: transparent;")
        title.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout.addWidget(title)

        self._action_description = QLabel("")
        self._action_description.setStyleSheet(f"color: {SoftColors.TEXT_PRIMARY}; font-size: 13px; background: transparent;")
        self._action_description.setWordWrap(True)
        self._action_description.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout.addWidget(self._action_description)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._confirm_btn = QPushButton("✓ تأكيد وتنفيذ")
        self._confirm_btn.setObjectName("success")
        self._confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._confirm_btn.clicked.connect(self._on_confirm_action)
        btn_layout.addWidget(self._confirm_btn)

        self._reject_btn = QPushButton("✗ رفض")
        self._reject_btn.setObjectName("danger")
        self._reject_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reject_btn.clicked.connect(self._on_reject_action)
        btn_layout.addWidget(self._reject_btn)

        layout.addLayout(btn_layout)

        return card

    def _on_send_clicked(self) -> None:
        """معالجة زر الإرسال."""
        text = self._input_bar.text()
        if not text:
            return

        self._input_bar.clear()
        self._add_user_message(text)
        self._process_ai_request(text)

    def _send_quick(self, prompt: str) -> None:
        """إرسال إجراء سريع."""
        self._add_user_message(prompt)
        self._process_ai_request(prompt)

    def _process_ai_request(self, text: str) -> None:
        """معالجة طلب AI."""
        # Show loading
        self._add_typing_indicator()

        if self._ai_service is None:
            # No AI service — show mock response
            QTimer.singleShot(500, lambda: self._handle_no_ai(text))
            return

        from infrastructure.services.ai_agent_service import AIRequest

        async def _process():
            request = AIRequest(
                text=text,
                user_id=self._current_user.id,
                username=self._current_user.username,
            )
            return self._ai_service.process_request(request, self._current_user)

        self._worker = AsyncWorker(_process)
        self._worker.finished_signal.connect(self._on_ai_response)
        self._worker.error_signal.connect(self._on_ai_error)
        self._worker.start()

    def _handle_no_ai(self, text: str) -> None:
        """معالجة عند عدم وجود AI service."""
        self._remove_typing_indicator()
        self._add_ai_message(
            "⚠️ المساعد الذكي غير مُفعّل حاليًا.\n\n"
            "لتفعيله، أضف مفتاح API للـ LLM (OpenAI أو Llama محلي) في الإعدادات.\n\n"
            "يمكنك استخدام الإجراءات السريعة أعلاه للوصول السريع."
        )

    def _on_ai_response(self, response) -> None:
        """معالجة استجابة AI."""
        self._remove_typing_indicator()

        # Add AI text response
        self._add_ai_message(response.text)

        # If there's a proposed action requiring confirmation
        if response.proposed_action and response.requires_confirmation:
            self._show_action_panel(response.proposed_action, response)
        elif response.proposed_action and not response.requires_confirmation:
            # Auto-executed
            if response.executed:
                self._add_ai_message(f"✅ تم التنفيذ: {response.result}")

    def _on_ai_error(self, error: str) -> None:
        """معالجة خطأ AI."""
        self._remove_typing_indicator()
        self._add_ai_message(f"❌ خطأ: {error}")

    def _show_action_panel(self, action: dict, response) -> None:
        """عرض لوحة الإجراء المقترح."""
        self._pending_response = response
        self._action_description.setText(
            f"الإجراء: {action['name']}\n"
            f"المعطيات: {action.get('arguments', {})}"
        )
        self._action_panel.setVisible(True)

    def _on_confirm_action(self) -> None:
        """تأكيد الإجراء المقترح."""
        if not hasattr(self, '_pending_response') or not self._pending_response:
            return

        response = self._pending_response
        action = response.proposed_action

        # Execute
        if self._ai_service:
            response = self._ai_service.execute_action(
                response=response,
                func_name=action["name"],
                func_args=action.get("arguments", {}),
                current_user=self._current_user,
            )

            if response.executed:
                self._add_ai_message(f"✅ تم تنفيذ الإجراء بنجاح!\n{response.result}")
            else:
                self._add_ai_message(f"❌ فشل التنفيذ: {response.error}")

        self._action_panel.setVisible(False)
        self._pending_response = None

    def _on_reject_action(self) -> None:
        """رفض الإجراء المقترح."""
        self._add_ai_message("تم رفض الإجراء. هل من شيء آخر يمكنني مساعدتك به؟")
        self._action_panel.setVisible(False)
        self._pending_response = None

    def _add_user_message(self, text: str) -> None:
        """إضافة رسالة مستخدم."""
        self._messages.append({"role": "user", "text": text, "time": datetime.now()})

        bubble = ChatBubble(text, is_user=True, parent=self._chat_container)
        # Align user messages to the right
        wrapper = QHBoxLayout()
        wrapper.addStretch()
        wrapper.addWidget(bubble)

        # Insert before the stretch
        self._chat_layout.insertLayout(self._chat_layout.count() - 1, wrapper)
        self._scroll_to_bottom()

    def _add_ai_message(self, text: str) -> None:
        """إضافة رسالة AI."""
        self._messages.append({"role": "ai", "text": text, "time": datetime.now()})

        bubble = ChatBubble(text, is_user=False, parent=self._chat_container)
        # Align AI messages to the left
        wrapper = QHBoxLayout()
        wrapper.addWidget(bubble)
        wrapper.addStretch()

        self._chat_layout.insertLayout(self._chat_layout.count() - 1, wrapper)
        self._scroll_to_bottom()

    def _add_typing_indicator(self) -> None:
        """إضافة مؤشر الكتابة."""
        self._typing = QLabel("🤖 يكتب...")
        self._typing.setStyleSheet(f"""
            color: {SoftColors.TEXT_MUTED};
            font-size: 12px;
            background: transparent;
            padding: 8px;
        """)
        self._typing.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._chat_layout.insertWidget(self._chat_layout.count() - 1, self._typing)
        self._scroll_to_bottom()

    def _remove_typing_indicator(self) -> None:
        """إزالة مؤشر الكتابة."""
        if hasattr(self, "_typing") and self._typing:
            self._typing.deleteLater()
            self._typing = None

    def _scroll_to_bottom(self) -> None:
        """التمرير لأسفل."""
        QTimer.singleShot(50, lambda: self._chat_scroll.verticalScrollBar().setValue(
            self._chat_scroll.verticalScrollBar().maximum()
        ))

    def _clear_chat(self) -> None:
        """مسح المحادثة."""
        reply = QMessageBox.question(
            self, "مسح المحادثة",
            "هل تريد مسح كل المحادثة؟",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            # Clear all widgets
            while self._chat_layout.count() > 1:
                item = self._chat_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self._messages.clear()
            self._add_ai_message("تم مسح المحادثة. كيف يمكنني مساعدتك؟")
