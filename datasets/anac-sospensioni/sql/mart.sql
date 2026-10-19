-- ANAC Sospensioni — MART
-- Un anno × motivo per riga: quante sospensioni e per quanti giorni.
-- Le durate oltre 10 anni sono trattate come anomalie di codifica e
-- escluse da medie/totali (restano contate in n_durata_anomala).
SELECT
    EXTRACT(YEAR FROM data_sospensione) AS anno,
    descrizione_motivo,
    COUNT(*) AS n_sospensioni,
    COUNT(DISTINCT cig) AS n_cig,
    COUNT(*) FILTER (WHERE data_ripresa IS NOT NULL) AS n_con_ripresa,
    COUNT(*) FILTER (WHERE data_ripresa >= data_sospensione
        AND date_diff('day', data_sospensione, data_ripresa) > 3650) AS n_durata_anomala,
    ROUND(AVG(CASE WHEN data_ripresa >= data_sospensione
        AND date_diff('day', data_sospensione, data_ripresa) <= 3650
        THEN date_diff('day', data_sospensione, data_ripresa) END), 1) AS giorni_medi,
    MAX(CASE WHEN data_ripresa >= data_sospensione
        AND date_diff('day', data_sospensione, data_ripresa) <= 3650
        THEN date_diff('day', data_sospensione, data_ripresa) END) AS giorni_max,
    SUM(CASE WHEN data_ripresa >= data_sospensione
        AND date_diff('day', data_sospensione, data_ripresa) <= 3650
        THEN date_diff('day', data_sospensione, data_ripresa) ELSE 0 END) AS giorni_totali
FROM clean_input
WHERE data_sospensione IS NOT NULL
GROUP BY 1, 2
ORDER BY anno DESC, n_sospensioni DESC
