SELECT
    normalize_string(cig) AS cig,
    id_subappalto,
    cf_subappaltante,
    safe_date(data_autorizzazione) AS data_autorizzazione,
    oggetto,
    cod_categoria,
    descrizione_categoria,
    classe_importo,
    descrizione_tipo_categoria,
    cod_cpv,
    descrizione_cpv,
    codice_fiscale,
    denominazione,
    ruolo,
    tipo_soggetto
FROM (
    -- Sostituzione per CIG (Manuale ANAC §5.1): il delta sostituisce il full
    -- per lo specifico CIG; `__source_file` porta l'ordine risorse.
    SELECT *, max(__source_file) OVER (PARTITION BY cig) AS __fonte_cig
    FROM raw_input
) __delta
WHERE __source_file = __fonte_cig
-- Dentro la risorsa la fonte puo' ripetere la chiave ufficiale: vince la
-- comunicazione piu' recente.
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY cig, id_subappalto, cod_categoria, codice_fiscale
    ORDER BY data_autorizzazione DESC NULLS LAST
) = 1
