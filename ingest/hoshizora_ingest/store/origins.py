from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import LiteralString
from urllib.parse import urlsplit

from psycopg import AsyncConnection

FOREIGN_PAYLOADS = """
SELECT count(*)
FROM raw.payload
WHERE source = %s AND mart.url_origin(endpoint) <> %s
"""

CANONICAL_PAYLOADS = """
SELECT id
FROM raw.payload
WHERE source = %s AND coalesce(mart.url_origin(endpoint), %s) = %s AND body IS NOT NULL
ORDER BY id
"""

FOREIGN_ONLY_ROWS = """
SELECT s.entity, s.entity_key
FROM core.source_record s
JOIN raw.payload p ON p.id = s.payload_id
WHERE p.source = %(source)s AND mart.url_origin(p.endpoint) <> %(origin)s
GROUP BY s.entity, s.entity_key
HAVING NOT EXISTS (
    SELECT 1
    FROM core.source_record k
    JOIN raw.payload q ON q.id = k.payload_id
    WHERE k.entity = s.entity
      AND k.entity_key = s.entity_key
      AND (q.source <> %(source)s OR coalesce(mart.url_origin(q.endpoint), %(origin)s) = %(origin)s)
)
"""

FOREIGN_LINKS = """
DELETE FROM core.source_record s
USING raw.payload p
WHERE p.id = s.payload_id AND p.source = %s AND mart.url_origin(p.endpoint) <> %s
"""

PRUNABLE: tuple[tuple[str, tuple[LiteralString, ...]], ...] = (
    ("core.launch", ("DELETE FROM core.launch WHERE ll2_id::text = ANY(%s)",)),
    (
        "core.mission",
        (
            "DELETE FROM core.mission_agency WHERE mission_ll2_id::text = ANY(%s)",
            "DELETE FROM core.mission WHERE ll2_id::text = ANY(%s)",
        ),
    ),
    ("core.launch_pad", ("DELETE FROM core.launch_pad WHERE ll2_id::text = ANY(%s)",)),
    ("core.launch_vehicle", ("DELETE FROM core.launch_vehicle WHERE ll2_id::text = ANY(%s)",)),
)


@dataclass(frozen=True)
class Pruned:
    deleted: Mapping[str, int] = field(default_factory=dict[str, int])
    unlinked: Mapping[str, int] = field(default_factory=dict[str, int])
    links_removed: int = 0


def origin_of(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}".lower()


async def foreign_payloads(db: AsyncConnection, source: str, origin: str) -> int:
    async with db.cursor() as cursor:
        await cursor.execute(FOREIGN_PAYLOADS, (source, origin))
        row = await cursor.fetchone()
    return int(row[0]) if row is not None else 0


async def canonical_payload_ids(db: AsyncConnection, source: str, origin: str) -> list[int]:
    async with db.cursor() as cursor:
        await cursor.execute(CANONICAL_PAYLOADS, (source, origin, origin))
        rows = await cursor.fetchall()
    return [int(row[0]) for row in rows]


async def foreign_only_rows(db: AsyncConnection, source: str, origin: str) -> dict[str, list[str]]:
    async with db.cursor() as cursor:
        await cursor.execute(FOREIGN_ONLY_ROWS, {"source": source, "origin": origin})
        rows = await cursor.fetchall()
    grouped: defaultdict[str, list[str]] = defaultdict(list)
    for entity, key in rows:
        grouped[str(entity)].append(str(key))
    return dict(grouped)


async def prune_foreign_rows(db: AsyncConnection, source: str, origin: str) -> Pruned:
    orphans = await foreign_only_rows(db, source, origin)
    deleted: dict[str, int] = {}
    async with db.cursor() as cursor:
        for entity, statements in PRUNABLE:
            keys = orphans.pop(entity, [])
            if not keys:
                continue
            for statement in statements:
                await cursor.execute(statement, (keys,))
            deleted[entity] = cursor.rowcount
        await cursor.execute(FOREIGN_LINKS, (source, origin))
        links_removed = cursor.rowcount
    unlinked = {entity: len(keys) for entity, keys in orphans.items()}
    return Pruned(deleted, unlinked, links_removed)
