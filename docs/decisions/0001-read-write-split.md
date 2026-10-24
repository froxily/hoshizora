# ADR 0001: Ingestion writes, the API only reads

- Status: accepted
- Date: 2026-10-16

## Context

Hoshizora pulls data from many external sources, normalizes it and serves analytics to the web app. Two very different workloads touch the same PostgreSQL database:

- **Ingestion** (Python) fetches source payloads on a schedule, lands them, upserts normalized rows, refreshes marts and regenerates facts.
- **The API** (Spring Boot) answers read-only queries from the browser at request time.

If both could write, a bug or an injection in the internet-facing API could corrupt data that took hours of rate-limited fetching to build. Schema changes could also come from two places and drift.

## Decision

1. `ingest` is the only writer. `api` is strictly read-only.
2. The schema is owned by Flyway migrations in `db/migration/`. Neither runtime runs DDL. Python never creates tables, and the API has no Flyway dependency at runtime (Flyway appears only in its tests).
3. The split is enforced by the database, not by convention. The baseline migration (`V1__baseline.sql`) creates two group roles, and neither has `CREATE` on any schema:

   | Role | `raw` | `core`, `mart`, `facts` |
   |---|---|---|
   | `hoshizora_writer` | `SELECT`, `INSERT` (append-only) | `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `MAINTAIN` |
   | `hoshizora_reader` | no access | `SELECT` |

   - The grants are default privileges, so every table a later migration creates inherits them.
   - `MAINTAIN` (PostgreSQL 17+) lets ingestion run `REFRESH MATERIALIZED VIEW` without owning the view.
   - `raw` stays append-only even for the writer, which keeps every transform replayable from the raw payloads.
4. Login roles are environment configuration, not schema:
   - **Local and CI:** a repeatable migration in `infra/flyway/dev/` creates `hoshizora_ingest` (member of the writer role) and `hoshizora_api` (member of the reader role). It takes its passwords from Flyway placeholders.
   - **Production:** the operator creates the two logins from secrets and grants the group roles, as in the runbook below.
   - No password ever appears in a migration.
5. The API also sets its Hikari pool to read-only, a second guard on top of the privileges.

## Consequences

- An API compromise can't modify data. Even a bug in ingestion can't rewrite raw payloads or change the schema.
- Every schema change is a reviewed, versioned migration. Tests apply the same migrations to a Testcontainers PostgreSQL (`BaselineMigrationTest` checks the privilege matrix).
- Adding a table needs no grant boilerplate. The default privileges cover it.
- If the API ever needs `raw` (for example to show fetch times in lineage), a migration must grant it explicitly. That's deliberate.
- Some managed PostgreSQL providers restrict `CREATE ROLE`. The migration owner needs `CREATEROLE` the first time V1 runs.

## Production runbook

As the migration owner, after `flyway migrate`:

```sql
CREATE ROLE hoshizora_ingest LOGIN PASSWORD '<from secret store>' IN ROLE hoshizora_writer;
CREATE ROLE hoshizora_api LOGIN PASSWORD '<from secret store>' IN ROLE hoshizora_reader;
```
