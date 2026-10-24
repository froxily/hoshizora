CREATE TABLE core.space_object (
    norad_id integer PRIMARY KEY,
    object_id text,
    launch_designator text,
    name text NOT NULL,
    object_type text,
    ops_status text,
    owner_code text,
    launch_date date,
    launch_site text,
    decay_date date,
    period_min double precision,
    inclination_deg double precision,
    apogee_km double precision,
    perigee_km double precision,
    rcs_m2 double precision,
    data_status text,
    orbit_center text,
    orbit_type text
);

CREATE INDEX space_object_owner_idx ON core.space_object (owner_code);
CREATE INDEX space_object_launch_designator_idx ON core.space_object (launch_designator);
CREATE INDEX space_object_decay_idx ON core.space_object (decay_date);

COMMENT ON TABLE core.space_object IS 'Every catalogued object from the CelesTrak SATCAT. owner_code is a SATCAT owner code (country, joint venture or organization), not an agency.';
COMMENT ON COLUMN core.space_object.launch_designator IS 'COSPAR launch id (YYYY-NNN) derived from object_id; joins to core.launch.launch_designator.';
COMMENT ON COLUMN core.space_object.orbit_center IS 'EA for Earth, SU for the Sun, MO for the Moon; a NORAD id when docked to that object.';

CREATE TABLE core.orbit_element (
    norad_id integer PRIMARY KEY REFERENCES core.space_object (norad_id),
    epoch timestamptz NOT NULL,
    mean_motion double precision NOT NULL,
    eccentricity double precision NOT NULL,
    inclination_deg double precision NOT NULL,
    ra_of_asc_node_deg double precision NOT NULL,
    arg_of_pericenter_deg double precision NOT NULL,
    mean_anomaly_deg double precision NOT NULL,
    bstar double precision,
    mean_motion_dot double precision,
    mean_motion_ddot double precision,
    element_set_no integer,
    rev_at_epoch integer,
    classification text,
    ephemeris_type smallint
);

COMMENT ON TABLE core.orbit_element IS 'Latest CCSDS OMM mean elements per object from CelesTrak GP (SGP4-ready). Only newer epochs replace a row; the history stays in raw.';

CREATE VIEW core.space_object_country AS
SELECT s.norad_id, a.country_code
FROM core.space_object s
JOIN core.country_alias a ON a.namespace = 'celestrak.owner' AND a.code = s.owner_code;

CREATE VIEW core.space_object_organization AS
SELECT s.norad_id, a.organization_id
FROM core.space_object s
JOIN core.organization_alias a ON a.namespace = 'celestrak.owner' AND a.code = s.owner_code;
