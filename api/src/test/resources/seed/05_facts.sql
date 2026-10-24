INSERT INTO facts.template (key, module, text_en, text_ja, min_score) VALUES
(
    'near-earth.closest_this_week',
    'near-earth',
    'This week''s closest asteroid, {designation}, passes at {distance_ld, number}× the Earth–Moon distance.',
    '今週地球に最も近づく小惑星{designation}は、地球と月の距離の{distance_ld, number}倍まで接近します。',
    0.5
),
(
    'launches.program_year',
    'launches',
    '{program} carried out {count, number, integer} launches in {year}.',
    '{year}年、{program}は{count, number, integer}回の打ち上げを行いました。',
    0.5
),
(
    'home.debris_in_orbit',
    'home',
    'About {debris, number, compact} pieces of tracked debris circle Earth.',
    '地球の周りには、追跡されているデブリが約{debris, number, compact}個あります。',
    0.5
),
(
    'sun.strongest_flare_month',
    'sun',
    'This month''s strongest flare, class {class}, peaked on {date, date}.',
    '今月最も強いフレアは、{date, date}にピークを迎えた{class}クラスです。',
    0.5
),
(
    'near-earth.moon_distance',
    'near-earth',
    'The Moon orbits on average {distance_km, number, integer} km from Earth.',
    '月は地球から平均{distance_km, number, integer}kmの距離を回っています。',
    0
);

INSERT INTO facts.fact (template_key, entity_type, entity_key, params, score, kind, source_refs, citation_url, generated_at, valid_until)
VALUES
(
    'near-earth.closest_this_week', 'small_body', '2026 TS',
    '{"designation": "2026 TS", "distance_ld": 2.4}', 0.9, 'computed',
    '[{"entity": "core.close_approach", "key": "2026 TS|Earth|2026-10-18 06:16:00"}]', NULL,
    '2026-10-16 07:30:00+00', '2026-10-23 00:00:00+00'
),
(
    'launches.program_year', 'program', 'japan',
    '{"program": {"en": "Japan", "ja": "日本"}, "count": 6, "year": "2017"}', 0.7, 'computed',
    '[{"entity": "mart.launch_cadence_yearly", "key": "program|japan|2017"}]', NULL,
    '2026-10-16 07:30:00+00', NULL
),
(
    'home.debris_in_orbit', NULL, NULL,
    '{"debris": 12550}', 0.6, 'computed',
    '[]', NULL,
    '2026-10-16 07:30:00+00', NULL
),
(
    'sun.strongest_flare_month', NULL, NULL,
    '{"class": "M6.4", "date": "2026-10-10"}', 0.8, 'computed',
    '[]', NULL,
    '2026-10-16 07:30:00+00', '2026-11-01 00:00:00+00'
),
(
    'near-earth.moon_distance', NULL, NULL,
    '{"distance_km": 384400}', 0.5, 'curated',
    '[]', 'https://nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html',
    '2026-10-16 07:30:00+00', NULL
),
(
    'launches.program_year', 'program', 'usa',
    '{"program": {"en": "the United States", "ja": "アメリカ"}, "count": 0, "year": "2026"}', 0.1, 'computed',
    '[]', NULL,
    '2026-10-16 07:30:00+00', NULL
),
(
    'near-earth.closest_this_week', 'small_body', '2026 TN77',
    '{"designation": "2026 TN77", "distance_ld": 0.1}', 0.95, 'computed',
    '[]', NULL,
    '2026-10-09 07:30:00+00', '2026-10-15 00:00:00+00'
);

INSERT INTO raw.payload (source, endpoint, params, fetched_at, content_hash, body)
VALUES (
    'jpl', 'https://ssd-api.jpl.nasa.gov/cad.api', '{"date-min": "2026-10-01", "date-max": "2026-12-31"}',
    '2026-10-16 06:01:00+00', '9e8d7c6b5a4f3e2d1c0b9a8f7e6d5c4b3a2f1e0d9c8b7a6f5e4d3c2b1a0f9e8d', '{"data": []}'
);

INSERT INTO core.source_record (entity, entity_key, payload_id, recorded_at)
SELECT 'core.close_approach', '2026 TS|Earth|2026-10-18 06:16:00', p.id, p.fetched_at
FROM raw.payload p
WHERE p.source = 'jpl';
