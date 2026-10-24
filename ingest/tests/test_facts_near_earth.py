import pytest

from conftest import Database
from fact_seed import generate, seed_all, stored_facts, templates_of, unresolved_refs

pytestmark = pytest.mark.anyio

EXPECTED = {
    "near-earth.closest_this_week": {
        "TEST1": {"designation": "TEST1", "distance": 0.78, "date": "2026-10-20"}
    },
    "near-earth.inside_moon_orbit_year": {None: {"flybys": 2, "year": "2026"}},
    "near-earth.largest_next_year": {
        "99942": {
            "designation": "99942 Apophis (2004 MN4)",
            "date": "2026-10-22",
            "size_min": 670.0,
            "size_max": 1500.0,
            "skytree": 2.4,
        }
    },
    "near-earth.fastest_next_year": {
        "99942": {
            "designation": "99942 Apophis (2004 MN4)",
            "date": "2026-10-22",
            "speed": 30.5,
            "times": 343,
        }
    },
    "near-earth.closest_this_century": {
        "TEST4": {
            "designation": "TEST4",
            "distance": 74799,
            "date": "2019-07-25",
            "diameters": 5.87,
        }
    },
    "near-earth.sentry_watchlist": {None: {"objects": 3}},
}


@pytest.fixture
async def seeded(clean_database: Database) -> Database:
    await seed_all(clean_database)
    return clean_database


async def test_every_near_earth_template_has_an_expectation() -> None:
    assert {template.key for template in templates_of("near-earth")} == set(EXPECTED)


async def test_near_earth_templates_store_the_expected_facts_with_lineage(
    seeded: Database,
) -> None:
    generated = await generate(seeded, templates_of("near-earth"))

    facts = stored_facts(seeded, "near-earth")
    assert generated.skipped == ()
    assert {
        key: {entity: fact["params"] for entity, fact in entities.items()}
        for key, entities in facts.items()
    } == EXPECTED
    assert facts["near-earth.closest_this_week"]["TEST1"]["score"] == pytest.approx(
        0.4473, abs=1e-4
    )
    assert facts["near-earth.largest_next_year"]["99942"]["score"] == pytest.approx(
        0.7778, abs=1e-4
    )
    assert unresolved_refs(seeded) == []


async def test_a_distant_week_keeps_the_closest_flyby_below_its_threshold(
    seeded: Database,
) -> None:
    week = next(t for t in templates_of("near-earth") if t.key == "near-earth.closest_this_week")
    stricter = week.model_copy(update={"min_score": 0.45})

    await generate(seeded, (stricter,))

    assert stored_facts(seeded, "near-earth") == {}
