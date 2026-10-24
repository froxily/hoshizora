import re
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import LiteralString, cast

import structlog
from psycopg import AsyncConnection, IsolationLevel
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from hoshizora_ingest.facts.params import Row, moment, number, param_value
from hoshizora_ingest.facts.scoring import Signals, score
from hoshizora_ingest.facts.spec import Template, TemplateError
from hoshizora_ingest.jsontypes import JsonValue

log = structlog.get_logger()

READY = "succeeded"
REF_ENTITY = re.compile(r"^(core|mart)\.[a-z][a-z0-9_]*$")

SOURCE_STATUS = """
SELECT s.source,
       CASE WHEN EXISTS (SELECT 1 FROM mart.dq_source_origin_mix m WHERE m.source = s.source)
            THEN 'mixed_origins'
            ELSE s.last_run_status
       END
FROM mart.source_status s
"""

UPSERT_TEMPLATE = """
INSERT INTO facts.template AS t (key, module, text_en, text_ja, min_score)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (key) DO UPDATE
SET module = EXCLUDED.module, text_en = EXCLUDED.text_en, text_ja = EXCLUDED.text_ja,
    min_score = EXCLUDED.min_score, updated_at = now()
WHERE (t.module, t.text_en, t.text_ja, t.min_score)
    IS DISTINCT FROM (EXCLUDED.module, EXCLUDED.text_en, EXCLUDED.text_ja, EXCLUDED.min_score)
"""

UPSERT_FACT = """
INSERT INTO facts.fact AS f (
    template_key, entity_type, entity_key, params, score, kind, source_refs,
    generated_at, valid_until
)
VALUES (%s, %s, %s, %s, %s, 'computed', %s, %s, %s)
ON CONFLICT (template_key, entity_type, entity_key) DO UPDATE
SET params = EXCLUDED.params, score = EXCLUDED.score, kind = 'computed',
    source_refs = EXCLUDED.source_refs, citation_url = NULL,
    generated_at = EXCLUDED.generated_at, valid_until = EXCLUDED.valid_until
RETURNING id
"""

DELETE_UNKNOWN_FACTS = "DELETE FROM facts.fact WHERE NOT (template_key = ANY(%s))"
DELETE_UNKNOWN_TEMPLATES = "DELETE FROM facts.template WHERE NOT (key = ANY(%s))"
DELETE_STALE_FACTS = "DELETE FROM facts.fact WHERE template_key = %s AND NOT (id = ANY(%s))"
DELETE_SKIPPED_FACTS = "DELETE FROM facts.fact WHERE template_key = ANY(%s)"
DELETE_EXPIRED_FACTS = "DELETE FROM facts.fact WHERE valid_until <= %s"


@dataclass(frozen=True)
class Candidate:
    entity_type: str | None
    entity_key: str | None
    params: dict[str, JsonValue]
    score: float
    source_refs: list[dict[str, str]]
    valid_until: datetime


@dataclass(frozen=True)
class Skipped:
    source: str
    status: str | None
    templates: tuple[str, ...]


@dataclass(frozen=True)
class Generated:
    templates: int
    facts: int
    removed: int
    skipped: tuple[Skipped, ...]


def hour_start(moment_: datetime) -> datetime:
    return moment_.astimezone(UTC).replace(minute=0, second=0, microsecond=0)


def source_refs(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        message = "source_refs must be a non-empty array"
        raise TemplateError(message)
    refs: list[dict[str, str]] = []
    for item in cast("list[object]", value):
        if not isinstance(item, dict):
            message = f"source ref {item!r} is not an object"
            raise TemplateError(message)
        ref = cast("dict[str, object]", item)
        entity, key = ref.get("entity"), ref.get("key")
        if not isinstance(entity, str) or not REF_ENTITY.match(entity) or not isinstance(key, str):
            message = f"source ref {ref!r} needs a core or mart entity and a string key"
            raise TemplateError(message)
        refs.append({"entity": entity, "key": key})
    return refs


def optional_text(row: Row, name: str) -> str | None:
    value = row.get(name)
    return None if value is None else str(value)


def signals(row: Row) -> Signals:
    percentile = row.get("percentile")
    event_at = row.get("event_at")
    return Signals(
        percentile=None if percentile is None else number(percentile),
        is_record=bool(row.get("is_record")),
        is_first=bool(row.get("is_first")),
        event_at=None if event_at is None else moment(event_at),
    )


def candidate(template: Template, row: Row, as_of: datetime) -> Candidate:
    try:
        valid_until = row.get("valid_until")
        return Candidate(
            entity_type=optional_text(row, "entity_type"),
            entity_key=optional_text(row, "entity_key"),
            params={name: param_value(param, row) for name, param in template.params.items()},
            score=score(signals(row), template.scoring, as_of),
            source_refs=source_refs(row.get("source_refs")),
            valid_until=as_of + template.valid_for if valid_until is None else moment(valid_until),
        )
    except TemplateError as broken:
        message = f"{template.key}: {broken}"
        raise TemplateError(message) from broken


async def source_statuses(db: AsyncConnection) -> dict[str, str | None]:
    async with db.cursor() as cursor:
        await cursor.execute(SOURCE_STATUS)
        rows = await cursor.fetchall()
    return {str(source): None if status is None else str(status) for source, status in rows}


def gate(
    templates: Iterable[Template], statuses: Mapping[str, str | None]
) -> tuple[list[Template], tuple[Skipped, ...]]:
    ready: list[Template] = []
    waiting: defaultdict[str, list[str]] = defaultdict(list)
    for template in templates:
        blocked = [source for source in template.requires if statuses.get(source) != READY]
        if blocked:
            for source in blocked:
                waiting[source].append(template.key)
        else:
            ready.append(template)
    skipped = tuple(
        Skipped(source, statuses.get(source), tuple(keys)) for source, keys in waiting.items()
    )
    return ready, skipped


async def template_candidates(
    db: AsyncConnection, template: Template, as_of: datetime
) -> list[Candidate]:
    async with db.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(cast("LiteralString", template.query), {"as_of": as_of})
        rows = await cursor.fetchall()
    found = [candidate(template, row, as_of) for row in rows]
    entities = [(c.entity_type, c.entity_key) for c in found]
    if len(set(entities)) != len(entities):
        message = f"{template.key}: query returns one entity more than once"
        raise TemplateError(message)
    return found


async def read_candidates(
    db: AsyncConnection, templates: Sequence[Template], as_of: datetime
) -> dict[str, list[Candidate]]:
    await db.commit()
    await db.set_read_only(True)
    await db.set_isolation_level(IsolationLevel.REPEATABLE_READ)
    try:
        await db.execute("SET LOCAL TIME ZONE 'UTC'")
        found = {t.key: await template_candidates(db, t, as_of) for t in templates}
    finally:
        await db.rollback()
        await db.set_read_only(None)
        await db.set_isolation_level(None)
    return found


async def sync_templates(db: AsyncConnection, templates: Sequence[Template]) -> int:
    keys = [template.key for template in templates]
    async with db.cursor() as cursor:
        for template in templates:
            await cursor.execute(
                UPSERT_TEMPLATE,
                (
                    template.key,
                    template.module,
                    template.text.en,
                    template.text.ja,
                    template.min_score,
                ),
            )
        await cursor.execute(DELETE_UNKNOWN_FACTS, (keys,))
        removed = cursor.rowcount
        await cursor.execute(DELETE_UNKNOWN_TEMPLATES, (keys,))
    return removed


async def store_facts(
    db: AsyncConnection, template: Template, candidates: Sequence[Candidate], as_of: datetime
) -> tuple[int, int]:
    ids: list[int] = []
    async with db.cursor() as cursor:
        for found in candidates:
            await cursor.execute(
                UPSERT_FACT,
                (
                    template.key,
                    found.entity_type,
                    found.entity_key,
                    Jsonb(found.params),
                    found.score,
                    Jsonb(found.source_refs),
                    as_of,
                    found.valid_until,
                ),
            )
            row = await cursor.fetchone()
            if row is not None:
                ids.append(int(row[0]))
        await cursor.execute(DELETE_STALE_FACTS, (template.key, ids))
        return len(ids), cursor.rowcount


async def generate_facts(
    db: AsyncConnection, templates: Sequence[Template], as_of: datetime
) -> Generated:
    ready, skipped = gate(templates, await source_statuses(db))
    found = await read_candidates(db, ready, as_of)
    removed = await sync_templates(db, templates)
    stored = 0
    for template in ready:
        shown = [c for c in found[template.key] if c.score >= template.min_score]
        kept, stale = await store_facts(db, template, shown, as_of)
        stored, removed = stored + kept, removed + stale
    async with db.cursor() as cursor:
        held = sorted({key for skip in skipped for key in skip.templates})
        await cursor.execute(DELETE_SKIPPED_FACTS, (held,))
        removed += cursor.rowcount
        await cursor.execute(DELETE_EXPIRED_FACTS, (as_of,))
        removed += cursor.rowcount
    await db.commit()
    for skip in skipped:
        log.warning(
            "facts skipped",
            source=skip.source,
            status=skip.status,
            templates=list(skip.templates),
        )
    log.info("facts generated", templates=len(ready), facts=stored, removed=removed)
    return Generated(len(ready), stored, removed, skipped)
