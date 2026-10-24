from collections.abc import AsyncIterator
from datetime import timedelta

from psycopg import AsyncConnection

from hoshizora_ingest.http.client import HttpPolicy, RetryPolicy
from hoshizora_ingest.http.limiter import RateLimit
from hoshizora_ingest.raw.store import Landed, RawPayload
from hoshizora_ingest.sources.base import FetchContext, SourceInfo, StoreResult
from hoshizora_ingest.sources.exoplanets.models import PlanetTable
from hoshizora_ingest.store.exoplanets import store_exoplanets
from hoshizora_ingest.transform.exoplanets import ExoplanetBatch, normalize

BASE_URL = "https://exoplanetarchive.ipac.caltech.edu"
TAP = f"{BASE_URL}/TAP/sync"
REFRESH = timedelta(days=1)
QUERY = (
    "select pl_name,hostname,sy_snum,sy_pnum,discoverymethod,disc_year,disc_facility,disc_locale,"
    "pl_orbper,pl_orbsmax,pl_rade,pl_bmasse,pl_orbeccen,pl_eqt,pl_insol,st_teff,st_rad,st_mass,"
    "sy_dist,pl_controv_flag from pscomppars order by pl_name"
)
PARAMS = {"query": QUERY, "format": "json"}

INFO = SourceInfo(
    slug="exoplanet-archive",
    name="NASA Exoplanet Archive",
    credit="This research has made use of the NASA Exoplanet Archive, which is operated by the "
    "California Institute of Technology, under contract with the National Aeronautics and Space "
    "Administration under the Exoplanet Exploration Program.",
    cadence="the composite planet table once a day; the archive updates it weekly",
)

POLICY = HttpPolicy(
    base_url=BASE_URL,
    rate_limit=RateLimit(requests=1, per_seconds=5),
    retry=RetryPolicy(
        attempts=3,
        statuses=frozenset({429, 500, 502, 503, 504}),
        base_delay_seconds=10,
        max_delay_seconds=600,
    ),
)


class ExoplanetArchiveSource:
    @property
    def info(self) -> SourceInfo:
        return INFO

    @property
    def http_policy(self) -> HttpPolicy:
        return POLICY

    async def fetch(self, ctx: FetchContext) -> AsyncIterator[Landed]:
        last = await ctx.last_fetched_at(TAP, PARAMS)
        if last is not None and ctx.now() - last < REFRESH:
            return
        landed = await ctx.get(TAP, PARAMS)
        if landed is not None:
            yield landed

    def parse(self, payload: RawPayload) -> PlanetTable:
        return PlanetTable.model_validate(payload.body)

    def normalize(self, parsed: PlanetTable) -> ExoplanetBatch:
        return normalize(parsed)

    async def store(
        self, db: AsyncConnection, batch: ExoplanetBatch, payload: RawPayload
    ) -> StoreResult:
        return await store_exoplanets(db, batch, payload.id)
