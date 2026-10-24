from dataclasses import dataclass
from datetime import datetime

from hoshizora_ingest.sources.swpc.models import (
    AlertList,
    FlareList,
    KpSeries,
    MagSeries,
    OvationGrid,
    PlasmaSeries,
    SwpcProduct,
)

KP = "kp"
AURORA_BOUNDARY_PERCENT = 10
XRAY_FLARE = "xray_flare"
ALERT = "alert"


@dataclass(frozen=True)
class GeomagneticRow:
    index: str
    observed_at: datetime
    value: float
    a_running: int | None
    station_count: int | None


@dataclass(frozen=True)
class EventRow:
    kind: str
    external_id: str
    begin_at: datetime | None
    peak_at: datetime | None
    end_at: datetime | None
    event_class: str | None
    peak_flux_wm2: float | None
    satellite: int | None
    product_id: str | None
    message: str | None


@dataclass(frozen=True)
class PlasmaRow:
    observed_at: datetime
    plasma_spacecraft: str
    speed_kms: float | None
    density_cm3: float | None
    temperature_k: float | None


@dataclass(frozen=True)
class MagRow:
    observed_at: datetime
    mag_spacecraft: str
    bt_nt: float | None
    bz_gsm_nt: float | None


@dataclass(frozen=True)
class GeomagneticBatch:
    rows: tuple[GeomagneticRow, ...]


@dataclass(frozen=True)
class EventBatch:
    rows: tuple[EventRow, ...]


@dataclass(frozen=True)
class PlasmaBatch:
    rows: tuple[PlasmaRow, ...]


@dataclass(frozen=True)
class MagBatch:
    rows: tuple[MagRow, ...]


@dataclass(frozen=True)
class AuroraForecastRow:
    observed_at: datetime
    forecast_at: datetime
    north_max_percent: int
    south_max_percent: int
    north_boundary_lat: int | None
    south_boundary_lat: int | None


@dataclass(frozen=True)
class AuroraCellRow:
    longitude: int
    latitude: int
    probability_percent: int
    observed_at: datetime


@dataclass(frozen=True)
class AuroraBatch:
    forecast: AuroraForecastRow
    cells: tuple[AuroraCellRow, ...]


type SwpcBatch = GeomagneticBatch | EventBatch | PlasmaBatch | MagBatch | AuroraBatch


def normalize_kp(series: KpSeries) -> GeomagneticBatch:
    return GeomagneticBatch(
        tuple(
            GeomagneticRow(KP, entry.time_tag, entry.kp, entry.a_running, entry.station_count)
            for entry in series.entries
        )
    )


def normalize_flares(flares: FlareList) -> EventBatch:
    return EventBatch(
        tuple(
            EventRow(
                kind=XRAY_FLARE,
                external_id=flare.begin_time.isoformat(),
                begin_at=flare.begin_time,
                peak_at=flare.max_time,
                end_at=flare.end_time,
                event_class=flare.max_class,
                peak_flux_wm2=flare.max_xrlong,
                satellite=flare.satellite,
                product_id=None,
                message=None,
            )
            for flare in flares.flares
        )
    )


def normalize_alerts(alerts: AlertList) -> EventBatch:
    return EventBatch(
        tuple(
            EventRow(
                kind=ALERT,
                external_id=f"{alert.product_id}@{alert.issue_datetime.isoformat()}",
                begin_at=alert.issue_datetime,
                peak_at=None,
                end_at=None,
                event_class=None,
                peak_flux_wm2=None,
                satellite=None,
                product_id=alert.product_id,
                message=alert.message,
            )
            for alert in alerts.alerts
        )
    )


def normalize_plasma(series: PlasmaSeries) -> PlasmaBatch:
    return PlasmaBatch(
        tuple(
            PlasmaRow(
                sample.time_tag,
                sample.source,
                sample.proton_speed,
                sample.proton_density,
                sample.proton_temperature,
            )
            for sample in series.samples
            if sample.active
        )
    )


def normalize_mag(series: MagSeries) -> MagBatch:
    return MagBatch(
        tuple(
            MagRow(sample.time_tag, sample.source, sample.bt, sample.bz_gsm)
            for sample in series.samples
            if sample.active
        )
    )


def normalize_ovation(grid: OvationGrid) -> AuroraBatch:
    cells = tuple(
        AuroraCellRow(longitude % 360, latitude, probability, grid.observation_time)
        for longitude, latitude, probability in grid.coordinates
        if probability > 0
    )
    north = [cell for cell in cells if cell.latitude > 0]
    south = [cell for cell in cells if cell.latitude < 0]
    forecast = AuroraForecastRow(
        observed_at=grid.observation_time,
        forecast_at=grid.forecast_time,
        north_max_percent=max((cell.probability_percent for cell in north), default=0),
        south_max_percent=max((cell.probability_percent for cell in south), default=0),
        north_boundary_lat=min(
            (c.latitude for c in north if c.probability_percent >= AURORA_BOUNDARY_PERCENT),
            default=None,
        ),
        south_boundary_lat=max(
            (c.latitude for c in south if c.probability_percent >= AURORA_BOUNDARY_PERCENT),
            default=None,
        ),
    )
    return AuroraBatch(forecast, cells)


def normalize(product: SwpcProduct) -> SwpcBatch:
    match product:
        case KpSeries():
            return normalize_kp(product)
        case FlareList():
            return normalize_flares(product)
        case AlertList():
            return normalize_alerts(product)
        case PlasmaSeries():
            return normalize_plasma(product)
        case MagSeries():
            return normalize_mag(product)
        case OvationGrid():
            return normalize_ovation(product)
