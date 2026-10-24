from psycopg import AsyncConnection

from hoshizora_ingest.sources.base import StoreResult
from hoshizora_ingest.store.upsert import Column, TableSpec, upsert_with_lineage
from hoshizora_ingest.transform.launch_library import LandingBatch, LauncherBatch

STAGE_IDENTITY = (
    Column("ll2_id", "integer"),
    Column("serial_number", "text"),
    Column("is_placeholder", "boolean"),
    Column("flight_proven", "boolean"),
    Column("status", "text"),
)

LAUNCHER_IDENTITIES = TableSpec(
    schema="core",
    name="launcher",
    columns=STAGE_IDENTITY,
    key=("ll2_id",),
)

LAUNCHERS = TableSpec(
    schema="core",
    name="launcher",
    columns=(
        *STAGE_IDENTITY,
        Column("vehicle_ll2_id", "integer"),
        Column("flights", "integer"),
        Column("attempted_landings", "integer"),
        Column("successful_landings", "integer"),
        Column("first_launch_at", "timestamptz"),
        Column("last_launch_at", "timestamptz"),
        Column("fastest_turnaround", "interval"),
    ),
    key=("ll2_id",),
)

LANDINGS = TableSpec(
    schema="core",
    name="landing",
    columns=(
        Column("ll2_id", "integer"),
        Column("launcher_ll2_id", "integer"),
        Column("stage_type", "text"),
        Column("launcher_flight_number", "integer"),
        Column("reused", "boolean"),
        Column("attempt", "boolean"),
        Column("success", "boolean"),
        Column("previous_flight_at", "timestamptz"),
        Column("turnaround", "interval"),
        Column("type_abbrev", "text"),
        Column("type_name", "text"),
        Column("location_name", "text"),
        Column("location_abbrev", "text"),
        Column("downrange_km", "double precision"),
    ),
    key=("ll2_id",),
)


async def store_launchers(
    db: AsyncConnection, batch: LauncherBatch, payload_id: int
) -> StoreResult:
    return await upsert_with_lineage(db, LAUNCHERS, batch.launchers, payload_id)


async def store_landings(db: AsyncConnection, batch: LandingBatch, payload_id: int) -> StoreResult:
    result = await upsert_with_lineage(db, LAUNCHER_IDENTITIES, batch.launchers, payload_id)
    return result + await upsert_with_lineage(db, LANDINGS, batch.landings, payload_id)
