from psycopg import AsyncConnection, sql

from hoshizora_ingest.sources.base import StoreResult
from hoshizora_ingest.store.organizations import apply_curation
from hoshizora_ingest.store.upsert import Column, TableSpec, delete_missing, upsert_with_lineage
from hoshizora_ingest.transform.reference import ReferenceBatch

COUNTRIES = TableSpec(
    schema="core",
    name="country",
    columns=(
        Column("code", "char(2)"),
        Column("alpha3", "char(3)"),
        Column("name_en", "text"),
        Column("name_ja", "text"),
    ),
    key=("code",),
)

PROGRAMS = TableSpec(
    schema="core",
    name="program",
    columns=(Column("slug", "text"), Column("name_en", "text"), Column("name_ja", "text")),
    key=("slug",),
)

CURATIONS = TableSpec(
    schema="core",
    name="organization_curation",
    columns=(
        Column("namespace", "text"),
        Column("code", "text"),
        Column("slug", "text"),
        Column("curated_name_en", "text"),
        Column("name_ja", "text"),
        Column("name_ja_source", "text"),
        Column("type_override", "text"),
        Column("countries", "char(2)[]"),
        Column("programs", "text[]"),
    ),
    key=("namespace", "code"),
)

EXTERNAL_CODES = TableSpec(
    schema="core",
    name="external_code",
    columns=(
        Column("namespace", "text"),
        Column("code", "text"),
        Column("label", "text"),
        Column("kind", "text"),
        Column("organization_slug", "text"),
        Column("country_codes", "char(2)[]"),
        Column("note", "text"),
    ),
    key=("namespace", "code"),
)


DATA_SOURCES = TableSpec(
    schema="core",
    name="data_source",
    columns=(
        Column("slug", "text"),
        Column("name_en", "text"),
        Column("name_ja", "text"),
        Column("description_en", "text"),
        Column("description_ja", "text"),
        Column("credit_en", "text"),
        Column("credit_ja", "text"),
        Column("license_en", "text"),
        Column("license_ja", "text"),
        Column("license_url", "text"),
        Column("homepage_url", "text"),
        Column("cadence_en", "text"),
        Column("cadence_ja", "text"),
        Column("update_interval", "interval"),
    ),
    key=("slug",),
)


async def store_reference(
    db: AsyncConnection, batch: ReferenceBatch, payload_id: int
) -> StoreResult:
    result = await upsert_with_lineage(db, COUNTRIES, batch.countries, payload_id)
    result += await upsert_with_lineage(db, PROGRAMS, batch.programs, payload_id)
    await delete_missing(db, CURATIONS, batch.curations)
    result += await upsert_with_lineage(db, CURATIONS, batch.curations, payload_id)
    namespaces = sorted({code.namespace for code in batch.codes})
    await delete_missing(
        db,
        EXTERNAL_CODES,
        batch.codes,
        sql.SQL("namespace = ANY({})").format(sql.Literal(namespaces)),
    )
    result += await upsert_with_lineage(db, EXTERNAL_CODES, batch.codes, payload_id)
    await delete_missing(db, DATA_SOURCES, batch.data_sources)
    result += await upsert_with_lineage(db, DATA_SOURCES, batch.data_sources, payload_id)
    changed = await apply_curation(db)
    return StoreResult(result.rows_in, result.rows_changed + changed)
