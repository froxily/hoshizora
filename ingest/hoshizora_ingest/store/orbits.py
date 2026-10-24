from psycopg import AsyncConnection

from hoshizora_ingest.sources.base import StoreResult
from hoshizora_ingest.store.organizations import observe_codes
from hoshizora_ingest.store.upsert import Column, TableSpec, upsert, upsert_with_lineage
from hoshizora_ingest.transform.celestrak import CelestrakBatch, SatcatBatch

CELESTRAK_OWNER = "celestrak.owner"

SPACE_OBJECTS = TableSpec(
    schema="core",
    name="space_object",
    columns=(
        Column("norad_id", "integer"),
        Column("object_id", "text"),
        Column("launch_designator", "text"),
        Column("name", "text"),
        Column("object_type", "text"),
        Column("ops_status", "text"),
        Column("owner_code", "text"),
        Column("launch_date", "date"),
        Column("launch_site", "text"),
        Column("decay_date", "date"),
        Column("period_min", "double precision"),
        Column("inclination_deg", "double precision"),
        Column("apogee_km", "double precision"),
        Column("perigee_km", "double precision"),
        Column("rcs_m2", "double precision"),
        Column("data_status", "text"),
        Column("orbit_center", "text"),
        Column("orbit_type", "text"),
    ),
    key=("norad_id",),
)

SPACE_OBJECT_STUBS = TableSpec(
    schema="core",
    name="space_object",
    columns=(
        Column("norad_id", "integer"),
        Column("object_id", "text"),
        Column("launch_designator", "text"),
        Column("name", "text"),
    ),
    key=("norad_id",),
    insert_only=True,
)

ORBIT_ELEMENTS = TableSpec(
    schema="core",
    name="orbit_element",
    columns=(
        Column("norad_id", "integer"),
        Column("epoch", "timestamptz"),
        Column("mean_motion", "double precision"),
        Column("eccentricity", "double precision"),
        Column("inclination_deg", "double precision"),
        Column("ra_of_asc_node_deg", "double precision"),
        Column("arg_of_pericenter_deg", "double precision"),
        Column("mean_anomaly_deg", "double precision"),
        Column("bstar", "double precision"),
        Column("mean_motion_dot", "double precision"),
        Column("mean_motion_ddot", "double precision"),
        Column("element_set_no", "integer"),
        Column("rev_at_epoch", "integer"),
        Column("classification", "text"),
        Column("ephemeris_type", "smallint"),
    ),
    key=("norad_id",),
    guard="excluded.epoch > t.epoch",
)


async def store_orbits(db: AsyncConnection, batch: CelestrakBatch, payload_id: int) -> StoreResult:
    if isinstance(batch, SatcatBatch):
        await observe_codes(
            db, CELESTRAK_OWNER, {row.owner_code for row in batch.objects if row.owner_code}
        )
        return await upsert_with_lineage(db, SPACE_OBJECTS, batch.objects, payload_id)
    created = await upsert(db, SPACE_OBJECT_STUBS, batch.stubs)
    result = await upsert_with_lineage(db, ORBIT_ELEMENTS, batch.elements, payload_id)
    return StoreResult(result.rows_in, result.rows_changed + len(created))
