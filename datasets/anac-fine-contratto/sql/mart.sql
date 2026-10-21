-- ANAC Fine Contratto — MART
-- Un anno per riga: conclusi, risoluzioni e interruzioni anticipate.
SELECT
    EXTRACT(YEAR FROM data_effettiva_ultimazione) AS anno,
    COUNT(*) AS n_conclusi,
    COUNT(DISTINCT cig) AS n_cig,
    COUNT(*) FILTER (WHERE motivo_risoluzione IS NOT NULL) AS n_con_risoluzione,
    COUNT(*) FILTER (WHERE motivo_interruzione_anticipata IS NOT NULL) AS n_con_interruzione,
    COUNT(*) FILTER (WHERE data_conclusione_anticipata IS NOT NULL) AS n_conclusione_anticipata,
    ROUND(COUNT(*) FILTER (WHERE motivo_risoluzione IS NOT NULL) * 100.0
        / NULLIF(COUNT(*), 0), 2) AS quota_risoluzione_pct,
    ROUND(COUNT(*) FILTER (WHERE motivo_interruzione_anticipata IS NOT NULL) * 100.0
        / NULLIF(COUNT(*), 0), 2) AS quota_interruzione_pct
FROM clean_input
WHERE data_effettiva_ultimazione IS NOT NULL
GROUP BY 1
ORDER BY 1
