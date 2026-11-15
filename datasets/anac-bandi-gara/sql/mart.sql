-- Riepilogo annuale leggero: 1 riga per anno per la dashboard overview.
-- Le tabelle esistenti (mart_top_stazioni, mart_trend_pnrr, ecc.) restano per drill-down.
--
-- Gli importi con flag_importo_sospetto (>= 1 mld su un singolo lotto) restano
-- fuori dalle aggregazioni: includerli gonfia il totale del 18% sulla serie
-- 2016-2025. Il loro peso e' dichiarato in n_importi_sospetti / importo_sospetti.
SELECT
    anno_pubblicazione AS anno,
    COUNT(*) AS n_lotti,
    COUNT(DISTINCT cig) AS n_cig,
    COUNT(DISTINCT cf_amministrazione_appaltante) AS n_stazioni_appaltanti,
    COUNT(DISTINCT oggetto_principale_contratto) AS n_settori,
    ROUND(SUM(importo_lotto) FILTER (WHERE NOT flag_importo_sospetto), 0) AS importo_totale,
    ROUND(AVG(importo_lotto) FILTER (WHERE NOT flag_importo_sospetto), 0) AS importo_medio,
    ROUND(MEDIAN(importo_lotto) FILTER (WHERE NOT flag_importo_sospetto), 0) AS importo_mediano,
    SUM(CASE WHEN flag_importo_sospetto THEN 1 ELSE 0 END) AS n_importi_sospetti,
    ROUND(SUM(CASE WHEN flag_importo_sospetto THEN importo_lotto ELSE 0 END), 0) AS importo_sospetti,
    SUM(CASE WHEN flag_pnrr = TRUE THEN 1 ELSE 0 END) AS n_pnrr,
    ROUND(SUM(CASE WHEN flag_pnrr = TRUE AND NOT flag_importo_sospetto THEN importo_lotto ELSE 0 END), 0) AS importo_pnrr,
    SUM(CASE WHEN ESITO = 'AGGIUDICATA' THEN 1 ELSE 0 END) AS n_aggiudicati,
    SUM(CASE WHEN ESITO != 'AGGIUDICATA' OR ESITO IS NULL THEN 1 ELSE 0 END) AS n_non_aggiudicati,
    ROUND(SUM(CASE WHEN ESITO = 'AGGIUDICATA' AND NOT flag_importo_sospetto THEN importo_lotto ELSE 0 END), 0) AS importo_aggiudicati
FROM clean_input
GROUP BY anno_pubblicazione
ORDER BY anno_pubblicazione
