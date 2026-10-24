# ADR 0010: Booster reuse from Launch Library 2 landings

Status: accepted (Phase 5, 2026-10-19).

## Context

- Phase 4 deferred the Launches reusability stats because core held no stage or landing data.
- Launch Library 2 has the data in three places:
  - Detailed launches embed `rocket.launcher_stage[]` with each stage's landing, but a detailed launch is about 45 KB. Even only the reusable-rocket launches (about 700) would land 31 MB, and every incremental update re-lands whole pages.
  - `/launchers/` lists each tracked stage with its flights, landings, first and latest launch and fastest turnaround. There are about 200 stages, about 0.1 MB a page.
  - `/landings/` lists every landing record: 1,787 on 2026-10-19. Each one carries `attempt`, `success`, the type and location, and the first stage's `launcher_flight_number`, `previous_flight_date` and `turn_around_time`. Landings have **no launch link and no date**.
- `/landings/` has no `last_updated` filter, so the launch watermark (ADR 0002) does not apply.
- Raw retention (ADR 0009) only works when a request repeats with the same params.

## Decision

1. **Sources.**
   - **Launchers:** a daily sweep of `/launchers/?mode=detailed&ordering=id`, the same code path as the weekly agency sweep.
   - **Landings:** `/landings/?mode=list&ordering=-id`. List mode is 30% smaller than normal mode and keeps every field we use.
   - Only first-stage landings are stored. Spacecraft and payload landings are skipped.
2. **Walking landings.**
   - **Until the backfill is complete,** the walk resumes at the highest offset already fetched and runs to the end. A page whose `next` is null marks it complete.
   - **After that,** each run walks from offset 0 until a page holds only landings that were already settled before the run. Settled means a known outcome, or no landing attempt (an expended stage). Newly scheduled landings are always unsettled, so that is usually two requests per run.
3. **Both endpoints are in `raw.retention_policy`** (48 hours). Their params repeat (mode, ordering, offset), so superseded bodies are pruned. Each of the newest landing pages changes whenever a landing is added.
4. **The launch time is derived, in `mart.landing_flight`:**
   - Normally it is `previous_flight_date + turn_around_time`.
   - For a stage's first flight, it is the stage's `first_launch_date` from the launcher sweep.
   - The match is the launch within one minute of that time.
   - Core keeps only what LL2 says. The derivation lives in the mart, so it is visible and replaceable.
5. **Misses are reported.** `mart.dq_unmatched_landing` lists settled landings without a match.
6. **Marts:**
   - `mart.reusability_yearly` uses `mart.launch_group`, so the same program, provider, vehicle-family, country and all groupings work.
   - `mart.booster_ranking` reports LL2's own per-stage counts.

## Consequences

- **Matching:** on 2026-10-19, all 845 settled first-stage landings matched a launch, and none were missed. The 27 unmatched landings are scheduled.
- **Storage:** about 1 MB in Postgres for all landing pages (TOAST-compressed), plus a few hundred KB of launcher snapshots.
- **Quota:** steady-state cost is about 2 landing requests per run and 2 launcher requests a day, within LL2's 15 an hour.
- **Missed corrections:** a correction to an old landing outcome deep in history is not refetched by the incremental walk. A replay or a fresh backfill picks it up.
- **New Shepard:** reflights in 2015–2016 come from New Shepard, which LL2 lists as suborbital launches. They count, as in the cadence marts.
- **Replay:** foreign-origin pruning (ADR 0002 amendment) does not cover `core.landing` and `core.launcher` yet. A dev-host landing would stay until it is deleted by hand.
