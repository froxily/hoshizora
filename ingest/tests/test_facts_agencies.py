import pytest

from conftest import Database
from fact_seed import generate, seed_all, stored_facts, templates_of, unresolved_refs
from fakes import execute

pytestmark = pytest.mark.anyio

SPACEX = {"en": "SpaceX", "ja": "スペースX"}
CASC = {"en": "China Aerospace Science and Technology Corporation", "ja": "中国航天科技集団"}
EXPECTED = {
    "agencies.launch_total": {
        "spacex": {"org": SPACEX, "attempts": 34, "since": "2024"},
        "casc": {"org": CASC, "attempts": 11, "since": "2026"},
    },
    "agencies.success_rate": {"spacex": {"org": SPACEX, "rate": 1.0, "completed": 34}},
    "agencies.first_launch": {
        "spacex": {"org": SPACEX, "date": "2024-01-05"},
        "casc": {"org": CASC, "date": "2026-01-10"},
    },
    "agencies.busiest_year": {"spacex": {"org": SPACEX, "year": "2025", "attempts": 12}},
    "agencies.oldest": {"casc": {"org": CASC, "founded": "1999"}},
}


@pytest.fixture
async def seeded(clean_database: Database) -> Database:
    await seed_all(clean_database)
    return clean_database


async def test_every_agency_template_has_an_expectation() -> None:
    assert {template.key for template in templates_of("agencies")} == set(EXPECTED)


async def test_agency_templates_store_the_expected_facts_with_lineage(seeded: Database) -> None:
    await generate(seeded, templates_of("agencies"))

    facts = stored_facts(seeded, "agencies")
    assert {
        key: {entity: fact["params"] for entity, fact in entities.items()}
        for key, entities in facts.items()
    } == EXPECTED
    assert "jaxa" not in facts["agencies.launch_total"]
    assert unresolved_refs(seeded) == []


async def test_agency_templates_wait_while_launch_library_is_incomplete(seeded: Database) -> None:
    execute(
        seeded.owner_url,
        "INSERT INTO raw.ingest_run (source, status, origin) "
        "VALUES ('launch-library', 'failed', 'https://seed.test') RETURNING id",
        (),
    )

    generated = await generate(seeded, templates_of("agencies"))

    assert [(skip.status, skip.templates) for skip in generated.skipped] == [
        ("failed", tuple(EXPECTED))
    ]
    assert stored_facts(seeded, "agencies") == {}
