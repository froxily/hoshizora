import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import LiteralString, cast

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

from hoshizora_ingest.runtime import event_loop_factory

MIGRATIONS = Path(__file__).resolve().parents[2] / "db" / "migration"
POSTGRES_IMAGE = "postgres:18.6-trixie"
WRITER = "ingest_test"
VERSIONED = re.compile(r"^V(\d+)__.+\.sql$")


@dataclass(frozen=True)
class Database:
    owner_url: str
    writer_url: str


def migration_version(path: Path) -> int | None:
    match = VERSIONED.match(path.name)
    return int(match.group(1)) if match is not None else None


def migration_files() -> list[Path]:
    versioned = [
        (version, path)
        for path in MIGRATIONS.iterdir()
        if (version := migration_version(path)) is not None
    ]
    return [path for _, path in sorted(versioned)]


def execute_script(url: str, script: str) -> None:
    with psycopg.connect(url, autocommit=True) as connection:
        connection.execute(cast("LiteralString", script))


@pytest.fixture
def anyio_backend() -> tuple[str, dict[str, object]]:
    options: dict[str, object] = {}
    factory = event_loop_factory()
    if factory is not None:
        options["loop_factory"] = factory
    return ("asyncio", options)


@pytest.fixture(scope="session")
def database() -> Iterator[Database]:
    with PostgresContainer(POSTGRES_IMAGE, driver=None) as container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(5432)
        owner_url = (
            f"postgresql://{container.username}:{container.password}"
            f"@{host}:{port}/{container.dbname}"
        )
        for path in migration_files():
            execute_script(owner_url, path.read_text(encoding="utf-8"))
        execute_script(
            owner_url,
            f"CREATE ROLE {WRITER} LOGIN PASSWORD '{WRITER}' IN ROLE hoshizora_writer;"
            "CREATE TABLE core.probe_item (id integer PRIMARY KEY, name text NOT NULL);",
        )
        yield Database(
            owner_url=owner_url,
            writer_url=f"postgresql://{WRITER}:{WRITER}@{host}:{port}/{container.dbname}",
        )


@pytest.fixture
def clean_database(database: Database) -> Database:
    with psycopg.connect(database.owner_url, autocommit=True) as connection:
        tables = connection.execute(
            "SELECT format('%I.%I', schemaname, tablename) FROM pg_tables "
            "WHERE schemaname IN ('raw', 'core', 'mart', 'facts') "
            "AND format('%I.%I', schemaname, tablename) <> 'raw.retention_policy'"
        ).fetchall()
        if tables:
            names = ", ".join(str(row[0]) for row in tables)
            connection.execute(cast("LiteralString", f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
    return database
