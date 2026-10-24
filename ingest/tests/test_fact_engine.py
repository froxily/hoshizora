from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import psycopg
import pytest
import yaml

from hoshizora_ingest.db import connections
from hoshizora_ingest.facts.engine import Generated, generate_facts, hour_start
from hoshizora_ingest.facts.humanize import Unit, humanize
from hoshizora_ingest.facts.params import param_value
from hoshizora_ingest.facts.scoring import Signals, score
from hoshizora_ingest.facts.spec import (
    Param,
    Scoring,
    Template,
    TemplateError,
    load_templates,
    parse_templates,
    unique,
)
from hoshizora_ingest.pipeline import RunEnvironment, run_source
from hoshizora_ingest.sources.reference.adapter import ReferenceSource

from conftest import Database
from fakes import RecordingSleep, execute, query, scalar

AS_OF = datetime(2026, 10, 18, 6, tzinfo=UTC)
COUNTRIES = """
SELECT 'country' AS entity_type, code AS entity_key, name_en AS country_en, name_ja AS country_ja,
       CASE code WHEN 'JP' THEN 0.9 ELSE 0.1 END AS percentile,
       jsonb_build_array(jsonb_build_object('entity', 'core.country', 'key', code)) AS source_refs
FROM core.country
WHERE code IN ('JP', 'US')
"""

WRITING = """
WITH gone AS (DELETE FROM core.country RETURNING code)
SELECT 'country' AS entity_type, code AS entity_key, code AS country_en, code AS country_ja,
       jsonb_build_array(jsonb_build_object('entity', 'core.country', 'key', code)) AS source_refs
FROM gone
"""


def template(**overrides: object) -> dict[str, Any]:
    spec: dict[str, Any] = {
        "key": "orbits.country_name",
        "module": "orbits",
        "query": COUNTRIES,
        "params": {"country": {"type": "name", "from": "country"}},
        "text": {"en": "{country} is in the catalog.", "ja": "{country}は目録にあります。"},
        "min_score": 0.5,
        "valid_for": "P1D",
        "scoring": {"base": 0.0},
        "examples": [
            {
                "params": {"country": {"en": "Japan", "ja": "日本"}},
                "en": "Japan is in the catalog.",
                "ja": "日本は目録にあります。",
            }
        ],
    }
    return spec | overrides


def parsed(*specs: dict[str, Any]) -> tuple[Template, ...]:
    return parse_templates("test.yaml", yaml.safe_dump(list(specs), allow_unicode=True))


@pytest.mark.parametrize(
    ("unit", "value", "expected"),
    [
        ("earth_moon_distances", 384_400, 1.0),
        ("earth_diameters", 12_742, 1.0),
        ("fuji_heights", 3.776, 1.0),
        ("skytree_heights", 0.634, 1.0),
        ("shinkansen_speeds", 320 / 3_600, 1.0),
        ("light_seconds", 299_792.458, 1.0),
        ("shinkansen_hours", 320, 1.0),
        ("minutes_to_cross_earth_moon", 384_400 / 60, 1.0),
        ("shinkansen_years", 320 * 24 * 365.25, 1.0),
    ],
)
def test_each_humanizer_unit_is_one_at_its_reference(
    unit: Unit, value: float, expected: float
) -> None:
    assert humanize(unit, value) == pytest.approx(expected)


def test_score_takes_the_strongest_signal_then_decays_with_distance_in_time() -> None:
    scoring = Scoring(base=0.3, half_life_days=7)

    assert score(Signals(percentile=0.8), scoring, AS_OF) == 0.8
    assert score(Signals(is_first=True), scoring, AS_OF) == 0.9
    assert score(Signals(percentile=0.99, is_record=True), scoring, AS_OF) == 1.0
    assert score(Signals(event_at=AS_OF - timedelta(days=7)), scoring, AS_OF) == 0.15
    assert score(Signals(event_at=AS_OF + timedelta(days=14)), scoring, AS_OF) == 0.075


@pytest.mark.parametrize(
    ("param", "value", "expected"),
    [
        (Param.model_validate({"type": "number", "from": "v", "significant": 2}), 0.04321, 0.043),
        (Param.model_validate({"type": "number", "from": "v", "decimals": 1}), 2.359, 2.4),
        (Param.model_validate({"type": "percent", "from": "v", "decimals": 1}), 0.61345, 0.613),
        (Param.model_validate({"type": "integer", "from": "v"}), 1107.6, 1108),
        (Param.model_validate({"type": "year", "from": "v"}), 2017, "2017"),
        (Param.model_validate({"type": "date", "from": "v"}), date(2026, 10, 18), "2026-10-18"),
        (
            Param.model_validate({"type": "date", "from": "v"}),
            datetime(2026, 10, 17, 23, 30, tzinfo=UTC),
            "2026-10-17",
        ),
        (
            Param.model_validate(
                {"type": "number", "from": "v", "humanize": "earth_moon_distances", "decimals": 1}
            ),
            115_320,
            0.3,
        ),
    ],
)
def test_params_round_and_humanize_before_storage(
    param: Param, value: object, expected: object
) -> None:
    assert param_value(param, {"v": value}) == expected


def test_names_fall_back_to_english_when_japanese_is_missing() -> None:
    param = Param.model_validate({"type": "name", "from": "org"})

    assert param_value(param, {"org_en": "JAXA", "org_ja": "JAXA"}) == {"en": "JAXA", "ja": "JAXA"}
    assert param_value(param, {"org_en": "Rocket Lab", "org_ja": None}) == {"en": "Rocket Lab"}


@pytest.mark.parametrize(
    ("overrides", "problem"),
    [
        ({"text": {"en": "{country} in {year}.", "ja": "{country}。"}}, "placeholders differ"),
        ({"text": {"en": "{country}", "ja": "{country, date}"}}, "can't use style"),
        ({"params": {}}, "must match params"),
        (
            {
                "text": {"en": "{country, number, percent}", "ja": "{country, number, percent}"},
            },
            "can't use style",
        ),
        ({"text": {"en": "{country} {n, plural}", "ja": "{country}"}}, "brace"),
        ({"query": "SELECT 1 FROM raw.payload, core.country"}, "core and mart only"),
        ({"query": "DELETE FROM core.country"}, "one SELECT"),
        ({"query": COUNTRIES + "; SELECT 1"}, "one SELECT"),
        ({"key": "launches.country_name"}, "must start with its module"),
        ({"params": {"country": {"type": "number", "from": "country"}}}, "exactly one of"),
        ({"examples": []}, "at least 1"),
    ],
)
def test_invalid_templates_fail_loudly(overrides: dict[str, Any], problem: str) -> None:
    with pytest.raises(TemplateError, match=problem):
        parsed(template(**overrides))


def test_template_keys_are_unique() -> None:
    with pytest.raises(TemplateError, match="duplicate"):
        unique(parsed(template(), template()))


def test_hour_start_is_the_as_of_convention() -> None:
    assert hour_start(datetime(2026, 10, 18, 6, 59, 59, tzinfo=UTC)) == AS_OF


async def seed_reference(database: Database) -> None:
    async with connections(database.writer_url) as db:
        env = RunEnvironment(db=db.data, log_db=db.log, user_agent="t", sleep=RecordingSleep())
        await run_source(ReferenceSource(), env)


async def generate(database: Database, templates: tuple[Template, ...]) -> Generated:
    async with connections(database.writer_url) as db:
        return await generate_facts(db.data, templates, AS_OF)


FACTS = "SELECT id, template_key, entity_key, params, score FROM facts.fact ORDER BY entity_key"


@pytest.mark.anyio
async def test_generation_keeps_facts_above_min_score_with_stable_ids(
    clean_database: Database,
) -> None:
    await seed_reference(clean_database)
    templates = parsed(template())
    url = clean_database.owner_url

    first = await generate(clean_database, templates)
    stored = query(url, FACTS)
    await generate(clean_database, templates)

    assert (first.templates, first.facts) == (1, 1)
    assert stored == query(url, FACTS)
    assert [(row[2], row[3], row[4]) for row in stored] == [
        ("JP", {"country": {"en": "Japan", "ja": "日本"}}, 0.9)
    ]
    assert query(url, "SELECT key, module, min_score FROM facts.template") == [
        ("orbits.country_name", "orbits", 0.5)
    ]
    assert scalar(url, "SELECT valid_until FROM facts.fact") == AS_OF + timedelta(days=1)


@pytest.mark.anyio
async def test_vanished_candidates_removed_templates_and_expired_facts_are_deleted(
    clean_database: Database,
) -> None:
    await seed_reference(clean_database)
    url = clean_database.owner_url
    await generate(clean_database, parsed(template(scoring={"base": 0.6})))
    narrower = COUNTRIES.replace("IN ('JP', 'US')", "= 'US'")

    narrowed = await generate(
        clean_database, parsed(template(query=narrower, scoring={"base": 0.6}))
    )
    kept = query(url, "SELECT entity_key FROM facts.fact")
    expiring = narrower.replace(
        "AS source_refs", "AS source_refs, timestamptz '2026-10-17 06:00Z' AS valid_until"
    )
    expired = await generate(
        clean_database, parsed(template(query=expiring, scoring={"base": 0.6}))
    )
    gone = await generate(clean_database, ())

    assert (narrowed.facts, narrowed.removed, kept) == (1, 1, [("US",)])
    assert expired.removed == 1
    assert gone.removed == 0
    assert scalar(url, "SELECT count(*) FROM facts.fact") == 0
    assert scalar(url, "SELECT count(*) FROM facts.template") == 0


@pytest.mark.anyio
async def test_templates_wait_for_a_source_until_its_latest_run_succeeded(
    clean_database: Database,
) -> None:
    await seed_reference(clean_database)
    url = clean_database.owner_url
    gated = parsed(template(requires=["launch-library"], scoring={"base": 0.6}))
    run = (
        "INSERT INTO raw.ingest_run (source, status, origin) "
        "VALUES ('launch-library', %s, 'x') RETURNING id"
    )
    execute(url, run, ("succeeded",))
    await generate(clean_database, gated)
    execute(url, run, ("partial",))

    waiting = await generate(clean_database, gated)

    assert waiting.facts == 0
    assert [(s.source, s.status, s.templates) for s in waiting.skipped] == [
        ("launch-library", "partial", ("orbits.country_name",))
    ]
    assert waiting.removed == 2
    assert scalar(url, "SELECT count(*) FROM facts.fact") == 0


@pytest.mark.anyio
async def test_template_queries_run_read_only(clean_database: Database) -> None:
    await seed_reference(clean_database)

    with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
        await generate(clean_database, parsed(template(query=WRITING)))

    assert (
        scalar(clean_database.owner_url, "SELECT count(*) FROM core.country WHERE code = 'JP'") == 1
    )


@pytest.mark.anyio
async def test_facts_must_carry_core_or_mart_lineage(clean_database: Database) -> None:
    await seed_reference(clean_database)
    unlinked = COUNTRIES.replace("'core.country'", "'elsewhere'")

    with pytest.raises(TemplateError, match="core or mart entity"):
        await generate(clean_database, parsed(template(query=unlinked)))


def test_the_catalog_loads_with_a_test_module_per_template_module() -> None:
    templates = load_templates()
    tested = {
        path.stem.removeprefix("test_facts_").replace("_", "-")
        for path in Path(__file__).parent.glob("test_facts_*.py")
    }

    assert len(templates) >= 25
    assert {template.module for template in templates} <= tested


@pytest.mark.anyio
async def test_templates_wait_while_a_source_mixes_origins_despite_a_successful_run(
    clean_database: Database,
) -> None:
    await seed_reference(clean_database)
    url = clean_database.owner_url
    execute(
        url,
        "INSERT INTO raw.ingest_run (source, status, origin) "
        "VALUES ('launch-library', 'succeeded', 'https://lldev.example') RETURNING id",
        (),
    )
    for host in ("https://ll.example", "https://lldev.example"):
        payload = execute(
            url,
            "INSERT INTO raw.payload (source, endpoint, params, content_hash, body) "
            "VALUES ('launch-library', %s, '{}', md5(%s), '{}') RETURNING id",
            (f"{host}/2.3.0/launches/", host),
        )
        execute(
            url,
            "INSERT INTO core.source_record (entity, entity_key, payload_id) "
            "VALUES ('core.country', 'JP', %s) RETURNING entity",
            (payload[0][0],),
        )

    waiting = await generate(clean_database, parsed(template(requires=["launch-library"])))

    assert [(s.source, s.status) for s in waiting.skipped] == [("launch-library", "mixed_origins")]
