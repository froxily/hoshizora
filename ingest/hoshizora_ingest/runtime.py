import asyncio
import sys
from collections.abc import Coroutine
from typing import Any


def event_loop_factory() -> type[asyncio.AbstractEventLoop] | None:
    return asyncio.SelectorEventLoop if sys.platform == "win32" else None


def run[T](main: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(main, loop_factory=event_loop_factory())
