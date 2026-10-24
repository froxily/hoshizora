INSERT INTO core.data_source (
    slug, name_en, name_ja, description_en, description_ja, credit_en, credit_ja,
    license_en, license_ja, license_url, homepage_url, cadence_en, cadence_ja, update_interval
) VALUES
(
    'launch-library',
    'Launch Library 2 (The Space Devs)',
    'Launch Library 2（The Space Devs）',
    'Launches, launch vehicles, pads, missions and agencies worldwide.',
    '世界の打ち上げ、ロケット、射場、ミッション、宇宙機関のデータです。',
    'Launch data: The Space Devs, Launch Library 2 (thespacedevs.com)',
    '打ち上げデータ：The Space Devs「Launch Library 2」（thespacedevs.com）',
    'No license or attribution requirement is published. Credited as a courtesy.',
    'ライセンスや出典表示の条件は公開されていません。感謝を込めて出典を表示しています。',
    NULL,
    'https://thespacedevs.com/llapi',
    'Incremental by last change, at most 15 requests per hour.',
    '最終更新日時による差分取得（1時間あたり最大15リクエスト）',
    interval '1 hour'
),
(
    'celestrak',
    'CelesTrak SATCAT and GP',
    'CelesTrak（SATCATとGP軌道要素）',
    'Every catalogued object, with its owner, launch and decay dates, and current orbital elements.',
    'カタログに登録されたすべての物体の所有者、打ち上げ日、落下日と最新の軌道要素です。',
    'Orbital data: CelesTrak (celestrak.org)',
    '軌道データ：CelesTrak（celestrak.org）',
    'No attribution requirement is stated. The data is freely available.',
    '出典表示の条件は示されていません。データは自由に利用できます。',
    NULL,
    'https://celestrak.org',
    'SATCAT at most every 12 hours, active orbital elements at most every 2 hours.',
    'SATCATは最短12時間ごと、運用中の軌道要素は最短2時間ごと',
    interval '2 hours'
),
(
    'jpl',
    'NASA/JPL Solar System Dynamics',
    'NASAジェット推進研究所（JPL）Solar System Dynamics',
    'Close approaches of asteroids and comets to Earth, and the Sentry impact-monitoring list.',
    '小惑星や彗星の地球への接近と、衝突監視システムSentryの監視対象です。',
    'Small-body data: NASA/JPL Solar System Dynamics (SBDB Close Approach and Sentry APIs)',
    '小天体データ：NASAジェット推進研究所（JPL）Solar System Dynamics（SBDB Close Approach API、Sentry API）',
    'No license or attribution requirement is stated.',
    'ライセンスや出典表示の条件は示されていません。',
    NULL,
    'https://ssd.jpl.nasa.gov',
    'A rolling close-approach window and Sentry, every 12 hours.',
    '接近予測とSentryを12時間ごとに更新',
    interval '12 hours'
),
(
    'swpc',
    'NOAA Space Weather Prediction Center',
    'アメリカ海洋大気庁（NOAA）宇宙天気予報センター',
    'Planetary Kp index, GOES X-ray flares and real-time solar wind at L1.',
    '惑星Kp指数、GOES衛星が観測したX線フレア、L1点のリアルタイム太陽風です。',
    'Space weather data: NOAA Space Weather Prediction Center (SWPC)',
    '宇宙天気データ：アメリカ海洋大気庁（NOAA）宇宙天気予報センター（SWPC）',
    'Open NOAA data. NOAA asks for attribution and does not endorse this site.',
    'NOAAのオープンデータです。NOAAは出典の表示を求めており、本サイトを推奨するものではありません。',
    NULL,
    'https://www.swpc.noaa.gov',
    'Kp and flares hourly, solar wind every 6 hours, with conditional requests.',
    'Kp指数とフレアは1時間ごと、太陽風は6時間ごと（条件付きリクエスト）',
    interval '1 hour'
),
(
    'reference',
    'Curated reference data',
    '整理済みの参照データ',
    'Country names from Unicode CLDR, CelesTrak owner codes and organization curation.',
    'Unicode CLDRの国名、CelesTrakの所有者コード、組織情報の整理データです。',
    'Country names: Unicode CLDR. Owner codes: CelesTrak. Curation: Hoshizora.',
    '国名：Unicode CLDR、所有者コード：CelesTrak、整理：Hoshizora',
    'Unicode CLDR data is licensed under the Unicode License v3.',
    'Unicode CLDRのデータはUnicode License v3で提供されています。',
    'https://www.unicode.org/license.txt',
    'https://cldr.unicode.org',
    'On change.',
    '変更時',
    NULL
);

INSERT INTO raw.ingest_run (source, started_at, finished_at, status, requests, not_modified, payloads_new, rows_in, rows_upserted)
VALUES
    ('swpc', '2026-10-16 07:00:00+00', '2026-10-16 07:00:12+00', 'succeeded', 5, 2, 3, 1400, 120),
    ('celestrak', '2026-10-15 20:00:00+00', '2026-10-15 20:01:30+00', 'succeeded', 2, 0, 2, 87825, 312),
    ('jpl', '2026-10-16 06:00:00+00', '2026-10-16 06:03:00+00', 'succeeded', 3, 0, 1, 900, 14),
    ('launch-library', '2026-10-16 06:50:00+00', '2026-10-16 06:51:00+00', 'partial', 7, 0, 7, 700, 650),
    ('launch-library', '2026-10-16 07:15:00+00', NULL, 'running', 0, 0, 0, 0, 0),
    ('reference', '2026-10-14 09:00:00+00', '2026-10-14 09:00:05+00', 'succeeded', 0, 0, 1, 900, 0);

INSERT INTO raw.fetch (run_id, source, endpoint, requested_at, http_status, duration_ms)
SELECT r.id, r.source, f.endpoint, f.requested_at, f.http_status, 120
FROM (
    VALUES
        ('swpc', 'https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json', timestamptz '2026-10-16 07:00:03+00', 304),
        ('celestrak', 'https://celestrak.org/NORAD/elements/gp.php', timestamptz '2026-10-15 20:01:00+00', 200),
        ('jpl', 'https://ssd-api.jpl.nasa.gov/cad.api', timestamptz '2026-10-16 06:01:00+00', 200),
        ('launch-library', 'https://ll.thespacedevs.com/2.3.0/launches/', timestamptz '2026-10-16 06:50:30+00', 200),
        ('launch-library', 'https://ll.thespacedevs.com/2.3.0/launches/', timestamptz '2026-10-16 06:50:45+00', 429)
) AS f (source, endpoint, requested_at, http_status)
JOIN raw.ingest_run r ON r.source = f.source AND r.status IN ('succeeded', 'partial');
