from datetime import datetime, timedelta
from uuid import UUID

from pydantic import Field

from hoshizora_ingest.sources.model import SourceModel

AGENCY_DETAIL_FIELDS = frozenset(
    {
        "response_mode",
        "url",
        "featured",
        "description",
        "administrator",
        "launchers",
        "spacecraft",
        "image",
        "logo",
        "social_logo",
        "total_launch_count",
        "consecutive_successful_launches",
        "successful_launches",
        "failed_launches",
        "pending_launches",
        "consecutive_successful_landings",
        "successful_landings",
        "failed_landings",
        "attempted_landings",
        "successful_landings_spacecraft",
        "failed_landings_spacecraft",
        "attempted_landings_spacecraft",
        "successful_landings_payload",
        "failed_landings_payload",
        "attempted_landings_payload",
        "info_url",
        "wiki_url",
        "social_media_links",
    }
)


class AgencyType(SourceModel):
    id: int
    name: str


class Country(SourceModel):
    unused = frozenset({"nationality_name", "nationality_name_composed"})

    id: int
    name: str
    alpha_2_code: str
    alpha_3_code: str


class AgencyRef(SourceModel):
    unused = frozenset({"response_mode", "url"})

    id: int
    name: str
    abbrev: str | None = None
    type: AgencyType | None = None


class Agency(SourceModel):
    unused = AGENCY_DETAIL_FIELDS

    id: int
    name: str
    abbrev: str | None = None
    type: AgencyType | None = None
    country: list[Country] = Field(default_factory=list[Country])
    founding_year: int | None = None
    parent: str | None = None


class Status(SourceModel):
    unused = frozenset({"description"})

    id: int
    name: str
    abbrev: str


class NetPrecision(SourceModel):
    unused = frozenset({"description"})

    id: int
    name: str
    abbrev: str


class VehicleFamily(SourceModel):
    unused = frozenset({"response_mode"})

    id: int
    name: str


class VehicleConfiguration(SourceModel):
    unused = frozenset({"response_mode", "url"})

    id: int
    name: str
    full_name: str | None = None
    variant: str | None = None
    families: list[VehicleFamily] = Field(default_factory=list[VehicleFamily])


class Rocket(SourceModel):
    id: int
    configuration: VehicleConfiguration


class Orbit(SourceModel):
    unused = frozenset({"celestial_body"})

    id: int
    name: str
    abbrev: str


class Mission(SourceModel):
    unused = frozenset({"image", "info_urls", "vid_urls"})

    id: int
    name: str
    type: str | None = None
    description: str | None = None
    orbit: Orbit | None = None
    agencies: list[Agency] = Field(default_factory=list[Agency])


class PadLocation(SourceModel):
    unused = frozenset(
        {
            "response_mode",
            "url",
            "celestial_body",
            "active",
            "country",
            "description",
            "image",
            "map_image",
            "longitude",
            "latitude",
            "timezone_name",
            "total_launch_count",
            "total_landing_count",
        }
    )

    id: int
    name: str


class Pad(SourceModel):
    unused = frozenset(
        {
            "url",
            "active",
            "agencies",
            "image",
            "description",
            "info_url",
            "wiki_url",
            "map_url",
            "map_image",
            "total_launch_count",
            "orbital_launch_attempt_count",
            "fastest_turnaround",
        }
    )

    id: int
    name: str
    latitude: float | None = None
    longitude: float | None = None
    country: Country | None = None
    location: PadLocation | None = None


class Launch(SourceModel):
    unused = frozenset(
        {
            "url",
            "response_mode",
            "image",
            "infographic",
            "probability",
            "weather_concerns",
            "hashtag",
            "webcast_live",
            "program",
            "orbital_launch_attempt_count",
            "location_launch_attempt_count",
            "pad_launch_attempt_count",
            "agency_launch_attempt_count",
            "orbital_launch_attempt_count_year",
            "location_launch_attempt_count_year",
            "pad_launch_attempt_count_year",
            "agency_launch_attempt_count_year",
        }
    )

    id: UUID
    name: str
    slug: str | None = None
    launch_designator: str | None = None
    status: Status
    last_updated: datetime
    net: datetime | None = None
    net_precision: NetPrecision | None = None
    window_start: datetime | None = None
    window_end: datetime | None = None
    failreason: str | None = None
    launch_service_provider: AgencyRef
    rocket: Rocket
    mission: Mission | None = None
    pad: Pad


class LaunchPage(SourceModel):
    count: int
    next: str | None
    previous: str | None
    results: list[Launch]


class AgencyPage(SourceModel):
    count: int
    next: str | None
    previous: str | None
    results: list[Agency]


class Throttle(SourceModel):
    your_request_limit: int
    limit_frequency_secs: int
    current_use: int
    next_use_secs: int
    ident: str


class LauncherStatus(SourceModel):
    id: int
    name: str


class LauncherConfig(SourceModel):
    unused = frozenset({"response_mode", "url"})

    id: int
    name: str
    full_name: str | None = None
    variant: str | None = None
    families: list[VehicleFamily] | None = None


class LauncherMini(SourceModel):
    unused = frozenset({"response_mode", "url", "image"})

    id: int
    serial_number: str | None = None
    is_placeholder: bool = False
    flight_proven: bool | None = None
    status: LauncherStatus | None = None


class Launcher(LauncherMini):
    unused = frozenset({"response_mode", "url", "image", "details"})

    flights: int | None = None
    attempted_landings: int | None = None
    successful_landings: int | None = None
    first_launch_date: datetime | None = None
    last_launch_date: datetime | None = None
    fastest_turnaround: timedelta | None = None
    launcher_config: LauncherConfig | None = None


class LandingLocation(SourceModel):
    unused = frozenset(
        {
            "active",
            "description",
            "location",
            "longitude",
            "latitude",
            "image",
            "successful_landings",
            "attempted_landings",
            "failed_landings",
            "celestial_body",
        }
    )

    id: int
    name: str
    abbrev: str | None = None


class LandingType(SourceModel):
    unused = frozenset({"description"})

    id: int
    name: str
    abbrev: str | None = None


class FirstStage(SourceModel):
    id: int
    type: str | None = None
    reused: bool | None = None
    launcher_flight_number: int | None = None
    launcher: LauncherMini
    previous_flight_date: datetime | None = None
    turn_around_time: timedelta | None = None


class Landing(SourceModel):
    unused = frozenset({"url", "response_mode", "description", "spacecraftflight", "payloadflight"})

    id: int
    attempt: bool
    success: bool | None = None
    downrange_distance: float | None = None
    landing_location: LandingLocation | None = None
    type: LandingType | None = None
    firststage: FirstStage | None = None


class LauncherPage(SourceModel):
    count: int
    next: str | None
    previous: str | None
    results: list[Launcher]


class LandingPage(SourceModel):
    count: int
    next: str | None
    previous: str | None
    results: list[Landing]
