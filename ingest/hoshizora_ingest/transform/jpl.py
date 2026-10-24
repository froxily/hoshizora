from dataclasses import dataclass
from datetime import date, datetime

from hoshizora_ingest.sources.jpl.models import (
    CadApproach,
    CadWindow,
    SentryObject,
    SentryRemovals,
    SentrySummary,
)


@dataclass(frozen=True)
class SmallBodyRow:
    designation: str
    fullname: str | None
    h_mag: float | None
    diameter_km: float | None
    diameter_sigma_km: float | None


@dataclass(frozen=True)
class SmallBodyStub:
    designation: str
    fullname: str | None


@dataclass(frozen=True)
class CloseApproachRow:
    designation: str
    body: str
    approach_tdb: datetime
    orbit_id: str | None
    jd_tdb: float
    dist_au: float
    dist_min_au: float | None
    dist_max_au: float | None
    v_rel_kms: float | None
    v_inf_kms: float | None
    t_sigma: str | None
    h_mag: float | None


@dataclass(frozen=True)
class ImpactRiskRow:
    designation: str
    sentry_id: str | None
    fullname: str | None
    impact_probability: float | None
    palermo_cumulative: float | None
    palermo_max: float | None
    torino_max: int | None
    potential_impacts: int | None
    impact_year_first: int | None
    impact_year_last: int | None
    last_observed: date | None
    diameter_km: float | None
    h_mag: float | None
    v_inf_kms: float | None


@dataclass(frozen=True)
class RemovalRow:
    designation: str
    removed_at: datetime


@dataclass(frozen=True)
class CloseApproachBatch:
    date_min: date
    date_max: date
    body: str
    bodies: tuple[SmallBodyRow, ...]
    approaches: tuple[CloseApproachRow, ...]


@dataclass(frozen=True)
class ImpactRiskBatch:
    bodies: tuple[SmallBodyStub, ...]
    risks: tuple[ImpactRiskRow, ...]


@dataclass(frozen=True)
class RemovalBatch:
    removals: tuple[RemovalRow, ...]


type JplBatch = CloseApproachBatch | ImpactRiskBatch | RemovalBatch


def impact_years(year_range: str | None) -> tuple[int | None, int | None]:
    if not year_range:
        return None, None
    first, _, last = year_range.partition("-")
    return int(first), int(last or first)


def small_body_row(approach: CadApproach) -> SmallBodyRow:
    return SmallBodyRow(
        designation=approach.des,
        fullname=approach.fullname,
        h_mag=approach.h,
        diameter_km=approach.diameter,
        diameter_sigma_km=approach.diameter_sigma,
    )


def close_approach_row(approach: CadApproach, body: str) -> CloseApproachRow:
    return CloseApproachRow(
        designation=approach.des,
        body=approach.body or body,
        approach_tdb=approach.cd,
        orbit_id=approach.orbit_id,
        jd_tdb=approach.jd,
        dist_au=approach.dist,
        dist_min_au=approach.dist_min,
        dist_max_au=approach.dist_max,
        v_rel_kms=approach.v_rel,
        v_inf_kms=approach.v_inf,
        t_sigma=approach.t_sigma_f,
        h_mag=approach.h,
    )


def impact_risk_row(risk: SentryObject) -> ImpactRiskRow:
    first, last = impact_years(risk.range)
    return ImpactRiskRow(
        designation=risk.des,
        sentry_id=risk.id,
        fullname=risk.fullname,
        impact_probability=risk.ip,
        palermo_cumulative=risk.ps_cum,
        palermo_max=risk.ps_max,
        torino_max=risk.ts_max,
        potential_impacts=risk.n_imp,
        impact_year_first=first,
        impact_year_last=last,
        last_observed=risk.last_obs,
        diameter_km=risk.diameter,
        h_mag=risk.h,
        v_inf_kms=risk.v_inf,
    )


def normalize_cad(window: CadWindow) -> CloseApproachBatch:
    return CloseApproachBatch(
        date_min=window.date_min,
        date_max=window.date_max,
        body=window.body,
        bodies=tuple(small_body_row(approach) for approach in window.approaches),
        approaches=tuple(
            close_approach_row(approach, window.body) for approach in window.approaches
        ),
    )


def normalize_sentry(summary: SentrySummary) -> ImpactRiskBatch:
    return ImpactRiskBatch(
        bodies=tuple(SmallBodyStub(risk.des, risk.fullname) for risk in summary.data),
        risks=tuple(impact_risk_row(risk) for risk in summary.data),
    )


def normalize_removals(removals: SentryRemovals) -> RemovalBatch:
    return RemovalBatch(tuple(RemovalRow(row.des, row.removed) for row in removals.data))


def normalize(parsed: CadWindow | SentrySummary | SentryRemovals) -> JplBatch:
    if isinstance(parsed, CadWindow):
        return normalize_cad(parsed)
    if isinstance(parsed, SentrySummary):
        return normalize_sentry(parsed)
    return normalize_removals(parsed)
