-- Riepilogo annuale: 1 riga per anno di comunicazione.
SELECT
    anno_comunicazione AS anno,
    COUNT(*) AS n_cig,
    COUNT(DISTINCT cf_amministrazione_appaltante) AS n_stazioni_appaltanti,
    ROUND(SUM(importo_lotto), 0) AS importo_totale,
    ROUND(AVG(importo_lotto), 0) AS importo_medio,
    ROUND(MEDIAN(importo_lotto), 0) AS importo_mediano,
    SUM(CASE WHEN fascia_importo = 'micro' THEN 1 ELSE 0 END) AS n_micro,
    SUM(CASE WHEN fascia_importo = 'piccola' THEN 1 ELSE 0 END) AS n_piccola,
    SUM(CASE WHEN fascia_importo = 'media' THEN 1 ELSE 0 END) AS n_media,
    SUM(CASE WHEN fascia_importo = 'sopra_40k' THEN 1 ELSE 0 END) AS n_sopra_40k,
    SUM(CASE WHEN flag_sopra_140k THEN 1 ELSE 0 END) AS n_sopra_140k,
    SUM(CASE WHEN fascia_importo = 'non_valido' THEN 1 ELSE 0 END) AS n_non_valido
FROM clean_input
WHERE anno_comunicazione IS NOT NULL
GROUP BY anno_comunicazione
ORDER BY anno_comunicazione
