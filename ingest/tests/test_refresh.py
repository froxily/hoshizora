from collections.abc import Iterator
from datetime import date

import psycopg
import pytest

from hoshizora_ingest.analytics.refresh import refresh_marts
from hoshizora_ingest.db import connections

from conftest import Database
from fakes import execute, query


@pytest.fixture
def unpopulated_mart(clean_database: Database) -> Iterator[Database]:
    with psycopg.connect(clean_database.owner_url, autocommit=True) as connection:
        connection.execute(
            "CREATE MATERIALIZED VIEW mart.refresh_probe AS SELECT 1 AS id WITH NO DATA"
        )
        connection.execute("CREATE UNIQUE INDEX refresh_probe_key ON mart.refresh_probe (id)")
    try:
        yield clean_database
    finally:
        with psycopg.connect(clean_database.owner_url, autocommit=True) as connection:
            connection.execute("DROP MATERIALIZED VIEW mart.refresh_probe")


@pytest.mark.anyio
async def test_writer_refreshes_every_mart_from_current_core_rows(clean_database: Database) -> None:
    execute(
        clean_database.owner_url,
        "INSERT INTO core.geomagnetic_index (index, observed_at, value) "
        "VALUES ('kp', '2026-10-16 03:00+00', 5.33), ('kp', '2026-10-16 06:00+00', 4.0) "
        "RETURNING index",
        (),
    )

    async with connections(clean_database.writer_url) as db:
        refreshed = await refresh_marts(db.data)

    marts = query(
        clean_database.owner_url, "SELECT matviewname FROM pg_matviews WHERE schemaname = 'mart'"
    )
    assert set(refreshed.views) == {str(row[0]) for row in marts}
    assert query(clean_database.owner_url, "SELECT day, kp_max, g_scale FROM mart.kp_daily") == [
        (date(2026, 10, 16), 5.33, 1)
    ]


@pytest.mark.anyio
async def test_unpopulated_marts_are_filled_without_concurrency(unpopulated_mart: Database) -> None:
    async with connections(unpopulated_mart.writer_url) as db:
        refreshed = await refresh_marts(db.data)

    assert "refresh_probe" in refreshed.views
    assert query(unpopulated_mart.owner_url, "SELECT id FROM mart.refresh_probe") == [(1,)]
