import copy
import json
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, LiteralString, cast

import psycopg
from psycopg import sql

from hoshizora_ingest.analytics.refresh import refresh_marts
from hoshizora_ingest.db import connections
from hoshizora_ingest.facts.engine import Generated, generate_facts
from hoshizora_ingest.facts.spec import Template, load_templates
from hoshizora_ingest.pipeline import RunEnvironment, apply_payload, run_source
from hoshizora_ingest.raw.runs import RunStats
from hoshizora_ingest.raw.store import land_payload
from hoshizora_ingest.sources.exoplanets.models import PlanetTable
from hoshizora_ingest.sources.launch_library.adapter import PRODUCTION_BASE_URL, LaunchLibrarySource
from hoshizora_ingest.sources.reference.adapter import ReferenceSource
from hoshizora_ingest.store.exoplanets import EXOPLANETS
from hoshizora_ingest.transform.exoplanets import normalize as normalize_exoplanets

from conftest import Database
from fakes import RecordingSleep

AS_OF = datetime(2026, 10, 18, 6, tzinfo=UTC)
FIXTURES = Path(__file__).parent / "fixtures" / "launch-library"
SUCCESS, FAILURE = 3, 4


@dataclass(frozen=True)
class Agency:
    ll2: int
    name: str
    abbrev: str
    kind: str
    country: str
    founded: int


AGENCIES = (
    Agency(121, "SpaceX", "SpX", "Commercial", "US", 2002),
    Agency(37, "Japan Aerospace Exploration Agency", "JAXA", "Government", "JP", 2003),
    Agency(
        88, "China Aerospace Science and Technology Corporation", "CASC", "Government", "CN", 1999
    ),
)
VEHICLES = (
    (1, "Falcon 9 Block 5", "Falcon"),
    (2, "H3-22S", "H3"),
    (3, "Long March 2D", "Long March 2"),
)
PADS = (
    (40, "Space Launch Complex 40", "Cape Canaveral SFS, FL, USA", "US"),
    (50, "Yoshinobu Launch Complex LP-2", "Tanegashima Space Center, Japan", "JP"),
    (60, "Launch Area 4 (SLS-2 / 603)", "Jiuquan Satellite Launch Center, China", "CN"),
)


def agency_page() -> dict[str, Any]:
    page = cast("dict[str, Any]", json.loads((FIXTURES / "agencies_page.json").read_text("utf-8")))
    nasa = next(result for result in page["results"] if result["id"] == 44)
    results: list[dict[str, Any]] = []
    for agency in AGENCIES:
        result = copy.deepcopy(nasa)
        result |= {
            "id": agency.ll2,
            "url": f"{PRODUCTION_BASE_URL}/2.3.0/agencies/{agency.ll2}/",
            "name": agency.name,
            "abbrev": agency.abbrev,
            "type": {"id": 1, "name": agency.kind},
            "founding_year": agency.founded,
            "parent": None,
        }
        result["country"] = [result["country"][0] | {"alpha_2_code": agency.country}]
        results.append(result)
    return page | {"count": len(results), "next": None, "results": results}


def dated(year: int, months: range, day: int) -> Iterator[datetime]:
    for month in months:
        yield datetime(year, month, day, 14, tzinfo=UTC)


def launch_plan() -> Iterator[tuple[str, int, int, datetime, int]]:
    falcon = [
        *dated(2024, range(1, 11), 5),
        *dated(2025, range(1, 13), 5),
        *dated(2026, range(1, 10), 5),
        *dated(2026, range(1, 4), 20),
    ]
    for when in falcon:
        yield "spacex", 1, 40, when, SUCCESS
    yield "jaxa", 2, 50, datetime(2023, 3, 7, 1, 37, tzinfo=UTC), FAILURE
    for when in (
        datetime(2024, 2, 17, tzinfo=UTC),
        datetime(2024, 7, 1, tzinfo=UTC),
        datetime(2025, 2, 2, tzinfo=UTC),
        datetime(2025, 6, 1, tzinfo=UTC),
        datetime(2025, 10, 26, tzinfo=UTC),
        datetime(2026, 6, 1, tzinfo=UTC),
        datetime(2026, 9, 1, tzinfo=UTC),
    ):
        yield "jaxa", 2, 50, when, SUCCESS
    for when in (*dated(2026, range(1, 10), 10), *dated(2026, range(1, 3), 25)):
        yield "casc", 3, 60, when, SUCCESS


def launch_id(provider: str, when: datetime) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{provider}/{when.isoformat()}"))


async def seed_reference_and_agencies(database: Database) -> None:
    async with connections(database.writer_url) as db:
        env = RunEnvironment(db=db.data, log_db=db.log, user_agent="t", sleep=RecordingSleep())
        await run_source(ReferenceSource(), env)
        source = LaunchLibrarySource(PRODUCTION_BASE_URL)
        params = {"mode": "normal", "ordering": "id", "limit": "100", "offset": "0"}
        landed = await land_payload(
            db.data, "launch-library", source.agencies_endpoint, params, agency_page()
        )
        await apply_payload(db.data, source, landed, RunStats())
        await db.data.commit()


def seed_launches(connection: psycopg.Connection) -> None:
    ids = dict(
        connection.execute(
            "SELECT slug, id FROM core.organization WHERE slug IN ('spacex', 'jaxa', 'casc')"
        ).fetchall()
    )
    connection.cursor().executemany(
        "INSERT INTO core.launch_vehicle (ll2_id, name, family) VALUES (%s, %s, %s)", VEHICLES
    )
    connection.cursor().executemany(
        "INSERT INTO core.launch_pad (ll2_id, name, location_name, country_code) "
        "VALUES (%s, %s, %s, %s)",
        PADS,
    )
    connection.cursor().executemany(
        "INSERT INTO core.launch (ll2_id, name, net, status_id, status, status_name, "
        "provider_org_id, vehicle_ll2_id, pad_ll2_id, source_updated_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        [
            (
                launch_id(provider, when),
                f"{provider} {when:%Y-%m-%d}",
                when,
                status,
                "Success" if status == SUCCESS else "Failure",
                "Launch Successful" if status == SUCCESS else "Launch Failure",
                ids[provider],
                vehicle,
                pad,
                when,
            )
            for provider, vehicle, pad, when, status in launch_plan()
        ],
    )


SMALL_BODIES = (
    ("TEST1", 26.0, "2026-10-20 12:00", 0.002, 12.0),
    ("99942", 18.0, "2026-10-22 12:00", 0.01, 30.5),
    ("TEST3", 22.0, "2026-11-30 12:00", 0.004, 8.0),
    ("TEST4", 25.0, "2019-07-25 12:00", 0.0005, 15.0),
    ("TEST5", 27.0, "2026-03-01 12:00", 0.0015, 10.0),
    ("TEST6", 24.0, "2025-05-01 12:00", 0.002, 9.0),
    ("TEST7", 28.0, "2026-06-01 12:00", 0.0024, 11.0),
    ("IMPACT", 30.4, "2008-10-07 12:00", 0.00001, 12.8),
    ("C/2026 A1", 15.0, "2026-10-19 12:00", 0.0001, 40.0),
)
UNTIMED_APPROACHES = (("OLD1", "1937-10-30 12:00", 0.005),)
FULL_NAMES = {"99942": "     99942 Apophis (2004 MN4)"}
IMPACT_RISKS = (
    ("TEST1", -3.1, None),
    ("TEST3", -5.0, None),
    ("TEST5", -7.2, None),
    ("TEST6", -2.0, "2026-09-01"),
)


def seed_near_earth(connection: psycopg.Connection) -> None:
    cursor = connection.cursor()
    cursor.executemany(
        "INSERT INTO core.small_body (designation, fullname, h_mag) VALUES (%s, %s, %s)",
        [(name, FULL_NAMES.get(name, f"({name})"), h_mag) for name, h_mag, *_ in SMALL_BODIES],
    )
    cursor.executemany(
        "INSERT INTO core.close_approach "
        "(designation, body, approach_tdb, jd_tdb, dist_au, v_rel_kms, h_mag) "
        "VALUES (%s, 'Earth', %s, 2460000.5, %s, %s, %s)",
        [(name, when, dist, speed, h_mag) for name, h_mag, when, dist, speed in SMALL_BODIES],
    )
    cursor.executemany(
        "INSERT INTO core.small_body (designation, fullname) VALUES (%s, %s)",
        [(name, f"({name})") for name, *_ in UNTIMED_APPROACHES],
    )
    cursor.executemany(
        "INSERT INTO core.close_approach (designation, body, approach_tdb, jd_tdb, dist_au) "
        "VALUES (%s, 'Earth', %s, 2428836.5, %s)",
        UNTIMED_APPROACHES,
    )
    cursor.executemany(
        "INSERT INTO core.impact_risk (designation, palermo_cumulative, removed_at) "
        "VALUES (%s, %s, %s)",
        IMPACT_RISKS,
    )


KP_PEAKS = {
    datetime(2026, 10, 15, 12, tzinfo=UTC): 6.33,
    datetime(2026, 10, 15, 15, tzinfo=UTC): 5.67,
}
FLARES = (
    ("F1", datetime(2026, 10, 16, 6, 22, tzinfo=UTC), "M2.3", 2.3e-5),
    ("F2", datetime(2026, 10, 14, 9, tzinfo=UTC), "C1.4", 1.4e-6),
    ("F3", datetime(2026, 10, 13, 9, tzinfo=UTC), "B8.0", 8e-7),
    ("F4", datetime(2026, 10, 1, 9, tzinfo=UTC), "X1.1", 1.1e-4),
)
ALERTS = (
    ("A1", datetime(2026, 10, 13, 2, tzinfo=UTC)),
    ("A2", datetime(2026, 10, 15, 13, tzinfo=UTC)),
    ("A3", datetime(2026, 10, 17, 20, tzinfo=UTC)),
    ("A4", datetime(2026, 9, 30, 8, tzinfo=UTC)),
)


def kp_readings() -> Iterator[tuple[datetime, float]]:
    yield datetime(2026, 10, 5, 9, tzinfo=UTC), 7.0
    start = datetime(2026, 10, 12, tzinfo=UTC)
    for step in range(48):
        moment = start + timedelta(hours=3 * step)
        yield moment, KP_PEAKS.get(moment, 2.0)


def wind_samples() -> Iterator[tuple[datetime, float]]:
    yield datetime(2026, 10, 16, 12, tzinfo=UTC), 800.0
    start = datetime(2026, 10, 17, 7, 5, tzinfo=UTC)
    for step in range(23):
        yield start + timedelta(hours=step), 400.0 + 5 * step
    yield datetime(2026, 10, 18, 3, 10, tzinfo=UTC), 612.3


def seed_space_weather(connection: psycopg.Connection) -> None:
    cursor = connection.cursor()
    cursor.executemany(
        "INSERT INTO core.geomagnetic_index (index, observed_at, value) VALUES ('kp', %s, %s)",
        list(kp_readings()),
    )
    cursor.executemany(
        "INSERT INTO core.space_weather_event "
        "(kind, external_id, begin_at, peak_at, event_class, peak_flux_wm2) "
        "VALUES ('xray_flare', %s, %s, %s, %s, %s)",
        [(name, peak, peak, flare_class, flux) for name, peak, flare_class, flux in FLARES],
    )
    cursor.executemany(
        "INSERT INTO core.space_weather_event (kind, external_id, begin_at) "
        "VALUES ('alert', %s, %s)",
        ALERTS,
    )
    cursor.executemany(
        "INSERT INTO core.solar_wind_sample (observed_at, speed_kms) VALUES (%s, %s)",
        list(wind_samples()),
    )
    run = connection.execute(
        "INSERT INTO raw.ingest_run (source, status, origin) "
        "VALUES ('swpc', 'succeeded', 'https://services.swpc.noaa.gov') RETURNING id"
    ).fetchone()
    connection.execute(
        "INSERT INTO raw.fetch (run_id, source, endpoint, requested_at, http_status, duration_ms) "
        "VALUES (%s, 'swpc', 'https://services.swpc.noaa.gov/feed.json', %s, 200, 5)",
        (run[0] if run else None, datetime(2026, 10, 18, 5, 30, tzinfo=UTC)),
    )


def space_objects() -> Iterator[tuple[int, str, str, str, date, date | None, str]]:
    yield 5, "VANGUARD 1", "PAY", "US", date(1958, 3, 17), None, "EA"
    yield 25544, "ISS (ZARYA)", "PAY", "ISS", date(1998, 11, 20), None, "EA"
    for owner, first, count in (("US", 1000, 20), ("PRC", 2000, 12), ("JPN", 3000, 5)):
        for norad in range(first, first + count):
            yield norad, f"{owner} SAT {norad}", "PAY", owner, date(2020, 1, 1), None, "EA"
    for norad in range(4000, 4010):
        yield norad, f"DEBRIS {norad}", "DEB", "US", date(2007, 1, 11), None, "EA"
    for norad in range(4100, 4103):
        yield norad, f"CZ-2D R/B {norad}", "R/B", "PRC", date(2021, 6, 1), None, "EA"
    decays = (
        date(2026, 1, 10),
        date(2026, 3, 10),
        date(2026, 6, 10),
        date(2026, 9, 10),
        date(2025, 2, 10),
        date(2025, 5, 10),
        date(2025, 11, 10),
        date(2024, 4, 10),
        date(2024, 8, 10),
    )
    for norad, decayed in enumerate(decays, start=5000):
        yield norad, f"DEBRIS {norad}", "DEB", "US", date(2019, 1, 1), decayed, "EA"
    yield 6000, "PROBE", "PAY", "US", date(2020, 7, 30), None, "SU"


def seed_orbits(connection: psycopg.Connection) -> None:
    connection.cursor().executemany(
        "INSERT INTO core.space_object (norad_id, name, object_type, owner_code, launch_date, "
        "decay_date, orbit_center, apogee_km, perigee_km) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        [(*row, *((425.0, 415.0) if row[0] == 25544 else (None, None))) for row in space_objects()],
    )


BOOSTERS = ((1, "B1062", 2024, 2024), (2, "B1077", 2025, 2026))
FAILED_LANDING = datetime(2026, 3, 20, 14, tzinfo=UTC)


def booster_flights() -> Iterator[tuple[int, list[datetime]]]:
    falcon = sorted(when for provider, _, _, when, _ in launch_plan() if provider == "spacex")
    for launcher, _, first_year, last_year in BOOSTERS:
        yield launcher, [when for when in falcon if first_year <= when.year <= last_year]


def seed_reusability(connection: psycopg.Connection) -> None:
    flights = dict(booster_flights())
    connection.cursor().executemany(
        "INSERT INTO core.launcher (ll2_id, serial_number, is_placeholder, status, vehicle_ll2_id, "
        "flights, first_launch_at, last_launch_at) VALUES (%s, %s, false, 'active', 1, %s, %s, %s)",
        [
            (launcher, serial, len(flights[launcher]), flights[launcher][0], flights[launcher][-1])
            for launcher, serial, _, _ in BOOSTERS
        ],
    )
    connection.cursor().executemany(
        "INSERT INTO core.landing (ll2_id, launcher_ll2_id, launcher_flight_number, attempt, "
        "success, previous_flight_at, turnaround) VALUES (%s, %s, %s, true, %s, %s, %s)",
        [
            (
                launcher * 1000 + number,
                launcher,
                number,
                when != FAILED_LANDING,
                previous,
                when - previous if previous is not None else None,
            )
            for launcher, dates in flights.items()
            for number, (previous, when) in enumerate(
                zip([None, *dates[:-1]], dates, strict=True), start=1
            )
        ],
    )


EXOPLANET_FIXTURES = Path(__file__).parent / "fixtures" / "exoplanet-archive"
SYNTHETIC_PLANETS = (
    {"pl_name": "TEST 2026 b", "hostname": "TEST", "discoverymethod": "Transit", "disc_year": 2026},
    {
        "pl_name": "TEST Earth b",
        "hostname": "TEST",
        "discoverymethod": "Transit",
        "disc_year": 2019,
        "pl_rade": 1.1,
        "pl_insol": 0.9,
    },
)


def seed_exoplanets(connection: psycopg.Connection) -> None:
    planets = [
        *json.loads((EXOPLANET_FIXTURES / "planets.json").read_text("utf-8")),
        *SYNTHETIC_PLANETS,
    ]
    rows = normalize_exoplanets(PlanetTable.model_validate(planets)).planets
    columns = [column.name for column in EXOPLANETS.columns]
    connection.cursor().executemany(
        sql.SQL("INSERT INTO core.exoplanet ({}) VALUES ({})").format(
            sql.SQL(", ").join(map(sql.Identifier, columns)),
            sql.SQL(", ").join(sql.Placeholder() * len(columns)),
        ),
        [tuple(getattr(row, column) for column in columns) for row in rows],
    )


def mark_succeeded(connection: psycopg.Connection, *sources: str) -> None:
    connection.cursor().executemany(
        "INSERT INTO raw.ingest_run (source, status, origin) VALUES (%s, 'succeeded', %s)",
        [(source, "https://seed.test") for source in sources],
    )


async def seed_all(database: Database) -> None:
    await seed_reference_and_agencies(database)
    with psycopg.connect(database.owner_url, autocommit=True) as connection:
        seed_launches(connection)
        seed_reusability(connection)
        seed_exoplanets(connection)
        seed_near_earth(connection)
        seed_space_weather(connection)
        seed_orbits(connection)
        mark_succeeded(connection, "launch-library", "exoplanet-archive")
    async with connections(database.writer_url) as db:
        await refresh_marts(db.data)


def templates_of(module: str) -> tuple[Template, ...]:
    return tuple(template for template in load_templates() if template.module == module)


async def generate(
    database: Database, templates: tuple[Template, ...], as_of: datetime = AS_OF
) -> Generated:
    async with connections(database.writer_url) as db:
        return await generate_facts(db.data, templates, as_of)


def stored_facts(database: Database, module: str) -> dict[str, dict[str | None, dict[str, Any]]]:
    with psycopg.connect(database.owner_url) as connection:
        rows = connection.execute(
            "SELECT f.template_key, f.entity_key, f.params, f.score, f.source_refs "
            "FROM facts.fact f JOIN facts.template t ON t.key = f.template_key "
            "WHERE t.module = %s",
            (module,),
        ).fetchall()
    found: dict[str, dict[str | None, dict[str, Any]]] = {}
    for key, entity, params, score, refs in rows:
        found.setdefault(key, {})[entity] = {"params": params, "score": score, "refs": refs}
    return found


KEY_EXPRESSIONS: dict[str, tuple[LiteralString, LiteralString]] = {
    "core.country": ("core.country", "code"),
    "core.launch": ("core.launch", "ll2_id::text"),
    "core.launch_pad": ("core.launch_pad", "ll2_id::text"),
    "core.launcher": ("core.launcher", "ll2_id::text"),
    "core.exoplanet": ("core.exoplanet", "name"),
    "mart.exoplanet_discoveries_yearly": (
        "mart.exoplanet_discoveries_yearly",
        "concat_ws('|', year, method)",
    ),
    "core.landing": ("core.landing", "ll2_id::text"),
    "core.small_body": ("core.small_body", "designation"),
    "core.close_approach": (
        "core.close_approach",
        "concat_ws('|', designation, body, approach_tdb)",
    ),
    "core.impact_risk": ("core.impact_risk", "designation"),
    "core.space_weather_event": ("core.space_weather_event", "concat_ws('|', kind, external_id)"),
    "core.space_object": ("core.space_object", "norad_id::text"),
    "mart.launch_cadence_yearly": (
        "mart.launch_cadence_yearly",
        "concat_ws('|', group_kind, group_key, year)",
    ),
    "mart.launch_pad_activity": ("mart.launch_pad_activity", "pad_id::text"),
    "mart.reusability_yearly": (
        "mart.reusability_yearly",
        "concat_ws('|', group_kind, group_key, year)",
    ),
    "mart.organization_launch_summary": ("mart.organization_profile", "key"),
    "mart.kp_daily": ("mart.kp_daily", "day::text"),
    "mart.solar_wind_hourly": ("mart.solar_wind_hourly", "hour::text"),
    "mart.objects_in_orbit_by_owner": ("mart.objects_in_orbit_by_owner", "orbit_state"),
    "mart.objects_in_orbit_by_country": (
        "mart.objects_in_orbit_by_country",
        "concat_ws('|', country_code, object_type, orbit_state)",
    ),
}


def unresolved_refs(database: Database) -> list[tuple[str, str]]:
    with psycopg.connect(database.owner_url) as connection:
        connection.execute("SET TIME ZONE 'UTC'")
        refs = connection.execute(
            "SELECT DISTINCT r ->> 'entity', r ->> 'key' "
            "FROM facts.fact, jsonb_array_elements(source_refs) AS r"
        ).fetchall()
        missing: list[tuple[str, str]] = []
        for entity, key in refs:
            if entity not in KEY_EXPRESSIONS:
                missing.append((entity, key))
                continue
            relation, expression = KEY_EXPRESSIONS[entity]
            statement = sql.SQL("SELECT EXISTS (SELECT 1 FROM {} WHERE {} = %s)").format(
                sql.SQL(relation), sql.SQL(expression)
            )
            found = connection.execute(statement, (key,)).fetchone()
            if found is None or not found[0]:
                missing.append((entity, key))
    return missing
