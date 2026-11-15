SELECT DISTINCT
    normalize_string(cig) AS cig,
    ruolo,
    codice_fiscale,
    denominazione,
    tipo_soggetto
FROM (
    -- Sostituzione per CIG (Manuale ANAC §5.1): il delta sostituisce il full
    -- per lo specifico CIG; `__source_file` porta l'ordine risorse.
    SELECT *, max(__source_file) OVER (PARTITION BY cig) AS __fonte_cig
    FROM raw_input
) __delta
WHERE __source_file = __fonte_cig
-- Il manuale non dichiara una chiave per questo dataset e la fonte ripete
-- righe identiche: si deduplica sul record intero.

