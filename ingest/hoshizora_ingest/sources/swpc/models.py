from pydantic import ConfigDict, Field

from hoshizora_ingest.sources.model import SourceModel, UtcDatetime


class KpEntry(SourceModel):
    model_config = ConfigDict(extra="allow", frozen=True, populate_by_name=True)

    time_tag: UtcDatetime
    kp: float = Field(alias="Kp")
    a_running: int | None = None
    station_count: int | None = None


class Flare(SourceModel):
    unused = frozenset({"time_tag", "max_ratio", "max_ratio_time", "current_int_xrlong"})

    begin_time: UtcDatetime
    begin_class: str | None = None
    max_time: UtcDatetime | None = None
    max_class: str | None = None
    max_xrlong: float | None = None
    end_time: UtcDatetime | None = None
    end_class: str | None = None
    satellite: int | None = None


class Alert(SourceModel):
    product_id: str
    issue_datetime: UtcDatetime
    message: str


class PlasmaSample(SourceModel):
    unused = frozenset(
        {
            "alpha_density",
            "alpha_sample_size",
            "alpha_speed",
            "alpha_temperature",
            "alpha_vx_gse",
            "alpha_vx_gsm",
            "alpha_vy_gse",
            "alpha_vy_gsm",
            "alpha_vz_gse",
            "alpha_vz_gsm",
            "max_convergence_flag",
            "max_data_flag",
            "max_error_count_flag",
            "max_processing_flag",
            "max_range_flag",
            "max_sample_count_flag",
            "max_telemetry_flag",
            "overall_quality",
            "proton_sample_size",
            "proton_vx_gse",
            "proton_vx_gsm",
            "proton_vy_gse",
            "proton_vy_gsm",
            "proton_vz_gse",
            "proton_vz_gsm",
        }
    )

    time_tag: UtcDatetime
    active: bool
    source: str
    proton_speed: float | None = None
    proton_density: float | None = None
    proton_temperature: float | None = None


class MagSample(SourceModel):
    unused = frozenset(
        {
            "bx_gse",
            "bx_gsm",
            "by_gse",
            "by_gsm",
            "bz_gse",
            "manual_mode",
            "max_data_flag",
            "max_telemetry_flag",
            "overall_quality",
            "phi_gse",
            "phi_gsm",
            "range",
            "sample_size",
            "scale",
            "sensitivity",
            "theta_gse",
            "theta_gsm",
        }
    )

    time_tag: UtcDatetime
    active: bool
    source: str
    bt: float | None = None
    bz_gsm: float | None = None


class KpSeries(SourceModel):
    entries: list[KpEntry]


class FlareList(SourceModel):
    flares: list[Flare]


class AlertList(SourceModel):
    alerts: list[Alert]


class PlasmaSeries(SourceModel):
    samples: list[PlasmaSample]


class MagSeries(SourceModel):
    samples: list[MagSample]


class OvationGrid(SourceModel):
    unused = frozenset({"type", "Data Format"})

    observation_time: UtcDatetime = Field(alias="Observation Time")
    forecast_time: UtcDatetime = Field(alias="Forecast Time")
    coordinates: tuple[tuple[int, int, int], ...]


type SwpcProduct = KpSeries | FlareList | AlertList | PlasmaSeries | MagSeries | OvationGrid
