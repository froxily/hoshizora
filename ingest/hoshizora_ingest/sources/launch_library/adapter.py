from collections.abc import AsyncIterator, Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast

import structlog
from psycopg import AsyncConnection

from hoshizora_ingest.http.client import HttpPolicy, RetryPolicy
from hoshizora_ingest.http.errors import QuotaExhaustedError
from hoshizora_ingest.http.limiter import RateLimit
from hoshizora_ingest.jsontypes import parse_json
from hoshizora_ingest.raw.store import Landed, RawPayload
from hoshizora_ingest.sources.base import FetchContext, SourceInfo, StoreResult
from hoshizora_ingest.sources.launch_library.models import (
    AgencyPage,
    LandingPage,
    LauncherPage,
    LaunchPage,
    Throttle,
)
from hoshizora_ingest.store.launches import store_launches
from hoshizora_ingest.store.organizations import store_agencies
from hoshizora_ingest.store.origins import origin_of
from hoshizora_ingest.store.reusability import store_landings, store_launchers
from hoshizora_ingest.transform.launch_library import (
    AgencyBatch,
    LandingBatch,
    LauncherBatch,
    Ll2Batch,
    Ll2Page,
    normalize,
)

log = structlog.get_logger()

API = "/2.3.0"
PRODUCTION_BASE_URL = "https://ll.thespacedevs.com"
PAGE_SIZE = 100
AGENCY_REFRESH = timedelta(days=7)
LAUNCHER_REFRESH = timedelta(days=1)
INITIAL_WATERMARK = datetime(1950, 1, 1, tzinfo=UTC)
RETRYABLE = frozenset({500, 502, 503, 504})
THROTTLE_CACHE_SECONDS = 60
QUOTA_MARGIN_SECONDS = 1
QUOTA_REJECTIONS = 3

INFO = SourceInfo(
    slug="launch-library",
    name="Launch Library 2 (The Space Devs)",
    credit="Launch data: The Space Devs, Launch Library 2 (thespacedevs.com)",
    cadence="incremental by last_updated; production allows 15 requests per hour",
)

LAST_FULL_SWEEP = """
SELECT max(f.requested_at)
FROM raw.fetch f
JOIN raw.payload p ON p.id = f.payload_id
WHERE f.source = %s AND f.endpoint = %s AND p.body IS NOT NULL AND p.body ->> 'next' IS NULL
"""

LANDING_RESUME_OFFSET = """
SELECT coalesce(max((f.params ->> 'offset')::integer), 0)
FROM raw.fetch f
WHERE f.source = %s AND f.endpoint = %s AND f.payload_id IS NOT NULL
"""

SETTLED_LANDINGS = """
SELECT ll2_id FROM core.landing WHERE success IS NOT NULL OR NOT attempt
"""

LAUNCH_WATERMARK = """
SELECT max((launch ->> 'last_updated')::timestamptz)
FROM raw.payload p
CROSS JOIN LATERAL jsonb_array_elements(p.body -> 'results') AS launch
WHERE p.source = %s AND p.endpoint = %s
"""


def iso(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def launch_params(watermark: datetime, offset: int, page_size: int) -> dict[str, str]:
    return {
        "mode": "normal",
        "ordering": "last_updated",
        "last_updated__gte": iso(watermark),
        "limit": str(page_size),
        "offset": str(offset),
    }


def agency_params(offset: int, page_size: int) -> dict[str, str]:
    return {"mode": "normal", "ordering": "id", "limit": str(page_size), "offset": str(offset)}


def launcher_params(offset: int, page_size: int) -> dict[str, str]:
    return {"mode": "detailed", "ordering": "id", "limit": str(page_size), "offset": str(offset)}


def landing_params(offset: int, page_size: int) -> dict[str, str]:
    return {"mode": "list", "ordering": "-id", "limit": str(page_size), "offset": str(offset)}


def landings_settled(page: LandingPage, settled: frozenset[int]) -> bool:
    return all(landing.id in settled for landing in page.results if landing.firststage is not None)


def next_page(landed: Landed) -> str | None:
    body = landed.payload.body
    if not isinstance(body, dict):
        return None
    following = body.get("next")
    return following if isinstance(following, str) else None


def quota_cooldown(retry_after: float | None) -> float:
    return max(retry_after or 0.0, THROTTLE_CACHE_SECONDS) + QUOTA_MARGIN_SECONDS


@dataclass(frozen=True)
class Quota:
    available: int
    wait_seconds: float


def quota(throttle: Throttle) -> Quota:
    available = max(0, throttle.your_request_limit - throttle.current_use)
    wait = 0.0 if available else float(throttle.next_use_secs + QUOTA_MARGIN_SECONDS)
    return Quota(available, wait)


def next_launch_window(
    watermark: datetime, offset: int, page: LaunchPage, page_size: int
) -> tuple[datetime, int] | None:
    if len(page.results) < page_size:
        return None
    newest = max(launch.last_updated for launch in page.results)
    if newest > watermark:
        return newest, 0
    return watermark, offset + page_size


class LaunchLibrarySource:
    def __init__(self, base_url: str, *, page_size: int = PAGE_SIZE) -> None:
        self._base_url = base_url.rstrip("/")
        self._page_size = page_size

    @property
    def info(self) -> SourceInfo:
        return INFO

    @property
    def production(self) -> bool:
        return origin_of(self._base_url) == PRODUCTION_BASE_URL

    @property
    def http_policy(self) -> HttpPolicy:
        if self.production:
            return HttpPolicy(
                base_url=self._base_url,
                rate_limit=RateLimit(requests=15, per_seconds=3600),
                retry=RetryPolicy(
                    attempts=4, statuses=RETRYABLE, base_delay_seconds=30, max_delay_seconds=3600
                ),
            )
        return HttpPolicy(
            base_url=self._base_url,
            rate_limit=RateLimit(requests=2, per_seconds=1),
            retry=RetryPolicy(
                attempts=4, statuses=RETRYABLE, base_delay_seconds=2, max_delay_seconds=60
            ),
        )

    @property
    def launches_endpoint(self) -> str:
        return f"{self._base_url}{API}/launches/"

    @property
    def agencies_endpoint(self) -> str:
        return f"{self._base_url}{API}/agencies/"

    @property
    def launchers_endpoint(self) -> str:
        return f"{self._base_url}{API}/launchers/"

    @property
    def landings_endpoint(self) -> str:
        return f"{self._base_url}{API}/landings/"

    @property
    def throttle_endpoint(self) -> str:
        return f"{self._base_url}{API}/api-throttle/"

    async def fetch(self, ctx: FetchContext) -> AsyncIterator[Landed]:
        async for landed in self._agencies(ctx):
            yield landed
        async for landed in self._launches(ctx):
            yield landed
        async for landed in self._launchers(ctx):
            yield landed
        async for landed in self._landings(ctx):
            yield landed

    def parse(self, payload: RawPayload) -> Ll2Page:
        endpoint = payload.endpoint
        if endpoint.endswith("/agencies/"):
            return AgencyPage.model_validate(payload.body)
        if endpoint.endswith("/launchers/"):
            return LauncherPage.model_validate(payload.body)
        if endpoint.endswith("/landings/"):
            return LandingPage.model_validate(payload.body)
        return LaunchPage.model_validate(payload.body)

    def normalize(self, parsed: Ll2Page) -> Ll2Batch:
        return normalize(parsed)

    async def store(self, db: AsyncConnection, batch: Ll2Batch, payload: RawPayload) -> StoreResult:
        match batch:
            case AgencyBatch():
                return await store_agencies(db, batch.agencies, payload.id)
            case LauncherBatch():
                return await store_launchers(db, batch, payload.id)
            case LandingBatch():
                return await store_landings(db, batch, payload.id)
            case _:
                return await store_launches(db, batch, payload.id)

    async def watermark(self, db: AsyncConnection) -> datetime:
        async with db.cursor() as cursor:
            await cursor.execute(LAUNCH_WATERMARK, (INFO.slug, self.launches_endpoint))
            row = await cursor.fetchone()
        newest = cast("datetime | None", row[0]) if row is not None else None
        return newest or INITIAL_WATERMARK

    async def last_full_sweep(self, db: AsyncConnection, endpoint: str) -> datetime | None:
        async with db.cursor() as cursor:
            await cursor.execute(LAST_FULL_SWEEP, (INFO.slug, endpoint))
            row = await cursor.fetchone()
        return cast("datetime | None", row[0]) if row is not None else None

    async def landing_resume_offset(self, db: AsyncConnection) -> int:
        async with db.cursor() as cursor:
            await cursor.execute(LANDING_RESUME_OFFSET, (INFO.slug, self.landings_endpoint))
            row = await cursor.fetchone()
        return cast("int", row[0]) if row is not None else 0

    async def settled_landings(self, db: AsyncConnection) -> frozenset[int]:
        async with db.cursor() as cursor:
            await cursor.execute(SETTLED_LANDINGS)
            rows = await cursor.fetchall()
        return frozenset(cast("int", row[0]) for row in rows)

    async def _agencies(self, ctx: FetchContext) -> AsyncIterator[Landed]:
        async for landed in self._sweep(ctx, self.agencies_endpoint, agency_params, AGENCY_REFRESH):
            yield landed

    async def _launchers(self, ctx: FetchContext) -> AsyncIterator[Landed]:
        endpoint = self.launchers_endpoint
        async for landed in self._sweep(ctx, endpoint, launcher_params, LAUNCHER_REFRESH):
            yield landed

    async def _sweep(
        self,
        ctx: FetchContext,
        endpoint: str,
        params_at: Callable[[int, int], dict[str, str]],
        refresh: timedelta,
    ) -> AsyncIterator[Landed]:
        last = await self.last_full_sweep(ctx.db, endpoint)
        if last is not None and ctx.now() - last < refresh:
            return
        offset = 0
        while True:
            landed = await self._get(ctx, endpoint, params_at(offset, self._page_size))
            if landed is None:
                return
            yield landed
            if next_page(landed) is None:
                return
            offset += self._page_size

    async def _landings(self, ctx: FetchContext) -> AsyncIterator[Landed]:
        endpoint = self.landings_endpoint
        caught_up = await self.last_full_sweep(ctx.db, endpoint) is not None
        settled = await self.settled_landings(ctx.db) if caught_up else frozenset[int]()
        offset = 0 if caught_up else await self.landing_resume_offset(ctx.db)
        while True:
            landed = await self._get(ctx, endpoint, landing_params(offset, self._page_size))
            if landed is None:
                return
            yield landed
            page = LandingPage.model_validate(landed.payload.body)
            if page.next is None or (caught_up and landings_settled(page, settled)):
                return
            offset += self._page_size

    async def _launches(self, ctx: FetchContext) -> AsyncIterator[Landed]:
        watermark, offset = await self.watermark(ctx.db), 0
        while True:
            params = launch_params(watermark, offset, self._page_size)
            landed = await self._get(ctx, self.launches_endpoint, params)
            if landed is None:
                return
            yield landed
            page = LaunchPage.model_validate(landed.payload.body)
            window = next_launch_window(watermark, offset, page, self._page_size)
            if window is None:
                return
            watermark, offset = window

    async def _get(
        self, ctx: FetchContext, endpoint: str, params: Mapping[str, str]
    ) -> Landed | None:
        rejections = 0
        while True:
            await self._respect_quota(ctx)
            try:
                return await ctx.get(endpoint, params)
            except QuotaExhaustedError as rejected:
                rejections += 1
                if rejections == QUOTA_REJECTIONS:
                    raise
                wait = quota_cooldown(rejected.retry_after)
                log.warning(
                    "quota exhausted",
                    source=INFO.slug,
                    url=rejected.url,
                    rejections=rejections,
                    wait_seconds=wait,
                )
                await ctx.sleep(wait)

    async def _respect_quota(self, ctx: FetchContext) -> None:
        if not self.production:
            return
        result = await ctx.probe(self.throttle_endpoint, {})
        wait = quota(Throttle.model_validate(parse_json(result.content))).wait_seconds
        if wait:
            await ctx.sleep(wait)
