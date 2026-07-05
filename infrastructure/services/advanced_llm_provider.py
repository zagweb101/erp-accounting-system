"""
Advanced LLM Provider — موفّر LLM متقدم

يدعم:
- OpenAI GPT-4o مع streaming
- Function Calling متقدم
- Caching للاستجابات (توفير تكلفة)
- Rate limiting
- Cost tracking
- Fallback بين providers
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional

from infrastructure.services.ai_agent_service import LLMProvider


@dataclass
class LLMUsage:
    """تتبّع استهلاك الـ LLM."""
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost: float = 0.0
    requests_count: int = 0
    last_request_at: Optional[datetime] = None


class AdvancedOpenAIProvider(LLMProvider):
    """موفّر OpenAI متقدم مع caching و rate limiting و cost tracking.

    Features:
    - Response caching (توفير 30-50% من التكلفة)
    - Rate limiting (10 طلب/دقيقة افتراضي)
    - Cost tracking (تتبّع الإنفاق)
    - Streaming support
    - Fallback provider

    Args:
        api_key: مفتاح OpenAI API.
        model: اسم النموذج.
        temperature: درجة الإبداع.
        max_tokens: الحد الأقصى للـ tokens.
        enable_cache: تفعيل التخزين المؤقت.
        rate_limit_per_minute: حد الطلبات في الدقيقة.
        fallback_provider: provider بديل عند الفشل.
    """

    # Pricing per 1K tokens (USD) — updated 2026
    PRICING = {
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4o": {"input": 0.0025, "output": 0.01},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        enable_cache: bool = True,
        rate_limit_per_minute: int = 10,
        fallback_provider: Optional[LLMProvider] = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._enable_cache = enable_cache
        self._rate_limit = rate_limit_per_minute
        self._fallback = fallback_provider
        self._client = None
        self._cache: dict[str, dict] = {}
        self._request_times: list[float] = []
        self._usage = LLMUsage()

        self._system_prompt = (
            "أنت مساعد محاسبي ذكي لنظام ERP محاسبي عربي. "
            "تجيب باللغة العربية بدقة وإيجاز. "
            "تستخدم Function Calling لتنفيذ الإجراءات. "
            "تطلب تأكيد المستخدم قبل العمليات الحساسة."
        )

    def _get_client(self):
        """الحصول على عميل OpenAI (lazy init)."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self._api_key)
            except ImportError:
                raise ImportError("openai package not installed. Run: pip install openai")
        return self._client

    def _cache_key(self, prompt: str, functions: list = None) -> str:
        """توليد مفتاح cache للطلب."""
        data = f"{prompt}:{json.dumps(functions or [], sort_keys=True)}"
        return hashlib.sha256(data.encode()).hexdigest()

    def _check_rate_limit(self) -> bool:
        """التحقق من rate limit."""
        now = time.time()
        # Remove requests older than 60 seconds
        self._request_times = [t for t in self._request_times if now - t < 60]
        if len(self._request_times) >= self._rate_limit:
            return False
        self._request_times.append(now)
        return True

    def _track_usage(self, response: Any) -> None:
        """تتبّع استهلاك tokens والتكلفة."""
        if hasattr(response, "usage") and response.usage:
            self._usage.total_tokens += response.usage.total_tokens
            self._usage.prompt_tokens += response.usage.prompt_tokens
            self._usage.completion_tokens += response.usage.completion_tokens
            self._usage.requests_count += 1
            self._usage.last_request_at = datetime.now()

            # Calculate cost
            pricing = self.PRICING.get(self._model, {"input": 0.001, "output": 0.002})
            input_cost = (response.usage.prompt_tokens / 1000) * pricing["input"]
            output_cost = (response.usage.completion_tokens / 1000) * pricing["output"]
            self._usage.estimated_cost += input_cost + output_cost

    def generate(self, prompt: str, functions: list[dict] = None) -> dict:
        """توليد استجابة مع caching و rate limiting."""
        # Check cache first
        if self._enable_cache:
            cache_key = self._cache_key(prompt, functions)
            if cache_key in self._cache:
                cached = self._cache[cache_key]
                return cached.copy()

        if not self._api_key:
            # Try fallback
            if self._fallback:
                return self._fallback.generate(prompt, functions)
            return {
                "text": "⚠️ مفتاح OpenAI API غير مُحدّد. أضف OPENAI_API_KEY في .env",
                "function_call": None,
            }

        # Check rate limit
        if not self._check_rate_limit():
            return {
                "text": "⏳ تم تجاوز حد الطلبات. حاول مرة أخرى بعد دقيقة.",
                "function_call": None,
            }

        try:
            client = self._get_client()

            messages = [
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": prompt},
            ]

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

            self._track_usage(response)

            choice = response.choices[0]
            message = choice.message

            result = {"text": message.content or "", "function_call": None}

            if hasattr(message, "tool_calls") and message.tool_calls:
                tool_call = message.tool_calls[0]
                result["function_call"] = {
                    "name": tool_call.function.name,
                    "arguments": json.loads(tool_call.function.arguments),
                }

            # Cache the result
            if self._enable_cache:
                self._cache[cache_key] = result.copy()

            return result

        except Exception as e:
            # Try fallback on error
            if self._fallback:
                return self._fallback.generate(prompt, functions)
            return {"text": f"❌ خطأ: {e}", "function_call": None}

    def generate_stream(
        self,
        prompt: str,
        on_chunk: Callable[[str], None],
        functions: list[dict] = None,
    ) -> dict:
        """توليد استجابة مع streaming (chunk by chunk).

        Args:
            prompt: نص الطلب.
            on_chunk: callback يُستدعى عند كل chunk.
            functions: قائمة الدوال المتاحة.

        Returns: النتيجة النهائية.
        """
        if not self._api_key:
            result = self.generate(prompt, functions)
            on_chunk(result["text"])
            return result

        try:
            client = self._get_client()
            messages = [
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": prompt},
            ]

            stream = client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
                stream=True,
            )

            full_text = ""
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    text = chunk.choices[0].delta.content
                    full_text += text
                    on_chunk(text)

            return {"text": full_text, "function_call": None}

        except Exception as e:
            return {"text": f"❌ خطأ: {e}", "function_call": None}

    def get_usage(self) -> LLMUsage:
        """الحصول على إحصائيات الاستخدام."""
        return self._usage

    def get_usage_report(self) -> str:
        """تقرير الاستخدام كنص."""
        u = self._usage
        return (
            f"📊 تقرير استهلاك LLM:\n"
            f"  الطلبات: {u.requests_count}\n"
            f"  إجمالي Tokens: {u.total_tokens:,}\n"
            f"  Tokens الإدخال: {u.prompt_tokens:,}\n"
            f"  Tokens الإخراج: {u.completion_tokens:,}\n"
            f"  التكلفة التقديرية: ${u.estimated_cost:.4f}\n"
            f"  آخر طلب: {u.last_request_at}"
        )

    def clear_cache(self) -> None:
        """مسح الـ cache."""
        self._cache.clear()

    def is_ready(self) -> bool:
        """هل المفتاح مُعّرف؟"""
        return bool(self._api_key)
