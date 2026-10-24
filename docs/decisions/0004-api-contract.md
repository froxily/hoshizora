# ADR 0004: A bilingual, cacheable, spec-first read API

- Status: accepted
- Date: 2026-10-16

## Context

The web app, and later anyone exploring the data, reads everything through `/api/v1`. Four forces shape the contract:

- **Two languages, uneven data.** Every user-facing string must exist in English and Japanese. Curated names have both, but most vehicle and mission names, all pad names and some source prose (Launch Library 2 mission descriptions and failure reasons) exist only in English. Inventing translations would break the project's honesty rule.
- **Slow-moving data.** Sources update hourly at best (SWPC, Launch Library 2) and every 12 hours at worst (JPL, CelesTrak). Most requests can be served from memory and revalidated cheaply.
- **Every number needs a source.** A chart value or a fact must lead back to the records and source responses behind it.
- **Two clients that must not drift.** The TypeScript client has to stay in step with the Java API.

## Decision

1. **Locale.** `Accept-Language` resolves to `en` or `ja`; English is the default and unsupported languages fall back to it. Every response carries `Content-Language` and `Vary: Accept-Language`.
2. **Localized fields say what language they are in.**
   - Wherever a value can fall back to English, the response pairs `name` with `name_lang` (and `description` with `description_lang`, `failure_reason` with `failure_reason_lang`, `label` with `label_lang`). The UI uses it for the `lang` attribute and for labels such as 原文（英語）.
   - Fields that always exist in both languages, such as source credits and country names, carry no `*_lang`; `Content-Language` covers them.
   - Closed vocabularies (launch status, organization type, mission type, orbit, object and orbit state, NOAA G and R scales, Torino category, run status, freshness) are terms: `{code, name, name_lang}`. Their labels live in `api/src/main/resources/i18n/messages{,_ja}.properties`, which a parity test keeps in step. An LL2 value with no curated label keeps its source label with `name_lang: "en"` instead of failing.
3. **JSON shape.**
   - snake_case, null fields omitted, ISO-8601 UTC instants, units in field names (`dist_km`, `v_rel_kms`, `peak_flux_wm2`).
   - JPL's TDB times stay TDB (`approach_tdb`, no offset) beside a derived `approach_utc`.
   - Field names avoid a digit or a second capital right after a letter (`flares_last_day`, not `flares24h`), because the snake_case strategy does not split them.
   - Lists use `{items, page, size, total_items, total_pages}` with a 1-based `page` and `size` capped at 100. Time series and rankings are unpaginated, with a bounded range or `limit`.
4. **Errors are RFC 9457 Problem Details**, localized through Spring's `problemDetail.*` message codes, with a `code` (`invalid_parameter`, `not_found`, …) and, for 400s, `errors[]` naming each parameter. A catch-all returns a generic 500 and logs the cause; SQL and stack traces never leave the server.
5. **Caching.**
   - Each resource has its own Caffeine cache, with a TTL (`hoshizora.cache.ttl`) matched to its source's cadence: 5 minutes for `meta/sources`, 1 hour for Launch Library 2, SWPC, facts and the overview, and 12 hours for JPL and CelesTrak.
   - Caches hold locale-neutral rows; localization happens after the cache, so one entry serves both languages.
   - Responses send `Cache-Control: public, max-age=<ttl>`. `ShallowEtagHeaderFilter` adds an ETag from the body hash and answers `If-None-Match` with 304. Since Phase 4 the ETag is weak (`W/"…"`): JSON is gzip-compressed above 2 KB, and a strong validator would have to differ between the gzip and identity encodings. Tomcat refuses to compress responses that carry a strong ETag.
   - Endpoints that depend on the clock round "now" to the hour so their cache keys stay stable.
6. **Lineage in the contract.** Detail routes return `lineage[]` (source, request URL, fetched_at, content hash). Every statistic carries `records_url`, an API query that returns exactly the records it counts. Fact references resolve to API routes and to lineage. See ADR 0005 for the data side.
7. **Spec first, enforced by tests.**
   - springdoc generates the spec, committed as `api/openapi.yaml`. A snapshot test fails on drift, and `just api-spec` rewrites the spec and regenerates `web/src/api/schema.d.ts` (openapi-typescript, checked by `pnpm api:check` in CI).
   - A completeness test requires a summary, a description, documented parameters, a real example and the 304/400/500 (and 404) responses on every operation. Examples are seeded responses, and a test validates each against its schema.
   - Every endpoint test validates its responses against the committed spec with the Atlassian OpenAPI validator.
   - Record components are required unless `@Nullable`, so the generated TypeScript types are exact.
8. **The read-only rule is tested, not assumed.** API tests connect as a login in `hoshizora_reader` against one seeded Testcontainers database built from real rows, so a write or a `raw` read would fail the suite. A fixed clock makes time-dependent routes deterministic.

## Consequences

- The UI never guesses a language: untranslated names are visible as such, and closing those gaps is ordinary curation work tracked by `hoshizora dq`.
- Japanese is not a translation layer. Adding a vocabulary value means adding both labels, or the parity test fails.
- Clients see changes no later than one TTL after ingestion, and repeat visits mostly cost a 304.
- The spec, the TypeScript types and the server can't drift silently: any change to a record shows up as a spec diff in review.
- The API answers only what the marts and core can back with lineage. New routes need SQL first, which is deliberate.
