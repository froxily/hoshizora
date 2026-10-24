import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import cast

from psycopg import AsyncConnection

from hoshizora_ingest.sources.launch_library.adapter import (
    INFO,
    PRODUCTION_BASE_URL,
    LaunchLibrarySource,
)

REQUESTS_PER_HOUR = 15
PRODUCTION = LaunchLibrarySource(PRODUCTION_BASE_URL)

PAGES = """
WITH pages AS (
    SELECT id, params, body
    FROM raw.payload
    WHERE source = %(source)s AND endpoint = %(endpoint)s
),
latest AS (
    SELECT
        (body ->> 'count')::int AS reported,
        jsonb_array_length(body -> 'results') AS returned,
        (params ->> 'offset')::int AS page_offset,
        (params ->> 'limit')::int AS page_size,
        (params ->> 'last_updated__gte')::timestamptz AS watermark
    FROM pages
    ORDER BY id DESC
    LIMIT 1
)
SELECT
    (
        SELECT count(DISTINCT launch ->> 'id')
        FROM pages CROSS JOIN LATERAL jsonb_array_elements(pages.body -> 'results') AS launch
    ),
    latest.reported,
    latest.returned,
    latest.page_offset,
    latest.page_size,
    latest.watermark
FROM (SELECT 1) AS anchor
LEFT JOIN latest ON true
"""

LAST_RUN = """
SELECT id, started_at, status, origin
FROM raw.ingest_run
WHERE source = %s
ORDER BY id DESC
LIMIT 1
"""


@dataclass(frozen=True)
class LastRun:
    id: int
    started_at: datetime
    status: str
    origin: str | None


@dataclass(frozen=True)
class LatestPage:
    reported: int
    returned: int
    offset: int
    size: int
    watermark: datetime

    @property
    def remaining(self) -> int:
        if self.returned < self.size:
            return 0
        return max(0, self.reported - self.offset - self.returned)


@dataclass(frozen=True)
class BackfillStatus:
    loaded: int
    latest: LatestPage | None
    last_run: LastRun | None

    @property
    def remaining(self) -> int | None:
        return self.latest.remaining if self.latest is not None else None

    @property
    def total(self) -> int | None:
        return self.loaded + self.remaining if self.remaining is not None else None

    @property
    def pages_left(self) -> int | None:
        if self.latest is None or self.remaining is None:
            return None
        return math.ceil(self.remaining / self.latest.size)

    @property
    def complete(self) -> bool:
        return self.remaining == 0

    @property
    def eta(self) -> timedelta | None:
        pages = self.pages_left
        return None if pages is None else timedelta(hours=pages / REQUESTS_PER_HOUR)


async def backfill_status(db: AsyncConnection) -> BackfillStatus:
    async with db.cursor() as cursor:
        await cursor.execute(PAGES, {"source": INFO.slug, "endpoint": PRODUCTION.launches_endpoint})
        pages = await cursor.fetchone()
        await cursor.execute(LAST_RUN, (INFO.slug,))
        run = await cursor.fetchone()
    loaded = int(pages[0]) if pages is not None else 0
    latest = (
        LatestPage(
            int(pages[1]), int(pages[2]), int(pages[3]), int(pages[4]), cast("datetime", pages[5])
        )
        if pages is not None and pages[1] is not None
        else None
    )
    last_run = (
        LastRun(int(run[0]), cast("datetime", run[1]), str(run[2]), cast("str | None", run[3]))
        if run is not None
        else None
    )
    return BackfillStatus(loaded, latest, last_run)


def utc(moment: datetime) -> str:
    return f"{moment:%Y-%m-%d %H:%M} UTC"


def duration(span: timedelta) -> str:
    minutes = math.ceil(span.total_seconds() / 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours} h {minutes} min" if hours else f"{minutes} min"


def progress(status: BackfillStatus) -> str:
    if status.total is None:
        return f"{status.loaded:,} launches loaded, no production page yet"
    return f"{status.loaded:,}/{status.total:,} launches, {status.pages_left} pages left"


def render_status(status: BackfillStatus) -> list[str]:
    lines = [f"Launch Library 2 backfill from {PRODUCTION_BASE_URL}"]
    total, latest = status.total, status.latest
    if total is None or latest is None:
        lines.append(f"Launches: {status.loaded:,} loaded; no production launch page landed yet")
    else:
        share = status.loaded / total if total else 1.0
        lines.append(f"Launches: {status.loaded:,} of {total:,} reported by LL2 ({share:.0%})")
        lines.append(
            f"Pages left: {status.pages_left} ({status.remaining:,} launches after watermark "
            f"{utc(latest.watermark)})"
        )
    run = status.last_run
    if run is None:
        lines.append("Last run: none yet")
    else:
        lines.append(
            f"Last run: #{run.id} at {utc(run.started_at)}, {run.status}, "
            f"from {run.origin or 'an unknown origin'}"
        )
    eta = status.eta
    if status.complete:
        lines.append("ETA: complete")
    elif eta is not None:
        lines.append(f"ETA: about {duration(eta)} at {REQUESTS_PER_HOUR} requests per hour")
    return lines
