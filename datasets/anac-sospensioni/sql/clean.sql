-- ANAC Sospensioni — CLEAN
-- Macro toolkit: normalize_string, cast_bigint
-- Date plausibili: 2000 -> anno corrente + 1. Il resto diventa NULL.
WITH src AS (
    SELECT
        normalize_string(cig) AS cig,
        safe_date(NULLIF(data_sospensione, '0001-01-01')) AS d_sospensione,
        safe_date(NULLIF(data_ripresa, '0001-01-01')) AS d_ripresa,
        normalize_string(descrizione_motivo) AS descrizione_motivo,
        cast_bigint(id_aggiudicazione) AS id_aggiudicazione
    FROM (
        -- Sostituzione per CIG (Manuale ANAC §5.1): il delta sostituisce il
        -- full per lo specifico CIG; `__source_file` porta l'ordine risorse.
        SELECT *, max(__source_file) OVER (PARTITION BY cig) AS __fonte_cig
        FROM raw_input
    ) __delta
    WHERE __source_file = __fonte_cig
    -- Dentro la risorsa la fonte puo' ripetere la chiave ufficiale: vince la
    -- comunicazione piu' recente.
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY cig, id_aggiudicazione, data_sospensione, descrizione_motivo
        ORDER BY d_sospensione DESC NULLS LAST
    ) = 1
)

SELECT
    cig,
    CASE WHEN d_sospensione BETWEEN DATE '2000-01-01' AND CURRENT_DATE
        THEN d_sospensione END AS data_sospensione,
    CASE WHEN d_ripresa BETWEEN DATE '2000-01-01' AND CURRENT_DATE
        THEN d_ripresa END AS data_ripresa,
    descrizione_motivo,
    id_aggiudicazione
FROM src
WHERE cig IS NOT NULL
