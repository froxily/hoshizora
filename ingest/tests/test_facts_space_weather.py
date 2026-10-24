from datetime import timedelta

import pytest

from conftest import Database
from fact_seed import AS_OF, generate, seed_all, stored_facts, templates_of, unresolved_refs

pytestmark = pytest.mark.anyio

EXPECTED = {
    "space-weather.strongest_flare_week": {
        "xray_flare|F1": {"flare_class": "M2.3", "date": "2026-10-16"}
    },
    "space-weather.flares_week": {None: {"flares": 2}},
    "space-weather.kp_peak_week": {None: {"kp": 6.33, "date": "2026-10-15"}},
    "space-weather.fastest_wind_day": {None: {"speed": 612, "minutes": 10}},
    "space-weather.alerts_week": {None: {"alerts": 3}},
}


@pytest.fixture
async def seeded(clean_database: Database) -> Database:
    await seed_all(clean_database)
    return clean_database


async def test_every_space_weather_template_has_an_expectation() -> None:
    assert {template.key for template in templates_of("space-weather")} == set(EXPECTED)


async def test_space_weather_templates_store_the_expected_facts_with_lineage(
    seeded: Database,
) -> None:
    await generate(seeded, templates_of("space-weather"))

    facts = stored_facts(seeded, "space-weather")
    assert {
        key: {entity: fact["params"] for entity, fact in entities.items()}
        for key, entities in facts.items()
    } == EXPECTED
    assert facts["space-weather.kp_peak_week"][None]["score"] == pytest.approx(0.5098, abs=1e-4)
    assert facts["space-weather.strongest_flare_week"]["xray_flare|F1"]["score"] == (
        pytest.approx(0.4929, abs=1e-4)
    )
    assert unresolved_refs(seeded) == []


async def test_a_stale_swpc_feed_publishes_no_window_facts(seeded: Database) -> None:
    generated = await generate(seeded, templates_of("space-weather"), AS_OF + timedelta(days=2))

    assert generated.facts == 0
    assert stored_facts(seeded, "space-weather") == {}
