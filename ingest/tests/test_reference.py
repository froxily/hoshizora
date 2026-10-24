from collections import Counter

import pytest

from hoshizora_ingest.db import connections
from hoshizora_ingest.pipeline import RunEnvironment, RunOutcome, run_source
from hoshizora_ingest.reference.docs import DOCS_PATH, current_document
from hoshizora_ingest.registry import SOURCES
from hoshizora_ingest.sources.reference.adapter import ReferenceSource, load_documents
from hoshizora_ingest.sources.reference.models import ReferenceData
from hoshizora_ingest.store.organizations import apply_curation
from hoshizora_ingest.transform.reference import normalize_reference

from conftest import Database
from fakes import RecordingSleep, execute, query, scalar

DATA = ReferenceData.model_validate(load_documents())
CURATED_ONLY = {"abs", "asiasat", "iss", "nato", "new-ico", "o3b", "orbcomm"}


def test_every_owner_organization_is_curated() -> None:
    slugs = {entry.slug for entry in DATA.organizations.organization}
    owners = DATA.celestrak_owners.owners.values()

    assert {o.organization for o in owners if o.organization is not None} <= slugs


def test_every_referenced_country_exists() -> None:
    known = set(DATA.countries.countries)
    used = {code for owner in DATA.celestrak_owners.owners.values() for code in owner.countries}
    used |= {code for entry in DATA.organizations.organization for code in entry.countries}

    assert used <= known


def test_every_program_membership_names_a_program() -> None:
    programs = {program.slug for program in DATA.organizations.program}
    used = {slug for entry in DATA.organizations.organization for slug in entry.programs}

    assert used <= programs


def test_curation_keys_and_slugs_are_unique() -> None:
    batch = normalize_reference(DATA)
    keys = Counter((row.namespace, row.code) for row in batch.curations)
    slugs = Counter(row.slug for row in batch.curations if row.slug is not None)

    assert [key for key, count in keys.items() if count > 1] == []
    assert [slug for slug, count in slugs.items() if count > 1] == []


def test_key_organizations_carry_cited_japanese_names() -> None:
    curated = {entry.slug: entry for entry in DATA.organizations.organization}

    for slug in ("nasa", "esa", "jaxa", "cnsa", "roscosmos", "isro", "spacex"):
        entry = curated[slug]
        assert entry.name_ja is not None, slug
        assert entry.name_ja_source is not None, slug
        assert entry.name_ja_source.startswith("https://ja.wikipedia.org/wiki/"), slug


def test_every_registered_source_is_described_once() -> None:
    assert set(DATA.sources.sources) == set(SOURCES)


def test_source_catalog_credits_match_the_registry() -> None:
    for slug, entry in SOURCES.items():
        assert DATA.sources.sources[slug].credit_en == entry.info.credit, slug


def test_owner_kinds_follow_their_mapping() -> None:
    kinds = {row.code: row.kind for row in normalize_reference(DATA).codes}

    assert (kinds["JPN"], kinds["CHBZ"], kinds["PRES"], kinds["ESA"], kinds["TBD"]) == (
        "country",
        "multinational",
        "multinational",
        "organization",
        "unknown",
    )


def test_organizations_doc_is_in_sync_with_the_curated_data() -> None:
    assert DOCS_PATH.read_text(encoding="utf-8") == current_document(), (
        "Run `uv run hoshizora docs` and commit docs/sources/organizations.md"
    )


async def ingest_reference(database: Database) -> RunOutcome:
    async with connections(database.writer_url) as db:
        env = RunEnvironment(
            db=db.data, log_db=db.log, user_agent="Hoshizora/test", sleep=RecordingSleep()
        )
        return await run_source(ReferenceSource(), env)


def add_ll2_agency(database: Database, ll2_id: int, name: str) -> None:
    execute(
        database.owner_url,
        """
        WITH created AS (
            INSERT INTO core.organization (source_name, source_type)
            VALUES (%s, 'Government') RETURNING id
        )
        INSERT INTO core.organization_alias (namespace, code, organization_id)
        SELECT 'll2.agency', %s, id FROM created RETURNING organization_id
        """,
        (name, str(ll2_id)),
    )


@pytest.mark.anyio
async def test_reference_loads_countries_programs_and_curated_only_organizations(
    clean_database: Database,
) -> None:
    outcome = await ingest_reference(clean_database)

    url = clean_database.owner_url
    assert outcome.stats.payloads_new == 1
    assert scalar(url, "SELECT count(*) FROM core.country") == len(DATA.countries.countries)
    assert scalar(url, "SELECT name_ja FROM core.country WHERE code = 'JP'") == "日本"
    assert scalar(url, "SELECT count(*) FROM core.program") == len(DATA.organizations.program)
    assert {str(row[0]) for row in query(url, "SELECT slug FROM core.organization")} == CURATED_ONLY
    assert query(
        url,
        "SELECT country_code FROM core.country_alias "
        "WHERE namespace = 'celestrak.owner' AND code = 'CHBZ' ORDER BY 1",
    ) == [("BR",), ("CN",)]


@pytest.mark.anyio
async def test_reference_loads_the_bilingual_source_catalog_with_lineage(
    clean_database: Database,
) -> None:
    await ingest_reference(clean_database)

    url = clean_database.owner_url
    assert scalar(url, "SELECT count(*) FROM core.data_source") == len(SOURCES)
    assert query(
        url,
        "SELECT name_ja, update_interval::text FROM core.data_source WHERE slug = 'swpc'",
    ) == [(DATA.sources.sources["swpc"].name_ja, "01:00:00")]
    assert (
        scalar(url, "SELECT update_interval FROM core.data_source WHERE slug = 'reference'") is None
    )
    assert (
        scalar(
            url,
            "SELECT count(*) FROM core.source_record "
            "WHERE entity = 'core.data_source' AND entity_key = 'jpl'",
        )
        == 1
    )


@pytest.mark.anyio
async def test_reloading_unchanged_reference_data_changes_nothing(
    clean_database: Database,
) -> None:
    await ingest_reference(clean_database)
    second = await ingest_reference(clean_database)

    assert (second.stats.payloads_new, second.stats.rows_upserted) == (0, 0)


@pytest.mark.anyio
async def test_owner_codes_wait_loudly_until_their_organization_exists(
    clean_database: Database,
) -> None:
    await ingest_reference(clean_database)

    unmapped = query(
        clean_database.owner_url,
        "SELECT code, problem FROM mart.dq_unmapped_code WHERE code = 'ESA'",
    )
    assert unmapped == [("ESA", "no alias for organization")]


@pytest.mark.anyio
@pytest.mark.parametrize("agency_first", [True, False])
async def test_curation_applies_whichever_side_arrives_first(
    clean_database: Database, *, agency_first: bool
) -> None:
    if agency_first:
        add_ll2_agency(clean_database, 27, "European Space Agency")
        await ingest_reference(clean_database)
    else:
        await ingest_reference(clean_database)
        add_ll2_agency(clean_database, 27, "European Space Agency")
        async with connections(clean_database.writer_url) as db:
            await apply_curation(db.data)
            await db.data.commit()

    url = clean_database.owner_url
    assert query(
        url, "SELECT slug, name_en, name_ja, type FROM core.organization WHERE slug = 'esa'"
    ) == [("esa", "European Space Agency", "欧州宇宙機関", "agency")]
    assert (
        scalar(
            url,
            "SELECT o.slug FROM core.organization_alias a JOIN core.organization o "
            "ON o.id = a.organization_id WHERE a.namespace = 'celestrak.owner' AND a.code = 'ESA'",
        )
        == "esa"
    )
    assert (
        scalar(
            url,
            "SELECT count(*) FROM core.program_member m JOIN core.organization o "
            "ON o.id = m.organization_id WHERE o.slug = 'esa' AND m.program_slug = 'europe'",
        )
        == 1
    )
