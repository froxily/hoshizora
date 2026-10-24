import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from hoshizora_ingest.analytics.refresh import Refreshed, refresh_marts
from hoshizora_ingest.backfill.status import BackfillStatus, backfill_status
from hoshizora_ingest.config import Settings, load_settings
from hoshizora_ingest.db import connections
from hoshizora_ingest.facts.engine import Generated, generate_facts, hour_start
from hoshizora_ingest.facts.spec import load_templates
from hoshizora_ingest.http.client import SourceClient
from hoshizora_ingest.jsontypes import parse_json
from hoshizora_ingest.pipeline import (
    Replayed,
    RunEnvironment,
    RunOutcome,
    bounded,
    replay_source,
    run_source,
)
from hoshizora_ingest.quality.report import Section, quality_report
from hoshizora_ingest.registry import SourceEntry
from hoshizora_ingest.runtime import run
from hoshizora_ingest.sources.launch_library.adapter import LaunchLibrarySource, Quota, quota
from hoshizora_ingest.sources.launch_library.models import Throttle


class Runner(Protocol):
    def ingest(
        self,
        entry: SourceEntry,
        max_requests: int | None,
        *,
        reviewed: bool = False,
        max_wait: float | None = None,
    ) -> RunOutcome: ...

    def replay(self, entry: SourceEntry) -> Replayed: ...

    def quality(self) -> list[Section]: ...

    def refresh_marts(self) -> Refreshed: ...

    def generate_facts(self) -> Generated: ...

    def backfill_status(self) -> BackfillStatus: ...

    def quota(self, entry: SourceEntry) -> Quota | None: ...


@dataclass
class DatabaseRunner:
    settings_factory: Callable[[], Settings] = load_settings
    _settings: Settings | None = field(default=None, init=False)

    @property
    def settings(self) -> Settings:
        if self._settings is None:
            self._settings = self.settings_factory()
        return self._settings

    def ingest(
        self,
        entry: SourceEntry,
        max_requests: int | None,
        *,
        reviewed: bool = False,
        max_wait: float | None = None,
    ) -> RunOutcome:
        return run(self._ingest(entry, max_requests, reviewed=reviewed, max_wait=max_wait))

    def replay(self, entry: SourceEntry) -> Replayed:
        return run(self._replay(entry))

    def quality(self) -> list[Section]:
        return run(self._quality())

    def refresh_marts(self) -> Refreshed:
        return run(self._refresh_marts())

    def generate_facts(self) -> Generated:
        return run(self._generate_facts())

    def backfill_status(self) -> BackfillStatus:
        return run(self._backfill_status())

    def quota(self, entry: SourceEntry) -> Quota | None:
        return run(self._quota(entry))

    async def _ingest(
        self,
        entry: SourceEntry,
        max_requests: int | None,
        *,
        reviewed: bool,
        max_wait: float | None,
    ) -> RunOutcome:
        settings = self.settings
        sleep = asyncio.sleep if max_wait is None else bounded(asyncio.sleep, max_wait)
        async with connections(settings.ingest_database_url) as db:
            env = RunEnvironment(
                db=db.data, log_db=db.log, user_agent=settings.user_agent, sleep=sleep
            )
            return await run_source(
                entry.build(settings), env, max_requests=max_requests, reviewed=reviewed
            )

    async def _replay(self, entry: SourceEntry) -> Replayed:
        settings = self.settings
        async with connections(settings.ingest_database_url) as db:
            return await replay_source(entry.build(settings), db=db.data)

    async def _quality(self) -> list[Section]:
        async with connections(self.settings.ingest_database_url) as db:
            return await quality_report(db.data)

    async def _refresh_marts(self) -> Refreshed:
        async with connections(self.settings.ingest_database_url) as db:
            return await refresh_marts(db.data)

    async def _generate_facts(self) -> Generated:
        templates = load_templates()
        async with connections(self.settings.ingest_database_url) as db:
            return await generate_facts(db.data, templates, hour_start(datetime.now(UTC)))

    async def _backfill_status(self) -> BackfillStatus:
        async with connections(self.settings.ingest_database_url) as db:
            return await backfill_status(db.data)

    async def _quota(self, entry: SourceEntry) -> Quota | None:
        source = entry.build(self.settings)
        if not isinstance(source, LaunchLibrarySource) or not source.production:
            return None
        async with SourceClient(source.http_policy, self.settings.user_agent) as http:
            result = await http.get(source.throttle_endpoint, {}, limited=False)
        return quota(Throttle.model_validate(parse_json(result.content)))
