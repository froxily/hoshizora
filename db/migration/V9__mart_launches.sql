CREATE VIEW mart.organization_key AS
SELECT o.id AS organization_id, coalesce(o.slug, 'll2-' || min(a.code), 'org-' || o.id) AS key
FROM core.organization o
LEFT JOIN core.organization_alias a ON a.organization_id = o.id AND a.namespace = 'll2.agency'
GROUP BY o.id, o.slug;

COMMENT ON VIEW mart.organization_key IS 'Stable public key per organization: the curated slug, otherwise ll2-<Launch Library 2 agency id>.';

CREATE FUNCTION mart.launch_outcome(status_id smallint) RETURNS text
LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
RETURN CASE
    WHEN status_id IN (3, 9) THEN 'success'
    WHEN status_id = 4 THEN 'failure'
    WHEN status_id = 7 THEN 'partial_failure'
    WHEN status_id = 6 THEN 'in_flight'
    WHEN status_id IN (1, 2, 5, 8) THEN 'upcoming'
    ELSE 'unknown'
END;

COMMENT ON FUNCTION mart.launch_outcome(smallint) IS 'Outcome from the Launch Library 2 status id: 3 Success and 9 Payload Deployed are successes; 1 Go, 2 TBD, 5 Hold and 8 TBC are upcoming; 6 is in flight.';

CREATE VIEW mart.launch_classified AS
SELECT
    l.ll2_id AS launch_id,
    l.net,
    extract(year FROM l.net AT TIME ZONE 'UTC')::smallint AS year,
    l.status_id,
    mart.launch_outcome(l.status_id) AS outcome,
    mart.launch_outcome(l.status_id) IN ('success', 'failure', 'partial_failure', 'in_flight') AS attempted,
    l.provider_org_id,
    l.vehicle_ll2_id,
    v.family AS vehicle_family,
    l.pad_ll2_id,
    p.country_code AS site_country
FROM core.launch l
LEFT JOIN core.launch_vehicle v ON v.ll2_id = l.vehicle_ll2_id
LEFT JOIN core.launch_pad p ON p.ll2_id = l.pad_ll2_id;

COMMENT ON VIEW mart.launch_classified IS 'Each launch with its outcome, whether it was attempted, and its grouping keys.';

CREATE VIEW mart.launch_listing AS
SELECT
    l.ll2_id AS launch_id,
    l.name,
    l.net,
    l.net_precision,
    mart.launch_outcome(l.status_id) AS outcome,
    l.launch_designator,
    l.window_start,
    l.window_end,
    l.failure_reason,
    l.provider_org_id,
    k.key AS provider_key,
    o.name_en AS provider_name_en,
    o.name_ja AS provider_name_ja,
    o.type AS provider_type,
    v.ll2_id AS vehicle_id,
    coalesce(v.full_name, v.name) AS vehicle_name,
    v.name_ja AS vehicle_name_ja,
    v.family AS vehicle_family,
    v.variant AS vehicle_variant,
    p.ll2_id AS pad_id,
    p.name AS pad_name,
    p.location_name AS pad_location,
    p.country_code AS pad_country_code,
    pc.name_en AS pad_country_en,
    pc.name_ja AS pad_country_ja,
    p.latitude AS pad_latitude,
    p.longitude AS pad_longitude,
    m.ll2_id AS mission_id,
    m.name AS mission_name,
    m.name_ja AS mission_name_ja,
    m.type AS mission_type,
    m.orbit AS mission_orbit,
    m.orbit_name AS mission_orbit_name,
    m.description AS mission_description
FROM core.launch l
LEFT JOIN core.organization o ON o.id = l.provider_org_id
LEFT JOIN mart.organization_key k ON k.organization_id = l.provider_org_id
LEFT JOIN core.launch_vehicle v ON v.ll2_id = l.vehicle_ll2_id
LEFT JOIN core.launch_pad p ON p.ll2_id = l.pad_ll2_id
LEFT JOIN core.country pc ON pc.code = p.country_code
LEFT JOIN core.mission m ON m.ll2_id = l.mission_ll2_id;

COMMENT ON VIEW mart.launch_listing IS 'One row per launch with its provider, vehicle, pad and mission, in English and Japanese where known: the shape the read API and facts share.';

CREATE VIEW mart.launch_group AS
SELECT 'all' AS group_kind, 'all' AS group_key, c.launch_id
FROM mart.launch_classified c
UNION ALL
SELECT 'program', m.program_slug, c.launch_id
FROM mart.launch_classified c
JOIN core.program_member m ON m.organization_id = c.provider_org_id
UNION ALL
SELECT 'provider', k.key, c.launch_id
FROM mart.launch_classified c
JOIN mart.organization_key k ON k.organization_id = c.provider_org_id
UNION ALL
SELECT 'vehicle_family', c.vehicle_family, c.launch_id
FROM mart.launch_classified c
WHERE c.vehicle_family IS NOT NULL AND c.vehicle_family <> ''
UNION ALL
SELECT 'site_country', c.site_country, c.launch_id
FROM mart.launch_classified c
WHERE c.site_country IS NOT NULL;

COMMENT ON VIEW mart.launch_group IS 'Every grouping a launch counts toward: all launches, the national program of its provider, the provider itself, the vehicle family and the country of the launch site.';

CREATE MATERIALIZED VIEW mart.launch_cadence_yearly AS
SELECT
    g.group_kind,
    g.group_key,
    c.year,
    count(*) FILTER (WHERE c.attempted) AS attempts,
    count(*) FILTER (WHERE c.outcome = 'success') AS successes,
    count(*) FILTER (WHERE c.outcome = 'failure') AS failures,
    count(*) FILTER (WHERE c.outcome = 'partial_failure') AS partial_failures,
    count(*) FILTER (WHERE c.outcome = 'upcoming') AS scheduled,
    'launch-library'::text AS source
FROM mart.launch_classified c
JOIN mart.launch_group g USING (launch_id)
WHERE c.year IS NOT NULL
GROUP BY g.group_kind, g.group_key, c.year;

CREATE UNIQUE INDEX launch_cadence_yearly_key ON mart.launch_cadence_yearly (group_kind, group_key, year);

COMMENT ON MATERIALIZED VIEW mart.launch_cadence_yearly IS 'Launch attempts and outcomes per UTC year for every launch grouping; scheduled counts launches not yet flown.';

CREATE MATERIALIZED VIEW mart.launch_success_rolling AS
WITH attempt AS (
    SELECT g.group_kind, g.group_key, c.launch_id, c.net, c.year, c.outcome = 'success' AS succeeded
    FROM mart.launch_classified c
    JOIN mart.launch_group g USING (launch_id)
    WHERE c.outcome IN ('success', 'failure', 'partial_failure')
),
counted AS (
    SELECT
        a.*,
        row_number() OVER history AS attempt_no,
        count(*) FILTER (WHERE a.succeeded) OVER history AS successes_to_date,
        count(*) FILTER (WHERE NOT a.succeeded) OVER history AS failures_to_date,
        count(*) OVER last_twenty AS window_attempts,
        count(*) FILTER (WHERE a.succeeded) OVER last_twenty AS window_successes
    FROM attempt a
    WINDOW
        history AS (PARTITION BY a.group_kind, a.group_key ORDER BY a.net, a.launch_id ROWS UNBOUNDED PRECEDING),
        last_twenty AS (PARTITION BY a.group_kind, a.group_key ORDER BY a.net, a.launch_id ROWS 19 PRECEDING)
)
SELECT
    c.group_kind,
    c.group_key,
    c.launch_id,
    c.net,
    c.year,
    c.attempt_no,
    c.succeeded,
    c.successes_to_date,
    c.window_attempts,
    c.window_successes,
    CASE
        WHEN c.succeeded THEN row_number() OVER (
            PARTITION BY c.group_kind, c.group_key, c.failures_to_date ORDER BY c.net, c.launch_id
        ) - CASE WHEN c.failures_to_date > 0 THEN 1 ELSE 0 END
        ELSE 0
    END AS success_streak,
    'launch-library'::text AS source
FROM counted c;

CREATE UNIQUE INDEX launch_success_rolling_key ON mart.launch_success_rolling (group_kind, group_key, attempt_no);
CREATE INDEX launch_success_rolling_launch ON mart.launch_success_rolling (launch_id);

COMMENT ON MATERIALIZED VIEW mart.launch_success_rolling IS 'Every completed launch attempt per grouping in flight order, with the success rate to date, over the last 20 attempts, and the current run of consecutive successes. Partial failures count as failures.';

CREATE MATERIALIZED VIEW mart.launch_pad_activity AS
WITH yearly AS (
    SELECT c.pad_ll2_id, c.year, count(*) AS attempts
    FROM mart.launch_classified c
    WHERE c.attempted
    GROUP BY c.pad_ll2_id, c.year
),
busiest AS (
    SELECT DISTINCT ON (y.pad_ll2_id) y.pad_ll2_id, y.year, y.attempts
    FROM yearly y
    ORDER BY y.pad_ll2_id, y.attempts DESC, y.year DESC
)
SELECT
    p.ll2_id AS pad_id,
    count(*) FILTER (WHERE c.attempted) AS attempts,
    count(*) FILTER (WHERE c.outcome = 'success') AS successes,
    count(*) FILTER (WHERE c.outcome IN ('failure', 'partial_failure')) AS failures,
    count(*) FILTER (WHERE c.outcome = 'upcoming') AS scheduled,
    min(c.net) FILTER (WHERE c.attempted) AS first_launch_at,
    max(c.net) FILTER (WHERE c.attempted) AS last_launch_at,
    b.year AS busiest_year,
    b.attempts AS busiest_year_attempts,
    'launch-library'::text AS source
FROM core.launch_pad p
JOIN mart.launch_classified c ON c.pad_ll2_id = p.ll2_id
LEFT JOIN busiest b ON b.pad_ll2_id = p.ll2_id
GROUP BY p.ll2_id, b.year, b.attempts;

CREATE UNIQUE INDEX launch_pad_activity_key ON mart.launch_pad_activity (pad_id);

COMMENT ON MATERIALIZED VIEW mart.launch_pad_activity IS 'Launch attempts, outcomes and the busiest UTC year per launch pad.';

CREATE MATERIALIZED VIEW mart.organization_launch_summary AS
SELECT
    c.provider_org_id AS organization_id,
    count(*) FILTER (WHERE c.attempted) AS attempts,
    count(*) FILTER (WHERE c.outcome = 'success') AS successes,
    count(*) FILTER (WHERE c.outcome = 'failure') AS failures,
    count(*) FILTER (WHERE c.outcome = 'partial_failure') AS partial_failures,
    count(*) FILTER (WHERE c.outcome = 'upcoming') AS scheduled,
    min(c.net) FILTER (WHERE c.attempted) AS first_launch_at,
    max(c.net) FILTER (WHERE c.attempted) AS last_launch_at,
    'launch-library'::text AS source
FROM mart.launch_classified c
WHERE c.provider_org_id IS NOT NULL
GROUP BY c.provider_org_id;

CREATE UNIQUE INDEX organization_launch_summary_key ON mart.organization_launch_summary (organization_id);

COMMENT ON MATERIALIZED VIEW mart.organization_launch_summary IS 'Launches each organization provided, by outcome, with its first and latest attempt.';
