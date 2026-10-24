from typing import LiteralString

from psycopg import AsyncConnection

from hoshizora_ingest.sources.base import StoreResult
from hoshizora_ingest.store.upsert import Column, TableSpec, upsert, upsert_with_lineage
from hoshizora_ingest.transform.jpl import (
    CloseApproachBatch,
    ImpactRiskBatch,
    JplBatch,
    RemovalBatch,
)

SMALL_BODIES = TableSpec(
    schema="core",
    name="small_body",
    columns=(
        Column("designation", "text"),
        Column("fullname", "text"),
        Column("h_mag", "double precision"),
        Column("diameter_km", "double precision"),
        Column("diameter_sigma_km", "double precision"),
    ),
    key=("designation",),
)

SMALL_BODY_STUBS = TableSpec(
    schema="core",
    name="small_body",
    columns=(Column("designation", "text"), Column("fullname", "text")),
    key=("designation",),
    insert_only=True,
)

CLOSE_APPROACHES = TableSpec(
    schema="core",
    name="close_approach",
    columns=(
        Column("designation", "text"),
        Column("body", "text"),
        Column("approach_tdb", "timestamp"),
        Column("orbit_id", "text"),
        Column("jd_tdb", "double precision"),
        Column("dist_au", "double precision"),
        Column("dist_min_au", "double precision"),
        Column("dist_max_au", "double precision"),
        Column("v_rel_kms", "double precision"),
        Column("v_inf_kms", "double precision"),
        Column("t_sigma", "text"),
        Column("h_mag", "double precision"),
    ),
    key=("designation", "body", "approach_tdb"),
)

IMPACT_RISKS = TableSpec(
    schema="core",
    name="impact_risk",
    columns=(
        Column("designation", "text"),
        Column("sentry_id", "text"),
        Column("fullname", "text"),
        Column("impact_probability", "double precision"),
        Column("palermo_cumulative", "double precision"),
        Column("palermo_max", "double precision"),
        Column("torino_max", "smallint"),
        Column("potential_impacts", "integer"),
        Column("impact_year_first", "smallint"),
        Column("impact_year_last", "smallint"),
        Column("last_observed", "date"),
        Column("diameter_km", "double precision"),
        Column("h_mag", "double precision"),
        Column("v_inf_kms", "double precision"),
    ),
    key=("designation",),
)

REPLACE_WINDOW = """
DELETE FROM core.close_approach c
WHERE c.body = %s
  AND c.approach_tdb >= %s AND c.approach_tdb < %s
  AND NOT EXISTS (
      SELECT FROM unnest(%s::text[], %s::timestamp[]) AS i(designation, approach_tdb)
      WHERE i.designation = c.designation AND i.approach_tdb = c.approach_tdb
  )
"""

CLEAR_REMOVAL = """
UPDATE core.impact_risk SET removed_at = NULL
WHERE designation = ANY(%s) AND removed_at IS NOT NULL
"""

MARK_REMOVED = """
WITH current_summary AS (
    SELECT p.body
    FROM raw.fetch f
    JOIN raw.payload p ON p.id = f.payload_id
    WHERE f.source = 'jpl' AND f.endpoint = %s AND f.params = '{}'::jsonb
    ORDER BY f.requested_at DESC, f.id DESC
    LIMIT 1
),
still_listed AS (
    SELECT entry ->> 'des' AS designation
    FROM current_summary CROSS JOIN LATERAL jsonb_array_elements(body -> 'data') AS entry
)
UPDATE core.impact_risk r SET removed_at = i.removed_at
FROM unnest(%s::text[], %s::timestamptz[]) AS i(designation, removed_at)
WHERE r.designation = i.designation
  AND r.removed_at IS DISTINCT FROM i.removed_at
  AND i.designation NOT IN (SELECT designation FROM still_listed)
"""


async def rowcount(
    db: AsyncConnection, statement: LiteralString, params: tuple[object, ...]
) -> int:
    async with db.cursor() as cursor:
        await cursor.execute(statement, params)
        return max(cursor.rowcount, 0)


async def store_close_approaches(
    db: AsyncConnection, batch: CloseApproachBatch, payload_id: int
) -> StoreResult:
    result = await upsert_with_lineage(db, SMALL_BODIES, batch.bodies, payload_id)
    removed = await rowcount(
        db,
        REPLACE_WINDOW,
        (
            batch.body,
            batch.date_min,
            batch.date_max,
            [row.designation for row in batch.approaches],
            [row.approach_tdb for row in batch.approaches],
        ),
    )
    result += await upsert_with_lineage(db, CLOSE_APPROACHES, batch.approaches, payload_id)
    return StoreResult(result.rows_in, result.rows_changed + removed)


async def store_impact_risks(
    db: AsyncConnection, batch: ImpactRiskBatch, payload_id: int
) -> StoreResult:
    await upsert(db, SMALL_BODY_STUBS, batch.bodies)
    result = await upsert_with_lineage(db, IMPACT_RISKS, batch.risks, payload_id)
    cleared = await rowcount(db, CLEAR_REMOVAL, ([row.designation for row in batch.risks],))
    return StoreResult(result.rows_in, result.rows_changed + cleared)


async def store_removals(
    db: AsyncConnection, batch: RemovalBatch, summary_endpoint: str
) -> StoreResult:
    marked = await rowcount(
        db,
        MARK_REMOVED,
        (
            summary_endpoint,
            [row.designation for row in batch.removals],
            [row.removed_at for row in batch.removals],
        ),
    )
    return StoreResult(len(batch.removals), marked)


async def store_small_bodies(
    db: AsyncConnection, batch: JplBatch, payload_id: int, summary_endpoint: str
) -> StoreResult:
    if isinstance(batch, CloseApproachBatch):
        return await store_close_approaches(db, batch, payload_id)
    if isinstance(batch, ImpactRiskBatch):
        return await store_impact_risks(db, batch, payload_id)
    return await store_removals(db, batch, summary_endpoint)
