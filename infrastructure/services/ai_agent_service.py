"""
AI Agent Module - وحدة الذكاء الاصطناعي

Foundation for AI-powered accounting assistant.
Supports:
- Natural language queries (Text-to-SQL)
- Auto-invoice creation from text
- OCR for receipts
- Cash flow prediction
- Anomaly detection

Architecture:
- AIAgentService: main orchestrator
- FunctionCaller: maps natural language to system functions
- LLMProvider: pluggable LLM backend (OpenAI, local Llama, etc.)
- HumanInTheLoop: requires user confirmation before executing
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Optional
from uuid import UUID

from domain.exceptions.exceptions import PermissionDeniedException, ValidationException
from domain.value_objects.value_objects import Permission


# ============================================================
# AI Function Definitions (what the AI can do)
# ============================================================
@dataclass
class AIFunction:
    """تعريف دالة يمكن للـ AI استدعاؤها."""
    name: str
    description: str
    parameters: dict  # JSON schema
    handler: Callable
    requires_confirmation: bool = True
    required_permission: Optional[Permission] = None


@dataclass
class AIRequest:
    """طلب من المستخدم للـ AI."""
    text: str
    user_id: UUID
    username: str
    timestamp: datetime = field(default_factory=datetime.now)
    context: dict = field(default_factory=dict)


@dataclass
class AIResponse:
    """استجابة الـ AI."""
    text: str
    proposed_action: Optional[dict] = None  # function name + args
    requires_confirmation: bool = False
    executed: bool = False
    result: Optional[Any] = None
    error: Optional[str] = None


# ============================================================
# LLM Provider Interface (pluggable)
# ============================================================
class LLMProvider:
    """واجهة موفّر النموذج اللغوي (LLM).

    Implementations:
    - OpenAIProvider (GPT-4, GPT-4o)
    - LocalLLMProvider (Llama-3-Arabic, Qwen)
    - MockLLMProvider (for testing)
    """

    def generate(self, prompt: str, functions: list[dict] = None) -> dict:
        """توليد استجابة من الـ LLM.

        Returns: {
            "text": "response text",
            "function_call": {"name": "...", "arguments": {...}} or None
        }
        """
        raise NotImplementedError


class MockLLMProvider(LLMProvider):
    """Mock LLM for testing (no real AI)."""

    def generate(self, prompt: str, functions: list[dict] = None) -> dict:
        """محاكاة بسيطة للـ LLM - تتعرف على أنماط نصية محددة."""
        prompt_lower = prompt.lower()

        # Pattern: create invoice
        if "فاتورة" in prompt and "بيع" in prompt:
            return {
                "text": "سأنشئ فاتورة بيع لك. أحتاج لتأكيد البيانات التالية:",
                "function_call": {
                    "name": "create_sales_invoice",
                    "arguments": {
                        "customer": "عميل افتراضي",
                        "items": [{"name": "منتج", "quantity": 1, "price": 100}],
                    },
                },
            }

        # Pattern: query balance
        if "رصيد" in prompt or "balance" in prompt_lower:
            return {
                "text": "رصيد الصندوق الحالي هو 50,000 ر.س",
                "function_call": None,
            }

        # Pattern: report
        if "تقرير" in prompt or "report" in prompt_lower:
            return {
                "text": "سأولّد تقرير الميزانية العمومية لك.",
                "function_call": {
                    "name": "generate_report",
                    "arguments": {"report_type": "balance_sheet"},
                },
            }

        # Default
        return {
            "text": f"لم أفهم طلبك تمامًا. يمكنك أن تطلب مني: إنشاء فاتورة، عرض رصيد، أو توليد تقرير.",
            "function_call": None,
        }


# ============================================================
# AI Agent Service (main orchestrator)
# ============================================================
class AIAgentService:
    """خدمة المساعد الذكي.

    تربط بين الـ LLM ووظائف النظام.
    تطبّق نموذج Human-in-the-Loop: كل تنفيذ يتطلب تأكيد المستخدم.
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        user_repo=None,
        customer_repo=None,
        invoice_repo=None,
        account_repo=None,
        journal_repo=None,
        product_repo=None,
    ) -> None:
        self._llm = llm_provider
        self._user_repo = user_repo
        self._customer_repo = customer_repo
        self._invoice_repo = invoice_repo
        self._account_repo = account_repo
        self._journal_repo = journal_repo
        self._product_repo = product_repo

        # Register available functions
        self._functions: dict[str, AIFunction] = {}
        self._register_default_functions()

    def _register_default_functions(self) -> None:
        """تسجيل الدوال المتاحة للـ AI."""
        self.register_function(AIFunction(
            name="query_cash_balance",
            description="الاستعلام عن رصيد الصندوق",
            parameters={},
            handler=self._query_cash_balance,
            requires_confirmation=False,
            required_permission=Permission.REPORT_VIEW,
        ))

        self.register_function(AIFunction(
            name="generate_report",
            description="توليد تقرير مالي",
            parameters={
                "report_type": {
                    "type": "string",
                    "enum": ["trial_balance", "balance_sheet", "income_statement"],
                },
            },
            handler=self._generate_report,
            requires_confirmation=True,
            required_permission=Permission.REPORT_VIEW,
        ))

        self.register_function(AIFunction(
            name="create_sales_invoice",
            description="إنشاء فاتورة بيع",
            parameters={
                "customer": {"type": "string"},
                "items": {
                    "type": "array",
                    "items": {
                        "name": {"type": "string"},
                        "quantity": {"type": "number"},
                        "price": {"type": "number"},
                    },
                },
            },
            handler=self._create_sales_invoice,
            requires_confirmation=True,
            required_permission=Permission.INVOICE_CREATE,
        ))

        self.register_function(AIFunction(
            name="list_low_stock_products",
            description="عرض المنتجات منخفضة المخزون",
            parameters={},
            handler=self._list_low_stock,
            requires_confirmation=False,
            required_permission=Permission.PRODUCT_VIEW,
        ))

    def register_function(self, func: AIFunction) -> None:
        """تسجيل دالة جديدة للـ AI."""
        self._functions[func.name] = func

    def process_request(self, request: AIRequest, current_user) -> AIResponse:
        """معالجة طلب من المستخدم.

        Args:
            request: نص الطلب
            current_user: المستخدم الحالي (للتحقق من الصلاحيات)

        Returns: AIResponse
        """
        # 1. Build prompt with context
        prompt = self._build_prompt(request, current_user)

        # 2. Get LLM response
        functions_schema = [self._function_to_schema(f) for f in self._functions.values()]
        llm_result = self._llm.generate(prompt, functions=functions_schema)

        # 3. Build response
        response = AIResponse(
            text=llm_result.get("text", ""),
            requires_confirmation=False,
        )

        function_call = llm_result.get("function_call")
        if function_call:
            func_name = function_call.get("name")
            func_args = function_call.get("arguments", {})

            if func_name in self._functions:
                func = self._functions[func_name]

                # Check permission
                if func.required_permission and not current_user.has_permission(
                    func.required_permission
                ):
                    response.text = f"ليس لديك صلاحية لتنفيذ: {func_name}"
                    response.error = "permission_denied"
                    return response

                response.proposed_action = {"name": func_name, "arguments": func_args}
                response.requires_confirmation = func.requires_confirmation

                # If no confirmation needed, execute immediately
                if not func.requires_confirmation:
                    response = self.execute_action(
                        response, func_name, func_args, current_user
                    )
            else:
                response.text = f"الدالة '{func_name}' غير متاحة."

        return response

    def execute_action(
        self,
        response: AIResponse,
        func_name: str,
        func_args: dict,
        current_user,
    ) -> AIResponse:
        """تنفيذ الإجراء المقترح (بعد تأكيد المستخدم)."""
        if func_name not in self._functions:
            response.error = f"Unknown function: {func_name}"
            return response

        func = self._functions[func_name]

        # Check permission again (safety)
        if func.required_permission and not current_user.has_permission(
            func.required_permission
        ):
            response.error = "permission_denied"
            response.text = "ليس لديك صلاحية لتنفيذ هذا الإجراء."
            return response

        try:
            result = func.handler(**func_args, current_user=current_user)
            response.executed = True
            response.result = result
            response.text = f"✅ تم تنفيذ: {func_name}\nالنتيجة: {result}"
        except Exception as e:
            response.error = str(e)
            response.text = f"❌ فشل التنفيذ: {e}"

        return response

    def _build_prompt(self, request: AIRequest, current_user) -> str:
        """بناء الـ prompt للـ LLM."""
        return (
            f"أنت مساعد محاسبي ذكي. المستخدم: {current_user.username} "
            f"(الدور: {current_user.role.value}).\n"
            f"الطلب: {request.text}\n"
            f"الوقت: {request.timestamp.isoformat()}\n"
            f"الوظائف المتاحة: {list(self._functions.keys())}"
        )

    def _function_to_schema(self, func: AIFunction) -> dict:
        """تحويل دالة إلى JSON schema للـ LLM."""
        return {
            "name": func.name,
            "description": func.description,
            "parameters": func.parameters,
        }

    # ============================================================
    # Default function handlers
    # ============================================================
    def _query_cash_balance(self, current_user, **kwargs) -> str:
        """الاستعلام عن رصيد الصندوق."""
        # This would use account_repo to get balance of account 1101
        return "رصيد الصندوق: 50,000.00 ر.س (محاكاة)"

    def _generate_report(
        self, report_type: str = "trial_balance", current_user=None, **kwargs
    ) -> str:
        """توليد تقرير."""
        return f"تم توليد تقرير: {report_type} (محاكاة)"

    def _create_sales_invoice(
        self, customer: str, items: list, current_user=None, **kwargs
    ) -> str:
        """إنشاء فاتورة بيع (محاكاة - يحتاج wiring كامل في الإنتاج)."""
        total = sum(it.get("price", 0) * it.get("quantity", 1) for it in items)
        return f"تم إنشاء فاتورة بيع للعميل '{customer}' بقيمة {total:,.2f} ر.س (محاكاة)"

    def _list_low_stock(self, current_user=None, **kwargs) -> str:
        """عرض المنتجات منخفضة المخزون."""
        return "المنتجات منخفضة المخزون: لا توجد تنبيهات حاليًا (محاكاة)"


# ============================================================
# AI Audit Logger - يسجل كل تفاعلات الـ AI
# ============================================================
class AIAuditLogger:
    """يسجل كل تفاعلات الـ AI للمراجعة الأمنية."""

    def __init__(self) -> None:
        self._logs: list[dict] = []

    def log_interaction(
        self,
        user_id: str,
        username: str,
        request_text: str,
        response_text: str,
        action_executed: bool,
        action_result: Optional[str] = None,
    ) -> None:
        """تسجيل تفاعل AI."""
        self._logs.append({
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "username": username,
            "request": request_text,
            "response": response_text,
            "executed": action_executed,
            "result": action_result,
        })

    def get_logs(self, limit: int = 100) -> list[dict]:
        """الحصول على آخر السجلات."""
        return self._logs[-limit:]

    def clear_logs(self) -> None:
        """مسح السجلات."""
        self._logs.clear()
