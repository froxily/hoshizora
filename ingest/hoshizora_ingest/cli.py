import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer

from hoshizora_ingest.backfill.loop import Backfill, BackfillEnd, Journal, describe_replay
from hoshizora_ingest.backfill.status import render_status
from hoshizora_ingest.config import ConfigurationError
from hoshizora_ingest.facts.engine import Generated
from hoshizora_ingest.pipeline import RunOutcome
from hoshizora_ingest.quality.report import render_report
from hoshizora_ingest.raw.runs import RunStatus
from hoshizora_ingest.reference.docs import write_document
from hoshizora_ingest.registry import LAUNCH_LIBRARY_PRODUCTION, SOURCES, Registry, SourceEntry
from hoshizora_ingest.runner import DatabaseRunner, Runner

NO_SOURCES = "No sources registered yet."
EXIT_FAILED = 1
EXIT_CONFIGURATION = 2
EXIT_NEEDS_REVIEW = 3
EXIT_INTERRUPTED = 130
BACKFILL_EXIT = {
    BackfillEnd.COMPLETE: 0,
    BackfillEnd.FAILED: EXIT_FAILED,
    BackfillEnd.NEEDS_REVIEW: EXIT_NEEDS_REVIEW,
    BackfillEnd.STALLED: EXIT_FAILED,
}

SourceSlug = Annotated[str, typer.Argument(help="Source slug from `hoshizora sources`.")]
MaxRequests = Annotated[int | None, typer.Option(min=1, help="Stop after this many data requests.")]
Reviewed = Annotated[
    bool,
    typer.Option(help="Resume a source held because its last run needs review."),
]
MaxWait = Annotated[
    float | None,
    typer.Option(
        min=0,
        help="End a source's run as partial instead of waiting longer than this many seconds.",
    ),
]
Strict = Annotated[bool, typer.Option(help="Exit 1 when a blocking check finds problems.")]
LogFile = Annotated[
    Path | None, typer.Option(help="Append each backfill line to this file as well.")
]


@contextmanager
def configuration_errors() -> Generator[None]:
    try:
        yield
    except ConfigurationError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(EXIT_CONFIGURATION) from error


def describe_facts(generated: Generated) -> str:
    summary = f"{generated.facts} from {generated.templates} templates, {generated.removed} removed"
    waits = "; ".join(
        f"{len(skip.templates)} templates wait for {skip.source} "
        f"(status {skip.status or 'missing'})"
        for skip in generated.skipped
    )
    return f"{summary}; {waits}" if waits else summary


def exit_code(outcome: RunOutcome) -> int:
    if outcome.status is RunStatus.NEEDS_REVIEW:
        return EXIT_NEEDS_REVIEW
    if outcome.status is RunStatus.FAILED:
        return EXIT_FAILED
    return 0


@dataclass(frozen=True)
class Ingested:
    code: int
    changed: bool


@dataclass(frozen=True)
class Commands:
    registry: Registry
    runner: Runner
    sleep: Callable[[float], None] = time.sleep

    def sources(self) -> None:
        if not self.registry:
            typer.echo(NO_SOURCES)
            return
        for entry in self.registry.values():
            info = entry.info
            typer.echo(f"{info.slug}\t{info.name}\t{info.cadence}")

    def ingest(
        self,
        source: SourceSlug,
        max_requests: MaxRequests = None,
        *,
        reviewed: Reviewed = False,
        max_wait: MaxWait = None,
    ) -> None:
        with configuration_errors():
            ingested = self._ingest_entry(
                self._entry_for(source), max_requests, reviewed=reviewed, max_wait=max_wait
            )
            code = max(ingested.code, self._refresh() if ingested.changed else 0)
        if code:
            raise typer.Exit(code)

    def ingest_all(self, *, reviewed: Reviewed = False, max_wait: MaxWait = None) -> None:
        if not self.registry:
            typer.echo(NO_SOURCES)
            return
        with configuration_errors():
            runs = [
                self._ingest_entry(entry, None, reviewed=reviewed, max_wait=max_wait)
                for entry in self.registry.values()
            ]
            refreshed = self._refresh() if any(ingested.changed for ingested in runs) else 0
        code = max([ingested.code for ingested in runs] + [refreshed])
        if code:
            raise typer.Exit(code)

    def replay(self, source: SourceSlug) -> None:
        with configuration_errors():
            replayed = self.runner.replay(self._entry_for(source))
            typer.echo(f"{source}: {describe_replay(replayed)}")
            changed = replayed.stats.rows_upserted or replayed.pruned.deleted
            code = self._refresh() if changed else 0
        if code:
            raise typer.Exit(code)

    def backfill(self, log_file: LogFile = None) -> None:
        journal = Journal(log_file)
        backfill = Backfill(self.runner, LAUNCH_LIBRARY_PRODUCTION, journal, self.sleep)
        with configuration_errors():
            try:
                end = backfill.run()
            except KeyboardInterrupt:
                journal("interrupted; run `just backfill` again to resume from the watermark")
                raise typer.Exit(EXIT_INTERRUPTED) from None
        if code := BACKFILL_EXIT[end]:
            raise typer.Exit(code)

    def backfill_status(self) -> None:
        with configuration_errors():
            status = self.runner.backfill_status()
        for line in render_status(status):
            typer.echo(line)

    def facts(self) -> None:
        with configuration_errors():
            code = self._facts()
        if code:
            raise typer.Exit(code)

    def refresh_marts(self) -> None:
        with configuration_errors():
            code = self._refresh()
        if code:
            raise typer.Exit(code)

    def dq(self, *, strict: Strict = False) -> None:
        with configuration_errors():
            sections = self.runner.quality()
        typer.echo(render_report(sections))
        if strict and any(section.failed for section in sections):
            raise typer.Exit(EXIT_FAILED)

    def docs(self) -> None:
        typer.echo(f"wrote {write_document()}")

    def _entry_for(self, slug: str) -> SourceEntry:
        entry = self.registry.get(slug)
        if entry is None:
            message = f"Unknown source: {slug}"
            raise typer.BadParameter(message, param_hint="SOURCE")
        return entry

    def _ingest_entry(
        self,
        entry: SourceEntry,
        max_requests: int | None,
        *,
        reviewed: bool = False,
        max_wait: float | None = None,
    ) -> Ingested:
        try:
            outcome = self.runner.ingest(entry, max_requests, reviewed=reviewed, max_wait=max_wait)
        except ConfigurationError:
            raise
        except Exception as failure:
            typer.echo(f"{entry.info.slug}: failed ({failure!r})", err=True)
            return Ingested(EXIT_FAILED, changed=True)
        typer.echo(f"{entry.info.slug}: {outcome.summary}")
        return Ingested(exit_code(outcome), changed=outcome.stats.rows_upserted > 0)

    def _refresh(self) -> int:
        try:
            refreshed = self.runner.refresh_marts()
        except ConfigurationError:
            raise
        except Exception as failure:
            typer.echo(f"marts: refresh failed ({failure!r})", err=True)
            return EXIT_FAILED
        typer.echo(f"marts: refreshed {len(refreshed.views)} views in {refreshed.seconds:.1f} s")
        return self._facts()

    def _facts(self) -> int:
        try:
            generated = self.runner.generate_facts()
        except ConfigurationError:
            raise
        except Exception as failure:
            typer.echo(f"facts: generation failed ({failure!r})", err=True)
            return EXIT_FAILED
        typer.echo(f"facts: {describe_facts(generated)}")
        return 0


def create_app(
    registry: Registry, runner: Runner, sleep: Callable[[float], None] = time.sleep
) -> typer.Typer:
    app = typer.Typer(name="hoshizora", no_args_is_help=True, add_completion=False)
    commands = Commands(registry, runner, sleep)
    app.command("sources")(commands.sources)
    app.command("ingest")(commands.ingest)
    app.command("ingest-all")(commands.ingest_all)
    app.command("replay")(commands.replay)
    app.command("backfill")(commands.backfill)
    app.command("backfill-status")(commands.backfill_status)
    app.command("refresh-marts")(commands.refresh_marts)
    app.command("facts")(commands.facts)
    app.command("dq")(commands.dq)
    app.command("docs")(commands.docs)
    return app


app = create_app(SOURCES, DatabaseRunner())
