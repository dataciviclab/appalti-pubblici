-- mart_territorio.sql — distribuzione territoriale delle stazioni appaltanti
SELECT
    provincia,
    COUNT(*) AS n_sa,
    COUNT(*) FILTER (WHERE stato = 'ATTIVO') AS n_attive,
    COUNT(DISTINCT citta) AS n_comuni,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS quota_pct
FROM clean_input
WHERE provincia IS NOT NULL AND TRIM(provincia) != ''
GROUP BY provincia
ORDER BY n_sa DESC
