from collections.abc import Sequence
from dataclasses import dataclass
from typing import LiteralString

from psycopg import AsyncConnection


@dataclass(frozen=True)
class Check:
    title: str
    query: LiteralString
    blocking: bool


@dataclass(frozen=True)
class Section:
    title: str
    columns: tuple[str, ...]
    rows: tuple[tuple[object, ...], ...]
    blocking: bool

    @property
    def failed(self) -> bool:
        return self.blocking and bool(self.rows)


CHECKS = (
    Check(
        "Sources mixing origins",
        "SELECT source, origin, linked_rows FROM mart.dq_source_origin_mix ORDER BY source, origin",
        blocking=True,
    ),
    Check(
        "Unmapped external codes",
        "SELECT namespace, code, problem FROM mart.dq_unmapped_code ORDER BY namespace, code",
        blocking=True,
    ),
    Check(
        "Organizations without a type",
        "SELECT id, name_en, source_type FROM mart.dq_untyped_organization ORDER BY name_en",
        blocking=True,
    ),
    Check(
        "Curation waiting for its source record",
        "SELECT namespace, code, slug FROM mart.dq_unapplied_curation ORDER BY namespace, code",
        blocking=False,
    ),
    Check(
        "Missing name_ja by entity",
        "SELECT entity, count(*) FROM mart.dq_missing_name_ja GROUP BY entity ORDER BY entity",
        blocking=False,
    ),
    Check(
        "Most relevant names missing name_ja",
        "SELECT entity, key, name_en, relevance FROM mart.dq_missing_name_ja "
        "ORDER BY relevance DESC, name_en LIMIT 25",
        blocking=False,
    ),
    Check(
        "Source freshness",
        "SELECT source, last_status, last_finished_at, last_succeeded_at, last_error "
        "FROM mart.dq_source_freshness ORDER BY source",
        blocking=False,
    ),
)


async def run_check(db: AsyncConnection, check: Check) -> Section:
    async with db.cursor() as cursor:
        await cursor.execute(check.query)
        rows = await cursor.fetchall()
        columns = tuple(column.name for column in cursor.description or ())
    return Section(check.title, columns, tuple(tuple(row) for row in rows), check.blocking)


async def quality_report(db: AsyncConnection) -> list[Section]:
    return [await run_check(db, check) for check in CHECKS]


def render_section(section: Section) -> str:
    marker = "FAIL" if section.failed else "ok"
    lines = [f"== {section.title} ({len(section.rows)}) [{marker}]"]
    if section.rows:
        lines.append("  " + " | ".join(section.columns))
        lines += [
            "  " + " | ".join("" if value is None else str(value) for value in row)
            for row in section.rows
        ]
    return "\n".join(lines)


def render_report(sections: Sequence[Section]) -> str:
    return "\n\n".join(render_section(section) for section in sections)
