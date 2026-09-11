SELECT
    normalize_string(cig) AS cig,
    ruolo,
    codice_fiscale,
    denominazione,
    tipo_soggetto
FROM raw_input
