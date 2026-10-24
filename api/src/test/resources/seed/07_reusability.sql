INSERT INTO core.launch_vehicle (ll2_id, name, full_name, variant, family, name_ja, name_ja_source)
VALUES (164, 'Falcon 9', 'Falcon 9 Block 5', 'Block 5', 'Falcon', 'ファルコン9 ブロック5', 'https://ja.wikipedia.org/wiki/ファルコン9');

INSERT INTO core.launch (ll2_id, name, slug, launch_designator, net, net_precision, window_start, window_end, status_id, status, status_name, failure_reason, provider_org_id, vehicle_ll2_id, pad_ll2_id, mission_ll2_id, source_updated_at)
VALUES
    ('a1f0e7c2-0b5d-4c41-9a43-5f2a9d1e0001', 'Falcon 9 Block 5 | Starlink Group 6-35', 'falcon-9-block-5-starlink-group-6-35', '2024-001', '2024-01-03 03:44:00+00', NULL, '2024-01-03 03:44:00+00', '2024-01-03 03:44:00+00', 3, 'Success', 'Launch Successful', NULL, 124, 164, 4, NULL, '2024-01-04 00:00:00+00'),
    ('a1f0e7c2-0b5d-4c41-9a43-5f2a9d1e0002', 'Falcon 9 Block 5 | Starlink Group 12-1', 'falcon-9-block-5-starlink-group-12-1', '2025-040', '2025-03-01 10:00:00+00', NULL, '2025-03-01 10:00:00+00', '2025-03-01 10:00:00+00', 3, 'Success', 'Launch Successful', NULL, 124, 164, 4, NULL, '2025-03-02 00:00:00+00'),
    ('a1f0e7c2-0b5d-4c41-9a43-5f2a9d1e0003', 'Falcon 9 Block 5 | Starlink Group 12-9', 'falcon-9-block-5-starlink-group-12-9', '2025-120', '2025-06-01 12:00:00+00', NULL, '2025-06-01 12:00:00+00', '2025-06-01 12:00:00+00', 3, 'Success', 'Launch Successful', NULL, 124, 164, 4, NULL, '2025-06-02 00:00:00+00'),
    ('a1f0e7c2-0b5d-4c41-9a43-5f2a9d1e0004', 'Falcon 9 Block 5 | NROL-140', 'falcon-9-block-5-nrol-140', '2025-190', '2025-09-01 08:00:00+00', NULL, '2025-09-01 08:00:00+00', '2025-09-01 08:00:00+00', 3, 'Success', 'Launch Successful', NULL, 124, 164, 4, NULL, '2025-09-02 00:00:00+00');

INSERT INTO core.launcher (ll2_id, serial_number, is_placeholder, flight_proven, status, vehicle_ll2_id, flights, attempted_landings, successful_landings, first_launch_at, last_launch_at, fastest_turnaround)
VALUES
    (1, 'B1067', false, true, 'active', 164, 3, 3, 2, '2024-01-03 03:44:00+00', '2025-06-01 12:00:00+00', interval '92 days 2 hours'),
    (2, 'B1080', false, false, 'expended', 164, 1, 0, 0, '2025-09-01 08:00:00+00', '2025-09-01 08:00:00+00', NULL),
    (3, 'Unknown F9', true, NULL, 'N/A', 164, NULL, NULL, NULL, NULL, NULL, NULL);

INSERT INTO core.landing (ll2_id, launcher_ll2_id, stage_type, launcher_flight_number, reused, attempt, success, previous_flight_at, turnaround, type_abbrev, type_name, location_name, location_abbrev, downrange_km)
VALUES
    (101, 1, 'Core', 1, false, true, true, NULL, NULL, 'ASDS', 'Autonomous Spaceport Drone Ship', 'A Shortfall of Gravitas', 'ASOG', 600),
    (102, 1, 'Core', 2, true, true, true, '2024-01-03 03:44:00+00', interval '423 days 6 hours 16 minutes', 'ASDS', 'Autonomous Spaceport Drone Ship', 'A Shortfall of Gravitas', 'ASOG', 610),
    (103, 1, 'Core', 3, true, true, false, '2025-03-01 10:00:00+00', interval '92 days 2 hours', 'RTLS', 'Return to Launch Site', 'Landing Zone 1', 'LZ-1', 0.3),
    (104, 2, 'Core', 1, false, false, NULL, NULL, NULL, 'EXP', 'Expended', NULL, NULL, NULL),
    (105, 1, 'Core', 4, true, true, NULL, '2025-06-01 12:00:00+00', interval '2000 days', 'ASDS', 'Autonomous Spaceport Drone Ship', 'A Shortfall of Gravitas', 'ASOG', NULL);
