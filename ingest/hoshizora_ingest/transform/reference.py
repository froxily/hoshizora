from dataclasses import dataclass
from datetime import timedelta

from hoshizora_ingest.sources.reference.models import (
    CodeKind,
    DataSourceEntry,
    OrganizationEntry,
    OwnerEntry,
    ReferenceData,
)

CELESTRAK_OWNER = "celestrak.owner"
LL2_AGENCY = "ll2.agency"
CURATED = "hoshizora"


@dataclass(frozen=True)
class CountryRow:
    code: str
    alpha3: str
    name_en: str
    name_ja: str


@dataclass(frozen=True)
class ProgramRow:
    slug: str
    name_en: str
    name_ja: str


@dataclass(frozen=True)
class CurationRow:
    namespace: str
    code: str
    slug: str | None
    curated_name_en: str | None
    name_ja: str | None
    name_ja_source: str | None
    type_override: str | None
    countries: tuple[str, ...]
    programs: tuple[str, ...]


@dataclass(frozen=True)
class ExternalCodeRow:
    namespace: str
    code: str
    label: str
    kind: str
    organization_slug: str | None
    country_codes: tuple[str, ...]
    note: str | None


@dataclass(frozen=True)
class DataSourceRow:
    slug: str
    name_en: str
    name_ja: str
    description_en: str
    description_ja: str
    credit_en: str
    credit_ja: str
    license_en: str
    license_ja: str
    license_url: str | None
    homepage_url: str
    cadence_en: str
    cadence_ja: str
    update_interval: timedelta | None


@dataclass(frozen=True)
class ReferenceBatch:
    countries: tuple[CountryRow, ...]
    programs: tuple[ProgramRow, ...]
    curations: tuple[CurationRow, ...]
    codes: tuple[ExternalCodeRow, ...]
    data_sources: tuple[DataSourceRow, ...]


def curation_key(entry: OrganizationEntry) -> tuple[str, str]:
    if entry.ll2 is not None:
        return (LL2_AGENCY, str(entry.ll2))
    if entry.slug is None:
        message = "curated organization without LL2 id or slug"
        raise ValueError(message)
    return (CURATED, entry.slug)


def curation_row(entry: OrganizationEntry) -> CurationRow:
    namespace, code = curation_key(entry)
    return CurationRow(
        namespace=namespace,
        code=code,
        slug=entry.slug,
        curated_name_en=entry.name_en,
        name_ja=entry.name_ja,
        name_ja_source=entry.name_ja_source,
        type_override=entry.type,
        countries=tuple(entry.countries),
        programs=tuple(entry.programs),
    )


def owner_kind(owner: OwnerEntry) -> CodeKind:
    if owner.unknown:
        return "unknown"
    if owner.organization is not None and not owner.countries:
        return "organization"
    if len(owner.countries) == 1 and owner.organization is None:
        return "country"
    return "multinational"


def owner_row(code: str, owner: OwnerEntry) -> ExternalCodeRow:
    return ExternalCodeRow(
        namespace=CELESTRAK_OWNER,
        code=code,
        label=owner.label,
        kind=owner_kind(owner),
        organization_slug=owner.organization,
        country_codes=tuple(owner.countries),
        note=owner.note,
    )


def data_source_row(slug: str, entry: DataSourceEntry) -> DataSourceRow:
    hours = entry.update_interval_hours
    return DataSourceRow(
        slug=slug,
        name_en=entry.name_en,
        name_ja=entry.name_ja,
        description_en=entry.description_en,
        description_ja=entry.description_ja,
        credit_en=entry.credit_en,
        credit_ja=entry.credit_ja,
        license_en=entry.license_en,
        license_ja=entry.license_ja,
        license_url=entry.license_url,
        homepage_url=entry.homepage_url,
        cadence_en=entry.cadence_en,
        cadence_ja=entry.cadence_ja,
        update_interval=None if hours is None else timedelta(hours=hours),
    )


def normalize_reference(data: ReferenceData) -> ReferenceBatch:
    countries = tuple(
        CountryRow(code, entry.alpha3, entry.en, entry.ja)
        for code, entry in sorted(data.countries.countries.items())
    )
    programs = tuple(
        ProgramRow(program.slug, program.name_en, program.name_ja)
        for program in data.organizations.program
    )
    curations = tuple(curation_row(entry) for entry in data.organizations.organization)
    vocabulary = tuple(
        ExternalCodeRow(entry.namespace, entry.code, entry.label, entry.kind, None, (), None)
        for entry in data.organizations.code
    )
    owners = tuple(
        owner_row(code, owner) for code, owner in sorted(data.celestrak_owners.owners.items())
    )
    data_sources = tuple(
        data_source_row(slug, entry) for slug, entry in sorted(data.sources.sources.items())
    )
    return ReferenceBatch(countries, programs, curations, vocabulary + owners, data_sources)
