-- ANAC Avvio Contratto — MART
-- Un anno per riga: tempi tra stipula, inizio effettivo e termine contrattuale.
SELECT
    EXTRACT(YEAR FROM data_stipula_contratto) AS anno,
    COUNT(*) AS n_contratti,
    COUNT(DISTINCT cig) AS n_cig,
    COUNT(*) FILTER (WHERE data_inizio_effettiva IS NOT NULL) AS n_con_inizio,
    COUNT(*) FILTER (WHERE data_termine_contrattuale IS NOT NULL) AS n_con_termine,
    ROUND(AVG(CASE WHEN date_diff('day', data_stipula_contratto, data_inizio_effettiva)
        BETWEEN -365 AND 3650
        THEN date_diff('day', data_stipula_contratto, data_inizio_effettiva) END), 1)
        AS giorni_medi_stipula_inizio,
    ROUND(AVG(CASE WHEN date_diff('day', data_stipula_contratto, data_termine_contrattuale)
        BETWEEN 0 AND 18250
        THEN date_diff('day', data_stipula_contratto, data_termine_contrattuale) END), 1)
        AS giorni_medi_durata_contrattuale,
    ROUND(AVG(CASE WHEN consegna_sotto_riserva THEN 1 ELSE 0 END) * 100, 1)
        AS quota_consegna_sotto_riserva_pct,
    ROUND(AVG(CASE WHEN consegna_frazionata THEN 1 ELSE 0 END) * 100, 1)
        AS quota_consegna_frazionata_pct
FROM clean_input
WHERE data_stipula_contratto IS NOT NULL
GROUP BY 1
ORDER BY 1
