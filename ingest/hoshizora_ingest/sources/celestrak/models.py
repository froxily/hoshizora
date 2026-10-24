from datetime import date
from typing import Annotated

from pydantic import BeforeValidator, ConfigDict, Field

from hoshizora_ingest.sources.model import SourceModel, UtcDatetime


def empty_as_none(value: object) -> object:
    return None if value == "" else value


type Blank[T] = Annotated[T | None, BeforeValidator(empty_as_none)]


class SatcatRecord(SourceModel):
    model_config = ConfigDict(extra="allow", frozen=True, populate_by_name=True)

    object_name: str = Field(alias="OBJECT_NAME")
    object_id: Blank[str] = Field(alias="OBJECT_ID")
    norad_cat_id: int = Field(alias="NORAD_CAT_ID")
    object_type: Blank[str] = Field(alias="OBJECT_TYPE")
    ops_status_code: Blank[str] = Field(alias="OPS_STATUS_CODE")
    owner: Blank[str] = Field(alias="OWNER")
    launch_date: Blank[date] = Field(alias="LAUNCH_DATE")
    launch_site: Blank[str] = Field(alias="LAUNCH_SITE")
    decay_date: Blank[date] = Field(alias="DECAY_DATE")
    period: Blank[float] = Field(alias="PERIOD")
    inclination: Blank[float] = Field(alias="INCLINATION")
    apogee: Blank[float] = Field(alias="APOGEE")
    perigee: Blank[float] = Field(alias="PERIGEE")
    rcs: Blank[float] = Field(alias="RCS")
    data_status_code: Blank[str] = Field(alias="DATA_STATUS_CODE")
    orbit_center: Blank[str] = Field(alias="ORBIT_CENTER")
    orbit_type: Blank[str] = Field(alias="ORBIT_TYPE")


class GpElement(SourceModel):
    model_config = ConfigDict(extra="allow", frozen=True, populate_by_name=True)

    object_name: str = Field(alias="OBJECT_NAME")
    object_id: str | None = Field(default=None, alias="OBJECT_ID")
    norad_cat_id: int = Field(alias="NORAD_CAT_ID")
    epoch: UtcDatetime = Field(alias="EPOCH")
    mean_motion: float = Field(alias="MEAN_MOTION")
    eccentricity: float = Field(alias="ECCENTRICITY")
    inclination: float = Field(alias="INCLINATION")
    ra_of_asc_node: float = Field(alias="RA_OF_ASC_NODE")
    arg_of_pericenter: float = Field(alias="ARG_OF_PERICENTER")
    mean_anomaly: float = Field(alias="MEAN_ANOMALY")
    bstar: float | None = Field(default=None, alias="BSTAR")
    mean_motion_dot: float | None = Field(default=None, alias="MEAN_MOTION_DOT")
    mean_motion_ddot: float | None = Field(default=None, alias="MEAN_MOTION_DDOT")
    element_set_no: int | None = Field(default=None, alias="ELEMENT_SET_NO")
    rev_at_epoch: int | None = Field(default=None, alias="REV_AT_EPOCH")
    classification_type: str | None = Field(default=None, alias="CLASSIFICATION_TYPE")
    ephemeris_type: int | None = Field(default=None, alias="EPHEMERIS_TYPE")


class SatcatCatalog(SourceModel):
    records: list[SatcatRecord]


class GpCatalog(SourceModel):
    elements: list[GpElement]
