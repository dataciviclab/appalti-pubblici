-- Macro toolkit: cast_int, cast_double
SELECT
    normalize_string(cig) AS cig,
    safe_date(data_delibera) AS data_delibera,
    safe_date(data_cert_collaudo) AS data_cert_collaudo,
    normalize_string(esito_collaudo) AS esito_collaudo,
    safe_date(data_inizio_oper) AS data_inizio_oper,
    safe_date(data_regolare_esec) AS data_regolare_esec,
    safe_date(data_nomina_coll) AS data_nomina_coll,
    safe_date(data_collaudo_stat) AS data_collaudo_stat,
    cast_int(id_aggiudicazione) AS id_aggiudicazione,
    cast_double(RISERVE_AVANZATE) AS riserve_avanzate,
    cast_double(RISERVE_DEFINITE) AS riserve_definite,
    cast_double(IMPORTO_CONTENZ_RISOLTO) AS importo_contenz_risolto
FROM (
    -- Sostituzione per CIG (Manuale ANAC §5.1): il delta sostituisce il full
    -- per lo specifico CIG. `__source_file` ordina le risorse per last_modified.
    SELECT *, max(__source_file) OVER (PARTITION BY cig) AS __fonte_cig
    FROM raw_input
) __delta
WHERE __source_file = __fonte_cig
  AND cig IS NOT NULL AND TRIM(cig) != ''
-- Dentro la risorsa la fonte puo' ripetere la chiave ufficiale
-- (cig + id_aggiudicazione): vince il collaudo piu' recente.
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY cig, id_aggiudicazione
    ORDER BY data_cert_collaudo DESC NULLS LAST, data_delibera DESC NULLS LAST
) = 1
