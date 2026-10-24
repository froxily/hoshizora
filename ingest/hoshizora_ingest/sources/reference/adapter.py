import tomllib
from collections.abc import AsyncIterator
from pathlib import Path
from typing import cast

from psycopg import AsyncConnection

from hoshizora_ingest.http.client import NO_RETRY, HttpPolicy
from hoshizora_ingest.http.limiter import RateLimit
from hoshizora_ingest.jsontypes import JsonValue
from hoshizora_ingest.raw.store import Landed, RawPayload
from hoshizora_ingest.sources.base import FetchContext, SourceInfo, StoreResult
from hoshizora_ingest.sources.reference.models import ReferenceData
from hoshizora_ingest.store.reference import store_reference
from hoshizora_ingest.transform.reference import ReferenceBatch, normalize_reference

REFERENCE_DIRECTORY = Path(__file__).resolve().parents[2] / "reference"
DOCUMENTS = {
    "countries": "countries.toml",
    "celestrak_owners": "celestrak_owners.toml",
    "organizations": "organizations.toml",
    "sources": "sources.toml",
}
ENDPOINT = "reference"

INFO = SourceInfo(
    slug="reference",
    name="Curated reference data",
    credit="Country names: Unicode CLDR. Owner codes: CelesTrak. Curation: Hoshizora.",
    cadence="on change",
)

LOCAL_ONLY = HttpPolicy(
    base_url="http://localhost", rate_limit=RateLimit(requests=1, per_seconds=1), retry=NO_RETRY
)


def load_documents(directory: Path = REFERENCE_DIRECTORY) -> dict[str, JsonValue]:
    return {
        name: cast("JsonValue", tomllib.loads((directory / file).read_text(encoding="utf-8")))
        for name, file in DOCUMENTS.items()
    }


class ReferenceSource:
    def __init__(self, directory: Path = REFERENCE_DIRECTORY) -> None:
        self._directory = directory

    @property
    def info(self) -> SourceInfo:
        return INFO

    @property
    def http_policy(self) -> HttpPolicy:
        return LOCAL_ONLY

    async def fetch(self, ctx: FetchContext) -> AsyncIterator[Landed]:
        yield await ctx.land(ENDPOINT, load_documents(self._directory))

    def parse(self, payload: RawPayload) -> ReferenceData:
        return ReferenceData.model_validate(payload.body)

    def normalize(self, parsed: ReferenceData) -> ReferenceBatch:
        return normalize_reference(parsed)

    async def store(
        self, db: AsyncConnection, batch: ReferenceBatch, payload: RawPayload
    ) -> StoreResult:
        return await store_reference(db, batch, payload.id)
