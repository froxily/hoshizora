import time
from collections.abc import Callable
from dataclasses import dataclass

import structlog
from psycopg import AsyncConnection, sql

log = structlog.get_logger()

MARTS = """
SELECT matviewname, ispopulated
FROM pg_matviews
WHERE schemaname = 'mart'
ORDER BY matviewname
"""


@dataclass(frozen=True)
class Refreshed:
    views: tuple[str, ...]
    seconds: float


async def refresh_marts(
    db: AsyncConnection, clock: Callable[[], float] = time.perf_counter
) -> Refreshed:
    started = clock()
    marts = await (await db.execute(MARTS)).fetchall()
    await db.commit()
    for name, populated in marts:
        statement = (
            "REFRESH MATERIALIZED VIEW CONCURRENTLY {}"
            if populated
            else "REFRESH MATERIALIZED VIEW {}"
        )
        await db.execute(sql.SQL(statement).format(sql.Identifier("mart", name)))
        await db.commit()
    refreshed = Refreshed(tuple(str(name) for name, _ in marts), clock() - started)
    log.info("marts refreshed", views=len(refreshed.views), seconds=round(refreshed.seconds, 2))
    return refreshed
