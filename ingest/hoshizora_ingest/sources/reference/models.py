from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

type OrganizationType = Literal["agency", "company", "military", "academic", "international"]
type CodeKind = Literal["country", "multinational", "organization", "category", "unknown"]

CountryCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CountryEntry(Strict):
    alpha3: str = Field(pattern=r"^[A-Z]{3}$")
    en: str
    ja: str


class CountriesDocument(Strict):
    meta: dict[str, str]
    countries: dict[CountryCode, CountryEntry]


class OwnerEntry(Strict):
    label: str
    countries: list[CountryCode] = Field(default_factory=list[CountryCode])
    organization: str | None = None
    unknown: bool = False
    note: str | None = None

    @model_validator(mode="after")
    def mapped_exactly_once(self) -> Self:
        mapped = bool(self.countries) or self.organization is not None
        if mapped == self.unknown:
            message = "an owner code is either mapped to countries/an organization or unknown"
            raise ValueError(message)
        return self


class OwnersDocument(Strict):
    meta: dict[str, str]
    owners: dict[str, OwnerEntry]


class ProgramEntry(Strict):
    slug: str
    name_en: str
    name_ja: str


class CodeEntry(Strict):
    namespace: str
    code: str
    label: str
    kind: CodeKind


class OrganizationEntry(Strict):
    ll2: int | None = None
    slug: str | None = None
    name_en: str | None = None
    name_ja: str | None = None
    name_ja_source: str | None = None
    type: OrganizationType | None = None
    countries: list[CountryCode] = Field(default_factory=list[CountryCode])
    programs: list[str] = Field(default_factory=list[str])

    @model_validator(mode="after")
    def cited_and_identifiable(self) -> Self:
        if self.name_ja is not None and self.name_ja_source is None:
            message = f"name_ja {self.name_ja!r} needs name_ja_source"
            raise ValueError(message)
        if self.ll2 is None and (self.slug is None or self.name_en is None or self.type is None):
            message = "an organization without an LL2 id needs slug, name_en and type"
            raise ValueError(message)
        return self


class OrganizationsDocument(Strict):
    meta: dict[str, str]
    program: list[ProgramEntry]
    code: list[CodeEntry]
    organization: list[OrganizationEntry]


class DataSourceEntry(Strict):
    name_en: str
    name_ja: str
    description_en: str
    description_ja: str
    credit_en: str
    credit_ja: str
    license_en: str
    license_ja: str
    license_url: str | None = None
    homepage_url: str = Field(pattern=r"^https://")
    cadence_en: str
    cadence_ja: str
    update_interval_hours: int | None = Field(default=None, gt=0)


class SourcesDocument(Strict):
    meta: dict[str, str]
    sources: dict[str, DataSourceEntry]


class ReferenceData(Strict):
    countries: CountriesDocument
    celestrak_owners: OwnersDocument
    organizations: OrganizationsDocument
    sources: SourcesDocument
