"""
Async Worker - مشترك بين كل الشاشات

يُشغّل coroutines في thread منفصل لعدم تجميد الواجهة.
"""
from __future__ import annotations

import asyncio
from typing import Callable, Awaitable, Any

from PySide6.QtCore import QThread, Signal


class AsyncWorker(QThread):
    """Generic async worker that runs a coroutine in background."""

    finished_signal = Signal(object)  # result or None
    error_signal = Signal(str)        # error message

    def __init__(self, coro_factory: Callable[[], Awaitable[Any]]) -> None:
        super().__init__()
        self._coro_factory = coro_factory

    def run(self) -> None:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._coro_factory())
            self.finished_signal.emit(result)
        except Exception as e:
            self.error_signal.emit(str(e))
        finally:
            try:
                loop.close()
            except Exception as e:
                # Silent fail - UI initialization should not crash
                # In production: use logger.warning(f"UI init error: {e}")
                pass
