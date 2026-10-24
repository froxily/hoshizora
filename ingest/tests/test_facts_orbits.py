import pytest

from conftest import Database
from fact_seed import generate, seed_all, stored_facts, templates_of, unresolved_refs

pytestmark = pytest.mark.anyio

EXPECTED = {
    "orbits.objects_in_orbit": {None: {"objects": 52}},
    "orbits.debris_share": {None: {"share": 0.25}},
    "orbits.country_payloads": {
        "US": {
            "country": {"en": "United States", "ja": "アメリカ合衆国"},
            "payloads": 21,
            "share": 0.538,
        }
    },
    "orbits.oldest_in_orbit": {"5": {"name": "VANGUARD 1", "date": "1958-03-17"}},
    "orbits.reentries_year": {None: {"objects": 4, "year": "2026"}},
    "orbits.iss_altitude": {"25544": {"altitude": 420, "fujis": 111}},
}


@pytest.fixture
async def seeded(clean_database: Database) -> Database:
    await seed_all(clean_database)
    return clean_database


async def test_every_orbit_template_has_an_expectation() -> None:
    assert {template.key for template in templates_of("orbits")} == set(EXPECTED)


async def test_orbit_templates_store_the_expected_facts_with_lineage(seeded: Database) -> None:
    await generate(seeded, templates_of("orbits"))

    facts = stored_facts(seeded, "orbits")
    assert {
        key: {entity: fact["params"] for entity, fact in entities.items()}
        for key, entities in facts.items()
    } == EXPECTED
    assert facts["orbits.country_payloads"].keys() == {"US"}
    assert unresolved_refs(seeded) == []
