import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

import httpx
import pytest
import respx

from hoshizora_ingest.db import connections
from hoshizora_ingest.pipeline import RunEnvironment, RunOutcome, run_source, utc_now
from hoshizora_ingest.raw.runs import RunStatus
from hoshizora_ingest.sources.exoplanets.adapter import BASE_URL, ExoplanetArchiveSource
from hoshizora_ingest.sources.exoplanets.models import PlanetTable
from hoshizora_ingest.sources.model import unexpected_fields
from hoshizora_ingest.transform.exoplanets import normalize

from conftest import Database
from fakes import RecordingSleep, query, scalar

FIXTURES = Path(__file__).parent / "fixtures" / "exoplanet-archive"
FIRST_RUN = utc_now()

pytestmark = pytest.mark.anyio


def planets() -> list[dict[str, Any]]:
    return cast("list[dict[str, Any]]", json.loads((FIXTURES / "planets.json").read_text("utf-8")))


def larger_table(copies: int) -> list[dict[str, Any]]:
    table = planets()
    return table + [
        {**planet, "pl_name": f"{planet['pl_name']} ({copy})"}
        for copy in range(1, copies)
        for planet in table
    ]


async def ingest(
    database: Database, body: object, *, at: datetime = FIRST_RUN
) -> tuple[RunOutcome, respx.Route]:
    with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
        route = router.get("/TAP/sync").mock(return_value=httpx.Response(200, json=body))
        async with connections(database.writer_url) as db:
            env = RunEnvironment(
                db=db.data,
                log_db=db.log,
                user_agent="Hoshizora/test",
                clock=lambda: at,
                sleep=RecordingSleep(),
            )
            return await run_source(ExoplanetArchiveSource(), env), route


def test_the_fixture_has_no_unexpected_fields() -> None:
    assert unexpected_fields(PlanetTable.model_validate(planets())) == set()


def test_normalizes_locales_flags_and_missing_values() -> None:
    rows = {row.name: row for row in normalize(PlanetTable.model_validate(planets())).planets}

    assert rows["ZTF J1230-2655 b"].discovery_locale == "ground"
    assert rows["TRAPPIST-1 e"].discovery_locale == "multiple locales"
    assert rows["BD-06 1339 b"].radius_earth is None
    assert rows["BD-06 1339 b"].controversial
    assert rows["OGLE-2016-BLG-1227L b"].distance_pc is None
    assert rows["Proxima Cen b"].distance_pc == pytest.approx(1.30119)


async def test_loads_the_table_once_a_day_and_skips_unchanged_content(
    clean_database: Database,
) -> None:
    first, _ = await ingest(clean_database, planets())
    same_day, same_day_route = await ingest(
        clean_database, planets(), at=FIRST_RUN + timedelta(hours=6)
    )
    next_day, next_day_route = await ingest(
        clean_database, planets(), at=FIRST_RUN + timedelta(days=1, hours=1)
    )

    url = clean_database.owner_url
    assert first.status is RunStatus.SUCCEEDED
    assert scalar(url, "SELECT count(*) FROM core.exoplanet") == len(planets())
    assert not same_day_route.called
    assert next_day_route.call_count == 1
    assert (next_day.stats.payloads_new, next_day.stats.rows_upserted) == (0, 0)
    assert same_day.stats.requests == 0
    assert scalar(
        url, "SELECT count(*) FROM core.source_record WHERE entity = 'core.exoplanet'"
    ) == (len(planets()))


async def test_a_planet_the_archive_drops_is_deleted(clean_database: Database) -> None:
    table = larger_table(3)
    await ingest(clean_database, table)
    kept = [planet for planet in table if planet["pl_name"] != "Kepler-452 b"]

    outcome, _ = await ingest(clean_database, kept, at=FIRST_RUN + timedelta(days=1, hours=1))

    names = query(clean_database.owner_url, "SELECT name FROM core.exoplanet ORDER BY name")
    assert outcome.status is RunStatus.SUCCEEDED
    assert ("Kepler-452 b",) not in names
    assert len(names) == len(kept)


async def test_a_much_smaller_table_fails_the_run_and_keeps_every_planet(
    clean_database: Database,
) -> None:
    await ingest(clean_database, planets())

    with pytest.raises(Exception, match="refusing to drop more than a tenth"):
        await ingest(clean_database, planets()[:2], at=FIRST_RUN + timedelta(days=1, hours=1))

    url = clean_database.owner_url
    assert scalar(url, "SELECT count(*) FROM core.exoplanet") == len(planets())
    assert query(
        url, "SELECT status FROM raw.ingest_run WHERE source = 'exoplanet-archive' ORDER BY id"
    ) == [("succeeded",), ("failed",)]
