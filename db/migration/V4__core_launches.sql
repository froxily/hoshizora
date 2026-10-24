CREATE TABLE core.launch_vehicle (
    ll2_id integer PRIMARY KEY,
    name text NOT NULL,
    full_name text,
    variant text,
    family text,
    name_ja text,
    name_ja_source text,
    CHECK (name_ja IS NULL OR name_ja_source IS NOT NULL)
);

COMMENT ON TABLE core.launch_vehicle IS 'Launcher configurations from Launch Library 2, e.g. Falcon 9 Block 5.';

CREATE TABLE core.launch_pad (
    ll2_id integer PRIMARY KEY,
    name text NOT NULL,
    location_name text,
    country_code char(2) REFERENCES core.country (code),
    latitude double precision,
    longitude double precision
);

CREATE TABLE core.mission (
    ll2_id integer PRIMARY KEY,
    name text NOT NULL,
    name_ja text,
    name_ja_source text,
    type text,
    orbit text,
    orbit_name text,
    description text,
    CHECK (name_ja IS NULL OR name_ja_source IS NOT NULL)
);

CREATE TABLE core.mission_agency (
    mission_ll2_id integer NOT NULL REFERENCES core.mission (ll2_id),
    organization_id bigint NOT NULL REFERENCES core.organization (id),
    PRIMARY KEY (mission_ll2_id, organization_id)
);

COMMENT ON TABLE core.mission_agency IS 'Customers and partners of a mission, e.g. NASA on a SpaceX-launched mission. Distinct from the launch provider.';

CREATE TABLE core.launch (
    ll2_id uuid PRIMARY KEY,
    name text NOT NULL,
    slug text,
    launch_designator text,
    net timestamptz,
    net_precision text,
    window_start timestamptz,
    window_end timestamptz,
    status_id smallint NOT NULL,
    status text NOT NULL,
    status_name text NOT NULL,
    failure_reason text,
    provider_org_id bigint REFERENCES core.organization (id),
    vehicle_ll2_id integer REFERENCES core.launch_vehicle (ll2_id),
    pad_ll2_id integer REFERENCES core.launch_pad (ll2_id),
    mission_ll2_id integer REFERENCES core.mission (ll2_id),
    source_updated_at timestamptz NOT NULL
);

CREATE INDEX launch_net_idx ON core.launch (net);
CREATE INDEX launch_provider_idx ON core.launch (provider_org_id);
CREATE INDEX launch_designator_idx ON core.launch (launch_designator);

COMMENT ON TABLE core.launch IS 'Launches from Launch Library 2. provider_org_id is the launch service provider; launch_designator is the COSPAR id (YYYY-NNN) that joins to catalogued objects.';
COMMENT ON COLUMN core.launch.source_updated_at IS 'LL2 last_updated. Upserts only move forward, so a stale payload never overwrites newer data.';

CREATE OR REPLACE VIEW mart.dq_missing_name_ja AS
SELECT 'organization' AS entity, o.id::text AS key, o.name_en, count(l.ll2_id) AS relevance
FROM core.organization o
LEFT JOIN core.launch l ON l.provider_org_id = o.id
WHERE o.name_ja IS NULL
GROUP BY o.id, o.name_en
UNION ALL
SELECT 'launch_vehicle', v.ll2_id::text, coalesce(v.full_name, v.name), count(l.ll2_id)
FROM core.launch_vehicle v
LEFT JOIN core.launch l ON l.vehicle_ll2_id = v.ll2_id
WHERE v.name_ja IS NULL
GROUP BY v.ll2_id, v.full_name, v.name
UNION ALL
SELECT 'mission', m.ll2_id::text, m.name, 0::bigint
FROM core.mission m
WHERE m.name_ja IS NULL;

CREATE OR REPLACE VIEW mart.dq_untyped_organization AS
SELECT o.id, o.name_en, o.source_type
FROM core.organization o
WHERE o.type IS NULL
  AND NOT EXISTS (
      SELECT FROM core.external_code e
      WHERE e.namespace = 'll2.agency_type' AND e.code = o.source_type AND e.kind = 'unknown'
  );
