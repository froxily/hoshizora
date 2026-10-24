from dataclasses import dataclass

from hoshizora_ingest.sources.exoplanets.models import Planet, PlanetTable


@dataclass(frozen=True)
class ExoplanetRow:
    name: str
    host_name: str
    star_count: int | None
    planet_count: int | None
    discovery_method: str
    discovery_year: int | None
    discovery_facility: str | None
    discovery_locale: str | None
    orbital_period_days: float | None
    semi_major_axis_au: float | None
    radius_earth: float | None
    mass_earth: float | None
    eccentricity: float | None
    equilibrium_temp_k: float | None
    insolation_earth: float | None
    star_temp_k: float | None
    star_radius_sun: float | None
    star_mass_sun: float | None
    distance_pc: float | None
    controversial: bool


@dataclass(frozen=True)
class ExoplanetBatch:
    planets: tuple[ExoplanetRow, ...]


def locale(value: str | None) -> str | None:
    return value.strip().lower() if value and value.strip() else None


def exoplanet_row(planet: Planet) -> ExoplanetRow:
    return ExoplanetRow(
        name=planet.pl_name,
        host_name=planet.hostname,
        star_count=planet.sy_snum,
        planet_count=planet.sy_pnum,
        discovery_method=planet.discoverymethod,
        discovery_year=planet.disc_year,
        discovery_facility=planet.disc_facility or None,
        discovery_locale=locale(planet.disc_locale),
        orbital_period_days=planet.pl_orbper,
        semi_major_axis_au=planet.pl_orbsmax,
        radius_earth=planet.pl_rade,
        mass_earth=planet.pl_bmasse,
        eccentricity=planet.pl_orbeccen,
        equilibrium_temp_k=planet.pl_eqt,
        insolation_earth=planet.pl_insol,
        star_temp_k=planet.st_teff,
        star_radius_sun=planet.st_rad,
        star_mass_sun=planet.st_mass,
        distance_pc=planet.sy_dist,
        controversial=planet.pl_controv_flag == 1,
    )


def normalize(table: PlanetTable) -> ExoplanetBatch:
    return ExoplanetBatch(tuple(exoplanet_row(planet) for planet in table.root))
