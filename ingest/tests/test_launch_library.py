import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import httpx
import pytest
import respx

from hoshizora_ingest.db import connections
from hoshizora_ingest.pipeline import (
    RunEnvironment,
    RunOutcome,
    apply_payload,
    replay_source,
    run_source,
)
from hoshizora_ingest.raw.runs import RunStats, RunStatus
from hoshizora_ingest.raw.store import land_payload
from hoshizora_ingest.sources.launch_library.adapter import (
    LaunchLibrarySource,
    next_launch_window,
)
from hoshizora_ingest.sources.launch_library.models import (
    AgencyPage,
    LandingPage,
    LauncherPage,
    LaunchPage,
)
from hoshizora_ingest.sources.model import unexpected_fields
from hoshizora_ingest.sources.reference.adapter import ReferenceSource
from hoshizora_ingest.transform.launch_library import normalize_landings, normalize_launches

from conftest import Database
from fakes import RecordingSleep, execute, query, scalar

FIXTURES = Path(__file__).parent / "fixtures" / "launch-library"
DEV = "https://lldev.thespacedevs.com"
PRODUCTION = "https://ll.thespacedevs.com"
PAGE_SIZE = 5


def fixture(name: str) -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads((FIXTURES / name).read_text(encoding="utf-8")))


EMPTY = fixture("launches_empty.json")

type LaunchReply = dict[str, Any] | httpx.Response


def throttled(retry_after: str | None = None) -> httpx.Response:
    headers = {} if retry_after is None else {"Retry-After": retry_after}
    return httpx.Response(429, headers=headers)


def each_after_a_quota_check(*endpoints: str) -> list[str]:
    return [step for endpoint in endpoints for step in ("api-throttle", endpoint)]


def launch_page(name: str) -> LaunchPage:
    return LaunchPage.model_validate(fixture(name))


def test_fixtures_contain_no_unexpected_fields() -> None:
    pages = [
        launch_page("launches_page.json"),
        launch_page("launches_history.json"),
        AgencyPage.model_validate(fixture("agencies_page.json")),
        LauncherPage.model_validate(fixture("launchers_page.json")),
        LandingPage.model_validate(fixture("landings_page.json")),
    ]

    assert [sorted(unexpected_fields(page)) for page in pages] == [[]] * len(pages)


def test_a_new_upstream_field_is_reported_with_its_path() -> None:
    body = fixture("launches_history.json")
    body["results"][0]["pad"]["elevation_m"] = 12

    assert unexpected_fields(LaunchPage.model_validate(body)) == {"results[].pad.elevation_m"}


def test_normalizes_launches_with_provider_designator_and_partners() -> None:
    batch = normalize_launches(launch_page("launches_history.json"))
    first = batch.launches[0]

    assert (first.name, first.status, first.launch_designator, first.provider_ll2_id) == (
        "Long March 8A | SatNet LEO Group 12",
        "Success",
        "2025-231",
        88,
    )
    assert first.net == datetime(2025, 10, 16, 1, 33, tzinfo=UTC)
    assert {row.ll2_id for row in batch.agencies if not row.complete} == {88, 121, 1040}
    assert {pad.country_code for pad in batch.pads} == {"CN", "US"}


def page_with(results: int, newest: str) -> LaunchPage:
    body = fixture("launches_page.json")
    body["results"] = body["results"][:results]
    for launch in body["results"]:
        launch["last_updated"] = newest
    return LaunchPage.model_validate(body)


def test_a_short_page_means_the_feed_is_caught_up() -> None:
    watermark = datetime(2023, 1, 1, tzinfo=UTC)

    assert next_launch_window(watermark, 0, page_with(3, "2024-01-01T00:00:00Z"), 5) is None


def test_a_full_page_moves_the_watermark_forward() -> None:
    watermark = datetime(2023, 1, 1, tzinfo=UTC)

    assert next_launch_window(watermark, 10, page_with(5, "2024-01-01T00:00:00Z"), 5) == (
        datetime(2024, 1, 1, tzinfo=UTC),
        0,
    )


def test_a_full_page_with_one_timestamp_advances_the_offset_instead() -> None:
    watermark = datetime(2024, 1, 1, tzinfo=UTC)

    assert next_launch_window(watermark, 5, page_with(5, "2024-01-01T00:00:00Z"), 5) == (
        watermark,
        10,
    )


@dataclass
class FakeLaunchLibrary:
    launch_pages: list[LaunchReply]
    throttle_use: int = 0
    launcher_pages: list[LaunchReply] = field(default_factory=list[LaunchReply])
    landing_pages: list[LaunchReply] = field(default_factory=list[LaunchReply])
    requests: list[httpx.Request] = field(default_factory=list[httpx.Request])

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if path.endswith("/api-throttle/"):
            used, self.throttle_use = self.throttle_use, 0
            return httpx.Response(
                200,
                json={
                    "your_request_limit": 15,
                    "limit_frequency_secs": 3600,
                    "current_use": used,
                    "next_use_secs": 120 if used >= 15 else 0,
                    "ident": "203.0.113.7",
                },
            )
        if path.endswith("/agencies/"):
            page = fixture("agencies_page.json") if request.url.params["offset"] == "0" else EMPTY
            return httpx.Response(200, json=page)
        if path.endswith("/launchers/"):
            return self.reply(self.launcher_pages)
        if path.endswith("/landings/"):
            return self.reply(self.landing_pages)
        return self.reply(self.launch_pages)

    @staticmethod
    def reply(pages: list[LaunchReply]) -> httpx.Response:
        if not pages:
            return httpx.Response(200, json=EMPTY)
        reply = pages.pop(0)
        return reply if isinstance(reply, httpx.Response) else httpx.Response(200, json=reply)

    def data_requests(self) -> list[httpx.Request]:
        return [r for r in self.requests if not r.url.path.endswith("/api-throttle/")]

    def endpoints(self) -> list[str]:
        return [request.url.path.split("/")[-2] for request in self.requests]


async def ingest(
    database: Database,
    source: ReferenceSource | LaunchLibrarySource,
    *,
    max_requests: int | None = None,
    sleep: RecordingSleep | None = None,
) -> RunOutcome:
    async with connections(database.writer_url) as db:
        env = RunEnvironment(
            db=db.data,
            log_db=db.log,
            user_agent="Hoshizora/test",
            sleep=sleep or RecordingSleep(),
        )
        return await run_source(source, env, max_requests=max_requests)


async def ingest_launch_library(
    database: Database,
    server: FakeLaunchLibrary,
    *,
    base_url: str = DEV,
    max_requests: int | None = None,
    sleep: RecordingSleep | None = None,
) -> RunOutcome:
    with respx.mock(base_url=base_url, assert_all_called=False) as router:
        router.route().mock(side_effect=server)
        return await ingest(
            database,
            LaunchLibrarySource(base_url, page_size=PAGE_SIZE),
            max_requests=max_requests,
            sleep=sleep,
        )


@pytest.mark.anyio
async def test_first_run_loads_agencies_and_launches_with_curation(
    clean_database: Database,
) -> None:
    await ingest(clean_database, ReferenceSource())
    server = FakeLaunchLibrary([fixture("launches_history.json")])

    outcome = await ingest_launch_library(clean_database, server)

    url = clean_database.owner_url
    assert outcome.status is RunStatus.SUCCEEDED
    assert scalar(url, "SELECT count(*) FROM core.launch") == 4
    assert query(
        url,
        "SELECT o.slug, o.name_ja, o.type, l.launch_designator FROM core.launch l "
        "JOIN core.organization o ON o.id = l.provider_org_id "
        "WHERE l.launch_designator = '2025-231'",
    ) == [("casc", "中国航天科技集団", "company", "2025-231")]
    assert (
        scalar(
            url,
            "SELECT count(*) FROM core.program_member m JOIN core.organization o "
            "ON o.id = m.organization_id WHERE m.program_slug = 'china' AND o.slug = 'cas-space'",
        )
        == 1
    )
    assert scalar(url, "SELECT count(*) FROM core.mission_agency") != 0


@pytest.mark.anyio
async def test_rerun_skips_fresh_agencies_and_changes_nothing(clean_database: Database) -> None:
    await ingest(clean_database, ReferenceSource())
    history = fixture("launches_history.json")
    await ingest_launch_library(clean_database, FakeLaunchLibrary([history]))
    server = FakeLaunchLibrary([history])

    second = await ingest_launch_library(clean_database, server)

    assert [r.url.path for r in server.data_requests()] == [
        "/2.3.0/launches/",
        "/2.3.0/landings/",
    ]
    assert (second.stats.payloads_new, second.stats.rows_upserted) == (0, 0)
    assert server.data_requests()[0].url.params["last_updated__gte"] == "2026-05-17T15:45:59Z"


@pytest.mark.anyio
async def test_an_interrupted_backfill_resumes_from_the_landed_watermark(
    clean_database: Database,
) -> None:
    await ingest(clean_database, ReferenceSource())
    first_page = fixture("launches_page.json")
    newest = max(launch["last_updated"] for launch in first_page["results"])

    interrupted = await ingest_launch_library(
        clean_database, FakeLaunchLibrary([first_page]), max_requests=3
    )
    resumed_server = FakeLaunchLibrary([])
    resumed = await ingest_launch_library(clean_database, resumed_server)

    assert interrupted.status is RunStatus.PARTIAL
    assert resumed.status is RunStatus.SUCCEEDED
    launches = [r for r in resumed_server.data_requests() if r.url.path.endswith("/launches/")]
    assert [r.url.params["last_updated__gte"] for r in launches] == [newest]


@pytest.mark.anyio
async def test_production_waits_for_the_quota_window_before_requesting(
    clean_database: Database,
) -> None:
    await ingest(clean_database, ReferenceSource())
    sleep = RecordingSleep()
    server = FakeLaunchLibrary([], throttle_use=15)

    await ingest_launch_library(clean_database, server, base_url=PRODUCTION, sleep=sleep)

    assert sleep.delays[0] == 121
    assert server.requests[0].url.path.endswith("/api-throttle/")


@pytest.mark.anyio
async def test_an_interrupted_agency_sweep_is_restarted_not_skipped(
    clean_database: Database,
) -> None:
    await ingest(clean_database, ReferenceSource())
    await ingest_launch_library(clean_database, FakeLaunchLibrary([]), max_requests=1)
    resumed_server = FakeLaunchLibrary([])

    await ingest_launch_library(clean_database, resumed_server)

    agency_offsets = [
        r.url.params["offset"] for r in resumed_server.data_requests() if "agencies" in r.url.path
    ]
    assert agency_offsets == ["0", "5"]


@pytest.mark.anyio
async def test_a_429_at_the_quota_boundary_waits_for_a_fresh_reading_and_continues(
    clean_database: Database,
) -> None:
    await ingest(clean_database, ReferenceSource())
    sleep = RecordingSleep()
    server = FakeLaunchLibrary(
        [fixture("launches_page.json"), throttled("900"), fixture("launches_history.json")]
    )

    outcome = await ingest_launch_library(clean_database, server, base_url=PRODUCTION, sleep=sleep)

    launches = [r for r in server.data_requests() if r.url.path.endswith("/launches/")]
    assert outcome.status is RunStatus.SUCCEEDED
    assert sleep.delays == [901]
    assert server.endpoints()[-8:-4] == each_after_a_quota_check("launches", "launches")
    assert launches[1].url.params == launches[2].url.params
    assert scalar(clean_database.owner_url, "SELECT count(*) FROM core.launch") == 9


@pytest.mark.anyio
async def test_repeated_429s_end_the_run_partial_and_the_next_run_resumes_cleanly(
    clean_database: Database,
) -> None:
    await ingest(clean_database, ReferenceSource())
    first_page = fixture("launches_page.json")
    newest = max(launch["last_updated"] for launch in first_page["results"])
    sleep = RecordingSleep()
    throttled_server = FakeLaunchLibrary([first_page, throttled(), throttled(), throttled()])

    interrupted = await ingest_launch_library(
        clean_database, throttled_server, base_url=PRODUCTION, sleep=sleep
    )
    resumed_server = FakeLaunchLibrary([fixture("launches_history.json")])
    resumed = await ingest_launch_library(clean_database, resumed_server, base_url=PRODUCTION)

    url = clean_database.owner_url
    rejected = throttled_server.data_requests()[-1]
    assert interrupted.status is RunStatus.PARTIAL
    assert interrupted.error == f"HTTP 429 from {rejected.url}"
    assert sleep.delays == [61, 61]
    assert throttled_server.endpoints() == each_after_a_quota_check(
        *["agencies"] * 2, *["launches"] * 4
    )
    assert resumed.status is RunStatus.SUCCEEDED
    assert resumed_server.data_requests()[0].url.params == rejected.url.params
    assert rejected.url.params["last_updated__gte"] == newest
    assert query(
        url, "SELECT status FROM raw.ingest_run WHERE source = 'launch-library' ORDER BY id"
    ) == [("partial",), ("succeeded",)]
    rejections = query(url, "SELECT http_status FROM raw.fetch WHERE payload_id IS NULL")
    assert rejections == [(429,), (429,), (429,)]
    assert scalar(url, "SELECT count(*) FROM core.launch") == 9


DEV_LINKS = """
SELECT count(*)
FROM core.source_record s
JOIN raw.payload p ON p.id = s.payload_id
WHERE mart.url_origin(p.endpoint) = 'https://lldev.thespacedevs.com'
"""


async def land_dev_page(database: Database, body: dict[str, Any]) -> None:
    dev = LaunchLibrarySource(DEV, page_size=PAGE_SIZE)
    async with connections(database.writer_url) as db:
        landed = await land_payload(
            db.data, "launch-library", dev.launches_endpoint, {"mode": "normal"}, body
        )
        await apply_payload(db.data, dev, landed, RunStats())
        await db.data.commit()


@pytest.mark.anyio
async def test_replay_rebuilds_from_the_pinned_origin_and_prunes_dev_only_rows(
    clean_database: Database,
) -> None:
    await ingest(clean_database, ReferenceSource())
    history = fixture("launches_history.json")
    await ingest_launch_library(clean_database, FakeLaunchLibrary([history]), base_url=PRODUCTION)
    shared = {**history["results"][0], "name": "Stale dev-host name"}
    dev_page = fixture("launches_page.json")
    await land_dev_page(clean_database, {**dev_page, "results": [*dev_page["results"], shared]})
    url = clean_database.owner_url
    mixed = {row[0] for row in query(url, "SELECT origin FROM mart.dq_source_origin_mix")}

    async with connections(clean_database.writer_url) as db:
        replayed = await replay_source(
            LaunchLibrarySource(PRODUCTION, page_size=PAGE_SIZE), db=db.data
        )

    assert mixed == {PRODUCTION, DEV}
    assert replayed.foreign_payloads == 1
    assert replayed.pruned.deleted["core.launch"] == len(dev_page["results"])
    assert scalar(url, "SELECT count(*) FROM core.launch") == len(history["results"])
    renamed = execute(url, "SELECT name FROM core.launch WHERE ll2_id = %s", (shared["id"],))
    assert renamed == [(history["results"][0]["name"],)]
    assert query(url, "SELECT * FROM mart.dq_source_origin_mix") == []
    assert scalar(url, DEV_LINKS) == 0


def full_page(body: dict[str, Any]) -> dict[str, Any]:
    return {**body, "next": "https://ll.thespacedevs.com/2.3.0/landings/?offset=5"}


def test_normalizes_first_stage_landings_and_skips_spacecraft() -> None:
    batch = normalize_landings(LandingPage.model_validate(fixture("landings_page.json")))

    reflight = next(row for row in batch.landings if row.ll2_id == 1710)
    expended = next(row for row in batch.landings if row.ll2_id == 1960)
    assert [row.ll2_id for row in batch.landings] == [1710, 1954, 1960, 1971]
    assert (reflight.launcher_flight_number, reflight.success, reflight.type_abbrev) == (
        3,
        True,
        "ASDS",
    )
    assert reflight.previous_flight_at == datetime(2025, 8, 27, 11, 10, 40, tzinfo=UTC)
    assert (expended.attempt, expended.success) == (False, None)
    assert {row.serial_number for row in batch.launchers} == {
        "B1095",
        "Booster 21",
        "B1106",
        "B1093",
    }


LANDING_FLIGHTS = """
SELECT landing_id, serial_number, flight_at, launch_id::text, flown
FROM mart.landing_flight ORDER BY landing_id
"""


@pytest.mark.anyio
async def test_landings_are_matched_to_the_launch_their_turnaround_points_at(
    clean_database: Database,
) -> None:
    await ingest(clean_database, ReferenceSource())
    server = FakeLaunchLibrary(
        [fixture("launches_history.json")],
        launcher_pages=[fixture("launchers_page.json")],
        landing_pages=[fixture("landings_page.json")],
    )

    outcome = await ingest_launch_library(clean_database, server)

    url = clean_database.owner_url
    flights = {row[0]: row for row in query(url, LANDING_FLIGHTS)}
    assert outcome.status is RunStatus.SUCCEEDED
    assert flights[1710][1:] == (
        "B1095",
        datetime(2025, 10, 16, 9, 27, 10, tzinfo=UTC),
        "02348ca1-d937-441b-86fe-5002275907db",
        True,
    )
    assert flights[1954][2] == datetime(2026, 9, 28, 12, 48, 59, tzinfo=UTC)
    assert query(url, "SELECT landing_id FROM mart.dq_unmatched_landing ORDER BY 1") == [
        (1954,),
        (1960,),
    ]
    assert query(
        url, "SELECT vehicle_ll2_id, flights FROM core.launcher WHERE serial_number = 'B1095'"
    ) == [(164, 7)]
    assert scalar(url, "SELECT count(*) FROM core.launcher WHERE is_placeholder") == 1


@pytest.mark.anyio
async def test_caught_up_landings_stop_at_a_page_of_settled_known_landings(
    clean_database: Database,
) -> None:
    await ingest(clean_database, ReferenceSource())
    landings = fixture("landings_page.json")
    await ingest_launch_library(
        clean_database,
        FakeLaunchLibrary(
            [], launcher_pages=[fixture("launchers_page.json")], landing_pages=[landings]
        ),
    )
    settled = {**landings, "results": [r for r in landings["results"] if r["id"] != 1971]}
    server = FakeLaunchLibrary([], landing_pages=[full_page(landings), full_page(settled)])

    second = await ingest_launch_library(clean_database, server)

    offsets = [r.url.params["offset"] for r in server.data_requests() if "landings" in r.url.path]
    assert second.status is RunStatus.SUCCEEDED
    assert offsets == ["0", "5"]
    assert [r.url.params["mode"] for r in server.data_requests() if "landings" in r.url.path] == [
        "list",
        "list",
    ]


@pytest.mark.anyio
async def test_an_interrupted_landing_backfill_resumes_at_its_last_page(
    clean_database: Database,
) -> None:
    await ingest(clean_database, ReferenceSource())
    landings = fixture("landings_page.json")
    launchers = fixture("launchers_page.json")
    await ingest_launch_library(
        clean_database,
        FakeLaunchLibrary(
            [], launcher_pages=[launchers], landing_pages=[full_page(landings), full_page(landings)]
        ),
        max_requests=6,
    )
    server = FakeLaunchLibrary([], landing_pages=[landings])

    resumed = await ingest_launch_library(clean_database, server)

    offsets = [r.url.params["offset"] for r in server.data_requests() if "landings" in r.url.path]
    assert resumed.status is RunStatus.SUCCEEDED
    assert offsets == ["5"]
    assert scalar(clean_database.owner_url, "SELECT count(*) FROM core.landing") == 4


@pytest.mark.anyio
async def test_launchers_are_swept_once_a_day(clean_database: Database) -> None:
    await ingest(clean_database, ReferenceSource())
    await ingest_launch_library(
        clean_database, FakeLaunchLibrary([], launcher_pages=[fixture("launchers_page.json")])
    )
    server = FakeLaunchLibrary([])

    await ingest_launch_library(clean_database, server)

    assert not [r for r in server.data_requests() if "launchers" in r.url.path]
