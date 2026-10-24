from psycopg import AsyncConnection

from hoshizora_ingest.sources.base import StoreResult
from hoshizora_ingest.store.upsert import Column, TableSpec, delete_missing, upsert_with_lineage
from hoshizora_ingest.transform.exoplanets import ExoplanetBatch

SMALLEST_KEPT_SHARE = 0.9

EXOPLANETS = TableSpec(
    schema="core",
    name="exoplanet",
    columns=(
        Column("name", "text"),
        Column("host_name", "text"),
        Column("star_count", "smallint"),
        Column("planet_count", "smallint"),
        Column("discovery_method", "text"),
        Column("discovery_year", "smallint"),
        Column("discovery_facility", "text"),
        Column("discovery_locale", "text"),
        Column("orbital_period_days", "double precision"),
        Column("semi_major_axis_au", "double precision"),
        Column("radius_earth", "double precision"),
        Column("mass_earth", "double precision"),
        Column("eccentricity", "double precision"),
        Column("equilibrium_temp_k", "double precision"),
        Column("insolation_earth", "double precision"),
        Column("star_temp_k", "double precision"),
        Column("star_radius_sun", "double precision"),
        Column("star_mass_sun", "double precision"),
        Column("distance_pc", "double precision"),
        Column("controversial", "boolean"),
    ),
    key=("name",),
)


class ShrunkTableError(Exception):
    pass


async def stored_count(db: AsyncConnection) -> int:
    async with db.cursor() as cursor:
        await cursor.execute("SELECT count(*) FROM core.exoplanet")
        row = await cursor.fetchone()
    return int(row[0]) if row is not None else 0


async def store_exoplanets(
    db: AsyncConnection, batch: ExoplanetBatch, payload_id: int
) -> StoreResult:
    stored = await stored_count(db)
    if len(batch.planets) < stored * SMALLEST_KEPT_SHARE:
        message = (
            f"the archive returned {len(batch.planets)} planets against {stored} stored; "
            "refusing to drop more than a tenth of the table"
        )
        raise ShrunkTableError(message)
    result = await upsert_with_lineage(db, EXOPLANETS, batch.planets, payload_id)
    removed = await delete_missing(db, EXOPLANETS, batch.planets)
    return result + StoreResult(0, removed)
