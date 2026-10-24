import re
from dataclasses import dataclass
from datetime import date, datetime

from hoshizora_ingest.sources.celestrak.models import (
    GpCatalog,
    GpElement,
    SatcatCatalog,
    SatcatRecord,
)

INTERNATIONAL_DESIGNATOR = re.compile(r"^(\d{4}-\d{3})[A-Z]*$")


@dataclass(frozen=True)
class SpaceObjectRow:
    norad_id: int
    object_id: str | None
    launch_designator: str | None
    name: str
    object_type: str | None
    ops_status: str | None
    owner_code: str | None
    launch_date: date | None
    launch_site: str | None
    decay_date: date | None
    period_min: float | None
    inclination_deg: float | None
    apogee_km: float | None
    perigee_km: float | None
    rcs_m2: float | None
    data_status: str | None
    orbit_center: str | None
    orbit_type: str | None


@dataclass(frozen=True)
class SpaceObjectStub:
    norad_id: int
    object_id: str | None
    launch_designator: str | None
    name: str


@dataclass(frozen=True)
class OrbitElementRow:
    norad_id: int
    epoch: datetime
    mean_motion: float
    eccentricity: float
    inclination_deg: float
    ra_of_asc_node_deg: float
    arg_of_pericenter_deg: float
    mean_anomaly_deg: float
    bstar: float | None
    mean_motion_dot: float | None
    mean_motion_ddot: float | None
    element_set_no: int | None
    rev_at_epoch: int | None
    classification: str | None
    ephemeris_type: int | None


@dataclass(frozen=True)
class SatcatBatch:
    objects: tuple[SpaceObjectRow, ...]


@dataclass(frozen=True)
class GpBatch:
    stubs: tuple[SpaceObjectStub, ...]
    elements: tuple[OrbitElementRow, ...]


type CelestrakBatch = SatcatBatch | GpBatch


def launch_designator(object_id: str | None) -> str | None:
    if object_id is None:
        return None
    match = INTERNATIONAL_DESIGNATOR.match(object_id)
    return match.group(1) if match is not None else None


def space_object_row(record: SatcatRecord) -> SpaceObjectRow:
    return SpaceObjectRow(
        norad_id=record.norad_cat_id,
        object_id=record.object_id,
        launch_designator=launch_designator(record.object_id),
        name=record.object_name,
        object_type=record.object_type,
        ops_status=record.ops_status_code,
        owner_code=record.owner,
        launch_date=record.launch_date,
        launch_site=record.launch_site,
        decay_date=record.decay_date,
        period_min=record.period,
        inclination_deg=record.inclination,
        apogee_km=record.apogee,
        perigee_km=record.perigee,
        rcs_m2=record.rcs,
        data_status=record.data_status_code,
        orbit_center=record.orbit_center,
        orbit_type=record.orbit_type,
    )


def orbit_element_row(element: GpElement) -> OrbitElementRow:
    return OrbitElementRow(
        norad_id=element.norad_cat_id,
        epoch=element.epoch,
        mean_motion=element.mean_motion,
        eccentricity=element.eccentricity,
        inclination_deg=element.inclination,
        ra_of_asc_node_deg=element.ra_of_asc_node,
        arg_of_pericenter_deg=element.arg_of_pericenter,
        mean_anomaly_deg=element.mean_anomaly,
        bstar=element.bstar,
        mean_motion_dot=element.mean_motion_dot,
        mean_motion_ddot=element.mean_motion_ddot,
        element_set_no=element.element_set_no,
        rev_at_epoch=element.rev_at_epoch,
        classification=element.classification_type,
        ephemeris_type=element.ephemeris_type,
    )


def normalize_satcat(catalog: SatcatCatalog) -> SatcatBatch:
    return SatcatBatch(tuple(space_object_row(record) for record in catalog.records))


def normalize_gp(catalog: GpCatalog) -> GpBatch:
    return GpBatch(
        stubs=tuple(
            SpaceObjectStub(
                element.norad_cat_id,
                element.object_id,
                launch_designator(element.object_id),
                element.object_name,
            )
            for element in catalog.elements
        ),
        elements=tuple(orbit_element_row(element) for element in catalog.elements),
    )


def normalize(catalog: SatcatCatalog | GpCatalog) -> CelestrakBatch:
    if isinstance(catalog, SatcatCatalog):
        return normalize_satcat(catalog)
    return normalize_gp(catalog)
