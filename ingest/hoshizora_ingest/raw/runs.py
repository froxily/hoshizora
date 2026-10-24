from dataclasses import dataclass, field
from enum import StrEnum
from typing import cast

from psycopg import AsyncConnection


class RunStatus(StrEnum):
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


@dataclass
class RunStats:
    requests: int = 0
    not_modified: int = 0
    payloads_new: int = 0
    rows_in: int = 0
    rows_upserted: int = 0
    unknown_fields: set[str] = field(default_factory=set[str])


async def start_run(db: AsyncConnection, source: str, origin: str) -> int:
    async with db.cursor() as cursor:
        await cursor.execute(
            "INSERT INTO raw.ingest_run (source, origin) VALUES (%s, %s) RETURNING id",
            (source, origin),
        )
        row = await cursor.fetchone()
    if row is None:
        msg = f"Could not start a run for {source}"
        raise LookupError(msg)
    return int(row[0])


async def finish_run(
    db: AsyncConnection,
    run_id: int,
    status: RunStatus,
    stats: RunStats,
    error: str | None,
) -> None:
    await db.execute(
        """
        UPDATE raw.ingest_run
        SET finished_at = now(), status = %s, requests = %s, not_modified = %s,
            payloads_new = %s, rows_in = %s, rows_upserted = %s, error = %s
        WHERE id = %s
        """,
        (
            status.value,
            stats.requests,
            stats.not_modified,
            stats.payloads_new,
            stats.rows_in,
            stats.rows_upserted,
            error,
            run_id,
        ),
    )


@dataclass(frozen=True)
class LastRun:
    id: int
    status: RunStatus


async def last_finished_run(db: AsyncConnection, source: str) -> LastRun | None:
    async with db.cursor() as cursor:
        await cursor.execute(
            "SELECT id, status FROM raw.ingest_run WHERE source = %s AND status <> 'running' "
            "ORDER BY id DESC LIMIT 1",
            (source,),
        )
        row = await cursor.fetchone()
    return LastRun(int(row[0]), RunStatus(cast("str", row[1]))) if row is not None else None


async def pinned_origin(db: AsyncConnection, source: str) -> str | None:
    async with db.cursor() as cursor:
        await cursor.execute(
            "SELECT origin FROM raw.ingest_run WHERE source = %s AND origin IS NOT NULL "
            "ORDER BY id LIMIT 1",
            (source,),
        )
        row = await cursor.fetchone()
    return cast("str", row[0]) if row is not None else None
