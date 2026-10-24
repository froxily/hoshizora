from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from psycopg import AsyncConnection


@dataclass(frozen=True)
class Connections:
    data: AsyncConnection
    log: AsyncConnection


@asynccontextmanager
async def connections(url: str) -> AsyncGenerator[Connections]:
    async with (
        await AsyncConnection.connect(url) as data,
        await AsyncConnection.connect(url, autocommit=True) as log,
    ):
        yield Connections(data=data, log=log)
