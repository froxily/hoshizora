INSERT INTO core.aurora_forecast
    (observed_at, forecast_at, north_max_percent, south_max_percent, north_boundary_lat, south_boundary_lat)
VALUES
    ('2026-10-14 06:00:00+00', '2026-10-14 07:00:00+00', 30, 12, 60, -58),
    ('2026-10-15 15:00:00+00', '2026-10-15 16:00:00+00', 18, 9, 65, NULL),
    ('2026-10-16 08:00:00+00', '2026-10-16 08:55:00+00', 26, 14, 64, -51);

INSERT INTO core.aurora_cell (longitude, latitude, probability_percent, observed_at)
VALUES
    (140, 67, 26, '2026-10-16 08:00:00+00'),
    (141, 66, 12, '2026-10-16 08:00:00+00'),
    (143, 44, 1, '2026-10-16 08:00:00+00'),
    (0, -51, 14, '2026-10-16 08:00:00+00'),
    (1, -50, 3, '2026-10-16 08:00:00+00');
