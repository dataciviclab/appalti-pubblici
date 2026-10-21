-- ANAC Varianti — MART
-- Un anno × motivo per riga: quante varianti e quante con proroga.
SELECT
    EXTRACT(YEAR FROM data_approvazione_variante) AS anno,
    motivo_variante,
    COUNT(*) AS n_varianti,
    COUNT(DISTINCT id_variante) AS n_varianti_distinte,
    COUNT(DISTINCT cig) AS n_cig,
    COUNT(DISTINCT cig) FILTER (WHERE cig_proroga IS NOT NULL) AS n_cig_con_proroga,
    ROUND(COUNT(*) FILTER (WHERE cig_proroga IS NOT NULL) * 100.0
        / NULLIF(COUNT(*), 0), 2) AS quota_con_proroga_pct
FROM clean_input
WHERE data_approvazione_variante IS NOT NULL
GROUP BY 1, 2
ORDER BY anno DESC, n_varianti DESC
