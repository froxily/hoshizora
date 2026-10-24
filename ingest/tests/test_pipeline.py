import asyncio
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx
import pytest
import respx

from hoshizora_ingest.config import ConfigurationError
from hoshizora_ingest.db import connections
from hoshizora_ingest.http.errors import RetryableHttpError, SourceHttpError
from hoshizora_ingest.pipeline import (
    RunEnvironment,
    RunOutcome,
    bounded,
    replay_source,
    run_source,
)
from hoshizora_ingest.raw.runs import RunStatus
from hoshizora_ingest.raw.store import Landed, last_fetched_at
from hoshizora_ingest.sources.base import FetchContext

from conftest import Database
from fakes import BASE_URL, FAST_RETRY, ProbeSource, RecordingSleep, Replies, query, scalar

pytestmark = pytest.mark.anyio

ITEMS = [{"id": 1, "name": "Hayabusa"}, {"id": 2, "name": "Hayabusa2"}]
FETCH_LOG = (
    "SELECT params ->> 'page', http_status, payload_id IS NOT NULL FROM raw.fetch ORDER BY id"
)


async def run_probe(
    database: Database,
    source: ProbeSource,
    *,
    max_requests: int | None = None,
    reviewed: bool = False,
    max_wait: float | None = None,
) -> RunOutcome:
    sleep = RecordingSleep()
    async with connections(database.writer_url) as db:
        env = RunEnvironment(
            db=db.data,
            log_db=db.log,
            user_agent="Hoshizora/test",
            sleep=sleep if max_wait is None else bounded(sleep, max_wait),
        )
        return await run_source(source, env, max_requests=max_requests, reviewed=reviewed)


async def test_first_run_lands_payload_and_upserts_rows(clean_database: Database) -> None:
    with respx.mock(base_url=BASE_URL) as router:
        router.get("/items", params={"page": "1"}).respond(json=ITEMS)
        outcome = await run_probe(clean_database, ProbeSource())

    assert outcome.status is RunStatus.SUCCEEDED
    assert (outcome.stats.payloads_new, outcome.stats.rows_upserted) == (1, 2)
    assert query(clean_database.owner_url, "SELECT id, name FROM core.probe_item ORDER BY id") == [
        (1, "Hayabusa"),
        (2, "Hayabusa2"),
    ]
    assert scalar(clean_database.owner_url, "SELECT count(*) FROM core.source_record") == 2
    assert scalar(clean_database.owner_url, "SELECT status FROM raw.ingest_run") == "succeeded"


async def test_rerun_with_identical_content_changes_nothing(clean_database: Database) -> None:
    with respx.mock(base_url=BASE_URL) as router:
        router.get("/items").respond(json=ITEMS)
        await run_probe(clean_database, ProbeSource())
        second = await run_probe(clean_database, ProbeSource())

    assert (second.stats.requests, second.stats.payloads_new, second.stats.rows_upserted) == (
        1,
        0,
        0,
    )
    assert scalar(clean_database.owner_url, "SELECT count(*) FROM raw.payload") == 1
    assert scalar(clean_database.owner_url, "SELECT count(*) FROM raw.fetch") == 2


async def test_changed_content_rewrites_only_changed_rows(clean_database: Database) -> None:
    renamed = [ITEMS[0], {"id": 2, "name": "Hayabusa 2"}]
    with respx.mock(base_url=BASE_URL) as router:
        router.get("/items").mock(
            side_effect=[httpx.Response(200, json=ITEMS), httpx.Response(200, json=renamed)]
        )
        await run_probe(clean_database, ProbeSource())
        second = await run_probe(clean_database, ProbeSource())

    assert second.stats.rows_upserted == 1
    assert query(
        clean_database.owner_url,
        "SELECT entity_key, count(*) FROM core.source_record GROUP BY 1 ORDER BY 1",
    ) == [("1", 1), ("2", 2)]


async def test_conditional_request_sends_validators_and_skips_unchanged(
    clean_database: Database,
) -> None:
    replies = Replies(
        [httpx.Response(200, json=ITEMS, headers={"ETag": '"v1"'}), httpx.Response(304)]
    )
    with respx.mock(base_url=BASE_URL) as router:
        router.get("/items").mock(side_effect=replies)
        await run_probe(clean_database, ProbeSource(conditional=True))
        second = await run_probe(clean_database, ProbeSource(conditional=True))

    assert "If-None-Match" not in replies.requests[0].headers
    assert replies.requests[1].headers["If-None-Match"] == '"v1"'
    assert (second.stats.not_modified, second.stats.payloads_new) == (1, 0)


async def test_request_budget_ends_the_run_as_partial_and_keeps_finished_pages(
    clean_database: Database,
) -> None:
    with respx.mock(base_url=BASE_URL) as router:
        router.get("/items", params={"page": "1"}).respond(json=ITEMS[:1])
        router.get("/items", params={"page": "2"}).respond(json=ITEMS[1:])
        outcome = await run_probe(clean_database, ProbeSource(pages=3), max_requests=2)

    assert outcome.status is RunStatus.PARTIAL
    assert scalar(clean_database.owner_url, "SELECT count(*) FROM core.probe_item") == 2


async def test_review_policy_stops_on_first_error_without_retrying(
    clean_database: Database,
) -> None:
    with respx.mock(base_url=BASE_URL) as router:
        route = router.get("/items").respond(403)
        outcome = await run_probe(clean_database, ProbeSource(review_on_error=True))

    assert outcome.status is RunStatus.NEEDS_REVIEW
    assert route.call_count == 1
    assert scalar(clean_database.owner_url, "SELECT error FROM raw.ingest_run") == (
        "HTTP 403 from https://example.test/items?page=1"
    )
    assert query(clean_database.owner_url, FETCH_LOG) == [("1", 403, False)]


async def test_retryable_status_is_retried(clean_database: Database) -> None:
    with respx.mock(base_url=BASE_URL) as router:
        route = router.get("/items").mock(
            side_effect=[httpx.Response(503), httpx.Response(200, json=ITEMS)]
        )
        outcome = await run_probe(clean_database, ProbeSource())

    assert outcome.status is RunStatus.SUCCEEDED
    assert route.call_count == 2


async def test_quota_exhaustion_ends_the_run_partial_and_keeps_landed_pages(
    clean_database: Database,
) -> None:
    with respx.mock(base_url=BASE_URL) as router:
        router.get("/items", params={"page": "1"}).respond(json=ITEMS)
        router.get("/items", params={"page": "2"}).respond(429)
        outcome = await run_probe(clean_database, ProbeSource(pages=2))

    assert outcome.status is RunStatus.PARTIAL
    assert outcome.error == "HTTP 429 from https://example.test/items?page=2"
    assert scalar(clean_database.owner_url, "SELECT status FROM raw.ingest_run") == "partial"
    assert scalar(clean_database.owner_url, "SELECT count(*) FROM core.probe_item") == 2
    assert query(clean_database.owner_url, FETCH_LOG) == [("1", 200, True), ("2", 429, False)]


async def test_unexpected_status_fails_the_run_and_raises(clean_database: Database) -> None:
    with respx.mock(base_url=BASE_URL) as router:
        router.get("/items").respond(404)
        with pytest.raises(SourceHttpError):
            await run_probe(clean_database, ProbeSource())

    assert scalar(clean_database.owner_url, "SELECT status FROM raw.ingest_run") == "failed"
    assert scalar(clean_database.owner_url, "SELECT count(*) FROM raw.payload") == 0


async def test_a_server_error_that_outlasts_the_retries_is_logged_although_the_run_fails(
    clean_database: Database,
) -> None:
    with respx.mock(base_url=BASE_URL) as router:
        router.get("/items", params={"page": "1"}).respond(json=ITEMS)
        route = router.get("/items", params={"page": "2"}).respond(503)
        with pytest.raises(RetryableHttpError):
            await run_probe(clean_database, ProbeSource(pages=2))

    assert route.call_count == FAST_RETRY.attempts
    assert scalar(clean_database.owner_url, "SELECT status FROM raw.ingest_run") == "failed"
    assert query(clean_database.owner_url, FETCH_LOG) == [("1", 200, True), ("2", 503, False)]


async def test_a_rejection_leaves_validators_and_the_last_fetch_time_unchanged(
    clean_database: Database,
) -> None:
    replies = Replies(
        [
            httpx.Response(200, json=ITEMS, headers={"ETag": '"v1"'}),
            *[httpx.Response(429)] * FAST_RETRY.attempts,
            httpx.Response(304),
        ]
    )
    with respx.mock(base_url=BASE_URL) as router:
        router.get("/items").mock(side_effect=replies)
        await run_probe(clean_database, ProbeSource(conditional=True))
        rejected = await run_probe(clean_database, ProbeSource(conditional=True))
        async with connections(clean_database.writer_url) as db:
            fetched_at = await last_fetched_at(db.data, "probe", "/items", {"page": "1"})
        resumed = await run_probe(clean_database, ProbeSource(conditional=True))

    accepted_at = scalar(
        clean_database.owner_url, "SELECT requested_at FROM raw.fetch WHERE http_status = 200"
    )
    assert rejected.status is RunStatus.PARTIAL
    assert fetched_at == accepted_at
    assert replies.requests[-1].headers["If-None-Match"] == '"v1"'
    assert resumed.stats.not_modified == 1
    assert query(clean_database.owner_url, FETCH_LOG) == [
        ("1", 200, True),
        ("1", 429, False),
        ("1", 304, False),
    ]


async def test_replay_rebuilds_core_from_raw(clean_database: Database) -> None:
    with respx.mock(base_url=BASE_URL) as router:
        router.get("/items").respond(json=ITEMS)
        await run_probe(clean_database, ProbeSource())
    query(clean_database.owner_url, "DELETE FROM core.probe_item RETURNING id")

    async with connections(clean_database.writer_url) as db:
        replayed = await replay_source(ProbeSource(), db=db.data)

    assert replayed.stats.rows_upserted == 2
    assert replayed.foreign_payloads == 0
    assert scalar(clean_database.owner_url, "SELECT count(*) FROM core.probe_item") == 2


async def test_a_run_records_the_origin_it_fetches_from(clean_database: Database) -> None:
    with respx.mock(base_url=BASE_URL) as router:
        router.get("/items").respond(json=ITEMS)
        await run_probe(clean_database, ProbeSource())

    assert query(clean_database.owner_url, "SELECT origin FROM raw.ingest_run") == [
        ("https://example.test",)
    ]


async def test_a_source_refuses_an_origin_other_than_the_one_that_first_fed_it(
    clean_database: Database,
) -> None:
    with respx.mock(base_url=BASE_URL) as router:
        router.get("/items").respond(json=ITEMS)
        await run_probe(clean_database, ProbeSource())

    other = "https://dev.example.test"
    with respx.mock(base_url=other, assert_all_called=False) as router:
        route = router.get("/items").respond(json=ITEMS)
        with pytest.raises(ConfigurationError, match=re.escape("refuses https://dev.example.test")):
            await run_probe(clean_database, ProbeSource(base_url=other))
        async with connections(clean_database.writer_url) as db:
            with pytest.raises(ConfigurationError):
                await replay_source(ProbeSource(base_url=other), db=db.data)

    assert not route.called
    assert scalar(clean_database.owner_url, "SELECT count(*) FROM raw.ingest_run") == 1


@dataclass
class InterruptedProbe(ProbeSource):
    async def fetch(self, ctx: FetchContext) -> AsyncIterator[Landed]:
        async for landed in super().fetch(ctx):
            yield landed
        raise asyncio.CancelledError


async def test_an_interrupted_run_keeps_its_pages_and_closes_as_partial(
    clean_database: Database,
) -> None:
    with respx.mock(base_url=BASE_URL) as router:
        router.get("/items").respond(json=ITEMS)
        with pytest.raises(asyncio.CancelledError):
            await run_probe(clean_database, InterruptedProbe())

    assert query(clean_database.owner_url, "SELECT status, error FROM raw.ingest_run") == [
        ("partial", "interrupted; the next run resumes from the raw watermark")
    ]
    assert scalar(clean_database.owner_url, "SELECT count(*) FROM core.probe_item") == 2


async def test_a_source_whose_last_run_needs_review_is_held(clean_database: Database) -> None:
    with respx.mock(base_url=BASE_URL) as router:
        route = router.get("/items").mock(
            side_effect=[httpx.Response(403), httpx.Response(200, json=ITEMS)]
        )
        first = await run_probe(clean_database, ProbeSource(review_on_error=True))
        held = await run_probe(clean_database, ProbeSource(review_on_error=True))

    assert (held.status, held.run_id, held.stats.requests) == (
        RunStatus.NEEDS_REVIEW,
        first.run_id,
        0,
    )
    assert held.error is not None
    assert "--reviewed" in held.error
    assert route.call_count == 1
    assert scalar(clean_database.owner_url, "SELECT count(*) FROM raw.ingest_run") == 1


async def test_a_reviewed_run_resumes_a_held_source(clean_database: Database) -> None:
    with respx.mock(base_url=BASE_URL) as router:
        router.get("/items").mock(
            side_effect=[httpx.Response(403)] + [httpx.Response(200, json=ITEMS)] * 2
        )
        await run_probe(clean_database, ProbeSource(review_on_error=True))
        resumed = await run_probe(clean_database, ProbeSource(review_on_error=True), reviewed=True)
        after = await run_probe(clean_database, ProbeSource(review_on_error=True))

    assert (resumed.status, after.status) == (RunStatus.SUCCEEDED, RunStatus.SUCCEEDED)


async def test_a_wait_over_the_limit_ends_the_run_as_partial(clean_database: Database) -> None:
    with respx.mock(base_url=BASE_URL) as router:
        router.get("/items", params={"page": "1"}).respond(json=ITEMS[:1])
        router.get("/items", params={"page": "2"}).respond(503, headers={"Retry-After": "50"})
        outcome = await run_probe(clean_database, ProbeSource(pages=2), max_wait=10)

    assert outcome.status is RunStatus.PARTIAL
    assert outcome.error == "Would wait 50 s, over the 10 s limit"
    assert scalar(clean_database.owner_url, "SELECT count(*) FROM core.probe_item") == 1
