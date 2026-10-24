from collections.abc import Generator, Iterable, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, LiteralString, cast

from psycopg import AsyncConnection, sql

from hoshizora_ingest.sources.base import StoreResult

ARRAY_SUFFIX = "[]"

_link_every_row: ContextVar[bool] = ContextVar("link_every_row", default=False)


@contextmanager
def linking_every_row(*, enabled: bool = True) -> Generator[None]:
    token = _link_every_row.set(enabled)
    try:
        yield
    finally:
        _link_every_row.reset(token)


def links_every_row() -> bool:
    return _link_every_row.get()


@dataclass(frozen=True)
class Column:
    name: LiteralString
    pg_type: LiteralString

    @property
    def is_array(self) -> bool:
        return self.pg_type.endswith(ARRAY_SUFFIX)

    @property
    def wire_type(self) -> LiteralString:
        return "text" if self.is_array else self.pg_type


@dataclass(frozen=True)
class TableSpec:
    schema: LiteralString
    name: LiteralString
    columns: tuple[Column, ...]
    key: tuple[LiteralString, ...]
    guard: LiteralString | None = None
    insert_only: bool = False

    @property
    def entity(self) -> str:
        return f"{self.schema}.{self.name}"

    @property
    def updatable(self) -> tuple[Column, ...]:
        return tuple(column for column in self.columns if column.name not in self.key)


def array_literal(values: Iterable[object]) -> str:
    escaped = (str(value).replace("\\", "\\\\").replace('"', '\\"') for value in values)
    return "{" + ",".join(f'"{value}"' for value in escaped) + "}"


def wire_value(value: object, column: Column) -> object:
    if column.is_array and isinstance(value, tuple):
        return array_literal(cast("tuple[object, ...]", value))
    return value


def dedupe_by_key[R](rows: Iterable[R], spec: TableSpec) -> list[R]:
    unique: dict[tuple[Any, ...], R] = {}
    for row in rows:
        unique[tuple(getattr(row, name) for name in spec.key)] = row
    return list(unique.values())


def _selected(column: Column) -> sql.Composable:
    identifier = sql.Identifier("u", column.name)
    if column.is_array:
        return sql.SQL("{}::{}").format(identifier, sql.SQL(column.pg_type))
    return identifier


def upsert_statement(spec: TableSpec) -> sql.Composed:
    table = sql.Identifier(spec.schema, spec.name)
    names = sql.SQL(", ").join(sql.Identifier(column.name) for column in spec.columns)
    selected = sql.SQL(", ").join(_selected(column) for column in spec.columns)
    arrays = sql.SQL(", ").join(
        sql.SQL("%s::{}[]").format(sql.SQL(column.wire_type)) for column in spec.columns
    )
    keys = sql.SQL(", ").join(sql.Identifier(name) for name in spec.key)
    returning = sql.SQL("concat_ws('|', {})").format(
        sql.SQL(", ").join(sql.Identifier("t", name) for name in spec.key)
    )
    if spec.insert_only or not spec.updatable:
        conflict = sql.SQL("DO NOTHING")
    else:
        assignments = sql.SQL(", ").join(
            sql.SQL("{} = EXCLUDED.{}").format(
                sql.Identifier(column.name), sql.Identifier(column.name)
            )
            for column in spec.updatable
        )
        current = sql.SQL(", ").join(sql.Identifier("t", c.name) for c in spec.updatable)
        incoming = sql.SQL(", ").join(sql.Identifier("excluded", c.name) for c in spec.updatable)
        changed = sql.SQL("ROW({}) IS DISTINCT FROM ROW({})").format(current, incoming)
        if spec.guard is not None:
            changed = sql.SQL("{} AND ({})").format(changed, sql.SQL(spec.guard))
        conflict = sql.SQL("DO UPDATE SET {} WHERE {}").format(assignments, changed)
    return sql.SQL(
        "INSERT INTO {table} AS t ({names}) "
        "SELECT {selected} FROM unnest({arrays}) AS u({names}) "
        "ON CONFLICT ({keys}) {conflict} "
        "RETURNING {returning}"
    ).format(
        table=table,
        names=names,
        selected=selected,
        arrays=arrays,
        keys=keys,
        conflict=conflict,
        returning=returning,
    )


def column_arrays(rows: Sequence[object], spec: TableSpec) -> list[list[object]]:
    return [
        [wire_value(getattr(row, column.name), column) for row in rows] for column in spec.columns
    ]


async def upsert(db: AsyncConnection, spec: TableSpec, rows: Sequence[object]) -> list[str]:
    unique = dedupe_by_key(rows, spec)
    if not unique:
        return []
    async with db.cursor() as cursor:
        await cursor.execute(upsert_statement(spec), column_arrays(unique, spec))
        changed = await cursor.fetchall()
    return [str(row[0]) for row in changed]


async def row_keys(db: AsyncConnection, spec: TableSpec, rows: Sequence[object]) -> list[str]:
    unique = dedupe_by_key(rows, spec)
    if not unique:
        return []
    by_name = {column.name: column for column in spec.columns}
    key_columns = tuple(by_name[name] for name in spec.key)
    names = sql.SQL(", ").join(sql.Identifier(column.name) for column in key_columns)
    arrays = sql.SQL(", ").join(
        sql.SQL("%s::{}[]").format(sql.SQL(column.wire_type)) for column in key_columns
    )
    statement = sql.SQL(
        "SELECT concat_ws('|', {names}) FROM unnest({arrays}) AS u({names})"
    ).format(names=names, arrays=arrays)
    async with db.cursor() as cursor:
        await cursor.execute(
            statement,
            column_arrays(unique, TableSpec(spec.schema, spec.name, key_columns, spec.key)),
        )
        found = await cursor.fetchall()
    return [str(row[0]) for row in found]


async def record_lineage(
    db: AsyncConnection, entity: str, keys: Sequence[str], payload_id: int
) -> None:
    if not keys:
        return
    await db.execute(
        """
        INSERT INTO core.source_record (entity, entity_key, payload_id)
        SELECT %s, key, %s FROM unnest(%s::text[]) AS key
        ON CONFLICT DO NOTHING
        """,
        (entity, payload_id, list(keys)),
    )


async def upsert_with_lineage(
    db: AsyncConnection, spec: TableSpec, rows: Sequence[object], payload_id: int
) -> StoreResult:
    changed = await upsert(db, spec, rows)
    linked = await row_keys(db, spec, rows) if links_every_row() else changed
    await record_lineage(db, spec.entity, linked, payload_id)
    return StoreResult(rows_in=len(rows), rows_changed=len(changed))


async def delete_missing(
    db: AsyncConnection,
    spec: TableSpec,
    rows: Sequence[object],
    scope: sql.Composable | None = None,
) -> int:
    keys = sql.SQL(", ").join(sql.Identifier(name) for name in spec.key)
    key_columns = tuple(column for column in spec.columns if column.name in spec.key)
    arrays = sql.SQL(", ").join(
        sql.SQL("%s::{}[]").format(sql.SQL(column.wire_type)) for column in key_columns
    )
    condition = sql.SQL("ROW({}) NOT IN (SELECT * FROM unnest({}))").format(keys, arrays)
    if scope is not None:
        condition = sql.SQL("{} AND {}").format(condition, scope)
    statement = sql.SQL("DELETE FROM {} WHERE {}").format(
        sql.Identifier(spec.schema, spec.name), condition
    )
    values = [[getattr(row, column.name) for row in rows] for column in key_columns]
    async with db.cursor() as cursor:
        await cursor.execute(statement, values)
        return cursor.rowcount
