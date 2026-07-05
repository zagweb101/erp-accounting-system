"""
OpenAI LLM Provider — موفّر OpenAI للمساعد الذكي

جاهز للاستخدام عند توفير مفتاح API.
يدعم:
- GPT-4o, GPT-4o-mini, GPT-4-turbo
- Function Calling (لتنفيذ إجراءات النظام)
- Streaming (اختياري)

Usage:
    from infrastructure.services.openai_provider import OpenAIProvider

    # Set API key in .env or directly
    provider = OpenAIProvider(api_key="sk-your-key-here")
    # أو من البيئة:
    provider = OpenAIProvider()  # يقرأ OPENAI_API_KEY من .env

    ai_service = AIAgentService(llm_provider=provider)
"""
from __future__ import annotations

import json
import os
from typing import Any, Optional

from infrastructure.services.ai_agent_service import LLMProvider


class OpenAIProvider(LLMProvider):
    """موفّر OpenAI GPT للذكاء الاصطناعي.

    يتطلب تثبيت: pip install openai

    Args:
        api_key: مفتاح OpenAI API. إذا لم يُمرَّر، يقرأ من OPENAI_API_KEY.
        model: اسم النموذج (افتراضي: gpt-4o-mini).
        temperature: درجة الإبداع (0-2، افتراضي: 0.7).
        max_tokens: الحد الأقصى للـ tokens في الرد.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._client = None

        # System prompt — يُعرّف الـ AI كمساعد محاسبي عربي
        self._system_prompt = (
            "أنت مساعد محاسبي ذكي لنظام ERP محاسبي. "
            "تجيب باللغة العربية. دورك:\n"
            "1. مساعدة المستخدمين في إنشاء الفواتير والقيود المحاسبية\n"
            "2. الاستعلام عن الأرصدة والتقارير المالية\n"
            "3. البحث عن العملاء والموردين والمنتجات\n"
            "4. تقديم نصائح محاسبية\n\n"
            "قواعد:\n"
            "- استخدم Function Calling لتنفيذ الإجراءات\n"
            "- اطلب تأكيد المستخدم قبل العمليات الحساسة\n"
            "- لا ت invent أرقامًا — استعلم من النظام\n"
            "- كن مختصرًا وواضحًا"
        )

    def _get_client(self):
        """الحصول على عميل OpenAI (lazy init)."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self._api_key)
            except ImportError:
                raise ImportError(
                    "openai package not installed. Run: pip install openai"
                )
        return self._client

    def generate(self, prompt: str, functions: list[dict] = None) -> dict:
        """توليد استجابة من OpenAI.

        Args:
            prompt: نص الطلب من المستخدم.
            functions: قائمة الدوال المتاحة (JSON schema).

        Returns: {
            "text": "response text",
            "function_call": {"name": "...", "arguments": {...}} or None
        }
        """
        if not self._api_key:
            return {
                "text": "⚠️ مفتاح OpenAI API غير مُحدّد. أضف OPENAI_API_KEY في ملف .env أو الإعدادات.",
                "function_call": None,
            }

        try:
            client = self._get_client()

            messages = [
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": prompt},
            ]

            # Build function definitions for OpenAI format
            tools = None
            if functions:
                tools = [
                    {
                        "type": "function",
                        "function": {
                            "name": f["name"],
                            "description": f["description"],
                            "parameters": {
                                "type": "object",
                                "properties": f.get("parameters", {}),
                            },
                        },
                    }
                    for f in functions
                ]

            response = client.chat.completions.create(
                model=self._model,
                messages=messages,
                tools=tools,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
            )

            choice = response.choices[0]
            message = choice.message

            # Check for function call
            if hasattr(message, "tool_calls") and message.tool_calls:
                tool_call = message.tool_calls[0]
                return {
                    "text": message.content or "سأنفذ الإجراء المطلوب.",
                    "function_call": {
                        "name": tool_call.function.name,
                        "arguments": json.loads(tool_call.function.arguments),
                    },
                }

            return {
                "text": message.content or "",
                "function_call": None,
            }

        except Exception as e:
            return {
                "text": f"❌ خطأ في الاتصال بـ OpenAI: {e}",
                "function_call": None,
            }

    def set_api_key(self, api_key: str) -> None:
        """تحديث مفتاح API."""
        self._api_key = api_key
        self._client = None  # Force re-init

    def set_model(self, model: str) -> None:
        """تغيير النموذج."""
        self._model = model

    def is_ready(self) -> bool:
        """هل المفتاح مُعّرف؟"""
        return bool(self._api_key)


class LocalLLMProvider(LLMProvider):
    """موفّر LLM محلي (Llama, Qwen, إلخ) عبر Ollama أو llama.cpp.

    يتطلب تثبيت Ollama: https://ollama.ai

    Usage:
        provider = LocalLLMProvider(model="llama3:8b", host="http://localhost:11434")
    """

    def __init__(
        self,
        model: str = "llama3:8b",
        host: str = "http://localhost:11434",
        temperature: float = 0.7,
    ) -> None:
        self._model = model
        self._host = host
        self._temperature = temperature

    def generate(self, prompt: str, functions: list[dict] = None) -> dict:
        """توليد استجابة من LLM محلي عبر Ollama."""
        try:
            import requests

            # Build context with available functions
            context = "Available functions:\n"
            if functions:
                for f in functions:
                    context += f"- {f['name']}: {f['description']}\n"

            full_prompt = f"{context}\n\nUser request: {prompt}\n\nResponse:"

            response = requests.post(
                f"{self._host}/api/generate",
                json={
                    "model": self._model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {"temperature": self._temperature},
                },
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()
                text = result.get("response", "")
                return {"text": text, "function_call": None}
            else:
                return {
                    "text": f"❌ خطأ من Ollama: {response.status_code}",
                    "function_call": None,
                }

        except ImportError:
            return {
                "text": "❌ requests package not installed. Run: pip install requests",
                "function_call": None,
            }
        except Exception as e:
            return {
                "text": f"❌ خطأ في الاتصال بـ Ollama: {e}",
                "function_call": None,
            }

    def is_ready(self) -> bool:
        """هل Ollama يعمل؟"""
        try:
            import requests
            r = requests.get(f"{self._host}/api/tags", timeout=5)
            return r.status_code == 200
        except Exception:
            return False
