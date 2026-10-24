from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from hoshizora_ingest.sources.launch_library.models import (
    Agency,
    AgencyPage,
    AgencyRef,
    Landing,
    LandingPage,
    Launch,
    Launcher,
    LauncherMini,
    LauncherPage,
    LaunchPage,
    Mission,
    Pad,
)


@dataclass(frozen=True)
class AgencyRow:
    ll2_id: int
    name: str
    abbrev: str | None
    source_type: str | None
    founding_year: int | None
    parent_name: str | None
    countries: tuple[str, ...]
    complete: bool


@dataclass(frozen=True)
class VehicleRow:
    ll2_id: int
    name: str
    full_name: str | None
    variant: str | None
    family: str | None


@dataclass(frozen=True)
class PadRow:
    ll2_id: int
    name: str
    location_name: str | None
    country_code: str | None
    latitude: float | None
    longitude: float | None


@dataclass(frozen=True)
class MissionRow:
    ll2_id: int
    name: str
    type: str | None
    orbit: str | None
    orbit_name: str | None
    description: str | None


@dataclass(frozen=True)
class MissionAgencyRow:
    mission_ll2_id: int
    agency_ll2_id: int


@dataclass(frozen=True)
class LaunchRow:
    ll2_id: UUID
    name: str
    slug: str | None
    launch_designator: str | None
    net: datetime | None
    net_precision: str | None
    window_start: datetime | None
    window_end: datetime | None
    status_id: int
    status: str
    status_name: str
    failure_reason: str | None
    provider_ll2_id: int
    vehicle_ll2_id: int
    pad_ll2_id: int
    mission_ll2_id: int | None
    source_updated_at: datetime


@dataclass(frozen=True)
class LauncherRow:
    ll2_id: int
    serial_number: str | None
    is_placeholder: bool
    flight_proven: bool | None
    status: str | None


@dataclass(frozen=True)
class LauncherDetailRow:
    ll2_id: int
    serial_number: str | None
    is_placeholder: bool
    flight_proven: bool | None
    status: str | None
    vehicle_ll2_id: int | None
    flights: int | None
    attempted_landings: int | None
    successful_landings: int | None
    first_launch_at: datetime | None
    last_launch_at: datetime | None
    fastest_turnaround: timedelta | None


@dataclass(frozen=True)
class LandingRow:
    ll2_id: int
    launcher_ll2_id: int
    stage_type: str | None
    launcher_flight_number: int | None
    reused: bool | None
    attempt: bool
    success: bool | None
    previous_flight_at: datetime | None
    turnaround: timedelta | None
    type_abbrev: str | None
    type_name: str | None
    location_name: str | None
    location_abbrev: str | None
    downrange_km: float | None


@dataclass(frozen=True)
class AgencyBatch:
    agencies: tuple[AgencyRow, ...]


@dataclass(frozen=True)
class LauncherBatch:
    launchers: tuple[LauncherDetailRow, ...]


@dataclass(frozen=True)
class LandingBatch:
    launchers: tuple[LauncherRow, ...]
    landings: tuple[LandingRow, ...]


@dataclass(frozen=True)
class LaunchBatch:
    agencies: tuple[AgencyRow, ...]
    vehicles: tuple[VehicleRow, ...]
    pads: tuple[PadRow, ...]
    missions: tuple[MissionRow, ...]
    mission_agencies: tuple[MissionAgencyRow, ...]
    launches: tuple[LaunchRow, ...]


type Ll2Batch = AgencyBatch | LaunchBatch | LauncherBatch | LandingBatch
type Ll2Page = AgencyPage | LaunchPage | LauncherPage | LandingPage


def blank_to_none(value: str | None) -> str | None:
    return value or None


def agency_row(agency: Agency) -> AgencyRow:
    return AgencyRow(
        ll2_id=agency.id,
        name=agency.name,
        abbrev=blank_to_none(agency.abbrev),
        source_type=agency.type.name if agency.type is not None else None,
        founding_year=agency.founding_year,
        parent_name=blank_to_none(agency.parent),
        countries=tuple(country.alpha_2_code for country in agency.country),
        complete=True,
    )


def provider_row(provider: AgencyRef) -> AgencyRow:
    return AgencyRow(
        ll2_id=provider.id,
        name=provider.name,
        abbrev=blank_to_none(provider.abbrev),
        source_type=provider.type.name if provider.type is not None else None,
        founding_year=None,
        parent_name=None,
        countries=(),
        complete=False,
    )


def pad_row(pad: Pad) -> PadRow:
    return PadRow(
        ll2_id=pad.id,
        name=pad.name,
        location_name=pad.location.name if pad.location is not None else None,
        country_code=pad.country.alpha_2_code if pad.country is not None else None,
        latitude=pad.latitude,
        longitude=pad.longitude,
    )


def mission_row(mission: Mission) -> MissionRow:
    return MissionRow(
        ll2_id=mission.id,
        name=mission.name,
        type=blank_to_none(mission.type),
        orbit=mission.orbit.abbrev if mission.orbit is not None else None,
        orbit_name=mission.orbit.name if mission.orbit is not None else None,
        description=blank_to_none(mission.description),
    )


def launch_row(launch: Launch) -> LaunchRow:
    return LaunchRow(
        ll2_id=launch.id,
        name=launch.name,
        slug=launch.slug,
        launch_designator=blank_to_none(launch.launch_designator),
        net=launch.net,
        net_precision=launch.net_precision.abbrev if launch.net_precision is not None else None,
        window_start=launch.window_start,
        window_end=launch.window_end,
        status_id=launch.status.id,
        status=launch.status.abbrev,
        status_name=launch.status.name,
        failure_reason=blank_to_none(launch.failreason),
        provider_ll2_id=launch.launch_service_provider.id,
        vehicle_ll2_id=launch.rocket.configuration.id,
        pad_ll2_id=launch.pad.id,
        mission_ll2_id=launch.mission.id if launch.mission is not None else None,
        source_updated_at=launch.last_updated,
    )


def normalize_agencies(page: AgencyPage) -> AgencyBatch:
    return AgencyBatch(tuple(agency_row(agency) for agency in page.results))


def normalize_launches(page: LaunchPage) -> LaunchBatch:
    launches = page.results
    missions = [launch.mission for launch in launches if launch.mission is not None]
    mission_partners = [agency for mission in missions for agency in mission.agencies]
    return LaunchBatch(
        agencies=tuple(
            [agency_row(agency) for agency in mission_partners]
            + [provider_row(launch.launch_service_provider) for launch in launches]
        ),
        vehicles=tuple(
            VehicleRow(
                ll2_id=config.id,
                name=config.name,
                full_name=blank_to_none(config.full_name),
                variant=blank_to_none(config.variant),
                family=config.families[0].name if config.families else None,
            )
            for config in (launch.rocket.configuration for launch in launches)
        ),
        pads=tuple(pad_row(launch.pad) for launch in launches),
        missions=tuple(mission_row(mission) for mission in missions),
        mission_agencies=tuple(
            MissionAgencyRow(mission.id, agency.id)
            for mission in missions
            for agency in mission.agencies
        ),
        launches=tuple(launch_row(launch) for launch in launches),
    )


def launcher_row(launcher: LauncherMini) -> LauncherRow:
    return LauncherRow(
        ll2_id=launcher.id,
        serial_number=blank_to_none(launcher.serial_number),
        is_placeholder=launcher.is_placeholder,
        flight_proven=launcher.flight_proven,
        status=launcher.status.name if launcher.status is not None else None,
    )


def launcher_detail_row(launcher: Launcher) -> LauncherDetailRow:
    return LauncherDetailRow(
        ll2_id=launcher.id,
        serial_number=blank_to_none(launcher.serial_number),
        is_placeholder=launcher.is_placeholder,
        flight_proven=launcher.flight_proven,
        status=launcher.status.name if launcher.status is not None else None,
        vehicle_ll2_id=launcher.launcher_config.id
        if launcher.launcher_config is not None
        else None,
        flights=launcher.flights,
        attempted_landings=launcher.attempted_landings,
        successful_landings=launcher.successful_landings,
        first_launch_at=launcher.first_launch_date,
        last_launch_at=launcher.last_launch_date,
        fastest_turnaround=launcher.fastest_turnaround,
    )


def landing_row(landing: Landing) -> LandingRow | None:
    stage = landing.firststage
    if stage is None:
        return None
    location, kind = landing.landing_location, landing.type
    return LandingRow(
        ll2_id=landing.id,
        launcher_ll2_id=stage.launcher.id,
        stage_type=blank_to_none(stage.type),
        launcher_flight_number=stage.launcher_flight_number,
        reused=stage.reused,
        attempt=landing.attempt,
        success=landing.success,
        previous_flight_at=stage.previous_flight_date,
        turnaround=stage.turn_around_time,
        type_abbrev=blank_to_none(kind.abbrev) if kind is not None else None,
        type_name=kind.name if kind is not None else None,
        location_name=location.name if location is not None else None,
        location_abbrev=blank_to_none(location.abbrev) if location is not None else None,
        downrange_km=landing.downrange_distance,
    )


def normalize_launchers(page: LauncherPage) -> LauncherBatch:
    return LauncherBatch(tuple(launcher_detail_row(launcher) for launcher in page.results))


def normalize_landings(page: LandingPage) -> LandingBatch:
    stages = [landing.firststage for landing in page.results if landing.firststage is not None]
    return LandingBatch(
        launchers=tuple(launcher_row(stage.launcher) for stage in stages),
        landings=tuple(row for row in map(landing_row, page.results) if row is not None),
    )


def normalize(page: Ll2Page) -> Ll2Batch:
    match page:
        case AgencyPage():
            return normalize_agencies(page)
        case LaunchPage():
            return normalize_launches(page)
        case LauncherPage():
            return normalize_launchers(page)
        case LandingPage():
            return normalize_landings(page)
