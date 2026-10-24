from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import LiteralString, cast

import httpx
import psycopg
from psycopg import AsyncConnection
from pydantic import TypeAdapter

from hoshizora_ingest.http.client import HttpPolicy, RetryPolicy
from hoshizora_ingest.http.limiter import RateLimit
from hoshizora_ingest.raw.store import Landed, RawPayload
from hoshizora_ingest.sources.base import FetchContext, SourceInfo, StoreResult
from hoshizora_ingest.store.upsert import Column, TableSpec, upsert_with_lineage

BASE_URL = "https://example.test"
FAST_RETRY = RetryPolicy(
    attempts=3, statuses=frozenset({429, 503}), base_delay_seconds=0.01, max_delay_seconds=60
)


@dataclass(frozen=True)
class ProbeItem:
    id: int
    name: str


PROBE_ITEMS = TableSpec(
    schema="core",
    name="probe_item",
    columns=(Column("id", "integer"), Column("name", "text")),
    key=("id",),
)
PROBE_PAGE = TypeAdapter(list[ProbeItem])


@dataclass
class ProbeSource:
    pages: int = 1
    conditional: bool = False
    review_on_error: bool = False
    base_url: str = BASE_URL

    @property
    def info(self) -> SourceInfo:
        return SourceInfo(slug="probe", name="Probe", credit="Test data", cadence="on demand")

    @property
    def http_policy(self) -> HttpPolicy:
        return HttpPolicy(
            base_url=self.base_url,
            rate_limit=RateLimit(requests=100, per_seconds=1),
            retry=FAST_RETRY,
            review_on_error=self.review_on_error,
        )

    async def fetch(self, ctx: FetchContext) -> AsyncIterator[Landed]:
        for page in range(1, self.pages + 1):
            landed = await ctx.get("/items", {"page": str(page)}, conditional=self.conditional)
            if landed is not None:
                yield landed

    def parse(self, payload: RawPayload) -> list[ProbeItem]:
        return PROBE_PAGE.validate_python(payload.body)

    def normalize(self, parsed: list[ProbeItem]) -> list[ProbeItem]:
        return parsed

    async def store(
        self, db: AsyncConnection, batch: list[ProbeItem], payload: RawPayload
    ) -> StoreResult:
        return await upsert_with_lineage(db, PROBE_ITEMS, batch, payload.id)


@dataclass
class Replies:
    responses: list[httpx.Response]
    requests: list[httpx.Request] = field(default_factory=list[httpx.Request])

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.responses[len(self.requests) - 1]


@dataclass
class RecordingSleep:
    delays: list[float] = field(default_factory=list[float])

    async def __call__(self, seconds: float) -> None:
        self.delays.append(seconds)


def query(url: str, statement: str) -> list[tuple[object, ...]]:
    with psycopg.connect(url) as connection:
        return connection.execute(cast("LiteralString", statement)).fetchall()


def execute(url: str, statement: str, params: tuple[object, ...]) -> list[tuple[object, ...]]:
    with psycopg.connect(url) as connection:
        return connection.execute(cast("LiteralString", statement), params).fetchall()


def scalar(url: str, statement: str) -> object:
    return query(url, statement)[0][0]
