INSERT INTO core.exoplanet (name, host_name, star_count, planet_count, discovery_method, discovery_year, discovery_facility, discovery_locale, orbital_period_days, semi_major_axis_au, radius_earth, mass_earth, eccentricity, equilibrium_temp_k, insolation_earth, star_temp_k, star_radius_sun, star_mass_sun, distance_pc, controversial)
VALUES
    ('Proxima Cen b', 'Proxima Cen', 3, 2, 'Radial Velocity', 2016, 'European Southern Observatory', 'ground', 11.18465, 0.04848, 1.02, 1.055, 0.0, 218.0, 0.641, 2900.0, 0.141, 0.1221, 1.30119, false),
    ('TRAPPIST-1 e', 'TRAPPIST-1', 1, 7, 'Transit', 2017, 'Multiple Observatories', 'multiple locales', 6.099043, 0.02925, 0.92, 0.692, 0.0051, 249.7, 0.646, 2566.0, 0.119, 0.0898, 12.42988881, false),
    ('Kepler-452 b', 'Kepler-452', 1, 1, 'Transit', 2015, 'Kepler', 'space', 384.843, 1.046, 1.63, NULL, NULL, 265.0, 1.1, 5757.0, 1.11, 1.037, 551.727, true),
    ('HAT-P-47 b', 'HAT-P-47', 1, 1, 'Transit', 2026, 'Transiting Exoplanet Survey Satellite (TESS)', 'space', 4.7322, 0.0574, 14.71739166, 65.0, 0.0, 1605.0, 379.567, 6703.0, 1.515, 1.387, 282.096, false),
    ('BD-06 1339 b', 'BD-06 1339', 1, 2, 'Radial Velocity', 2013, 'La Silla Observatory', 'ground', 3.8728, 0.0428, NULL, 6.3, 0.0, NULL, 51.8934, 4040.0, 0.69, 0.7, 20.2695, true),
    ('OGLE-2016-BLG-1227L b', 'OGLE-2016-BLG-1227L', 1, 1, 'Microlensing', 2020, 'Optical Gravitational Lensing Experiment (OGLE)', 'ground', NULL, 3.4, 13.9, 250.0, NULL, NULL, NULL, NULL, NULL, 0.1, NULL, false);

INSERT INTO raw.payload (source, endpoint, params, fetched_at, content_hash, body)
VALUES (
    'exoplanet-archive',
    'https://exoplanetarchive.ipac.caltech.edu/TAP/sync',
    '{"format": "json", "query": "select pl_name from pscomppars order by pl_name"}',
    '2026-10-19 12:00:00+00',
    '9b1f6c2d4e8a7f3c5d1e9b0a2c4f6e8d0b2a4c6e8f0a1b3c5d7e9f1a3b5c7d9e',
    '[]'
);

INSERT INTO core.source_record (entity, entity_key, payload_id, recorded_at)
SELECT 'core.exoplanet', 'Proxima Cen b', p.id, p.fetched_at
FROM raw.payload p
WHERE p.source = 'exoplanet-archive';
