CREATE TABLE core.geomagnetic_index (
    index text NOT NULL,
    observed_at timestamptz NOT NULL,
    value double precision NOT NULL,
    a_running integer,
    station_count smallint,
    PRIMARY KEY (index, observed_at)
);

COMMENT ON TABLE core.geomagnetic_index IS 'Geomagnetic indices from NOAA SWPC. index kp: planetary Kp per 3-hour interval starting at observed_at; estimates are revised in place.';

CREATE TABLE core.space_weather_event (
    kind text NOT NULL CHECK (kind IN ('xray_flare', 'alert')),
    external_id text NOT NULL,
    begin_at timestamptz,
    peak_at timestamptz,
    end_at timestamptz,
    event_class text,
    peak_flux_wm2 double precision,
    satellite smallint,
    product_id text,
    message text,
    PRIMARY KEY (kind, external_id)
);

CREATE INDEX space_weather_event_begin_idx ON core.space_weather_event (kind, begin_at);

COMMENT ON TABLE core.space_weather_event IS 'GOES X-ray flares (event_class such as M1.2, peak flux in W/m² for 0.1–0.8 nm) and SWPC alerts, watches and warnings (product_id, message).';

CREATE TABLE core.solar_wind_sample (
    observed_at timestamptz PRIMARY KEY,
    plasma_spacecraft text,
    speed_kms double precision,
    density_cm3 double precision,
    temperature_k double precision,
    mag_spacecraft text,
    bt_nt double precision,
    bz_gsm_nt double precision
);

COMMENT ON TABLE core.solar_wind_sample IS 'Real-time solar wind at L1, one row per minute, taken only from the spacecraft SWPC marks active for that minute.';
