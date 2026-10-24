from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID

from psycopg import AsyncConnection

from hoshizora_ingest.sources.base import StoreResult
from hoshizora_ingest.store.organizations import (
    LL2_AGENCY,
    known_countries,
    observe_codes,
    organization_ids,
    store_agencies,
)
from hoshizora_ingest.store.upsert import Column, TableSpec, upsert_with_lineage
from hoshizora_ingest.transform.launch_library import LaunchBatch, LaunchRow, PadRow

VEHICLES = TableSpec(
    schema="core",
    name="launch_vehicle",
    columns=(
        Column("ll2_id", "integer"),
        Column("name", "text"),
        Column("full_name", "text"),
        Column("variant", "text"),
        Column("family", "text"),
    ),
    key=("ll2_id",),
)

PADS = TableSpec(
    schema="core",
    name="launch_pad",
    columns=(
        Column("ll2_id", "integer"),
        Column("name", "text"),
        Column("location_name", "text"),
        Column("country_code", "char(2)"),
        Column("latitude", "double precision"),
        Column("longitude", "double precision"),
    ),
    key=("ll2_id",),
)

MISSIONS = TableSpec(
    schema="core",
    name="mission",
    columns=(
        Column("ll2_id", "integer"),
        Column("name", "text"),
        Column("type", "text"),
        Column("orbit", "text"),
        Column("orbit_name", "text"),
        Column("description", "text"),
    ),
    key=("ll2_id",),
)

LAUNCHES = TableSpec(
    schema="core",
    name="launch",
    columns=(
        Column("ll2_id", "uuid"),
        Column("name", "text"),
        Column("slug", "text"),
        Column("launch_designator", "text"),
        Column("net", "timestamptz"),
        Column("net_precision", "text"),
        Column("window_start", "timestamptz"),
        Column("window_end", "timestamptz"),
        Column("status_id", "smallint"),
        Column("status", "text"),
        Column("status_name", "text"),
        Column("failure_reason", "text"),
        Column("provider_org_id", "bigint"),
        Column("vehicle_ll2_id", "integer"),
        Column("pad_ll2_id", "integer"),
        Column("mission_ll2_id", "integer"),
        Column("source_updated_at", "timestamptz"),
    ),
    key=("ll2_id",),
    guard="excluded.source_updated_at >= t.source_updated_at",
)

SYNC_MISSION_AGENCIES = """
WITH incoming AS (
    SELECT i.mission_ll2_id, a.organization_id
    FROM unnest(%s::int[], %s::text[]) AS i(mission_ll2_id, agency_code)
    JOIN core.organization_alias a ON a.namespace = 'll2.agency' AND a.code = i.agency_code
),
removed AS (
    DELETE FROM core.mission_agency m
    WHERE m.mission_ll2_id = ANY(%s::int[])
      AND NOT EXISTS (
          SELECT FROM incoming i
          WHERE i.mission_ll2_id = m.mission_ll2_id AND i.organization_id = m.organization_id
      )
    RETURNING 1
),
added AS (
    INSERT INTO core.mission_agency (mission_ll2_id, organization_id)
    SELECT mission_ll2_id, organization_id FROM incoming
    ON CONFLICT DO NOTHING
    RETURNING 1
)
SELECT (SELECT count(*) FROM removed) + (SELECT count(*) FROM added)
"""


@dataclass(frozen=True)
class LaunchRecord:
    ll2_id: UUID
    name: str
    slug: str | None
    launch_designator: str | None
    net: datetime | None
    net_precision: str | None
    window_start: datetime | None
    window_end: datetime | None
    status_id: int
    status: str
    status_name: str
    failure_reason: str | None
    provider_org_id: int | None
    vehicle_ll2_id: int
    pad_ll2_id: int
    mission_ll2_id: int | None
    source_updated_at: datetime


def launch_record(row: LaunchRow, providers: dict[str, int]) -> LaunchRecord:
    return LaunchRecord(
        ll2_id=row.ll2_id,
        name=row.name,
        slug=row.slug,
        launch_designator=row.launch_designator,
        net=row.net,
        net_precision=row.net_precision,
        window_start=row.window_start,
        window_end=row.window_end,
        status_id=row.status_id,
        status=row.status,
        status_name=row.status_name,
        failure_reason=row.failure_reason,
        provider_org_id=providers.get(str(row.provider_ll2_id)),
        vehicle_ll2_id=row.vehicle_ll2_id,
        pad_ll2_id=row.pad_ll2_id,
        mission_ll2_id=row.mission_ll2_id,
        source_updated_at=row.source_updated_at,
    )


async def resolve_pad_countries(db: AsyncConnection, pads: tuple[PadRow, ...]) -> list[PadRow]:
    codes = {pad.country_code for pad in pads if pad.country_code is not None}
    known = await known_countries(db, codes)
    await observe_codes(db, "ll2.country", codes - known)
    return [
        pad
        if pad.country_code is None or pad.country_code in known
        else replace(pad, country_code=None)
        for pad in pads
    ]


async def sync_mission_agencies(db: AsyncConnection, batch: LaunchBatch) -> int:
    async with db.cursor() as cursor:
        await cursor.execute(
            SYNC_MISSION_AGENCIES,
            (
                [row.mission_ll2_id for row in batch.mission_agencies],
                [str(row.agency_ll2_id) for row in batch.mission_agencies],
                [mission.ll2_id for mission in batch.missions],
            ),
        )
        counted = await cursor.fetchone()
    return int(counted[0]) if counted is not None else 0


async def store_launches(db: AsyncConnection, batch: LaunchBatch, payload_id: int) -> StoreResult:
    result = await store_agencies(db, batch.agencies, payload_id)
    result += await upsert_with_lineage(db, VEHICLES, batch.vehicles, payload_id)
    pads = await resolve_pad_countries(db, batch.pads)
    result += await upsert_with_lineage(db, PADS, pads, payload_id)
    result += await upsert_with_lineage(db, MISSIONS, batch.missions, payload_id)
    providers = await organization_ids(
        db, LL2_AGENCY, (str(launch.provider_ll2_id) for launch in batch.launches)
    )
    records = [launch_record(launch, providers) for launch in batch.launches]
    result += await upsert_with_lineage(db, LAUNCHES, records, payload_id)
    return result + StoreResult(0, await sync_mission_agencies(db, batch))
