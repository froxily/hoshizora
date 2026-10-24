import asyncio
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
import structlog
from psycopg import AsyncConnection
from pydantic import BaseModel

from hoshizora_ingest.config import ConfigurationError
from hoshizora_ingest.http.client import HttpResult, SourceClient
from hoshizora_ingest.http.errors import (
    NeedsReviewError,
    QuotaExhaustedError,
    RequestBudgetExhaustedError,
    SourceHttpError,
    WaitLimitExceededError,
)
from hoshizora_ingest.jsontypes import JsonValue, parse_json
from hoshizora_ingest.raw.runs import (
    RunStats,
    RunStatus,
    finish_run,
    last_finished_run,
    pinned_origin,
    start_run,
)
from hoshizora_ingest.raw.store import (
    FetchRecord,
    Landed,
    apply_retention,
    land_payload,
    last_fetched_at,
    latest_validators,
    load_payload,
    log_fetch,
    reclaim_payload_space,
)
from hoshizora_ingest.sources.base import BodyFormat, Source
from hoshizora_ingest.sources.model import unexpected_fields
from hoshizora_ingest.store.origins import (
    Pruned,
    canonical_payload_ids,
    foreign_payloads,
    origin_of,
    prune_foreign_rows,
)
from hoshizora_ingest.store.upsert import linking_every_row

log = structlog.get_logger()

INTERRUPTED = "interrupted; the next run resumes from the raw watermark"

type Clock = Callable[[], datetime]
type Sleep = Callable[[float], Awaitable[None]]


def utc_now() -> datetime:
    return datetime.now(UTC)


def bounded(sleep: Sleep, limit: float) -> Sleep:
    async def bounded_sleep(seconds: float) -> None:
        if seconds > limit:
            raise WaitLimitExceededError(seconds, limit)
        await sleep(seconds)

    return bounded_sleep


@dataclass(frozen=True)
class RunEnvironment:
    db: AsyncConnection
    log_db: AsyncConnection
    user_agent: str
    transport: httpx.AsyncBaseTransport | None = None
    clock: Clock = utc_now
    sleep: Sleep = asyncio.sleep


@dataclass(frozen=True)
class RunOutcome:
    run_id: int
    status: RunStatus
    stats: RunStats
    error: str | None

    @property
    def summary(self) -> str:
        stats = self.stats
        summary = (
            f"run {self.run_id} {self.status.value}: {stats.requests} requests, "
            f"{stats.not_modified} not modified, {stats.payloads_new} new payloads, "
            f"{stats.rows_upserted}/{stats.rows_in} rows changed"
        )
        return summary if self.error is None else f"{summary} ({self.error})"


@dataclass(frozen=True)
class Replayed:
    stats: RunStats
    origin: str
    foreign_payloads: int
    pruned: Pruned


@dataclass
class PipelineContext:
    env: RunEnvironment
    http: SourceClient
    source: str
    run_id: int
    stats: RunStats
    max_requests: int | None

    @property
    def db(self) -> AsyncConnection:
        return self.env.db

    def now(self) -> datetime:
        return self.env.clock()

    async def sleep(self, seconds: float) -> None:
        await self.env.sleep(seconds)

    async def get(
        self,
        endpoint: str,
        params: Mapping[str, str],
        *,
        body: BodyFormat = "json",
        conditional: bool = False,
    ) -> Landed | None:
        if self.max_requests is not None and self.stats.requests >= self.max_requests:
            raise RequestBudgetExhaustedError(self.max_requests)
        validators = (
            await latest_validators(self.db, self.source, endpoint, params) if conditional else None
        )
        self.stats.requests += 1
        try:
            result = await self.http.get(endpoint, params, validators)
        except SourceHttpError as rejected:
            await log_fetch(
                self.env.log_db,
                FetchRecord(
                    self.run_id,
                    self.source,
                    endpoint,
                    params,
                    rejected.status,
                    rejected.duration_ms,
                ),
            )
            raise
        landed = (
            None
            if result.not_modified
            else await land_payload(self.db, self.source, endpoint, params, decode(result, body))
        )
        await log_fetch(
            self.db,
            FetchRecord(
                self.run_id,
                self.source,
                endpoint,
                params,
                result.status,
                result.duration_ms,
                result.etag,
                result.last_modified,
                landed.payload.id if landed is not None else None,
            ),
        )
        if landed is None:
            self.stats.not_modified += 1
        elif landed.is_new:
            self.stats.payloads_new += 1
        return landed

    async def land(self, endpoint: str, body: JsonValue) -> Landed:
        landed = await land_payload(self.db, self.source, endpoint, {}, body)
        if landed.is_new:
            self.stats.payloads_new += 1
        return landed

    async def probe(self, endpoint: str, params: Mapping[str, str]) -> HttpResult:
        return await self.http.get(endpoint, params, limited=False)

    async def last_fetched_at(self, endpoint: str, params: Mapping[str, str]) -> datetime | None:
        return await last_fetched_at(self.db, self.source, endpoint, params)


def decode(result: HttpResult, body: BodyFormat) -> JsonValue:
    if body == "text":
        return result.content.decode("utf-8")
    return parse_json(result.content)


async def apply_payload(
    db: AsyncConnection, source: Source[Any, Any], landed: Landed, stats: RunStats
) -> None:
    if not landed.is_new:
        return
    parsed = source.parse(landed.payload)
    if isinstance(parsed, BaseModel):
        stats.unknown_fields |= unexpected_fields(parsed)
    result = await source.store(db, source.normalize(parsed), landed.payload)
    stats.rows_in += result.rows_in
    stats.rows_upserted += result.rows_changed


def source_origin(source: Source[Any, Any]) -> str:
    return origin_of(source.http_policy.base_url)


async def ensure_pinned_origin(db: AsyncConnection, source: Source[Any, Any]) -> str:
    slug, origin = source.info.slug, source_origin(source)
    pinned = await pinned_origin(db, slug)
    if pinned is not None and pinned != origin:
        message = (
            f"This database holds {slug} data from {pinned}, so it refuses {origin}. "
            f"Use a separate database for {origin}."
        )
        raise ConfigurationError(message)
    return origin


KEEPS_RAW_CURRENT = frozenset({RunStatus.SUCCEEDED, RunStatus.PARTIAL})


async def prune_superseded_bodies(env: RunEnvironment, source: str) -> int:
    pruned = await apply_retention(env.db, source, env.clock())
    await env.db.commit()
    if pruned:
        await reclaim_payload_space(env.log_db)
    return pruned


async def held_for_review(db: AsyncConnection, slug: str) -> RunOutcome | None:
    last = await last_finished_run(db, slug)
    if last is None or last.status is not RunStatus.NEEDS_REVIEW:
        return None
    message = f"held: run {last.id} needs review; rerun with --reviewed once it is checked"
    return RunOutcome(last.id, RunStatus.NEEDS_REVIEW, RunStats(), message)


async def run_source(
    source: Source[Any, Any],
    env: RunEnvironment,
    *,
    max_requests: int | None = None,
    reviewed: bool = False,
) -> RunOutcome:
    slug = source.info.slug
    origin = await ensure_pinned_origin(env.log_db, source)
    if not reviewed and (held := await held_for_review(env.log_db, slug)) is not None:
        log.warning("source held for review", source=slug, run_id=held.run_id)
        return held
    run_id = await start_run(env.log_db, slug, origin)
    stats = RunStats()
    status = RunStatus.SUCCEEDED
    error: str | None = None
    try:
        async with SourceClient(
            source.http_policy, env.user_agent, transport=env.transport, sleep=env.sleep
        ) as http:
            ctx = PipelineContext(env, http, slug, run_id, stats, max_requests)
            async for landed in source.fetch(ctx):
                await apply_payload(env.db, source, landed, stats)
                await env.db.commit()
            await env.db.commit()
    except (
        RequestBudgetExhaustedError,
        QuotaExhaustedError,
        WaitLimitExceededError,
    ) as exhausted:
        await env.db.commit()
        status, error = RunStatus.PARTIAL, str(exhausted)
    except NeedsReviewError as review:
        await env.db.rollback()
        status, error = RunStatus.NEEDS_REVIEW, str(review)
    except asyncio.CancelledError, KeyboardInterrupt:
        await env.db.rollback()
        await finish_run(env.log_db, run_id, RunStatus.PARTIAL, stats, INTERRUPTED)
        raise
    except Exception as failure:
        await env.db.rollback()
        await finish_run(env.log_db, run_id, RunStatus.FAILED, stats, repr(failure))
        raise
    pruned = await prune_superseded_bodies(env, slug) if status in KEEPS_RAW_CURRENT else 0
    await finish_run(env.log_db, run_id, status, stats, error)
    if stats.unknown_fields:
        log.warning("unexpected source fields", source=slug, fields=sorted(stats.unknown_fields))
    log.info(
        "run finished",
        source=slug,
        run_id=run_id,
        status=status.value,
        requests=stats.requests,
        not_modified=stats.not_modified,
        payloads_new=stats.payloads_new,
        rows_in=stats.rows_in,
        rows_upserted=stats.rows_upserted,
        bodies_pruned=pruned,
    )
    return RunOutcome(run_id, status, stats, error)


async def replay_source(source: Source[Any, Any], *, db: AsyncConnection) -> Replayed:
    slug = source.info.slug
    origin = await ensure_pinned_origin(db, source)
    foreign = await foreign_payloads(db, slug, origin)
    stats = RunStats()
    with linking_every_row(enabled=foreign > 0):
        for payload_id in await canonical_payload_ids(db, slug, origin):
            landed = Landed(await load_payload(db, payload_id), is_new=True)
            await apply_payload(db, source, landed, stats)
            await db.commit()
    pruned = await prune_foreign_rows(db, slug, origin) if foreign else Pruned()
    await db.commit()
    log.info(
        "replay finished",
        source=slug,
        origin=origin,
        foreign_payloads=foreign,
        deleted=dict(pruned.deleted),
        unlinked=dict(pruned.unlinked),
        links_removed=pruned.links_removed,
    )
    return Replayed(stats, origin, foreign, pruned)
