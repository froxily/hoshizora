from datetime import UTC, datetime

import httpx
import pytest
import respx

from hoshizora_ingest.http.client import (
    NO_RETRY,
    HttpPolicy,
    RetryPolicy,
    SourceClient,
    Validators,
    parse_retry_after,
)
from hoshizora_ingest.http.errors import (
    NeedsReviewError,
    QuotaExhaustedError,
    RetryableHttpError,
    SourceHttpError,
)
from hoshizora_ingest.http.limiter import RateLimit

from fakes import BASE_URL, FAST_RETRY, RecordingSleep, Replies

pytestmark = pytest.mark.anyio

USER_AGENT = "Hoshizora/0.1 (+https://github.com/froxily)"


SERVER_ERRORS_ONLY = RetryPolicy(
    attempts=3, statuses=frozenset({503}), base_delay_seconds=0.01, max_delay_seconds=60
)


def policy(
    *, review_on_error: bool = False, retry: bool = True, retry_policy: RetryPolicy = FAST_RETRY
) -> HttpPolicy:
    return HttpPolicy(
        base_url=BASE_URL,
        rate_limit=RateLimit(requests=100, per_seconds=1),
        retry=retry_policy if retry else NO_RETRY,
        review_on_error=review_on_error,
    )


async def test_sends_the_application_user_agent() -> None:
    replies = Replies([httpx.Response(200, json=[])])
    with respx.mock(base_url=BASE_URL) as router:
        router.get("/data").mock(side_effect=replies)
        async with SourceClient(policy(), USER_AGENT) as client:
            await client.get("/data", {})

    assert replies.requests[0].headers["User-Agent"] == USER_AGENT


async def test_sends_conditional_headers_and_returns_not_modified() -> None:
    validators = Validators(etag='"abc"', last_modified="Fri, 16 Oct 2026 05:30:52 GMT")
    replies = Replies([httpx.Response(304)])
    with respx.mock(base_url=BASE_URL) as router:
        router.get("/data").mock(side_effect=replies)
        async with SourceClient(policy(), USER_AGENT) as client:
            result = await client.get("/data", {}, validators)

    headers = replies.requests[0].headers
    assert (headers["If-None-Match"], headers["If-Modified-Since"]) == (
        '"abc"',
        "Fri, 16 Oct 2026 05:30:52 GMT",
    )
    assert result.not_modified


async def test_honours_retry_after_on_throttling() -> None:
    sleep = RecordingSleep()
    with respx.mock(base_url=BASE_URL) as router:
        router.get("/data").mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "7"}),
                httpx.Response(200, json=[]),
            ]
        )
        async with SourceClient(policy(), USER_AGENT, sleep=sleep) as client:
            result = await client.get("/data", {})

    assert result.status == 200
    assert sleep.delays == [7.0]


async def test_gives_up_after_the_last_attempt() -> None:
    with respx.mock(base_url=BASE_URL) as router:
        route = router.get("/data").respond(503)
        async with SourceClient(policy(), USER_AGENT, sleep=RecordingSleep()) as client:
            with pytest.raises(RetryableHttpError):
                await client.get("/data", {})

    assert route.call_count == FAST_RETRY.attempts


async def test_throttling_that_outlasts_the_retries_is_quota_exhaustion() -> None:
    with respx.mock(base_url=BASE_URL) as router:
        route = router.get("/data").respond(429)
        async with SourceClient(policy(), USER_AGENT, sleep=RecordingSleep()) as client:
            with pytest.raises(QuotaExhaustedError):
                await client.get("/data", {})

    assert route.call_count == FAST_RETRY.attempts


async def test_throttling_outside_the_retry_policy_is_returned_to_the_caller_at_once() -> None:
    sleep = RecordingSleep()
    with respx.mock(base_url=BASE_URL) as router:
        route = router.get("/data").respond(429, headers={"Retry-After": "42"})
        async with SourceClient(
            policy(retry_policy=SERVER_ERRORS_ONLY), USER_AGENT, sleep=sleep
        ) as client:
            with pytest.raises(QuotaExhaustedError) as raised:
                await client.get("/data", {})

    assert (route.call_count, raised.value.retry_after, sleep.delays) == (1, 42, [])


async def test_review_policy_raises_on_any_error_status_without_retrying() -> None:
    with respx.mock(base_url=BASE_URL) as router:
        route = router.get("/data").respond(503)
        async with SourceClient(policy(review_on_error=True), USER_AGENT) as client:
            with pytest.raises(NeedsReviewError):
                await client.get("/data", {})

    assert route.call_count == 1


async def test_does_not_follow_redirects() -> None:
    with respx.mock(base_url=BASE_URL) as router:
        router.get("/old").respond(301, headers={"Location": f"{BASE_URL}/new"})
        async with SourceClient(policy(retry=False), USER_AGENT) as client:
            with pytest.raises(SourceHttpError) as raised:
                await client.get("/old", {})

    assert raised.value.status == 301


def test_parses_retry_after_seconds_and_http_dates() -> None:
    now = datetime(2026, 10, 16, 5, 0, 0, tzinfo=UTC)

    assert parse_retry_after("120", now=now) == 120
    assert parse_retry_after("Fri, 16 Oct 2026 05:01:30 GMT", now=now) == 90
    assert parse_retry_after("soon", now=now) is None
    assert parse_retry_after(None, now=now) is None
