from collections.abc import Callable
from typing import Literal

EARTH_MOON_KM = 384_400
EARTH_DIAMETER_KM = 12_742
MT_FUJI_M = 3_776
TOKYO_SKYTREE_M = 634
E5_SHINKANSEN_KMH = 320
LIGHT_KMS = 299_792.458
SECONDS_PER_HOUR = 3_600
SECONDS_PER_MINUTE = 60
METERS_PER_KM = 1_000
HOURS_PER_YEAR = 24 * 365.25

type Unit = Literal[
    "earth_moon_distances",
    "earth_diameters",
    "fuji_heights",
    "skytree_heights",
    "shinkansen_speeds",
    "light_seconds",
    "shinkansen_hours",
    "minutes_to_cross_earth_moon",
    "shinkansen_years",
]


def earth_moon_distances(km: float) -> float:
    return km / EARTH_MOON_KM


def earth_diameters(km: float) -> float:
    return km / EARTH_DIAMETER_KM


def fuji_heights(km: float) -> float:
    return km * METERS_PER_KM / MT_FUJI_M


def skytree_heights(km: float) -> float:
    return km * METERS_PER_KM / TOKYO_SKYTREE_M


def shinkansen_speeds(kms: float) -> float:
    return kms * SECONDS_PER_HOUR / E5_SHINKANSEN_KMH


def light_seconds(km: float) -> float:
    return km / LIGHT_KMS


def shinkansen_hours(km: float) -> float:
    return km / E5_SHINKANSEN_KMH


def minutes_to_cross_earth_moon(kms: float) -> float:
    return EARTH_MOON_KM / kms / SECONDS_PER_MINUTE


def shinkansen_years(km: float) -> float:
    return km / E5_SHINKANSEN_KMH / HOURS_PER_YEAR


UNITS: dict[Unit, Callable[[float], float]] = {
    "earth_moon_distances": earth_moon_distances,
    "earth_diameters": earth_diameters,
    "fuji_heights": fuji_heights,
    "skytree_heights": skytree_heights,
    "shinkansen_speeds": shinkansen_speeds,
    "light_seconds": light_seconds,
    "shinkansen_hours": shinkansen_hours,
    "minutes_to_cross_earth_moon": minutes_to_cross_earth_moon,
    "shinkansen_years": shinkansen_years,
}


def humanize(unit: Unit, value: float) -> float:
    return UNITS[unit](value)
