import psycopg
import pytest

from conftest import Database
from fact_seed import generate, seed_all, stored_facts, templates_of, unresolved_refs
from fakes import execute

pytestmark = pytest.mark.anyio

EXPECTED = {
    "launches.year_to_date": {None: {"launches": 25, "year": "2026", "ratio": 2.1}},
    "launches.record_year": {None: {"year": "2025", "attempts": 15}},
    "launches.program_year": {
        "usa": {
            "program": {"en": "United States", "ja": "アメリカ"},
            "attempts": 12,
            "year": "2025",
        },
        "japan": {"program": {"en": "Japan", "ja": "日本"}, "attempts": 3, "year": "2025"},
    },
    "launches.success_streak": {"Falcon": {"family": {"en": "Falcon"}, "streak": 34}},
    "launches.busiest_pad": {
        "40": {
            "pad": "Space Launch Complex 40",
            "location": "Cape Canaveral SFS, FL, USA",
            "attempts": 34,
        }
    },
    "launches.site_country_share": {
        "US": {
            "share": 0.8,
            "year": "2025",
            "country": {"en": "United States", "ja": "アメリカ合衆国"},
        }
    },
    "launches.most_flown_booster": {"2": {"serial": "B1077", "flights": 24}},
    "launches.landing_success_year": {
        None: {"year": "2026", "landings": 11, "attempts": 12, "rate": 0.917}
    },
    "launches.reflown_share": {None: {"year": "2025", "share": 0.92, "reflown": 11}},
    "launches.fastest_turnaround": {
        "2017": {"serial": "B1077", "days": 13.0, "flown_on": "2026-03-05"}
    },
}


@pytest.fixture
async def seeded(clean_database: Database) -> Database:
    await seed_all(clean_database)
    return clean_database


async def test_every_launch_template_has_an_expectation() -> None:
    assert {template.key for template in templates_of("launches")} == set(EXPECTED)


async def test_launch_templates_store_the_expected_facts_with_lineage(seeded: Database) -> None:
    generated = await generate(seeded, templates_of("launches"))

    facts = stored_facts(seeded, "launches")
    assert generated.skipped == ()
    assert {
        key: {entity: fact["params"] for entity, fact in entities.items()}
        for key, entities in facts.items()
    } == EXPECTED
    assert facts["launches.record_year"][None]["score"] == 1.0
    assert unresolved_refs(seeded) == []


async def test_launch_templates_wait_while_launch_library_is_incomplete(seeded: Database) -> None:
    execute(
        seeded.owner_url,
        "INSERT INTO raw.ingest_run (source, status, origin) "
        "VALUES ('launch-library', 'partial', 'https://seed.test') RETURNING id",
        (),
    )

    generated = await generate(seeded, templates_of("launches"))

    assert [skip.templates for skip in generated.skipped] == [tuple(EXPECTED)]
    assert stored_facts(seeded, "launches") == {}


async def test_a_tie_for_most_flights_publishes_no_booster_record(seeded: Database) -> None:
    with psycopg.connect(seeded.owner_url, autocommit=True) as connection:
        connection.execute("UPDATE core.launcher SET flights = 24 WHERE ll2_id = 1")
        connection.execute("REFRESH MATERIALIZED VIEW mart.booster_ranking")

    await generate(seeded, templates_of("launches"))

    assert "launches.most_flown_booster" not in stored_facts(seeded, "launches")
