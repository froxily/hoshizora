from dataclasses import dataclass, field

import pytest
from typer.testing import CliRunner

from hoshizora_ingest.analytics.refresh import Refreshed
from hoshizora_ingest.backfill.status import BackfillStatus
from hoshizora_ingest.cli import (
    EXIT_CONFIGURATION,
    EXIT_FAILED,
    EXIT_NEEDS_REVIEW,
    NO_SOURCES,
    create_app,
)
from hoshizora_ingest.facts.engine import Generated, Skipped
from hoshizora_ingest.pipeline import Replayed, RunOutcome
from hoshizora_ingest.quality.report import Section
from hoshizora_ingest.raw.runs import RunStats, RunStatus
from hoshizora_ingest.registry import Registry, SourceEntry, registry_of
from hoshizora_ingest.runner import DatabaseRunner
from hoshizora_ingest.sources.base import SourceInfo
from hoshizora_ingest.sources.launch_library.adapter import Quota
from hoshizora_ingest.store.origins import Pruned

from fakes import ProbeSource

cli = CliRunner()


def entry(slug: str) -> SourceEntry:
    info = SourceInfo(slug=slug, name=slug.title(), credit="Test", cadence="daily")
    return SourceEntry(info=info, build=lambda _settings: ProbeSource())


@dataclass
class FakeRunner:
    statuses: dict[str, RunStatus] = field(default_factory=dict[str, RunStatus])
    changed: set[str] = field(default_factory=set[str])
    crashing: set[str] = field(default_factory=set[str])
    replay_changes: int = 0
    refresh_fails: bool = False
    ingested: list[tuple[str, int | None]] = field(default_factory=list[tuple[str, int | None]])
    reviewed: list[str] = field(default_factory=list[str])
    max_waits: list[float | None] = field(default_factory=list[float | None])
    replayed: list[str] = field(default_factory=list[str])
    sections: list[Section] = field(default_factory=list[Section])
    refreshes: int = 0
    generations: int = 0

    def ingest(
        self,
        entry: SourceEntry,
        max_requests: int | None,
        *,
        reviewed: bool = False,
        max_wait: float | None = None,
    ) -> RunOutcome:
        slug = entry.info.slug
        self.ingested.append((slug, max_requests))
        self.max_waits.append(max_wait)
        if reviewed:
            self.reviewed.append(slug)
        if slug in self.crashing:
            message = f"{slug} crashed"
            raise RuntimeError(message)
        status = self.statuses.get(slug, RunStatus.SUCCEEDED)
        stats = RunStats(requests=1, rows_in=3, rows_upserted=3 if slug in self.changed else 0)
        return RunOutcome(run_id=1, status=status, stats=stats, error=None)

    def replay(self, entry: SourceEntry) -> Replayed:
        self.replayed.append(entry.info.slug)
        stats = RunStats(rows_in=4, rows_upserted=self.replay_changes)
        return Replayed(stats, "https://example.test", 0, Pruned())

    def generate_facts(self) -> Generated:
        self.generations += 1
        waiting = Skipped("launch-library", "partial", ("launches.record_year",))
        return Generated(templates=2, facts=5, removed=1, skipped=(waiting,))

    def backfill_status(self) -> BackfillStatus:
        return BackfillStatus(loaded=0, latest=None, last_run=None)

    def quota(self, entry: SourceEntry) -> Quota | None:
        del entry

    def quality(self) -> list[Section]:
        return self.sections

    def refresh_marts(self) -> Refreshed:
        if self.refresh_fails:
            message = "refresh broke"
            raise RuntimeError(message)
        self.refreshes += 1
        return Refreshed(views=("kp_daily", "launch_cadence_yearly"), seconds=0.25)


def invoke(registry: Registry, runner: FakeRunner, *args: str) -> tuple[int, str]:
    result = cli.invoke(create_app(registry, runner), list(args))
    return result.exit_code, result.output


def test_sources_reports_an_empty_registry() -> None:
    code, output = invoke(registry_of(), FakeRunner(), "sources")

    assert code == 0
    assert output.strip() == NO_SOURCES


def test_sources_lists_slugs_in_registry_order() -> None:
    _, output = invoke(registry_of(entry("swpc"), entry("celestrak")), FakeRunner(), "sources")

    assert [line.split("\t")[0] for line in output.splitlines()] == ["swpc", "celestrak"]


def test_ingest_runs_only_the_named_source_with_its_budget() -> None:
    runner = FakeRunner()

    code, _ = invoke(
        registry_of(entry("swpc"), entry("celestrak")),
        runner,
        "ingest",
        "swpc",
        "--max-requests",
        "5",
    )

    assert code == 0
    assert runner.ingested == [("swpc", 5)]


def test_ingest_all_passes_review_and_wait_limits_to_every_source() -> None:
    runner = FakeRunner()

    code, _ = invoke(
        registry_of(entry("swpc"), entry("celestrak")),
        runner,
        "ingest-all",
        "--reviewed",
        "--max-wait",
        "120",
    )

    assert code == 0
    assert (runner.reviewed, runner.max_waits) == (["swpc", "celestrak"], [120.0, 120.0])


def test_ingest_rejects_an_unknown_source() -> None:
    runner = FakeRunner()

    code, output = invoke(registry_of(entry("swpc")), runner, "ingest", "nope")

    assert code == 2
    assert "Unknown source: nope" in output
    assert runner.ingested == []


def test_ingest_exits_with_a_distinct_code_when_a_run_needs_review() -> None:
    runner = FakeRunner(statuses={"celestrak": RunStatus.NEEDS_REVIEW})

    code, _ = invoke(registry_of(entry("celestrak")), runner, "ingest", "celestrak")

    assert code == EXIT_NEEDS_REVIEW


def test_ingest_all_runs_every_source_and_reports_the_worst_outcome() -> None:
    runner = FakeRunner(statuses={"celestrak": RunStatus.NEEDS_REVIEW})

    code, _ = invoke(
        registry_of(entry("reference"), entry("celestrak"), entry("swpc")), runner, "ingest-all"
    )

    assert [slug for slug, _ in runner.ingested] == ["reference", "celestrak", "swpc"]
    assert code == EXIT_NEEDS_REVIEW


def test_ingest_all_with_an_empty_registry_succeeds() -> None:
    code, output = invoke(registry_of(), FakeRunner(), "ingest-all")

    assert code == 0
    assert output.strip() == NO_SOURCES


def test_replay_reports_changed_rows() -> None:
    runner = FakeRunner()

    _, output = invoke(registry_of(entry("swpc")), runner, "replay", "swpc")

    assert runner.replayed == ["swpc"]
    assert "0/4 rows changed" in output


def test_ingest_refreshes_marts_only_when_rows_changed() -> None:
    quiet = FakeRunner()
    busy = FakeRunner(changed={"swpc"})

    invoke(registry_of(entry("swpc")), quiet, "ingest", "swpc")
    code, output = invoke(registry_of(entry("swpc")), busy, "ingest", "swpc")

    assert quiet.refreshes == 0
    assert busy.refreshes == 1
    assert code == 0
    assert "marts: refreshed 2 views in 0.2 s" in output


def test_ingest_all_refreshes_once_after_every_source() -> None:
    runner = FakeRunner(changed={"reference", "swpc"})

    invoke(registry_of(entry("reference"), entry("celestrak"), entry("swpc")), runner, "ingest-all")

    assert runner.refreshes == 1


def test_a_crashed_run_still_refreshes_because_earlier_pages_committed() -> None:
    runner = FakeRunner(crashing={"launch-library"})

    code, _ = invoke(registry_of(entry("launch-library")), runner, "ingest", "launch-library")

    assert code == EXIT_FAILED
    assert runner.refreshes == 1


def test_replay_refreshes_when_rows_changed() -> None:
    runner = FakeRunner(replay_changes=2)

    invoke(registry_of(entry("swpc")), runner, "replay", "swpc")

    assert runner.refreshes == 1


def test_refresh_marts_command_reports_failures() -> None:
    ok, output = invoke(registry_of(), FakeRunner(), "refresh-marts")
    failed, _ = invoke(registry_of(), FakeRunner(refresh_fails=True), "refresh-marts")

    assert ok == 0
    assert "refreshed 2 views" in output
    assert failed == EXIT_FAILED


def test_dq_prints_every_section() -> None:
    runner = FakeRunner(
        sections=[Section("Unmapped external codes", ("code",), (("XYZ",),), blocking=True)]
    )

    code, output = invoke(registry_of(), runner, "dq")

    assert code == 0
    assert "Unmapped external codes (1) [FAIL]" in output
    assert "XYZ" in output


def test_dq_strict_fails_only_on_blocking_problems() -> None:
    informational = Section(
        "Missing name_ja by entity", ("entity",), (("organization",),), blocking=False
    )
    blocking = Section("Unmapped external codes", ("code",), (("XYZ",),), blocking=True)

    clean, _ = invoke(registry_of(), FakeRunner(sections=[informational]), "dq", "--strict")
    failing, _ = invoke(registry_of(), FakeRunner(sections=[blocking]), "dq", "--strict")

    assert (clean, failing) == (0, 1)


def test_missing_settings_produce_one_clear_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HOSHIZORA_INGEST_DATABASE_URL", raising=False)
    monkeypatch.delenv("HOSHIZORA_LL2_BASE_URL", raising=False)

    result = cli.invoke(create_app(registry_of(), DatabaseRunner()), ["dq"])

    assert result.exit_code == EXIT_CONFIGURATION
    assert "HOSHIZORA_INGEST_DATABASE_URL" in result.output


def test_a_refresh_regenerates_facts_and_reports_waiting_templates() -> None:
    runner = FakeRunner(changed={"swpc"})

    code, output = invoke(registry_of(entry("swpc")), runner, "ingest", "swpc")

    assert code == 0
    assert runner.generations == 1
    assert (
        "facts: 5 from 2 templates, 1 removed; 1 templates wait for launch-library (status partial)"
    ) in output


def test_facts_command_regenerates_without_a_refresh() -> None:
    runner = FakeRunner()

    code, _ = invoke(registry_of(entry("swpc")), runner, "facts")

    assert code == 0
    assert (runner.refreshes, runner.generations) == (0, 1)
