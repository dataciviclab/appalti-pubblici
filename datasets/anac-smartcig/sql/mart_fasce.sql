-- Distribuzione per fascia di importo: quante procedure e quanta spesa.
-- Esclude gli importi non validi (NULL, zero, negativi): sono 809 nel 2025,
-- quasi tutti storni/correzioni, e falserebbero le quote.
SELECT
    fascia_importo,
    COUNT(*) AS n_cig,
    ROUND(SUM(importo_lotto), 0) AS importo_totale,
    ROUND(AVG(importo_lotto), 0) AS importo_medio,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS quota_n_pct,
    ROUND(100.0 * SUM(importo_lotto) / SUM(SUM(importo_lotto)) OVER (), 2) AS quota_importo_pct
FROM clean_input
WHERE fascia_importo != 'non_valido'
GROUP BY fascia_importo
ORDER BY n_cig DESC
