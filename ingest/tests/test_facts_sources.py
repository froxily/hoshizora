import pytest

from conftest import Database
from fact_seed import generate, seed_all, stored_facts, templates_of, unresolved_refs
from fakes import execute

pytestmark = pytest.mark.anyio

EXPECTED = {
    "sources.launch_records": {None: {"launches": 53, "date": "2023-03-07"}},
    "sources.catalog_size": {None: {"objects": 62, "date": "1958-03-17"}},
    "sources.close_approach_span": {None: {"approaches": 10, "first": "1937", "last": "2026"}},
}


@pytest.fixture
async def seeded(clean_database: Database) -> Database:
    await seed_all(clean_database)
    return clean_database


async def test_every_source_template_has_an_expectation() -> None:
    assert {template.key for template in templates_of("sources")} == set(EXPECTED)


async def test_source_templates_store_the_expected_facts_with_lineage(seeded: Database) -> None:
    await generate(seeded, templates_of("sources"))

    facts = stored_facts(seeded, "sources")
    assert {
        key: {entity: fact["params"] for entity, fact in entities.items()}
        for key, entities in facts.items()
    } == EXPECTED
    assert unresolved_refs(seeded) == []


async def test_only_the_launch_library_fact_waits_for_its_backfill(seeded: Database) -> None:
    execute(
        seeded.owner_url,
        "INSERT INTO raw.ingest_run (source, status, origin) "
        "VALUES ('launch-library', 'partial', 'https://seed.test') RETURNING id",
        (),
    )

    generated = await generate(seeded, templates_of("sources"))

    assert [skip.templates for skip in generated.skipped] == [("sources.launch_records",)]
    assert set(stored_facts(seeded, "sources")) == {
        "sources.catalog_size",
        "sources.close_approach_span",
    }
