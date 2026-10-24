# ADR 0006: Fact engine

- Status: accepted
- Date: 2026-10-18

## Context

Every page shows fun facts, and every one must be computed from ingested data, carry its lineage, and read naturally in English and Japanese. The API already renders stored facts (`facts.template`, `facts.fact`, V13) with a subset of ICU MessageFormat. Phase 3 needs the template format, the generator, scoring and the unit humanizer.

## Decision

1. **Templates are YAML in `facts/templates/<module>.yaml`, validated on load** (`hoshizora_ingest/facts/spec.py`).
   - **Fields:** `key`, `module`, `query`, `params`, `text.en`, `text.ja`, `min_score`, `valid_for`, `scoring`, `requires` and `examples`.
   - **Queries:** one `SELECT` or `WITH` over `core` and `mart` only, with `%(as_of)s` as its only parameter. A literal `%` must be written `%%`.
   - **Placeholders:** en and ja must name exactly the declared params. Each style must fit the param type and the renderer's grammar: `{p}`, `{p, number[, integer|percent|compact]}`, `{p, date}`. The two languages may style a param differently, so Japanese can show 3.4万 where English shows 34,186. A brace the renderer can't format fails the load, because the renderer would print it literally.
   - **Examples:** each template carries at least one, with params and the exact rendered en and ja. The API's `FactTemplateCatalogTest` renders them through `FactRenderer`.
2. **Facts store params, never prose.**
   - The engine rounds numbers before storage (`decimals` or `significant`), and the renderer shows exactly those digits.
   - Percents are stored as fractions, dates as ISO dates and years as strings, so they aren't grouped like numbers.
   - Names are `{"en", "ja"}` maps. A missing `name_ja` falls back to English rather than an invented translation.
3. **The humanizer is a param transform** (`humanize: <unit>`).
   - **Units:**
     - Earth–Moon distances (384,400 km) and Earth diameters (12,742 km).
     - Mt. Fuji (3,776 m) and Tokyo Skytree (634 m) heights.
     - E5 Shinkansen speed (320 km/h) and travel hours.
     - Light-seconds, and minutes to cross the Earth–Moon distance.
   - The comparison is computed from the same row as the number it explains.
4. **Scoring:** `score = min(1, max(base, percentile, 0.9 if first, 1.0 if record)) × 0.5^(|as_of − event_at| / half_life)`.
   - The query supplies `percentile` (usually `percent_rank()` against history), `is_record`, `is_first` and `event_at`. The template sets `base` and `half_life_days`.
   - Where history is too short for a percentile (SWPC keeps about a week), the query maps the reading onto its physical scale instead: Kp / 9, or the NOAA R level for flares.
   - Facts below `min_score` are never stored.
5. **One as-of convention.** `as_of` is the start of the current UTC hour, as in `stats/overview`, and queries run in a UTC session.
6. **Generation is one consistent step.**
   - All queries run in one `REPEATABLE READ READ ONLY` transaction, so templates see the same snapshot and can't write.
   - One write transaction then:
     - syncs `facts.template`;
     - upserts facts on `(template_key, entity_type, entity_key)`, keeping ids stable;
     - deletes facts whose candidate vanished, whose template was removed, or whose `valid_until` passed.
   - A template error fails the whole run instead of publishing a partial set.
   - Mart refreshes trigger it, and `just facts` runs it on demand.
7. **Lineage is mandatory.** Every fact needs at least one `source_refs` entry naming a `core.*` or `mart.*` row. Tests resolve each reference to an existing row. The API turns them into lineage (`core.*`) and records links ("How we know this").
8. **Completeness gate.**
   - A template that lists a source in `requires` runs only when that source's latest run in `mart.source_status` succeeded. That's the status the Sources page shows.
   - A run succeeds only when it drained every page; quota stops end `partial`. So "succeeded" means the history is complete.
   - A source whose core rows still trace back to two origins (`mart.dq_source_origin_mix`) isn't ready either, whatever its last run says. Until the production backfill replays over them, the LL2 dev-host runs succeeded on stale data.
   - While a source waits, its templates are skipped and their stored facts deleted, and the skip is logged as `facts skipped`.
   - The launch, agency and Launch Library 2 source facts require `launch-library`. Without the gate, a partial backfill made 1971 the "record year".
   - Window facts guard freshness in SQL instead: the space-weather templates also need an SWPC fetch in the last day.

## Consequences

- Adding a fact is a YAML entry plus a test expectation, with no code change. A catalog test requires a test module for every template module and at least 25 templates.
- The renderer's grammar has no plural or select, so English text avoids plurals that could be singular: queries emit counts of 2 or more. English also avoids articles that some names need: organizations and programs lead with a label, as in "SpaceX: …", and countries appear attributively, as in "United States launch sites".
- The gate is deliberately conservative. Any non-`succeeded` LL2 run hides launch facts until the next successful run.
- Curated facts with citations (`facts/curated/`) are not built yet. Every Phase 3 fact is computed.

## Amendment (Phase 4): the Home mix

- Many templates tie at score 1.0, so a page-agnostic `GET /api/v1/facts` returned only agency facts, the module with the most tied templates.
- With no `module` or entity filter, the API now interleaves modules after filtering current facts: every module's best fact first, then every module's second best, and so on, each round best first. A filtered request keeps the plain score order.
- The mix runs in the controller rather than in SQL because the list is cached by query while expiry is checked per request. Ranking in SQL would let an expired fact hold its module's first slot.
- The SQL keeps each module's best 40 facts instead of the best 200 overall. With 205 facts, a global cut dropped every space-weather fact (score 0.5) behind the many 1.0 ties before the mix could pick one. Forty per module is twice the API's largest page.
