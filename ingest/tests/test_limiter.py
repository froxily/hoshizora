from dataclasses import dataclass, field

import pytest

from hoshizora_ingest.http.limiter import RateLimit, RateLimiter

pytestmark = pytest.mark.anyio


@dataclass
class FakeClock:
    now: float = 1000.0
    sleeps: list[float] = field(default_factory=list[float])

    def __call__(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


async def request(limiter: RateLimiter, clock: FakeClock, *, taking: float = 0) -> None:
    async with limiter.slot():
        clock.now += taking


async def test_allows_a_burst_up_to_the_limit_without_waiting() -> None:
    clock = FakeClock()
    limiter = RateLimiter(RateLimit(requests=3, per_seconds=60), clock=clock, sleep=clock.sleep)

    for _ in range(3):
        await request(limiter, clock)

    assert clock.sleeps == []


async def test_waits_until_the_oldest_request_leaves_the_window() -> None:
    clock = FakeClock()
    limiter = RateLimiter(RateLimit(requests=2, per_seconds=60), clock=clock, sleep=clock.sleep)

    await request(limiter, clock)
    clock.now += 10
    await request(limiter, clock)
    await request(limiter, clock)

    assert clock.sleeps == [50]


async def test_requests_outside_the_window_no_longer_count() -> None:
    clock = FakeClock()
    limiter = RateLimiter(RateLimit(requests=1, per_seconds=60), clock=clock, sleep=clock.sleep)

    await request(limiter, clock)
    clock.now += 61
    await request(limiter, clock)

    assert clock.sleeps == []


async def test_a_slow_request_counts_from_when_its_response_arrives() -> None:
    clock = FakeClock()
    limiter = RateLimiter(RateLimit(requests=1, per_seconds=60), clock=clock, sleep=clock.sleep)

    await request(limiter, clock, taking=34)
    await request(limiter, clock)

    assert clock.sleeps == [60]


async def test_paces_launch_library_at_fifteen_per_hour() -> None:
    clock = FakeClock()
    limiter = RateLimiter(RateLimit(requests=15, per_seconds=3600), clock=clock, sleep=clock.sleep)

    for _ in range(31):
        await request(limiter, clock)

    assert clock.sleeps == [3600, 3600]
