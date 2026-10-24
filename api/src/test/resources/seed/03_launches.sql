INSERT INTO core.mission_agency (mission_ll2_id, organization_id) VALUES (822, 44);

INSERT INTO raw.payload (source, endpoint, params, fetched_at, content_hash, body)
VALUES
    (
        'launch-library',
        'https://ll.thespacedevs.com/2.3.0/launches/',
        '{"mode": "normal", "limit": "100", "offset": "0", "ordering": "last_updated"}',
        '2026-10-16 06:50:30+00',
        '6d1f0c9a2b7e4f31a8c5d2e9b0f7a6c3d4e5f60718293a4b5c6d7e8f90a1b2c3',
        '{"results": []}'
    ),
    (
        'launch-library',
        'https://ll.thespacedevs.com/2.3.0/launches/',
        '{"mode": "normal", "limit": "100", "offset": "100", "ordering": "last_updated"}',
        '2026-10-16 07:15:40+00',
        '0a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5061728394a5b6c7d8e9f',
        '{"results": []}'
    );

INSERT INTO core.source_record (entity, entity_key, payload_id, recorded_at)
SELECT 'core.launch', '2dd0f8af-5182-4a97-b8b4-4846983ddf59', p.id, p.fetched_at
FROM raw.payload p
WHERE p.source = 'launch-library';
