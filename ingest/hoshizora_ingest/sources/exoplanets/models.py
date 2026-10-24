from pydantic import RootModel

from hoshizora_ingest.sources.model import SourceModel


class Planet(SourceModel):
    pl_name: str
    hostname: str
    sy_snum: int | None = None
    sy_pnum: int | None = None
    discoverymethod: str
    disc_year: int | None = None
    disc_facility: str | None = None
    disc_locale: str | None = None
    pl_orbper: float | None = None
    pl_orbsmax: float | None = None
    pl_rade: float | None = None
    pl_bmasse: float | None = None
    pl_orbeccen: float | None = None
    pl_eqt: float | None = None
    pl_insol: float | None = None
    st_teff: float | None = None
    st_rad: float | None = None
    st_mass: float | None = None
    sy_dist: float | None = None
    pl_controv_flag: int = 0


class PlanetTable(RootModel[list[Planet]]):
    pass
