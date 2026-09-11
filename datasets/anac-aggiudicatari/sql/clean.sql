-- ANAC Aggiudicatari — CLEAN
-- Macro toolkit: normalize_string, cast_bigint
SELECT
    normalize_string(cig) AS cig,
    ruolo,
    codice_fiscale,
    denominazione,
    tipo_soggetto,
    cast_bigint(id_aggiudicazione) AS id_aggiudicazione
FROM raw_input
