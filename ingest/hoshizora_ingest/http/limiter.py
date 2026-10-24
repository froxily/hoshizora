import asyncio
import time
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass

type Clock = Callable[[], float]
type Sleep = Callable[[float], Awaitable[None]]


@dataclass(frozen=True)
class RateLimit:
    requests: int
    per_seconds: float


@dataclass
class Slot:
    counted_at: float


class RateLimiter:
    def __init__(
        self,
        limit: RateLimit,
        *,
        clock: Clock = time.monotonic,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self._limit = limit
        self._clock = clock
        self._sleep = sleep
        self._slots: list[Slot] = []
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def slot(self) -> AsyncGenerator[None]:
        async with self._lock:
            held = Slot(await self._wait_for_room())
            self._slots.append(held)
        try:
            yield
        finally:
            held.counted_at = self._clock()

    async def _wait_for_room(self) -> float:
        now = self._evict_expired()
        if len(self._slots) >= self._limit.requests:
            oldest = min(slot.counted_at for slot in self._slots)
            await self._sleep(oldest + self._limit.per_seconds - now)
            now = self._evict_expired()
        return now

    def _evict_expired(self) -> float:
        now = self._clock()
        horizon = now - self._limit.per_seconds
        self._slots = [slot for slot in self._slots if slot.counted_at > horizon]
        return now
