-- ANAC Aggiudicatari — CLEAN
-- Macro toolkit: normalize_string, cast_bigint
SELECT
    normalize_string(cig) AS cig,
    ruolo,
    codice_fiscale,
    denominazione,
    tipo_soggetto,
    cast_bigint(id_aggiudicazione) AS id_aggiudicazione
FROM (
    -- Sostituzione per CIG (Manuale ANAC §5.1): il delta sostituisce il full
    -- per lo specifico CIG; `__source_file` porta l'ordine risorse.
    SELECT *, max(__source_file) OVER (PARTITION BY cig) AS __fonte_cig
    FROM raw_input
) __delta
WHERE __source_file = __fonte_cig
  -- 3 righe dei delta hanno id_aggiudicazione non numerico: la chiave e' NULL
  AND TRY_CAST(id_aggiudicazione AS BIGINT) IS NOT NULL
-- Dentro la risorsa la chiave ufficiale (cig + id_aggiudicazione + codice_fiscale)
-- puo' ripetersi: si tiene una riga sola, ordine deterministico.
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY cig, id_aggiudicazione, codice_fiscale
    ORDER BY ruolo NULLS LAST, denominazione NULLS LAST
) = 1
