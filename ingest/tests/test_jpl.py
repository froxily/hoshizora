import json
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import httpx
import pytest
import respx

from hoshizora_ingest.db import connections
from hoshizora_ingest.http.errors import SourceHttpError
from hoshizora_ingest.pipeline import RunEnvironment, RunOutcome, run_source
from hoshizora_ingest.raw.runs import RunStatus
from hoshizora_ingest.sources.jpl.adapter import (
    BASE_URL,
    JplSource,
    UnsupportedVersionError,
    cad_window,
    decade_windows,
    rolling_window,
)
from hoshizora_ingest.sources.jpl.models import CadResponse, calendar_tdb, observation_date
from hoshizora_ingest.transform.jpl import impact_years

from conftest import Database
from fakes import RecordingSleep, execute, query, scalar

FIXTURES = Path(__file__).parent / "fixtures" / "jpl"
TODAY = datetime(2026, 10, 16, 12, 0, tzinfo=UTC)


def fixture(name: str) -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads((FIXTURES / name).read_text(encoding="utf-8")))


CAD_WINDOW = fixture("cad_window.json")
CAD_EMPTY = fixture("cad_empty.json")
SUMMARY = fixture("sentry_summary.json")
REMOVED = fixture("sentry_removed.json")
WINDOW_PARAMS = {"date-min": "2026-10-01", "date-max": "2026-10-08", "body": "Earth"}


def test_close_approach_times_are_parsed_as_tdb_calendar_dates() -> None:
    assert calendar_tdb("2026-Oct-01 11:01") == datetime.fromisoformat("2026-10-01T11:01")


def test_cad_rows_map_by_field_name_and_strip_full_names() -> None:
    window = cad_window(CadResponse.model_validate(CAD_WINDOW), WINDOW_PARAMS)
    first = window.approaches[0]

    assert (first.des, first.fullname, first.diameter) == ("2026 TZ", "(2026 TZ)", None)
    assert len(window.approaches) == int(CAD_WINDOW["count"])


def test_an_empty_window_has_no_approaches() -> None:
    assert cad_window(CadResponse.model_validate(CAD_EMPTY), WINDOW_PARAMS).approaches == []


def test_a_new_api_version_fails_loudly() -> None:
    changed = deepcopy(CAD_WINDOW)
    changed["signature"]["version"] = "1.6"

    with pytest.raises(UnsupportedVersionError):
        cad_window(CadResponse.model_validate(changed), WINDOW_PARAMS)


def test_fractional_observation_days_keep_their_date() -> None:
    assert observation_date("2020-10-3.80160") == date(2020, 10, 3)
    assert observation_date("2013-01-12") == "2013-01-12"


def test_sentry_year_ranges() -> None:
    assert [impact_years(v) for v in ("2178-2290", "2064", None)] == [
        (2178, 2290),
        (2064, 2064),
        (None, None),
    ]


def test_backfill_covers_1900_to_2200_in_decades() -> None:
    windows = decade_windows()

    assert (len(windows), windows[0][0], windows[-1][1]) == (30, date(1900, 1, 1), date(2200, 1, 1))


@dataclass
class FakeJpl:
    rolling: list[dict[str, Any]] = field(default_factory=lambda: [CAD_WINDOW])
    summaries: list[dict[str, Any]] = field(default_factory=lambda: [SUMMARY])
    removals: list[dict[str, Any]] = field(default_factory=lambda: [REMOVED])
    error: httpx.Response | None = None
    today: date = field(default_factory=TODAY.date)
    requests: list[httpx.Request] = field(default_factory=list[httpx.Request])

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.error is not None:
            return self.error
        params = request.url.params
        if request.url.path == "/cad.api":
            start, _ = rolling_window(self.today)
            if params["date-min"] == start.isoformat():
                return httpx.Response(200, json=self.rolling.pop(0))
            return httpx.Response(200, json=CAD_EMPTY)
        if params.get("removed") == "1":
            return httpx.Response(200, json=self.removals.pop(0))
        return httpx.Response(200, json=self.summaries.pop(0))


async def ingest_jpl(
    database: Database, server: FakeJpl, clock: Callable[[], datetime] = lambda: TODAY
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
            return await run_source(JplSource(), env)


def thirteen_hours_later() -> datetime:
    return datetime.now(UTC) + timedelta(hours=13)


@pytest.mark.anyio
async def test_first_run_backfills_decades_then_refreshes_the_rolling_window(
    clean_database: Database,
) -> None:
    server = FakeJpl()

    outcome = await ingest_jpl(clean_database, server)

    url = clean_database.owner_url
    assert outcome.status is RunStatus.SUCCEEDED
    assert len(server.requests) == 33
    assert scalar(url, "SELECT count(*) FROM core.close_approach") == int(CAD_WINDOW["count"])
    assert scalar(url, "SELECT count(*) FROM core.impact_risk") == len(SUMMARY["data"])
    assert query(
        url,
        "SELECT designation, impact_year_first, impact_year_last FROM core.impact_risk "
        "WHERE designation = '101955'",
    ) == [("101955", 2178, 2290)]


@pytest.mark.anyio
async def test_an_immediate_rerun_makes_no_requests(clean_database: Database) -> None:
    await ingest_jpl(clean_database, FakeJpl())
    server = FakeJpl(rolling=[], summaries=[], removals=[])

    second = await ingest_jpl(clean_database, server)

    assert (second.status, len(server.requests)) == (RunStatus.SUCCEEDED, 0)


@pytest.mark.anyio
async def test_a_revised_prediction_replaces_its_stale_row(clean_database: Database) -> None:
    revised = deepcopy(CAD_WINDOW)
    revised["data"][0][3] = "2026-Oct-01 11:04"
    await ingest_jpl(clean_database, FakeJpl())
    later = thirteen_hours_later()

    await ingest_jpl(clean_database, FakeJpl(rolling=[revised], today=later.date()), lambda: later)

    assert query(
        clean_database.owner_url,
        "SELECT approach_tdb::text FROM core.close_approach WHERE designation = '2026 TZ'",
    ) == [("2026-10-01 11:04:00",)]


@pytest.mark.anyio
async def test_removal_marks_only_objects_no_longer_listed(clean_database: Database) -> None:
    await ingest_jpl(clean_database, FakeJpl())
    dropped, kept = SUMMARY["data"][-1]["des"], SUMMARY["data"][0]["des"]
    trimmed = deepcopy(SUMMARY)
    trimmed["data"] = [row for row in SUMMARY["data"] if row["des"] != dropped]
    removals = deepcopy(REMOVED)
    removals["data"] = [
        {"des": dropped, "removed": "2026-10-16 08:00:00"},
        {"des": kept, "removed": "2001-01-01 00:00:00"},
    ]

    later = thirteen_hours_later()

    await ingest_jpl(
        clean_database,
        FakeJpl(rolling=[CAD_WINDOW], summaries=[trimmed], removals=[removals], today=later.date()),
        lambda: later,
    )

    assert execute(
        clean_database.owner_url,
        "SELECT designation, removed_at IS NOT NULL FROM core.impact_risk "
        "WHERE designation = ANY(%s) ORDER BY 2",
        ([dropped, kept],),
    ) == [(kept, False), (dropped, True)]


@pytest.mark.anyio
async def test_a_client_error_fails_the_run_without_retrying(clean_database: Database) -> None:
    server = FakeJpl(error=httpx.Response(400, json=fixture("cad_error.json")))

    with pytest.raises(SourceHttpError):
        await ingest_jpl(clean_database, server)

    assert len(server.requests) == 1
    assert scalar(clean_database.owner_url, "SELECT status FROM raw.ingest_run") == "failed"
