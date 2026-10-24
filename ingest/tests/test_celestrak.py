import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import httpx
import pytest
import respx

from hoshizora_ingest.db import connections
from hoshizora_ingest.pipeline import RunEnvironment, RunOutcome, run_source, utc_now
from hoshizora_ingest.raw.runs import RunStatus
from hoshizora_ingest.sources.celestrak.adapter import BASE_URL, CelestrakSource, parse_csv
from hoshizora_ingest.sources.celestrak.models import GpCatalog, SatcatCatalog
from hoshizora_ingest.sources.reference.adapter import ReferenceSource
from hoshizora_ingest.transform.celestrak import launch_designator, normalize_gp, normalize_satcat

from conftest import Database
from fakes import RecordingSleep, execute, query, scalar

FIXTURES = Path(__file__).parent / "fixtures" / "celestrak"
SATCAT_CSV = (FIXTURES / "satcat_stations.csv").read_text(encoding="utf-8") + "".join(
    (FIXTURES / "satcat_sputnik.csv").read_text(encoding="utf-8").splitlines(keepends=True)[1:]
)
GP_JSON = cast("list[dict[str, Any]]", json.loads((FIXTURES / "gp_stations.json").read_text()))
OBJECTS = len(parse_csv(SATCAT_CSV))


def test_designators_reduce_to_the_cospar_launch_id() -> None:
    assert [launch_designator(v) for v in ("1957-001B", "2026-123ABC", "UNKNOWN", None)] == [
        "1957-001",
        "2026-123",
        None,
        None,
    ]


def test_satcat_rows_keep_owner_codes_docking_and_missing_values() -> None:
    rows = {
        row.norad_id: row
        for row in normalize_satcat(
            SatcatCatalog.model_validate({"records": parse_csv(SATCAT_CSV)})
        ).objects
    }

    sputnik, poisk = rows[2], rows[36086]
    assert (sputnik.owner_code, sputnik.launch_designator, sputnik.rcs_m2) == (
        "CIS",
        "1957-001",
        None,
    )
    assert (poisk.orbit_center, poisk.orbit_type, poisk.owner_code) == ("25544", "DOC", "ISS")


def test_gp_epochs_are_utc() -> None:
    elements = normalize_gp(GpCatalog.model_validate({"elements": GP_JSON})).elements

    assert all(element.epoch.tzinfo is not None for element in elements)
    assert elements[0].epoch.utcoffset() == timedelta(0)


@dataclass
class FakeCelestrak:
    satcat: list[httpx.Response]
    gp: list[httpx.Response]
    requests: list[httpx.Request] = field(default_factory=list[httpx.Request])

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        queue = self.satcat if request.url.path.endswith("satcat.csv") else self.gp
        return queue.pop(0)


def satcat_ok(text: str = SATCAT_CSV, etag: str = '"v1"') -> httpx.Response:
    return httpx.Response(200, text=text, headers={"ETag": etag})


def gp_ok(elements: list[dict[str, Any]] = GP_JSON) -> httpx.Response:
    return httpx.Response(200, json=elements)


async def ingest(
    database: Database,
    source: ReferenceSource | CelestrakSource,
    clock: Callable[[], datetime] = utc_now,
) -> RunOutcome:
    async with connections(database.writer_url) as db:
        env = RunEnvironment(
            db=db.data,
            log_db=db.log,
            user_agent="Hoshizora/test",
            sleep=RecordingSleep(),
            clock=clock,
        )
        return await run_source(source, env)


async def ingest_celestrak(
    database: Database, server: FakeCelestrak, clock: Callable[[], datetime] = utc_now
) -> RunOutcome:
    with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
        router.route().mock(side_effect=server)
        return await ingest(database, CelestrakSource(), clock)


def later(hours: int) -> Callable[[], datetime]:
    return lambda: datetime.now(UTC) + timedelta(hours=hours)


@pytest.mark.anyio
async def test_first_run_loads_objects_elements_and_resolves_owners(
    clean_database: Database,
) -> None:
    await ingest(clean_database, ReferenceSource())

    outcome = await ingest_celestrak(clean_database, FakeCelestrak([satcat_ok()], [gp_ok()]))

    url = clean_database.owner_url
    assert outcome.status is RunStatus.SUCCEEDED
    assert scalar(url, "SELECT count(*) FROM core.space_object") == OBJECTS
    assert scalar(url, "SELECT count(*) FROM core.orbit_element") == len(GP_JSON)
    assert query(url, "SELECT country_code FROM core.space_object_country WHERE norad_id = 2") == [
        ("RU",)
    ]
    assert query(
        url,
        "SELECT o.slug FROM core.space_object_organization s "
        "JOIN core.organization o ON o.id = s.organization_id WHERE s.norad_id = 25544",
    ) == [("iss",)]


@pytest.mark.anyio
async def test_an_immediate_rerun_makes_no_requests(clean_database: Database) -> None:
    await ingest_celestrak(clean_database, FakeCelestrak([satcat_ok()], [gp_ok()]))
    server = FakeCelestrak([], [])

    second = await ingest_celestrak(clean_database, server)

    assert (second.status, second.stats.requests, len(server.requests)) == (
        RunStatus.SUCCEEDED,
        0,
        0,
    )


@pytest.mark.anyio
async def test_after_the_interval_satcat_is_requested_conditionally(
    clean_database: Database,
) -> None:
    await ingest_celestrak(clean_database, FakeCelestrak([satcat_ok()], [gp_ok()]))
    server = FakeCelestrak([httpx.Response(304)], [gp_ok()])

    second = await ingest_celestrak(clean_database, server, later(13))

    satcat_request = server.requests[0]
    assert satcat_request.headers["If-None-Match"] == '"v1"'
    assert (second.stats.not_modified, second.stats.payloads_new, second.stats.rows_upserted) == (
        1,
        0,
        0,
    )


@pytest.mark.anyio
async def test_a_refusal_stops_the_run_for_review_without_retrying(
    clean_database: Database,
) -> None:
    server = FakeCelestrak([satcat_ok()], [httpx.Response(403, text="limit exceeded")])

    outcome = await ingest_celestrak(clean_database, server)

    url = clean_database.owner_url
    assert outcome.status is RunStatus.NEEDS_REVIEW
    assert [r.url.path for r in server.requests] == ["/pub/satcat.csv", "/NORAD/elements/gp.php"]
    assert scalar(url, "SELECT count(*) FROM core.space_object") == OBJECTS
    assert scalar(url, "SELECT count(*) FROM core.orbit_element") == 0


@pytest.mark.anyio
async def test_unknown_owner_codes_fail_loudly(clean_database: Database) -> None:
    await ingest(clean_database, ReferenceSource())
    renamed = SATCAT_CSV.replace(",ISS,", ",ISSX,", 1)

    await ingest_celestrak(clean_database, FakeCelestrak([satcat_ok(renamed)], [gp_ok()]))

    assert query(
        clean_database.owner_url,
        "SELECT code, problem FROM mart.dq_unmapped_code "
        "WHERE namespace = 'celestrak.owner' AND problem = 'not in vocabulary'",
    ) == [("ISSX", "not in vocabulary")]


@pytest.mark.anyio
async def test_older_elements_never_replace_newer_ones(clean_database: Database) -> None:
    older = [dict(GP_JSON[0], EPOCH="2020-01-01T00:00:00.000000")]
    await ingest_celestrak(clean_database, FakeCelestrak([satcat_ok()], [gp_ok()]))

    await ingest_celestrak(
        clean_database, FakeCelestrak([httpx.Response(304)], [gp_ok(older)]), later(13)
    )

    epoch = execute(
        clean_database.owner_url,
        "SELECT epoch FROM core.orbit_element WHERE norad_id = %s",
        (GP_JSON[0]["NORAD_CAT_ID"],),
    )[0][0]
    assert epoch == datetime.fromisoformat(f"{GP_JSON[0]['EPOCH']}+00:00")


@pytest.mark.anyio
async def test_gp_objects_missing_from_satcat_become_stubs_until_satcat_catches_up(
    clean_database: Database,
) -> None:
    newcomer = dict(GP_JSON[0], NORAD_CAT_ID=100001, OBJECT_ID="2026-300A", OBJECT_NAME="NEWSAT")
    newcomer_row = (
        "NEWSAT 1,2026-300A,100001,PAY,+,JPN,2026-10-15,TNSTA,,95.5,97.4,560,540,,,EA,ORB\n"
    )

    await ingest_celestrak(clean_database, FakeCelestrak([satcat_ok()], [gp_ok([newcomer])]))
    stub = query(
        clean_database.owner_url,
        "SELECT name, owner_code FROM core.space_object WHERE norad_id = 100001",
    )
    await ingest_celestrak(
        clean_database,
        FakeCelestrak([satcat_ok(SATCAT_CSV + newcomer_row, '"v2"')], [gp_ok([newcomer])]),
        later(13),
    )
    full = query(
        clean_database.owner_url,
        "SELECT name, owner_code FROM core.space_object WHERE norad_id = 100001",
    )

    assert (stub, full) == ([("NEWSAT", None)], [("NEWSAT 1", "JPN")])
