SELECT
    f.month,
    sum(f.flares) AS total,
    coalesce(sum(f.flares) FILTER (WHERE f.class_letter = 'A'), 0) AS a,
    coalesce(sum(f.flares) FILTER (WHERE f.class_letter = 'B'), 0) AS b,
    coalesce(sum(f.flares) FILTER (WHERE f.class_letter = 'C'), 0) AS c,
    coalesce(sum(f.flares) FILTER (WHERE f.class_letter = 'M'), 0) AS m,
    coalesce(sum(f.flares) FILTER (WHERE f.class_letter = 'X'), 0) AS x,
    max(f.max_peak_flux_wm2) AS max_peak_flux_wm2,
    (array_agg(f.strongest_class ORDER BY f.max_peak_flux_wm2 DESC NULLS LAST))[1] AS strongest_class
FROM mart.flare_counts_monthly f
WHERE f.month >= :from AND f.month < :to
GROUP BY f.month
ORDER BY f.month
