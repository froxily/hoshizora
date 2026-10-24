import json
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import httpx
import psycopg
import pytest
import respx

from hoshizora_ingest.db import connections
from hoshizora_ingest.pipeline import RunEnvironment, RunOutcome, replay_source, run_source, utc_now
from hoshizora_ingest.raw.runs import RunStatus
from hoshizora_ingest.sources.model import unexpected_fields
from hoshizora_ingest.sources.swpc.adapter import (
    BASE_URL,
    BY_URL,
    PRODUCTS,
    SwpcSource,
    parse_product,
)
from hoshizora_ingest.sources.swpc.models import SwpcProduct
from hoshizora_ingest.transform.swpc import (
    AuroraBatch,
    AuroraForecastRow,
    EventBatch,
    MagBatch,
    PlasmaBatch,
    normalize,
)

from conftest import Database
from fakes import RecordingSleep, execute, query, scalar

FIXTURES = Path(__file__).parent / "fixtures" / "swpc"
FILES = {
    "noaa-planetary-k-index.json": "kp.json",
    "xray-flares-7-day.json": "flares.json",
    "alerts.json": "alerts.json",
    "rtsw_wind_1m.json": "rtsw_wind.json",
    "rtsw_mag_1m.json": "rtsw_mag.json",
    "ovation_aurora_latest.json": "ovation.json",
}
OVATION = f"{BASE_URL}/json/ovation_aurora_latest.json"


def body_for(url: str) -> object:
    name = FILES[url.rsplit("/", 1)[-1]]
    body: object = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return body


def fixture_for(url: str) -> list[dict[str, Any]]:
    return cast("list[dict[str, Any]]", body_for(url))


def ovation_fixture() -> dict[str, Any]:
    return cast("dict[str, Any]", body_for(OVATION))


def parsed(suffix: str) -> SwpcProduct:
    url = next(url for url in BY_URL if url.endswith(suffix))
    return parse_product(BY_URL[url], body_for(url))


def test_fixtures_contain_no_unexpected_fields() -> None:
    assert [sorted(unexpected_fields(parsed(name))) for name in FILES] == [[]] * len(FILES)


def test_solar_wind_keeps_only_the_active_spacecraft() -> None:
    plasma = normalize(parsed("rtsw_wind_1m.json"))
    magnetic = normalize(parsed("rtsw_mag_1m.json"))

    assert isinstance(plasma, PlasmaBatch)
    assert isinstance(magnetic, MagBatch)
    assert {row.plasma_spacecraft for row in plasma.rows} == {"SOLAR1"}
    assert {row.bz_gsm_nt for row in magnetic.rows} == {-0.68, -0.67, -0.47}


def test_flares_and_alerts_become_events_in_utc() -> None:
    flares = normalize(parsed("xray-flares-7-day.json"))
    alerts = normalize(parsed("alerts.json"))

    assert isinstance(flares, EventBatch)
    assert isinstance(alerts, EventBatch)
    assert flares.rows[-1].end_at is None
    assert all(
        row.begin_at is not None and row.begin_at.utcoffset() == timedelta(0) for row in alerts.rows
    )
    assert alerts.rows[0].external_id == "K04W@2026-10-13T20:58:58.750000+00:00"


def test_aurora_forecast_summarizes_each_hemisphere() -> None:
    aurora = normalize(parsed("ovation_aurora_latest.json"))

    assert isinstance(aurora, AuroraBatch)
    assert aurora.forecast == AuroraForecastRow(
        observed_at=datetime(2026, 10, 18, 14, 24, tzinfo=UTC),
        forecast_at=datetime(2026, 10, 18, 15, 26, tzinfo=UTC),
        north_max_percent=17,
        south_max_percent=14,
        north_boundary_lat=67,
        south_boundary_lat=-51,
    )
    assert len(aurora.cells) == 185
    assert all(cell.probability_percent > 0 for cell in aurora.cells)


def test_a_quiet_grid_has_no_boundary() -> None:
    quiet = ovation_fixture()
    quiet["coordinates"] = [[lon, lat, 0] for lon, lat, _ in quiet["coordinates"]]

    aurora = normalize(parse_product(BY_URL[OVATION], quiet))

    assert isinstance(aurora, AuroraBatch)
    assert (
        aurora.cells,
        aurora.forecast.north_boundary_lat,
        aurora.forecast.north_max_percent,
    ) == (
        (),
        None,
        0,
    )


def ovation_at(observed: datetime, probability: int) -> dict[str, Any]:
    grid = ovation_fixture()
    grid["Observation Time"] = observed.strftime("%Y-%m-%dT%H:%M:00Z")
    grid["Forecast Time"] = (observed + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:00Z")
    grid["coordinates"] = [
        [lon, lat, probability if p > 0 else 0] for lon, lat, p in grid["coordinates"]
    ]
    return grid


@dataclass
class FakeSwpc:
    overrides: dict[str, list[httpx.Response]] = field(
        default_factory=dict[str, list[httpx.Response]]
    )
    requests: list[httpx.Request] = field(default_factory=list[httpx.Request])

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        name = request.url.path.rsplit("/", 1)[-1]
        queued = self.overrides.get(name)
        if queued:
            return queued.pop(0)
        return httpx.Response(200, json=body_for(str(request.url)), headers={"ETag": f'"{name}"'})


async def ingest_swpc(
    database: Database, server: FakeSwpc, clock: Callable[[], datetime] = utc_now
) -> RunOutcome:
    with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
        router.route().mock(side_effect=server)
        async with connections(database.writer_url) as db:
            env = RunEnvironment(
                db=db.data,
                log_db=db.log,
                user_agent="Hoshizora/test",
                sleep=RecordingSleep(),
                clock=clock,
            )
            return await run_source(SwpcSource(), env)


def later(hours: int) -> Callable[[], datetime]:
    return lambda: datetime.now(UTC) + timedelta(hours=hours)


@pytest.mark.anyio
async def test_first_run_loads_every_product(clean_database: Database) -> None:
    server = FakeSwpc()

    outcome = await ingest_swpc(clean_database, server)

    url = clean_database.owner_url
    assert (outcome.status, len(server.requests)) == (RunStatus.SUCCEEDED, len(PRODUCTS))
    assert scalar(url, "SELECT count(*) FROM core.geomagnetic_index WHERE index = 'kp'") == 8
    assert query(
        url, "SELECT kind, count(*) FROM core.space_weather_event GROUP BY kind ORDER BY kind"
    ) == [("alert", 3), ("xray_flare", 5)]
    assert query(
        url,
        "SELECT count(*), count(speed_kms), count(bz_gsm_nt), "
        "bool_and(plasma_spacecraft = 'SOLAR1' AND mag_spacecraft = 'SOLAR1') "
        "FROM core.solar_wind_sample",
    ) == [(3, 3, 3, True)]
    assert query(
        url, "SELECT (SELECT count(*) FROM core.aurora_forecast), count(*) FROM core.aurora_cell"
    ) == [(1, 185)]


@pytest.mark.anyio
async def test_an_immediate_rerun_makes_no_requests(clean_database: Database) -> None:
    await ingest_swpc(clean_database, FakeSwpc())
    server = FakeSwpc()

    second = await ingest_swpc(clean_database, server)

    assert (second.stats.requests, len(server.requests)) == (0, 0)


@pytest.mark.anyio
async def test_unchanged_products_cost_one_conditional_request_each(
    clean_database: Database,
) -> None:
    await ingest_swpc(clean_database, FakeSwpc())
    server = FakeSwpc(overrides={name: [httpx.Response(304)] for name in FILES})

    second = await ingest_swpc(clean_database, server, later(7))

    assert all(request.headers.get("If-None-Match") for request in server.requests)
    assert (second.stats.not_modified, second.stats.payloads_new) == (len(PRODUCTS), 0)


@pytest.mark.anyio
async def test_revised_kp_and_finished_flares_update_in_place(clean_database: Database) -> None:
    await ingest_swpc(clean_database, FakeSwpc())
    kp = deepcopy(fixture_for(f"{BASE_URL}/products/noaa-planetary-k-index.json"))
    kp[-1]["Kp"] = 4.67
    flares = deepcopy(fixture_for(f"{BASE_URL}/json/goes/primary/xray-flares-7-day.json"))
    flares[-1].update({"end_time": "2026-10-16T07:30:00Z", "end_class": "C1.0"})
    server = FakeSwpc(
        overrides={
            "noaa-planetary-k-index.json": [httpx.Response(200, json=kp)],
            "xray-flares-7-day.json": [httpx.Response(200, json=flares)],
            "alerts.json": [httpx.Response(304)],
            "rtsw_wind_1m.json": [httpx.Response(304)],
            "rtsw_mag_1m.json": [httpx.Response(304)],
        }
    )

    second = await ingest_swpc(clean_database, server, later(7))

    url = clean_database.owner_url
    assert second.stats.rows_upserted == 2
    assert (
        scalar(url, "SELECT value FROM core.geomagnetic_index ORDER BY observed_at DESC LIMIT 1")
        == 4.67
    )
    assert (
        scalar(
            url,
            "SELECT end_at IS NOT NULL FROM core.space_weather_event "
            "WHERE kind = 'xray_flare' ORDER BY begin_at DESC LIMIT 1",
        )
        is True
    )


@pytest.mark.anyio
async def test_a_newer_aurora_forecast_replaces_the_cells_and_old_grids_expire(
    clean_database: Database,
) -> None:
    now = datetime.now(UTC).replace(second=0, microsecond=0)
    first = FakeSwpc(
        overrides={
            "ovation_aurora_latest.json": [
                httpx.Response(200, json=ovation_at(now - timedelta(days=3), 5))
            ]
        }
    )
    await ingest_swpc(clean_database, first)
    url = clean_database.owner_url
    execute(
        url,
        "UPDATE raw.payload SET fetched_at = now() - interval '3 days' "
        "WHERE endpoint = %s RETURNING id",
        (OVATION,),
    )
    second = FakeSwpc(
        overrides={"ovation_aurora_latest.json": [httpx.Response(200, json=ovation_at(now, 9))]}
    )

    await ingest_swpc(clean_database, second, later(2))

    assert query(url, "SELECT observed_at FROM core.aurora_forecast") == [(now,)]
    assert query(
        url,
        "SELECT count(*), min(probability_percent), max(probability_percent) FROM core.aurora_cell",
    ) == [(185, 9, 9)]
    assert execute(
        url, "SELECT count(*), count(body) FROM raw.payload WHERE endpoint = %s", (OVATION,)
    ) == [(2, 1)]
    assert execute(
        url,
        "SELECT count(*), count(payload_id) FROM raw.fetch "
        "WHERE endpoint = %s AND http_status = 200",
        (OVATION,),
    ) == [(2, 2)]
    assert (
        scalar(
            url,
            "SELECT count(*) FROM core.source_record s "
            "LEFT JOIN raw.payload p ON p.id = s.payload_id WHERE p.id IS NULL",
        )
        == 0
    )


def revised(name: str, field_name: str) -> list[dict[str, Any]]:
    rows = deepcopy(fixture_for(f"{BASE_URL}/json/rtsw/{name}"))
    rows[-1][field_name] = cast("float", rows[-1][field_name]) + 1
    return rows


UNCHANGED = [name for name in FILES if not name.startswith("rtsw_")]


async def ingest_revised_solar_wind_three_days_later(database: Database) -> RunOutcome:
    await ingest_swpc(database, FakeSwpc())
    execute(
        database.owner_url,
        "UPDATE raw.payload SET fetched_at = fetched_at - interval '3 days' RETURNING id",
        (),
    )
    server = FakeSwpc(
        overrides={
            "noaa-planetary-k-index.json": [httpx.Response(304)],
            "xray-flares-7-day.json": [httpx.Response(304)],
            "alerts.json": [httpx.Response(304)],
            "rtsw_wind_1m.json": [
                httpx.Response(200, json=revised("rtsw_wind_1m.json", "proton_speed"))
            ],
            "rtsw_mag_1m.json": [httpx.Response(200, json=revised("rtsw_mag_1m.json", "bt"))],
            "ovation_aurora_latest.json": [httpx.Response(304)],
        }
    )
    return await ingest_swpc(database, server, later(7))


@pytest.mark.anyio
async def test_retention_prunes_only_superseded_listed_bodies(clean_database: Database) -> None:
    outcome = await ingest_revised_solar_wind_three_days_later(clean_database)

    assert outcome.status is RunStatus.SUCCEEDED
    assert query(
        clean_database.owner_url,
        "SELECT regexp_replace(endpoint, '^.*/', ''), count(*), count(body) "
        "FROM raw.payload GROUP BY 1 ORDER BY 1",
    ) == [
        ("alerts.json", 1, 1),
        ("noaa-planetary-k-index.json", 1, 1),
        ("ovation_aurora_latest.json", 1, 1),
        ("rtsw_mag_1m.json", 2, 1),
        ("rtsw_wind_1m.json", 2, 1),
        ("xray-flares-7-day.json", 1, 1),
    ]


@pytest.mark.anyio
async def test_pruned_payloads_keep_their_metadata_and_lineage(clean_database: Database) -> None:
    await ingest_revised_solar_wind_three_days_later(clean_database)

    url = clean_database.owner_url
    assert query(
        url,
        "SELECT count(*), bool_and(pruned_at IS NOT NULL AND content_hash <> '' "
        "AND endpoint LIKE 'https://services.swpc.noaa.gov/%' AND fetched_at IS NOT NULL) "
        "FROM raw.payload WHERE body IS NULL",
    ) == [(2, True)]
    links = scalar(url, "SELECT count(*) FROM core.source_record")
    assert scalar(url, "SELECT count(*) FROM mart.record_lineage") == links
    assert (
        cast(
            "int",
            scalar(
                url,
                "SELECT count(*) FROM mart.record_lineage l JOIN raw.payload p "
                "ON p.content_hash = l.content_hash WHERE p.body IS NULL",
            ),
        )
        > 0
    )


@pytest.mark.anyio
async def test_the_latest_body_of_each_request_is_never_pruned(clean_database: Database) -> None:
    await ingest_swpc(clean_database, FakeSwpc())
    execute(
        clean_database.owner_url,
        "UPDATE raw.payload SET fetched_at = now() - interval '30 days' RETURNING id",
        (),
    )

    pruned = execute(clean_database.writer_url, "SELECT raw.apply_retention('swpc', now())", ())

    assert pruned == [(0,)]
    assert (
        scalar(
            clean_database.owner_url, "SELECT count(*) FILTER (WHERE body IS NULL) FROM raw.payload"
        )
        == 0
    )


@pytest.mark.anyio
async def test_raw_payloads_cannot_be_deleted_under_their_lineage(clean_database: Database) -> None:
    await ingest_swpc(clean_database, FakeSwpc())
    referenced = (
        "DELETE FROM raw.payload WHERE id = (SELECT min(payload_id) FROM core.source_record)"
    )

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        query(clean_database.writer_url, f"{referenced} RETURNING id")
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        query(clean_database.owner_url, f"{referenced} RETURNING id")


@pytest.mark.anyio
async def test_replay_skips_pruned_bodies_and_keeps_core_history(clean_database: Database) -> None:
    await ingest_revised_solar_wind_three_days_later(clean_database)
    url = clean_database.owner_url
    samples = scalar(url, "SELECT count(*) FROM core.solar_wind_sample")

    async with connections(clean_database.writer_url) as db:
        replayed = await replay_source(SwpcSource(), db=db.data)

    assert replayed.stats.rows_in > 0
    assert scalar(url, "SELECT count(*) FROM core.solar_wind_sample") == samples


@pytest.mark.anyio
async def test_content_that_returns_after_pruning_gets_its_body_back(
    clean_database: Database,
) -> None:
    await ingest_revised_solar_wind_three_days_later(clean_database)
    url = clean_database.owner_url
    original = FakeSwpc(overrides={name: [httpx.Response(304)] for name in UNCHANGED})

    third = await ingest_swpc(clean_database, original, later(14))

    assert (third.stats.payloads_new, third.stats.rows_upserted) == (2, 2)
    assert query(
        url,
        "SELECT regexp_replace(endpoint, '^.*/', ''), count(*), count(body), count(pruned_at) "
        "FROM raw.payload WHERE endpoint LIKE '%rtsw%' GROUP BY 1 ORDER BY 1",
    ) == [("rtsw_mag_1m.json", 2, 2, 0), ("rtsw_wind_1m.json", 2, 2, 0)]
