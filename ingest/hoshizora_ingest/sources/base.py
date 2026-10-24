from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol, Self

from psycopg import AsyncConnection

from hoshizora_ingest.http.client import HttpPolicy, HttpResult
from hoshizora_ingest.jsontypes import JsonValue
from hoshizora_ingest.raw.store import Landed, RawPayload

type BodyFormat = Literal["json", "text"]


@dataclass(frozen=True)
class SourceInfo:
    slug: str
    name: str
    credit: str
    cadence: str


@dataclass(frozen=True)
class StoreResult:
    rows_in: int
    rows_changed: int

    def __add__(self, other: Self) -> Self:
        return type(self)(self.rows_in + other.rows_in, self.rows_changed + other.rows_changed)


NOTHING_STORED = StoreResult(0, 0)


class FetchContext(Protocol):
    @property
    def db(self) -> AsyncConnection: ...

    def now(self) -> datetime: ...

    async def sleep(self, seconds: float) -> None: ...

    async def get(
        self,
        endpoint: str,
        params: Mapping[str, str],
        *,
        body: BodyFormat = "json",
        conditional: bool = False,
    ) -> Landed | None: ...

    async def land(self, endpoint: str, body: JsonValue) -> Landed: ...

    async def probe(self, endpoint: str, params: Mapping[str, str]) -> HttpResult: ...

    async def last_fetched_at(
        self, endpoint: str, params: Mapping[str, str]
    ) -> datetime | None: ...


class Source[ParsedT, BatchT](Protocol):
    @property
    def info(self) -> SourceInfo: ...

    @property
    def http_policy(self) -> HttpPolicy: ...

    def fetch(self, ctx: FetchContext) -> AsyncIterator[Landed]: ...

    def parse(self, payload: RawPayload) -> ParsedT: ...

    def normalize(self, parsed: ParsedT) -> BatchT: ...

    async def store(
        self, db: AsyncConnection, batch: BatchT, payload: RawPayload
    ) -> StoreResult: ...
