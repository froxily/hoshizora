from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import cast

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

from hoshizora_ingest.http.client import Validators
from hoshizora_ingest.jsontypes import JsonValue, content_hash


@dataclass(frozen=True)
class RawPayload:
    id: int
    endpoint: str
    params: Mapping[str, str]
    body: JsonValue


@dataclass(frozen=True)
class Landed:
    payload: RawPayload
    is_new: bool


async def land_payload(
    db: AsyncConnection,
    source: str,
    endpoint: str,
    params: Mapping[str, str],
    body: JsonValue,
) -> Landed:
    digest = content_hash(body)
    async with db.cursor() as cursor:
        await cursor.execute(
            """
            INSERT INTO raw.payload (source, endpoint, params, content_hash, body)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (source, content_hash) DO NOTHING
            RETURNING id
            """,
            (source, endpoint, Jsonb(dict(params)), digest, Jsonb(body)),
        )
        inserted = await cursor.fetchone()
        if inserted is not None:
            return Landed(RawPayload(int(inserted[0]), endpoint, params, body), is_new=True)
        await cursor.execute("SELECT raw.restore_body(%s, %s, %s)", (source, digest, Jsonb(body)))
        restored = await cursor.fetchone()
        if restored is not None and restored[0] is not None:
            return Landed(RawPayload(int(restored[0]), endpoint, params, body), is_new=True)
        await cursor.execute(
            "SELECT id FROM raw.payload WHERE source = %s AND content_hash = %s",
            (source, digest),
        )
        existing = await cursor.fetchone()
    if existing is None:
        msg = f"Payload {digest} for {source} vanished between insert and select"
        raise LookupError(msg)
    return Landed(RawPayload(int(existing[0]), endpoint, params, body), is_new=False)


@dataclass(frozen=True)
class FetchRecord:
    run_id: int
    source: str
    endpoint: str
    params: Mapping[str, str]
    status: int
    duration_ms: int
    etag: str | None = None
    last_modified: str | None = None
    payload_id: int | None = None


async def log_fetch(db: AsyncConnection, record: FetchRecord) -> None:
    await db.execute(
        """
        INSERT INTO raw.fetch (
            run_id, source, endpoint, params, http_status, etag, last_modified,
            payload_id, duration_ms
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            record.run_id,
            record.source,
            record.endpoint,
            Jsonb(dict(record.params)),
            record.status,
            record.etag,
            record.last_modified,
            record.payload_id,
            record.duration_ms,
        ),
    )


async def latest_validators(
    db: AsyncConnection, source: str, endpoint: str, params: Mapping[str, str]
) -> Validators | None:
    async with db.cursor() as cursor:
        await cursor.execute(
            """
            SELECT etag, last_modified
            FROM raw.fetch
            WHERE source = %s AND endpoint = %s AND params = %s
              AND http_status = 200 AND (etag IS NOT NULL OR last_modified IS NOT NULL)
            ORDER BY requested_at DESC
            LIMIT 1
            """,
            (source, endpoint, Jsonb(dict(params))),
        )
        row = await cursor.fetchone()
    if row is None:
        return None
    return Validators(etag=cast("str | None", row[0]), last_modified=cast("str | None", row[1]))


async def last_fetched_at(
    db: AsyncConnection, source: str, endpoint: str, params: Mapping[str, str]
) -> datetime | None:
    async with db.cursor() as cursor:
        await cursor.execute(
            """
            SELECT max(requested_at)
            FROM raw.fetch
            WHERE source = %s AND endpoint = %s AND params = %s AND http_status IN (200, 304)
            """,
            (source, endpoint, Jsonb(dict(params))),
        )
        row = await cursor.fetchone()
    return cast("datetime | None", row[0]) if row is not None else None


async def load_payload(db: AsyncConnection, payload_id: int) -> RawPayload:
    async with db.cursor() as cursor:
        await cursor.execute(
            "SELECT endpoint, params, body FROM raw.payload WHERE id = %s", (payload_id,)
        )
        row = await cursor.fetchone()
    if row is None:
        msg = f"No raw payload {payload_id}"
        raise LookupError(msg)
    return RawPayload(
        payload_id,
        cast("str", row[0]),
        cast("dict[str, str]", row[1]),
        cast("JsonValue", row[2]),
    )


async def apply_retention(db: AsyncConnection, source: str, reference: datetime) -> int:
    async with db.cursor() as cursor:
        await cursor.execute("SELECT raw.apply_retention(%s, %s)", (source, reference))
        row = await cursor.fetchone()
    return int(row[0]) if row is not None else 0


async def reclaim_payload_space(autocommit_db: AsyncConnection) -> None:
    await autocommit_db.execute("VACUUM raw.payload")
