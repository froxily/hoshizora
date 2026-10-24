from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from psycopg.types.json import Jsonb
from typer.testing import CliRunner

from hoshizora_ingest.analytics.refresh import Refreshed
from hoshizora_ingest.backfill.status import (
    PRODUCTION,
    BackfillStatus,
    LastRun,
    LatestPage,
    backfill_status,
    render_status,
)
from hoshizora_ingest.cli import create_app
from hoshizora_ingest.db import connections
from hoshizora_ingest.facts.engine import Generated
from hoshizora_ingest.pipeline import Replayed, RunOutcome
from hoshizora_ingest.quality.report import Section
from hoshizora_ingest.raw.runs import RunStats, RunStatus
from hoshizora_ingest.registry import SOURCES, SourceEntry
from hoshizora_ingest.sources.launch_library.adapter import Quota
from hoshizora_ingest.store.origins import Pruned

from conftest import Database
from fakes import execute

WATERMARK = datetime(2023, 6, 14, 17, 25, 30, tzinfo=UTC)
STARTED = datetime(2026, 10, 18, 7, 0, tzinfo=UTC)
LAST_RUN = LastRun(16, STARTED, "partial", "https://ll.thespacedevs.com")


def page(reported: int, returned: int, offset: int = 0) -> LatestPage:
    return LatestPage(reported, returned, offset, 100, WATERMARK)


def status(loaded: int, latest: LatestPage | None) -> BackfillStatus:
    return BackfillStatus(loaded, latest, LAST_RUN)


def outcome(status: RunStatus, payloads: int, error: str | None = None) -> RunOutcome:
    stats = RunStats(requests=payloads, payloads_new=payloads, rows_in=payloads, rows_upserted=1)
    return RunOutcome(run_id=16, status=status, stats=stats, error=error)


@dataclass
class ScriptedRunner:
    outcomes: list[RunOutcome | Exception]
    statuses: list[BackfillStatus]
    quotas: list[Quota] = field(default_factory=list[Quota])
    budgets: list[int | None] = field(default_factory=list[int | None])
    replays: int = 0
    refreshes: int = 0

    def ingest(
        self,
        entry: SourceEntry,
        max_requests: int | None,
        *,
        reviewed: bool = False,
        max_wait: float | None = None,
    ) -> RunOutcome:
        del entry, reviewed, max_wait
        self.budgets.append(max_requests)
        result = self.outcomes.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def replay(self, entry: SourceEntry) -> Replayed:
        del entry
        self.replays += 1
        return Replayed(
            RunStats(rows_in=9), "https://ll.thespacedevs.com", 7, Pruned({"core.launch": 2})
        )

    def quality(self) -> list[Section]:
        return []

    def refresh_marts(self) -> Refreshed:
        self.refreshes += 1
        return Refreshed(views=("launch_cadence_yearly",), seconds=0.1)

    def generate_facts(self) -> Generated:
        return Generated(templates=20, facts=60, removed=0, skipped=())

    def backfill_status(self) -> BackfillStatus:
        return self.statuses.pop(0)

    def quota(self, entry: SourceEntry) -> Quota | None:
        del entry
        return self.quotas.pop(0) if self.quotas else Quota(15, 0.0)


@dataclass
class Sleeps:
    seconds: list[float] = field(default_factory=list[float])

    def __call__(self, seconds: float) -> None:
        self.seconds.append(seconds)


def backfill(runner: ScriptedRunner, log_file: Path) -> tuple[int, str, Sleeps]:
    sleeps = Sleeps()
    app = create_app(SOURCES, runner, sleeps)
    result = CliRunner().invoke(app, ["backfill", "--log-file", str(log_file)])
    return result.exit_code, result.output, sleeps


def test_a_page_short_of_the_page_size_means_nothing_is_left() -> None:
    assert page(3268, 40, offset=3200).remaining == 0
    assert status(8126, page(3268, 40, offset=3200)).complete


def test_status_counts_pages_left_after_the_latest_page() -> None:
    current = status(4958, page(3268, 100))

    assert current.remaining == 3168
    assert current.total == 8126
    assert current.pages_left == 32
    assert current.eta == timedelta(hours=32 / 15)


def test_status_renders_progress_last_run_and_eta() -> None:
    lines = render_status(status(4958, page(3268, 100)))

    assert lines[1:] == [
        "Launches: 4,958 of 8,126 reported by LL2 (61%)",
        "Pages left: 32 (3,168 launches after watermark 2023-06-14 17:25 UTC)",
        "Last run: #16 at 2026-10-18 07:00 UTC, partial, from https://ll.thespacedevs.com",
        "ETA: about 2 h 8 min at 15 requests per hour",
    ]


def test_status_without_a_production_page_says_so() -> None:
    lines = render_status(BackfillStatus(515, None, None))

    assert lines[1:] == [
        "Launches: 515 loaded; no production launch page landed yet",
        "Last run: none yet",
    ]


@pytest.mark.anyio
async def test_status_reads_only_production_launch_pages(clean_database: Database) -> None:
    url = clean_database.owner_url
    pages = (
        (PRODUCTION.launches_endpoint, "0", 3268, ["a", "b"]),
        (PRODUCTION.launches_endpoint, "2", 3268, ["b", "c"]),
        ("https://lldev.thespacedevs.com/2.3.0/launches/", "0", 1, ["dev-only"]),
    )
    for endpoint, offset, count, ids in pages:
        params = {"limit": "2", "offset": offset, "last_updated__gte": "2023-06-14T17:25:30Z"}
        execute(
            url,
            "INSERT INTO raw.payload (source, endpoint, params, content_hash, body) "
            "VALUES ('launch-library', %s, %s, md5(%s), %s) RETURNING id",
            (
                endpoint,
                Jsonb(params),
                f"{endpoint}{offset}",
                Jsonb({"count": count, "results": [{"id": launch} for launch in ids]}),
            ),
        )
    execute(
        url,
        "INSERT INTO raw.ingest_run (source, origin) VALUES ('launch-library', %s) RETURNING id",
        ("https://ll.thespacedevs.com",),
    )

    async with connections(clean_database.writer_url) as db:
        current = await backfill_status(db.data)

    assert current.loaded == 3
    assert current.remaining == 3268 - 2 - 2
    assert current.last_run is not None
    assert current.last_run.status == "running"


def test_backfill_waits_for_quota_then_replays_and_finishes(tmp_path: Path) -> None:
    runner = ScriptedRunner(
        outcomes=[outcome(RunStatus.PARTIAL, 15, "quota"), outcome(RunStatus.SUCCEEDED, 3)],
        statuses=[status(6458, page(1768, 100)), status(8126, page(1768, 40, 1700))],
        quotas=[Quota(15, 0.0), Quota(0, 1500.0), Quota(15, 0.0)],
    )
    log_file = tmp_path / "logs" / "backfill.log"

    code, output, sleeps = backfill(runner, log_file)

    assert code == 0
    assert runner.budgets == [15, 15]
    assert sleeps.seconds == [61, 1500.0]
    assert runner.replays == 1
    assert runner.refreshes == 3
    logged = log_file.read_text(encoding="utf-8")
    assert "waiting 25 min for the LL2 quota" in logged
    assert "6,458/8,126 launches, 17 pages left" in logged
    assert "deleted 2 core.launch" in logged
    assert logged.rstrip().endswith("complete: no launch pages left")
    assert logged.splitlines() == output.splitlines()


def test_backfill_stops_when_a_run_needs_review(tmp_path: Path) -> None:
    runner = ScriptedRunner(
        outcomes=[outcome(RunStatus.NEEDS_REVIEW, 1)], statuses=[status(10, page(50, 100))]
    )

    code, output, _ = backfill(runner, tmp_path / "backfill.log")

    assert code == 3
    assert "needs review; stopping" in output
    assert runner.replays == 0


def test_backfill_stops_after_two_runs_without_progress(tmp_path: Path) -> None:
    runner = ScriptedRunner(
        outcomes=[outcome(RunStatus.PARTIAL, 0), outcome(RunStatus.PARTIAL, 0)],
        statuses=[status(10, page(50, 100)), status(10, page(50, 100))],
    )

    code, output, _ = backfill(runner, tmp_path / "backfill.log")

    assert code == 1
    assert "2 runs in a row landed nothing; stopping" in output


def test_backfill_stops_when_a_run_fails(tmp_path: Path) -> None:
    runner = ScriptedRunner(outcomes=[RuntimeError("database went away")], statuses=[])

    code, output, _ = backfill(runner, tmp_path / "backfill.log")

    assert code == 1
    assert "run failed (RuntimeError('database went away')); stopping" in output
