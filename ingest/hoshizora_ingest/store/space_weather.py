from psycopg import AsyncConnection

from hoshizora_ingest.raw.store import RawPayload
from hoshizora_ingest.sources.base import StoreResult
from hoshizora_ingest.store.upsert import Column, TableSpec, upsert, upsert_with_lineage
from hoshizora_ingest.transform.swpc import (
    AuroraBatch,
    EventBatch,
    GeomagneticBatch,
    MagBatch,
    PlasmaBatch,
    SwpcBatch,
)

GEOMAGNETIC_INDICES = TableSpec(
    schema="core",
    name="geomagnetic_index",
    columns=(
        Column("index", "text"),
        Column("observed_at", "timestamptz"),
        Column("value", "double precision"),
        Column("a_running", "integer"),
        Column("station_count", "smallint"),
    ),
    key=("index", "observed_at"),
)

EVENTS = TableSpec(
    schema="core",
    name="space_weather_event",
    columns=(
        Column("kind", "text"),
        Column("external_id", "text"),
        Column("begin_at", "timestamptz"),
        Column("peak_at", "timestamptz"),
        Column("end_at", "timestamptz"),
        Column("event_class", "text"),
        Column("peak_flux_wm2", "double precision"),
        Column("satellite", "smallint"),
        Column("product_id", "text"),
        Column("message", "text"),
    ),
    key=("kind", "external_id"),
)

PLASMA = TableSpec(
    schema="core",
    name="solar_wind_sample",
    columns=(
        Column("observed_at", "timestamptz"),
        Column("plasma_spacecraft", "text"),
        Column("speed_kms", "double precision"),
        Column("density_cm3", "double precision"),
        Column("temperature_k", "double precision"),
    ),
    key=("observed_at",),
)

MAGNETIC_FIELD = TableSpec(
    schema="core",
    name="solar_wind_sample",
    columns=(
        Column("observed_at", "timestamptz"),
        Column("mag_spacecraft", "text"),
        Column("bt_nt", "double precision"),
        Column("bz_gsm_nt", "double precision"),
    ),
    key=("observed_at",),
)


SOURCE = "swpc"

AURORA_FORECASTS = TableSpec(
    schema="core",
    name="aurora_forecast",
    columns=(
        Column("observed_at", "timestamptz"),
        Column("forecast_at", "timestamptz"),
        Column("north_max_percent", "smallint"),
        Column("south_max_percent", "smallint"),
        Column("north_boundary_lat", "smallint"),
        Column("south_boundary_lat", "smallint"),
    ),
    key=("observed_at",),
)

AURORA_CELLS = TableSpec(
    schema="core",
    name="aurora_cell",
    columns=(
        Column("longitude", "smallint"),
        Column("latitude", "smallint"),
        Column("probability_percent", "smallint"),
        Column("observed_at", "timestamptz"),
    ),
    key=("longitude", "latitude"),
)


async def store_aurora(db: AsyncConnection, batch: AuroraBatch, payload: RawPayload) -> StoreResult:
    stored = await upsert_with_lineage(db, AURORA_FORECASTS, (batch.forecast,), payload.id)
    observed_at = batch.forecast.observed_at
    replaced = 0
    async with db.cursor() as cursor:
        await cursor.execute(
            "SELECT max(observed_at) = %s FROM core.aurora_forecast", (observed_at,)
        )
        latest = await cursor.fetchone()
        if latest is not None and latest[0] is True:
            await cursor.execute("DELETE FROM core.aurora_cell")
            replaced = len(await upsert(db, AURORA_CELLS, batch.cells))
        await cursor.execute(
            "DELETE FROM core.aurora_forecast WHERE observed_at < %s - ("
            "SELECT keep FROM raw.retention_policy WHERE source = %s AND endpoint = %s)",
            (observed_at, SOURCE, payload.endpoint),
        )
    return stored + StoreResult(rows_in=len(batch.cells), rows_changed=replaced)


async def store_space_weather(
    db: AsyncConnection, batch: SwpcBatch, payload: RawPayload
) -> StoreResult:
    payload_id = payload.id
    match batch:
        case GeomagneticBatch():
            return await upsert_with_lineage(db, GEOMAGNETIC_INDICES, batch.rows, payload_id)
        case EventBatch():
            return await upsert_with_lineage(db, EVENTS, batch.rows, payload_id)
        case PlasmaBatch():
            return await upsert_with_lineage(db, PLASMA, batch.rows, payload_id)
        case MagBatch():
            return await upsert_with_lineage(db, MAGNETIC_FIELD, batch.rows, payload_id)
        case AuroraBatch():
            return await store_aurora(db, batch, payload)
