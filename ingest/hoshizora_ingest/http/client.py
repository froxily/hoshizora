import asyncio
import time
from collections.abc import Mapping
from contextlib import AbstractAsyncContextManager, nullcontext
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from types import TracebackType
from typing import Self

import httpx
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from hoshizora_ingest.http.errors import (
    NeedsReviewError,
    QuotaExhaustedError,
    RetryableHttpError,
    SourceHttpError,
)
from hoshizora_ingest.http.limiter import RateLimit, RateLimiter, Sleep

OK = 200
NOT_MODIFIED = 304
TOO_MANY_REQUESTS = 429
ACCEPTED_STATUSES = frozenset({OK, NOT_MODIFIED})


@dataclass(frozen=True)
class RetryPolicy:
    attempts: int
    statuses: frozenset[int]
    base_delay_seconds: float
    max_delay_seconds: float


NO_RETRY = RetryPolicy(attempts=1, statuses=frozenset(), base_delay_seconds=0, max_delay_seconds=0)


@dataclass(frozen=True)
class HttpPolicy:
    base_url: str
    rate_limit: RateLimit
    retry: RetryPolicy
    review_on_error: bool = False
    timeout_seconds: float = 120


@dataclass(frozen=True)
class Validators:
    etag: str | None
    last_modified: str | None

    def headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.etag is not None:
            headers["If-None-Match"] = self.etag
        if self.last_modified is not None:
            headers["If-Modified-Since"] = self.last_modified
        return headers


@dataclass(frozen=True)
class HttpResult:
    status: int
    url: str
    content: bytes
    etag: str | None
    last_modified: str | None
    duration_ms: int

    @property
    def not_modified(self) -> bool:
        return self.status == NOT_MODIFIED


def parse_retry_after(value: str | None, *, now: datetime) -> float | None:
    if value is None:
        return None
    if value.strip().isdigit():
        return float(value)
    try:
        moment = parsedate_to_datetime(value)
    except TypeError, ValueError:
        return None
    return max((moment - now).total_seconds(), 0.0)


class SourceClient:
    def __init__(
        self,
        policy: HttpPolicy,
        user_agent: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self._policy = policy
        self._sleep = sleep
        self._limiter = RateLimiter(policy.rate_limit, sleep=sleep)
        self._backoff = wait_exponential_jitter(
            multiplier=policy.retry.base_delay_seconds,
            jitter=policy.retry.base_delay_seconds,
            max=policy.retry.max_delay_seconds,
        )
        self._http = httpx.AsyncClient(
            base_url=policy.base_url,
            headers={"User-Agent": user_agent, "Accept-Encoding": "gzip"},
            timeout=policy.timeout_seconds,
            transport=transport,
            follow_redirects=False,
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._http.aclose()

    async def get(
        self,
        endpoint: str,
        params: Mapping[str, str],
        validators: Validators | None = None,
        *,
        limited: bool = True,
    ) -> HttpResult:
        retrying = AsyncRetrying(
            stop=stop_after_attempt(self._policy.retry.attempts),
            wait=self._wait,
            retry=retry_if_exception(self._retryable),
            sleep=self._sleep,
            reraise=True,
        )
        return await retrying(self._attempt, endpoint, params, validators, limited=limited)

    async def _attempt(
        self,
        endpoint: str,
        params: Mapping[str, str],
        validators: Validators | None,
        *,
        limited: bool,
    ) -> HttpResult:
        headers = validators.headers() if validators is not None else {}
        async with self._slot(limited=limited):
            started = time.perf_counter()
            response = await self._http.get(endpoint, params=dict(params), headers=headers)
            duration_ms = round((time.perf_counter() - started) * 1000)
        url = str(response.url)
        if response.status_code in ACCEPTED_STATUSES:
            return HttpResult(
                status=response.status_code,
                url=url,
                content=response.content,
                etag=response.headers.get("ETag"),
                last_modified=response.headers.get("Last-Modified"),
                duration_ms=duration_ms,
            )
        status = response.status_code
        if self._policy.review_on_error:
            raise NeedsReviewError(status, url, duration_ms=duration_ms)
        retry_after = parse_retry_after(response.headers.get("Retry-After"), now=datetime.now(UTC))
        if status == TOO_MANY_REQUESTS:
            raise QuotaExhaustedError(status, url, retry_after, duration_ms=duration_ms)
        if status in self._policy.retry.statuses:
            raise RetryableHttpError(status, url, retry_after, duration_ms=duration_ms)
        raise SourceHttpError(status, url, duration_ms=duration_ms)

    def _slot(self, *, limited: bool) -> AbstractAsyncContextManager[None]:
        return self._limiter.slot() if limited else nullcontext()

    def _retryable(self, error: BaseException) -> bool:
        if isinstance(error, RetryableHttpError):
            return error.status in self._policy.retry.statuses
        return isinstance(error, httpx.TransportError)

    def _wait(self, state: RetryCallState) -> float:
        exception = state.outcome.exception() if state.outcome is not None else None
        if isinstance(exception, RetryableHttpError) and exception.retry_after is not None:
            return min(exception.retry_after, self._policy.retry.max_delay_seconds)
        return self._backoff(state)
