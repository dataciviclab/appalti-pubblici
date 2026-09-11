-- Top subappalti: aggregazione per categoria e impresa
SELECT
    descrizione_categoria,
    descrizione_cpv,
    codice_fiscale,
    denominazione,
    ruolo,
    COUNT(DISTINCT cig) AS n_cig,
    COUNT(DISTINCT id_subappalto) AS n_subappalti,
    COUNT(*) AS n_record
FROM clean_input
GROUP BY descrizione_categoria, descrizione_cpv, codice_fiscale, denominazione, ruolo
ORDER BY n_subappalti DESC
