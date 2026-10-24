import pytest

from conftest import Database
from fact_seed import generate, seed_all, stored_facts, templates_of, unresolved_refs

pytestmark = pytest.mark.anyio

EXPECTED = {
    "exoplanets.confirmed_total": {None: {"total": 10, "this_year": 2, "year": "2026"}},
    "exoplanets.record_year": {None: {"year": "2025", "planets": 2}},
    "exoplanets.nearest": {
        "Proxima Cen b": {"planet": "Proxima Cen b", "light_years": 4.2, "years": 14000000}
    },
    "exoplanets.transit_share": {None: {"share": 0.6}},
    "exoplanets.earth_sized_temperate": {None: {"planets": 2}},
}


@pytest.fixture
async def seeded(clean_database: Database) -> Database:
    await seed_all(clean_database)
    return clean_database


async def test_every_exoplanet_template_has_an_expectation() -> None:
    assert {template.key for template in templates_of("exoplanets")} == set(EXPECTED)


async def test_exoplanet_templates_store_the_expected_facts_with_lineage(
    seeded: Database,
) -> None:
    generated = await generate(seeded, templates_of("exoplanets"))

    facts = stored_facts(seeded, "exoplanets")
    assert generated.skipped == ()
    assert {
        key: {entity: fact["params"] for entity, fact in entities.items()}
        for key, entities in facts.items()
    } == EXPECTED
    assert facts["exoplanets.nearest"]["Proxima Cen b"]["score"] == 1.0
    assert len(facts["exoplanets.earth_sized_temperate"][None]["refs"]) == 2
    assert unresolved_refs(seeded) == []
