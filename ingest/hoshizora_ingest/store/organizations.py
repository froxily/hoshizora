from collections.abc import Iterable, Sequence
from typing import LiteralString

from psycopg import AsyncConnection

from hoshizora_ingest.sources.base import StoreResult
from hoshizora_ingest.store.upsert import links_every_row, record_lineage
from hoshizora_ingest.transform.launch_library import AgencyRow

LL2_AGENCY = "ll2.agency"
ORGANIZATION_ENTITY = "core.organization"

UPDATE_AGENCIES = """
UPDATE core.organization o
SET source_name = i.name,
    abbrev = i.abbrev,
    source_type = i.source_type,
    founding_year = CASE WHEN i.complete THEN i.founding_year ELSE o.founding_year END
FROM unnest(%s::text[], %s::text[], %s::text[], %s::text[], %s::int[], %s::bool[])
    AS i(code, name, abbrev, source_type, founding_year, complete)
JOIN core.organization_alias a ON a.namespace = 'll2.agency' AND a.code = i.code
WHERE a.organization_id = o.id
  AND ROW(o.source_name, o.abbrev, o.source_type, o.founding_year) IS DISTINCT FROM
      ROW(i.name, i.abbrev, i.source_type,
          CASE WHEN i.complete THEN i.founding_year ELSE o.founding_year END)
RETURNING o.id
"""

LINK_PARENTS = """
WITH unique_names AS (
    SELECT source_name, min(id) AS id
    FROM core.organization
    WHERE source_name IS NOT NULL
    GROUP BY source_name
    HAVING count(*) = 1
)
UPDATE core.organization child
SET parent_id = parent.id
FROM unnest(%s::text[], %s::text[]) AS i(code, parent_name)
JOIN core.organization_alias a ON a.namespace = 'll2.agency' AND a.code = i.code
JOIN unique_names parent ON parent.source_name = i.parent_name
WHERE child.id = a.organization_id
  AND child.parent_id IS DISTINCT FROM parent.id
  AND parent.id <> child.id
RETURNING child.id
"""

ADD_COUNTRIES = """
INSERT INTO core.organization_country (organization_id, country_code)
SELECT a.organization_id, i.country
FROM unnest(%s::text[], %s::text[]) AS i(code, country)
JOIN core.organization_alias a ON a.namespace = 'll2.agency' AND a.code = i.code
JOIN core.country c ON c.code = i.country
ON CONFLICT DO NOTHING
RETURNING organization_id
"""

CREATE_CURATED_ONLY = """
SELECT c.code, c.curated_name_en, c.type_override
FROM core.organization_curation c
WHERE c.namespace = 'hoshizora'
  AND NOT EXISTS (
      SELECT FROM core.organization_alias a WHERE a.namespace = c.namespace AND a.code = c.code
  )
ORDER BY c.code
"""

APPLY_FIELDS = """
UPDATE core.organization o
SET slug = c.slug,
    curated_name_en = c.curated_name_en,
    name_ja = c.name_ja,
    name_ja_source = c.name_ja_source,
    type_override = c.type_override
FROM core.organization_alias a
JOIN core.organization_curation c ON c.namespace = a.namespace AND c.code = a.code
WHERE a.organization_id = o.id
  AND ROW(o.slug, o.curated_name_en, o.name_ja, o.name_ja_source, o.type_override)
      IS DISTINCT FROM ROW(c.slug, c.curated_name_en, c.name_ja, c.name_ja_source, c.type_override)
"""

APPLY_COUNTRIES = """
INSERT INTO core.organization_country (organization_id, country_code)
SELECT a.organization_id, country
FROM core.organization_curation c
JOIN core.organization_alias a ON a.namespace = c.namespace AND a.code = c.code
CROSS JOIN unnest(c.countries) AS country
ON CONFLICT DO NOTHING
"""

SYNC_PROGRAM_MEMBERS = """
WITH desired AS (
    SELECT DISTINCT program, a.organization_id
    FROM core.organization_curation c
    JOIN core.organization_alias a ON a.namespace = c.namespace AND a.code = c.code
    CROSS JOIN unnest(c.programs) AS program
),
removed AS (
    DELETE FROM core.program_member m
    WHERE NOT EXISTS (
        SELECT FROM desired d
        WHERE d.program = m.program_slug AND d.organization_id = m.organization_id
    )
)
INSERT INTO core.program_member (program_slug, organization_id)
SELECT program, organization_id FROM desired
ON CONFLICT DO NOTHING
"""

LINK_CODES_TO_ORGANIZATIONS = """
INSERT INTO core.organization_alias (namespace, code, organization_id)
SELECT e.namespace, e.code, o.id
FROM core.external_code e
JOIN core.organization o ON o.slug = e.organization_slug
ON CONFLICT (namespace, code) DO UPDATE
SET organization_id = EXCLUDED.organization_id
WHERE core.organization_alias.organization_id <> EXCLUDED.organization_id
"""

SYNC_COUNTRY_ALIASES = """
WITH desired AS (
    SELECT e.namespace, e.code, country AS country_code
    FROM core.external_code e
    CROSS JOIN unnest(e.country_codes) AS country
),
removed AS (
    DELETE FROM core.country_alias c
    WHERE NOT EXISTS (
        SELECT FROM desired d
        WHERE d.namespace = c.namespace AND d.code = c.code AND d.country_code = c.country_code
    )
)
INSERT INTO core.country_alias (namespace, code, country_code)
SELECT namespace, code, country_code FROM desired
ON CONFLICT DO NOTHING
"""

APPLY_STEPS: tuple[LiteralString, ...] = (
    APPLY_FIELDS,
    APPLY_COUNTRIES,
    SYNC_PROGRAM_MEMBERS,
    LINK_CODES_TO_ORGANIZATIONS,
    SYNC_COUNTRY_ALIASES,
)


async def create_curated_only(db: AsyncConnection) -> int:
    async with db.cursor() as cursor:
        await cursor.execute(CREATE_CURATED_ONLY)
        missing = await cursor.fetchall()
        for code, name_en, type_override in missing:
            await cursor.execute(
                "INSERT INTO core.organization (curated_name_en, type_override) "
                "VALUES (%s, %s) RETURNING id",
                (name_en, type_override),
            )
            created = await cursor.fetchone()
            if created is None:
                message = f"Could not create curated organization {code}"
                raise LookupError(message)
            await cursor.execute(
                "INSERT INTO core.organization_alias (namespace, code, organization_id) "
                "VALUES ('hoshizora', %s, %s)",
                (code, created[0]),
            )
    return len(missing)


async def apply_curation(db: AsyncConnection) -> int:
    changed = await create_curated_only(db)
    async with db.cursor() as cursor:
        for step in APPLY_STEPS:
            await cursor.execute(step)
            changed += max(cursor.rowcount, 0)
    return changed


async def observe_codes(db: AsyncConnection, namespace: str, codes: set[str]) -> None:
    if not codes:
        return
    await db.execute(
        """
        INSERT INTO core.observed_code (namespace, code)
        SELECT %s, code FROM unnest(%s::text[]) AS code
        ON CONFLICT (namespace, code) DO UPDATE SET last_seen = now()
        """,
        (namespace, sorted(codes)),
    )


def prefer_complete(rows: Iterable[AgencyRow]) -> list[AgencyRow]:
    chosen: dict[int, AgencyRow] = {}
    for row in rows:
        current = chosen.get(row.ll2_id)
        if current is None or (row.complete and not current.complete):
            chosen[row.ll2_id] = row
    return list(chosen.values())


async def organization_ids(
    db: AsyncConnection, namespace: str, codes: Iterable[str]
) -> dict[str, int]:
    async with db.cursor() as cursor:
        await cursor.execute(
            "SELECT code, organization_id FROM core.organization_alias "
            "WHERE namespace = %s AND code = ANY(%s)",
            (namespace, sorted(set(codes))),
        )
        rows = await cursor.fetchall()
    return {str(code): int(organization_id) for code, organization_id in rows}


async def known_countries(db: AsyncConnection, codes: Iterable[str]) -> set[str]:
    async with db.cursor() as cursor:
        await cursor.execute(
            "SELECT code FROM core.country WHERE code = ANY(%s)", (sorted(set(codes)),)
        )
        rows = await cursor.fetchall()
    return {str(row[0]) for row in rows}


async def create_missing_agencies(db: AsyncConnection, rows: Sequence[AgencyRow]) -> list[int]:
    existing = await organization_ids(db, LL2_AGENCY, (str(row.ll2_id) for row in rows))
    created: list[int] = []
    async with db.cursor() as cursor:
        for row in rows:
            if str(row.ll2_id) in existing:
                continue
            await cursor.execute(
                "INSERT INTO core.organization (source_name, abbrev, source_type, founding_year) "
                "VALUES (%s, %s, %s, %s) RETURNING id",
                (row.name, row.abbrev, row.source_type, row.founding_year),
            )
            inserted = await cursor.fetchone()
            if inserted is None:
                message = f"Could not create organization for LL2 agency {row.ll2_id}"
                raise LookupError(message)
            await cursor.execute(
                "INSERT INTO core.organization_alias (namespace, code, organization_id) "
                "VALUES (%s, %s, %s)",
                (LL2_AGENCY, str(row.ll2_id), inserted[0]),
            )
            created.append(int(inserted[0]))
    return created


async def returned_ids(
    db: AsyncConnection, statement: LiteralString, params: Sequence[object]
) -> set[int]:
    async with db.cursor() as cursor:
        await cursor.execute(statement, params)
        rows = await cursor.fetchall()
    return {int(row[0]) for row in rows}


async def store_agencies(
    db: AsyncConnection, rows: Sequence[AgencyRow], payload_id: int
) -> StoreResult:
    agencies = prefer_complete(rows)
    if not agencies:
        return StoreResult(0, 0)
    changed = set(await create_missing_agencies(db, agencies))
    changed |= await returned_ids(
        db,
        UPDATE_AGENCIES,
        (
            [str(row.ll2_id) for row in agencies],
            [row.name for row in agencies],
            [row.abbrev for row in agencies],
            [row.source_type for row in agencies],
            [row.founding_year for row in agencies],
            [row.complete for row in agencies],
        ),
    )
    complete = [row for row in agencies if row.complete]
    with_parent = [row for row in complete if row.parent_name is not None]
    changed |= await returned_ids(
        db,
        LINK_PARENTS,
        ([str(row.ll2_id) for row in with_parent], [row.parent_name for row in with_parent]),
    )
    memberships = [(str(row.ll2_id), country) for row in complete for country in row.countries]
    known = await known_countries(db, (country for _, country in memberships))
    changed |= await returned_ids(
        db,
        ADD_COUNTRIES,
        (
            [code for code, country in memberships if country in known],
            [country for _, country in memberships if country in known],
        ),
    )
    await observe_codes(db, "ll2.country", {country for _, country in memberships} - known)
    await observe_codes(
        db, "ll2.agency_type", {row.source_type for row in agencies if row.source_type is not None}
    )
    linked = set(changed)
    if links_every_row():
        everyone = await organization_ids(db, LL2_AGENCY, (str(row.ll2_id) for row in agencies))
        linked |= set(everyone.values())
    await record_lineage(db, ORGANIZATION_ENTITY, [str(id_) for id_ in sorted(linked)], payload_id)
    curated = await apply_curation(db)
    return StoreResult(rows_in=len(agencies), rows_changed=len(changed) + curated)
