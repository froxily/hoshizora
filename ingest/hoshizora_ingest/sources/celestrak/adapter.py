import csv
import io
from collections.abc import AsyncIterator, Mapping
from datetime import timedelta

from psycopg import AsyncConnection

from hoshizora_ingest.http.client import NO_RETRY, HttpPolicy
from hoshizora_ingest.http.limiter import RateLimit
from hoshizora_ingest.raw.store import Landed, RawPayload
from hoshizora_ingest.sources.base import BodyFormat, FetchContext, SourceInfo, StoreResult
from hoshizora_ingest.sources.celestrak.models import GpCatalog, SatcatCatalog
from hoshizora_ingest.store.orbits import store_orbits
from hoshizora_ingest.transform.celestrak import CelestrakBatch, normalize

BASE_URL = "https://celestrak.org"
SATCAT = f"{BASE_URL}/pub/satcat.csv"
GP = f"{BASE_URL}/NORAD/elements/gp.php"
GP_ACTIVE = {"GROUP": "active", "FORMAT": "json"}
SATCAT_INTERVAL = timedelta(hours=12)
GP_INTERVAL = timedelta(hours=2)

INFO = SourceInfo(
    slug="celestrak",
    name="CelesTrak SATCAT and GP",
    credit="Orbital data: CelesTrak (celestrak.org)",
    cadence="SATCAT at most every 12 hours, GP active group at most every 2 hours",
)

POLICY = HttpPolicy(
    base_url=BASE_URL,
    rate_limit=RateLimit(requests=1, per_seconds=5),
    retry=NO_RETRY,
    review_on_error=True,
)


def parse_csv(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(text)))


class CelestrakSource:
    @property
    def info(self) -> SourceInfo:
        return INFO

    @property
    def http_policy(self) -> HttpPolicy:
        return POLICY

    async def fetch(self, ctx: FetchContext) -> AsyncIterator[Landed]:
        satcat = await self._due(ctx, SATCAT, {}, SATCAT_INTERVAL, body="text")
        if satcat is not None:
            yield satcat
        gp = await self._due(ctx, GP, GP_ACTIVE, GP_INTERVAL, body="json")
        if gp is not None:
            yield gp

    def parse(self, payload: RawPayload) -> SatcatCatalog | GpCatalog:
        if payload.endpoint == SATCAT:
            if not isinstance(payload.body, str):
                message = "SATCAT payload must be CSV text"
                raise TypeError(message)
            return SatcatCatalog.model_validate({"records": parse_csv(payload.body)})
        return GpCatalog.model_validate({"elements": payload.body})

    def normalize(self, parsed: SatcatCatalog | GpCatalog) -> CelestrakBatch:
        return normalize(parsed)

    async def store(
        self, db: AsyncConnection, batch: CelestrakBatch, payload: RawPayload
    ) -> StoreResult:
        return await store_orbits(db, batch, payload.id)

    async def _due(
        self,
        ctx: FetchContext,
        endpoint: str,
        params: Mapping[str, str],
        interval: timedelta,
        *,
        body: BodyFormat,
    ) -> Landed | None:
        last = await ctx.last_fetched_at(endpoint, params)
        if last is not None and ctx.now() - last < interval:
            return None
        return await ctx.get(endpoint, params, body=body, conditional=True)
