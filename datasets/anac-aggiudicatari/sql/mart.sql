-- Top aggiudicatari: aggregazione perimpresa (non SELECT * dal clean)
SELECT
    codice_fiscale,
    denominazione,
    tipo_soggetto,
    ruolo,
    COUNT(DISTINCT cig) AS n_cig,
    COUNT(DISTINCT id_aggiudicazione) AS n_aggiudicazioni,
    COUNT(*) AS n_record
FROM clean_input
WHERE codice_fiscale IS NOT NULL
  AND codice_fiscale != ''
GROUP BY codice_fiscale, denominazione, tipo_soggetto, ruolo
ORDER BY n_cig DESC
