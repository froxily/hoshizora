from datetime import date, datetime
from typing import Annotated

from pydantic import BeforeValidator, Field

from hoshizora_ingest.sources.model import SourceModel, UtcDatetime

MONTHS = {
    name: number
    for number, name in enumerate(
        ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
        start=1,
    )
}


def calendar_tdb(value: object) -> object:
    if not isinstance(value, str):
        return value
    day, clock = value.split(" ")
    year, month, dom = day.split("-")
    hour, minute = clock.split(":")
    return datetime(int(year), MONTHS[month], int(dom), int(hour), int(minute))


def observation_date(value: object) -> object:
    if not isinstance(value, str) or "." not in value:
        return value
    year, month, day = value.split("-")
    return date(int(year), int(month), int(float(day)))


def stripped(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


TdbDatetime = Annotated[datetime, BeforeValidator(calendar_tdb)]
Stripped = Annotated[str, BeforeValidator(stripped)]
ObservationDate = Annotated[date, BeforeValidator(observation_date)]


class Signature(SourceModel):
    source: str
    version: str


class CadResponse(SourceModel):
    signature: Signature
    count: int
    fields: list[str] = Field(default_factory=list[str])
    data: list[list[str | None]] = Field(default_factory=list[list[str | None]])


class CadApproach(SourceModel):
    des: str
    orbit_id: str | None = None
    jd: float
    cd: TdbDatetime
    dist: float
    dist_min: float | None = None
    dist_max: float | None = None
    v_rel: float | None = None
    v_inf: float | None = None
    t_sigma_f: str | None = None
    h: float | None = None
    diameter: float | None = None
    diameter_sigma: float | None = None
    fullname: Stripped | None = None
    body: str | None = None


class CadWindow(SourceModel):
    date_min: date
    date_max: date
    body: str
    approaches: list[CadApproach]


class SentryObject(SourceModel):
    unused = frozenset({"last_obs_jd"})

    des: str
    id: str | None = None
    fullname: Stripped | None = None
    ip: float | None = None
    ps_cum: float | None = None
    ps_max: float | None = None
    ts_max: int | None = None
    n_imp: int | None = None
    range: str | None = None
    last_obs: ObservationDate | None = None
    diameter: float | None = None
    h: float | None = None
    v_inf: float | None = None


class SentrySummary(SourceModel):
    signature: Signature
    count: int
    data: list[SentryObject] = Field(default_factory=list[SentryObject])


class SentryRemoval(SourceModel):
    des: str
    removed: UtcDatetime


class SentryRemovals(SourceModel):
    signature: Signature
    count: int
    data: list[SentryRemoval] = Field(default_factory=list[SentryRemoval])
