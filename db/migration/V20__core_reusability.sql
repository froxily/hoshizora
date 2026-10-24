CREATE TABLE core.launcher (
    ll2_id integer PRIMARY KEY,
    serial_number text,
    is_placeholder boolean NOT NULL,
    flight_proven boolean,
    status text,
    vehicle_ll2_id integer,
    flights integer CHECK (flights >= 0),
    attempted_landings integer CHECK (attempted_landings >= 0),
    successful_landings integer CHECK (successful_landings >= 0),
    first_launch_at timestamptz,
    last_launch_at timestamptz,
    fastest_turnaround interval
);

COMMENT ON TABLE core.launcher IS 'Individual rocket stages tracked by Launch Library 2, e.g. Falcon 9 booster B1067. vehicle_ll2_id is the launcher configuration (the same id space as core.launch_vehicle) and is only known from the launcher sweep; landings add new stages with their serial alone.';
COMMENT ON COLUMN core.launcher.is_placeholder IS 'LL2 placeholder stages such as "Unknown F9" stand in for boosters whose serial was never published.';

CREATE TABLE core.landing (
    ll2_id integer PRIMARY KEY,
    launcher_ll2_id integer NOT NULL REFERENCES core.launcher (ll2_id),
    stage_type text,
    launcher_flight_number integer CHECK (launcher_flight_number >= 1),
    reused boolean,
    attempt boolean NOT NULL,
    success boolean,
    previous_flight_at timestamptz,
    turnaround interval,
    type_abbrev text,
    type_name text,
    location_name text,
    location_abbrev text,
    downrange_km double precision
);

CREATE INDEX landing_launcher_idx ON core.landing (launcher_ll2_id);

COMMENT ON TABLE core.landing IS 'First-stage landing records from Launch Library 2: the stage, its flight number, whether a landing was attempted and how it went. Spacecraft and payload landings are not kept. attempt = false is an expended stage.';
COMMENT ON COLUMN core.landing.turnaround IS 'Time since the same stage last flew, as LL2 reports it. previous_flight_at + turnaround is this flight''s launch time (see mart.landing_flight).';

INSERT INTO raw.retention_policy (source, endpoint, keep, reason)
VALUES
    (
        'launch-library',
        'https://ll.thespacedevs.com/2.3.0/landings/',
        interval '48 hours',
        'Landing pages ordered newest first, about 0.35 MB each. The newest two are fetched every run and shift as landings are added; core keeps every landing.'
    ),
    (
        'launch-library',
        'https://ll.thespacedevs.com/2.3.0/launchers/',
        interval '48 hours',
        'A daily sweep of every tracked stage, about 0.12 MB a page. Core keeps the latest state per stage.'
    );

CREATE VIEW mart.landing_flight AS
WITH dated AS (
    SELECT
        d.*,
        s.serial_number,
        s.is_placeholder,
        s.vehicle_ll2_id AS stage_vehicle_ll2_id,
        CASE
            WHEN d.previous_flight_at IS NOT NULL AND d.turnaround IS NOT NULL
                THEN d.previous_flight_at + d.turnaround
            WHEN d.launcher_flight_number = 1 THEN s.first_launch_at
        END AS flight_at
    FROM core.landing d
    JOIN core.launcher s ON s.ll2_id = d.launcher_ll2_id
)
SELECT
    d.ll2_id AS landing_id,
    d.launcher_ll2_id AS launcher_id,
    d.serial_number,
    d.is_placeholder,
    d.stage_type,
    d.launcher_flight_number,
    d.launcher_flight_number > 1 AS reflight,
    d.attempt,
    d.success,
    d.attempt AND d.success IS NOT NULL AS landing_settled,
    d.turnaround,
    d.type_abbrev,
    d.location_name,
    d.location_abbrev,
    d.flight_at,
    m.launch_id,
    m.year,
    m.outcome AS launch_outcome,
    m.outcome IN ('success', 'failure', 'partial_failure') AS flown
FROM dated d
LEFT JOIN LATERAL (
    SELECT c.launch_id, c.year, c.outcome
    FROM mart.launch_classified c
    WHERE c.net BETWEEN d.flight_at - interval '1 minute' AND d.flight_at + interval '1 minute'
    ORDER BY abs(extract(epoch FROM c.net - d.flight_at)), c.launch_id
    LIMIT 1
) m ON true;

COMMENT ON VIEW mart.landing_flight IS 'Each first-stage landing record with the launch it flew on. LL2 landings carry no launch link, so the launch time is derived: the previous flight plus the turnaround, or the stage''s first launch for its first flight. The launch within a minute of that time is the match; mart.dq_unmatched_landing lists the misses.';

CREATE MATERIALIZED VIEW mart.reusability_yearly AS
SELECT
    g.group_kind,
    g.group_key,
    f.year,
    count(DISTINCT f.launch_id) AS launches,
    count(DISTINCT f.launch_id) FILTER (WHERE f.reflight) AS launches_reflown,
    count(*) AS stage_flights,
    count(*) FILTER (WHERE f.reflight) AS stage_reflights,
    count(*) FILTER (WHERE f.landing_settled) AS landing_attempts,
    count(*) FILTER (WHERE f.landing_settled AND f.success) AS landings,
    'launch-library'::text AS source
FROM mart.landing_flight f
JOIN mart.launch_group g USING (launch_id)
WHERE f.flown
GROUP BY g.group_kind, g.group_key, f.year;

CREATE UNIQUE INDEX reusability_yearly_key ON mart.reusability_yearly (group_kind, group_key, year);

COMMENT ON MATERIALIZED VIEW mart.reusability_yearly IS 'First-stage reuse per UTC year for every launch grouping: launches with a recorded stage, those flying a stage that had flown before, stage flights, and landing attempts and successes. Only launches that have flown count.';

CREATE MATERIALIZED VIEW mart.booster_ranking AS
WITH latest_launch AS (
    SELECT DISTINCT ON (f.launcher_id) f.launcher_id, f.launch_id
    FROM mart.landing_flight f
    WHERE f.flown
    ORDER BY f.launcher_id, f.flight_at DESC
)
SELECT
    s.ll2_id AS launcher_id,
    s.serial_number,
    s.status,
    s.flight_proven,
    s.vehicle_ll2_id,
    coalesce(v.full_name, v.name) AS vehicle_name,
    v.name_ja AS vehicle_name_ja,
    v.family AS vehicle_family,
    c.provider_org_id,
    s.flights,
    s.attempted_landings,
    s.successful_landings,
    s.first_launch_at,
    s.last_launch_at,
    s.fastest_turnaround,
    rank() OVER (ORDER BY s.flights DESC) AS flights_rank,
    'launch-library'::text AS source
FROM core.launcher s
LEFT JOIN core.launch_vehicle v ON v.ll2_id = s.vehicle_ll2_id
LEFT JOIN latest_launch l ON l.launcher_id = s.ll2_id
LEFT JOIN mart.launch_classified c ON c.launch_id = l.launch_id
WHERE NOT s.is_placeholder AND s.flights > 0;

CREATE UNIQUE INDEX booster_ranking_key ON mart.booster_ranking (launcher_id);
CREATE INDEX booster_ranking_rank ON mart.booster_ranking (flights_rank);

COMMENT ON MATERIALIZED VIEW mart.booster_ranking IS 'Every flown, identified stage ranked by flights, with its vehicle, landings, first and latest flight, fastest turnaround and the provider of its latest launch.';

CREATE VIEW mart.dq_unmatched_landing AS
SELECT f.landing_id, f.serial_number, f.launcher_flight_number, f.flight_at
FROM mart.landing_flight f
JOIN core.landing d ON d.ll2_id = f.landing_id
WHERE f.launch_id IS NULL
  AND (d.success IS NOT NULL OR (NOT d.attempt AND f.flight_at < now()));

COMMENT ON VIEW mart.dq_unmatched_landing IS 'Settled landing records whose derived launch time matches no launch, or that have no derivable time (placeholder stages without a flight number). They are left out of the reusability marts.';
