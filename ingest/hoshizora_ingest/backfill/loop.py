from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path

import typer

from hoshizora_ingest.backfill.status import duration, progress
from hoshizora_ingest.config import ConfigurationError
from hoshizora_ingest.pipeline import Replayed
from hoshizora_ingest.raw.runs import RunStatus
from hoshizora_ingest.registry import SourceEntry
from hoshizora_ingest.runner import Runner
from hoshizora_ingest.sources.launch_library.adapter import (
    QUOTA_MARGIN_SECONDS,
    THROTTLE_CACHE_SECONDS,
)

STALL_LIMIT = 2


class BackfillEnd(StrEnum):
    COMPLETE = "complete"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"
    STALLED = "stalled"


@dataclass(frozen=True)
class Journal:
    path: Path | None
    clock: Callable[[], datetime] = lambda: datetime.now(UTC)

    def __call__(self, line: str) -> None:
        stamped = f"{self.clock():%Y-%m-%dT%H:%M:%SZ} {line}"
        typer.echo(stamped)
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as log_file:
            log_file.write(f"{stamped}\n")


def describe_replay(replayed: Replayed) -> str:
    pruned = replayed.pruned
    deleted = ", ".join(f"{count} {entity}" for entity, count in pruned.deleted.items())
    return (
        f"replayed from {replayed.origin}: {replayed.stats.rows_upserted}/"
        f"{replayed.stats.rows_in} rows changed, {replayed.foreign_payloads} foreign payloads "
        f"skipped, {pruned.links_removed} foreign links removed, "
        f"deleted {deleted or 'nothing'}"
    )


@dataclass(frozen=True)
class Backfill:
    runner: Runner
    entry: SourceEntry
    journal: Callable[[str], None]
    sleep: Callable[[float], None]

    def run(self) -> BackfillEnd:
        stalled = 0
        while True:
            budget = self._await_quota()
            try:
                outcome = self.runner.ingest(self.entry, budget)
            except ConfigurationError:
                raise
            except Exception as failure:
                self.journal(f"run failed ({failure!r}); stopping")
                return BackfillEnd.FAILED
            status = self.runner.backfill_status()
            self.journal(f"{outcome.summary} | {progress(status)}")
            if outcome.status is RunStatus.NEEDS_REVIEW:
                self.journal("run needs review; stopping")
                return BackfillEnd.NEEDS_REVIEW
            if outcome.stats.rows_upserted:
                self._refresh()
            if outcome.status is RunStatus.SUCCEEDED and status.complete:
                return self._finish()
            stalled = 0 if outcome.stats.payloads_new else stalled + 1
            if stalled == STALL_LIMIT:
                self.journal(f"{STALL_LIMIT} runs in a row landed nothing; stopping")
                return BackfillEnd.STALLED
            self.sleep(THROTTLE_CACHE_SECONDS + QUOTA_MARGIN_SECONDS)

    def _finish(self) -> BackfillEnd:
        self.journal(describe_replay(self.runner.replay(self.entry)))
        self._refresh()
        self.journal("complete: no launch pages left")
        return BackfillEnd.COMPLETE

    def _refresh(self) -> None:
        try:
            refreshed = self.runner.refresh_marts()
        except ConfigurationError:
            raise
        except Exception as failure:
            self.journal(f"marts: refresh failed ({failure!r})")
            return
        self.journal(f"marts: refreshed {len(refreshed.views)} views")
        try:
            generated = self.runner.generate_facts()
        except ConfigurationError:
            raise
        except Exception as failure:
            self.journal(f"facts: generation failed ({failure!r})")
            return
        self.journal(f"facts: {generated.facts} from {generated.templates} templates")

    def _await_quota(self) -> int | None:
        while True:
            quota = self.runner.quota(self.entry)
            if quota is None:
                return None
            if quota.available:
                return quota.available
            self.journal(
                f"waiting {duration(timedelta(seconds=quota.wait_seconds))} for the LL2 quota"
            )
            self.sleep(quota.wait_seconds)
