from collections.abc import AsyncIterator, Mapping
from datetime import date, timedelta

from psycopg import AsyncConnection

from hoshizora_ingest.http.client import HttpPolicy, RetryPolicy
from hoshizora_ingest.http.limiter import RateLimit
from hoshizora_ingest.raw.store import Landed, RawPayload
from hoshizora_ingest.sources.base import FetchContext, SourceInfo, StoreResult
from hoshizora_ingest.sources.jpl.models import (
    CadApproach,
    CadResponse,
    CadWindow,
    SentryRemovals,
    SentrySummary,
    Signature,
)
from hoshizora_ingest.store.small_bodies import store_small_bodies
from hoshizora_ingest.transform.jpl import JplBatch, normalize

BASE_URL = "https://ssd-api.jpl.nasa.gov"
CAD = f"{BASE_URL}/cad.api"
SENTRY = f"{BASE_URL}/sentry.api"
CAD_VERSION = "1.5"
SENTRY_VERSION = "2.0"
BACKFILL_FIRST_YEAR = 1900
BACKFILL_LAST_YEAR = 2200
WINDOW_YEARS = 10
ROLLING_BEFORE = timedelta(days=60)
ROLLING_AFTER = timedelta(days=366)
REFRESH = timedelta(hours=12)
SENTRY_REMOVED = {"removed": "1"}
SENTRY_SUMMARY: dict[str, str] = {}

INFO = SourceInfo(
    slug="jpl",
    name="NASA/JPL SSD close approaches and Sentry",
    credit="Small-body data: NASA/JPL Solar System Dynamics (SBDB Close Approach and Sentry APIs)",
    cadence="close approaches backfilled once by decade, then a rolling window every 12 hours; "
    "Sentry every 12 hours",
)

POLICY = HttpPolicy(
    base_url=BASE_URL,
    rate_limit=RateLimit(requests=1, per_seconds=2),
    retry=RetryPolicy(
        attempts=3,
        statuses=frozenset({429, 500, 502, 503, 504}),
        base_delay_seconds=10,
        max_delay_seconds=600,
    ),
)


class UnsupportedVersionError(Exception):
    pass


def require_version(signature: Signature, expected: str) -> None:
    if signature.version != expected:
        message = f"{signature.source} version {signature.version}; adapter supports {expected}"
        raise UnsupportedVersionError(message)


def cad_params(start: date, end: date) -> dict[str, str]:
    return {
        "date-min": start.isoformat(),
        "date-max": end.isoformat(),
        "dist-max": "0.05",
        "body": "Earth",
        "fullname": "true",
        "diameter": "true",
    }


def decade_windows() -> list[tuple[date, date]]:
    return [
        (date(year, 1, 1), date(year + WINDOW_YEARS, 1, 1))
        for year in range(BACKFILL_FIRST_YEAR, BACKFILL_LAST_YEAR, WINDOW_YEARS)
    ]


def rolling_window(today: date) -> tuple[date, date]:
    return today - ROLLING_BEFORE, today + ROLLING_AFTER


def cad_window(response: CadResponse, params: Mapping[str, str]) -> CadWindow:
    require_version(response.signature, CAD_VERSION)
    approaches = [
        CadApproach.model_validate(dict(zip(response.fields, row, strict=True)))
        for row in response.data
    ]
    return CadWindow(
        date_min=date.fromisoformat(params["date-min"]),
        date_max=date.fromisoformat(params["date-max"]),
        body=params["body"],
        approaches=approaches,
    )


class JplSource:
    @property
    def info(self) -> SourceInfo:
        return INFO

    @property
    def http_policy(self) -> HttpPolicy:
        return POLICY

    async def fetch(self, ctx: FetchContext) -> AsyncIterator[Landed]:
        for start, end in decade_windows():
            params = cad_params(start, end)
            if await ctx.last_fetched_at(CAD, params) is None:
                landed = await ctx.get(CAD, params)
                if landed is not None:
                    yield landed
        start, end = rolling_window(ctx.now().date())
        for endpoint, params in (
            (CAD, cad_params(start, end)),
            (SENTRY, SENTRY_SUMMARY),
            (SENTRY, SENTRY_REMOVED),
        ):
            landed = await self._due(ctx, endpoint, params)
            if landed is not None:
                yield landed

    def parse(self, payload: RawPayload) -> CadWindow | SentrySummary | SentryRemovals:
        if payload.endpoint == CAD:
            return cad_window(CadResponse.model_validate(payload.body), payload.params)
        if payload.params.get("removed") == "1":
            removals = SentryRemovals.model_validate(payload.body)
            require_version(removals.signature, SENTRY_VERSION)
            return removals
        summary = SentrySummary.model_validate(payload.body)
        require_version(summary.signature, SENTRY_VERSION)
        return summary

    def normalize(self, parsed: CadWindow | SentrySummary | SentryRemovals) -> JplBatch:
        return normalize(parsed)

    async def store(self, db: AsyncConnection, batch: JplBatch, payload: RawPayload) -> StoreResult:
        return await store_small_bodies(db, batch, payload.id, SENTRY)

    async def _due(
        self, ctx: FetchContext, endpoint: str, params: Mapping[str, str]
    ) -> Landed | None:
        last = await ctx.last_fetched_at(endpoint, params)
        if last is not None and ctx.now() - last < REFRESH:
            return None
        return await ctx.get(endpoint, params)
