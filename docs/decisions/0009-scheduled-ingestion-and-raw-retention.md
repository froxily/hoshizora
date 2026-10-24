# ADR 0009: Scheduled ingestion and body-only raw retention

Status: accepted (Phase 7, 2026-10-19). Amends [ADR 0002](0002-resumable-ingestion.md) and [ADR 0007](0007-aurora-storage.md).

## Context

- Until Phase 7, the preview database on Neon held a snapshot copied from a local machine. Space-weather facts expire a day after the last SWPC run, so the snapshot went stale quickly.
- Scheduling needs a host that is free, keeps secrets out of git, and does not need a new image or cloud identity.
- Scheduled runs land far more raw data than occasional local runs; hourly is the worst case. Measured payload sizes: CelesTrak GP 1.6 MB every 2 hours, SATCAT 2.5 MB every 12 hours, the SWPC real-time solar wind files 0.42 MB every 6 hours, the OVATION grid 0.46 MB an hour. That is about 37 MB a day against Neon's 1 GB free plan.
- ADR 0007 pruned raw by deleting whole payload rows, and `core.source_record` cascaded with them. "How we know this" then lost the request behind a number.
- CelesTrak's usage policy asks clients to stop on errors. A scheduled job that simply runs again next hour would keep calling after an error.
- GitHub-hosted runners share IP addresses, and Launch Library 2's free tier is 15 requests an hour per IP. Other users' requests count against the same quota.

## Decision

1. **GitHub Actions runs `hoshizora ingest-all` on a schedule** (`.github/workflows/ingest.yml`, minute 17): every 6 hours while the repository is private, to stay well inside the free Actions minutes, and hourly once it is public. Each run lands raw data, upserts core, refreshes marts and regenerates facts when rows changed, and the refetch intervals in each adapter decide what is actually requested. Its only secret is `PREVIEW_INGEST_DATABASE_URL` for the `hoshizora_ingest` login: a repository secret while private (GitHub Free has no environments for private repositories), a main-only `preview` environment secret once public. A Container Apps job was rejected: it would need an ingest image, an Azure identity and secrets in two places.
2. **Bounded waits.** `--max-wait 120` ends a source's run as `partial` instead of sleeping out a quota hour or a long `Retry-After`. The next run resumes from the raw watermark (ADR 0002), so nothing is lost.
3. **Held for review.** A source whose last finished run is `needs_review` is not requested again. `ingest` and `ingest-all` report it with exit code 3 until someone checks the cause and runs once with `--reviewed`. The workflow exposes this as a `reviewed` input.
4. **Retention prunes bodies, never rows.**
   - `raw.payload.body` becomes NULL and `pruned_at` is set. The row keeps its endpoint, params, `fetched_at` and `content_hash`, so `core.source_record`, `mart.record_lineage` and the API's lineage still resolve.
   - A body is pruned only when its endpoint is listed in `raw.retention_policy`, it is older than the policy's window, and the latest fetch of the same endpoint and params returned a different payload. The current body for each request always stays. When a source returns content whose body was already pruned, `raw.restore_body` puts the body back and the payload is applied again. That also fixes an older gap: content that went A → B → A used to be skipped as a duplicate and left core at B.
   - Policies (48 hours): CelesTrak GP and SATCAT, the SWPC real-time magnetic field and plasma files, OVATION, and JPL Sentry. Launch Library 2 pages are incremental and stay forever. JPL close-approach windows change their params daily, so each is the latest fetch of its own request and none is listed.
   - The foreign keys from `raw.fetch` and `core.source_record` to `raw.payload` are plain `NO ACTION` again. A delete of a referenced payload fails, even for the owner.
   - Each run applies retention for its own source once it has succeeded or ended as partial. When anything was pruned, a plain `VACUUM raw.payload` follows on the autocommit connection, so the freed TOAST space is reused without a lock-heavy `VACUUM FULL`. The writer has `MAINTAIN` on `raw.payload` only, for this.
5. **Replay skips pruned bodies.** It rebuilds from the bodies that remain and never deletes core rows, so core history outlives the raw window.

## Consequences

- Raw stays near 100 MB on the preview: two days of GP, SATCAT, solar wind and OVATION, plus every LL2 page and the JPL windows.
- Close-approach rolling windows grow by about 0.45 MB a day, about 14 MB a month. Pruning them needs a series key recorded at landing time, so a later slice can recognise the decade backfill windows. That is left for when it matters.
- Core history of the solar wind and GP elements now outlives its raw evidence. Replay covers the last 48 hours of those products, and their lineage rows still name the request that produced each value.
- The scheduled job depends on the Neon schema being current. `just preview-migrate` must run before a migration is merged, or the job fails loudly.
- GitHub disables scheduled workflows in public repositories after 60 days without repository activity (see `docs/deploy.md`).
