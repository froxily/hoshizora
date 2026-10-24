CREATE VIEW mart.space_object_classified AS
SELECT
    s.norad_id,
    s.owner_code,
    CASE s.object_type
        WHEN 'PAY' THEN 'payload'
        WHEN 'R/B' THEN 'rocket_body'
        WHEN 'DEB' THEN 'debris'
        ELSE 'unknown'
    END AS object_type,
    CASE
        WHEN s.decay_date IS NOT NULL THEN 'decayed'
        WHEN s.orbit_center = 'EA' OR s.orbit_center ~ '^[0-9]+$' THEN 'earth_orbit'
        ELSE 'beyond_earth'
    END AS orbit_state
FROM core.space_object s;

COMMENT ON VIEW mart.space_object_classified IS 'Each catalogued object as payload, rocket body, debris or unknown, and as in Earth orbit (centred on Earth or docked to another object), beyond Earth, or decayed.';

CREATE MATERIALIZED VIEW mart.objects_in_orbit_by_owner AS
SELECT o.owner_code, o.object_type, o.orbit_state, count(*) AS objects, 'celestrak'::text AS source
FROM mart.space_object_classified o
GROUP BY o.owner_code, o.object_type, o.orbit_state;

CREATE UNIQUE INDEX objects_in_orbit_by_owner_key ON mart.objects_in_orbit_by_owner (owner_code, object_type, orbit_state);

COMMENT ON MATERIALIZED VIEW mart.objects_in_orbit_by_owner IS 'Catalogued objects per CelesTrak SATCAT owner code, object type and orbit state.';

CREATE MATERIALIZED VIEW mart.objects_in_orbit_by_country AS
WITH owner_countries AS (
    SELECT a.code, count(*) AS countries
    FROM core.country_alias a
    WHERE a.namespace = 'celestrak.owner'
    GROUP BY a.code
)
SELECT
    a.country_code,
    o.object_type,
    o.orbit_state,
    count(*) AS objects,
    count(*) FILTER (WHERE oc.countries > 1) AS shared_objects,
    'celestrak'::text AS source
FROM mart.space_object_classified o
JOIN core.country_alias a ON a.namespace = 'celestrak.owner' AND a.code = o.owner_code
JOIN owner_countries oc ON oc.code = o.owner_code
GROUP BY a.country_code, o.object_type, o.orbit_state;

CREATE UNIQUE INDEX objects_in_orbit_by_country_key ON mart.objects_in_orbit_by_country (country_code, object_type, orbit_state);

COMMENT ON MATERIALIZED VIEW mart.objects_in_orbit_by_country IS 'Catalogued objects per country through the SATCAT owner code. An object of a joint owner such as CHBZ counts for each member country and also in shared_objects. Organization owners such as ESA have no country and appear only by owner.';
