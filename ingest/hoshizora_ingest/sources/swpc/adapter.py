from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import timedelta

from psycopg import AsyncConnection

from hoshizora_ingest.http.client import HttpPolicy, RetryPolicy
from hoshizora_ingest.http.limiter import RateLimit
from hoshizora_ingest.raw.store import Landed, RawPayload
from hoshizora_ingest.sources.base import FetchContext, SourceInfo, StoreResult
from hoshizora_ingest.sources.swpc.models import (
    AlertList,
    FlareList,
    KpSeries,
    MagSeries,
    OvationGrid,
    PlasmaSeries,
    SwpcProduct,
)
from hoshizora_ingest.store.space_weather import store_space_weather
from hoshizora_ingest.transform.swpc import SwpcBatch, normalize

BASE_URL = "https://services.swpc.noaa.gov"


@dataclass(frozen=True)
class Product:
    url: str
    refresh: timedelta
    model: type[SwpcProduct]
    field: str | None


PRODUCTS = (
    Product(
        f"{BASE_URL}/products/noaa-planetary-k-index.json", timedelta(hours=1), KpSeries, "entries"
    ),
    Product(
        f"{BASE_URL}/json/goes/primary/xray-flares-7-day.json",
        timedelta(hours=1),
        FlareList,
        "flares",
    ),
    Product(f"{BASE_URL}/products/alerts.json", timedelta(hours=1), AlertList, "alerts"),
    Product(f"{BASE_URL}/json/rtsw/rtsw_wind_1m.json", timedelta(hours=6), PlasmaSeries, "samples"),
    Product(f"{BASE_URL}/json/rtsw/rtsw_mag_1m.json", timedelta(hours=6), MagSeries, "samples"),
    Product(f"{BASE_URL}/json/ovation_aurora_latest.json", timedelta(hours=1), OvationGrid, None),
)
BY_URL = {product.url: product for product in PRODUCTS}

INFO = SourceInfo(
    slug="swpc",
    name="NOAA Space Weather Prediction Center",
    credit="Space weather data: NOAA Space Weather Prediction Center (SWPC)",
    cadence=(
        "Kp, flares, alerts and the aurora forecast hourly; real-time solar wind every 6 hours;"
        " all conditional"
    ),
)

POLICY = HttpPolicy(
    base_url=BASE_URL,
    rate_limit=RateLimit(requests=1, per_seconds=1),
    retry=RetryPolicy(
        attempts=3,
        statuses=frozenset({429, 500, 502, 503, 504}),
        base_delay_seconds=5,
        max_delay_seconds=300,
    ),
)


def parse_product(product: Product, body: object) -> SwpcProduct:
    return product.model.model_validate(body if product.field is None else {product.field: body})


class SwpcSource:
    @property
    def info(self) -> SourceInfo:
        return INFO

    @property
    def http_policy(self) -> HttpPolicy:
        return POLICY

    async def fetch(self, ctx: FetchContext) -> AsyncIterator[Landed]:
        for product in PRODUCTS:
            last = await ctx.last_fetched_at(product.url, {})
            if last is not None and ctx.now() - last < product.refresh:
                continue
            landed = await ctx.get(product.url, {}, conditional=True)
            if landed is not None:
                yield landed

    def parse(self, payload: RawPayload) -> SwpcProduct:
        return parse_product(BY_URL[payload.endpoint], payload.body)

    def normalize(self, parsed: SwpcProduct) -> SwpcBatch:
        return normalize(parsed)

    async def store(
        self, db: AsyncConnection, batch: SwpcBatch, payload: RawPayload
    ) -> StoreResult:
        return await store_space_weather(db, batch, payload)
